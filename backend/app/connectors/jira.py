from typing import List, Optional
import httpx
from datetime import datetime

from app.connectors.base import ITSMConnector, Ticket, TicketFilter, CreateTicketRequest, UpdateTicketRequest, ConnectionStatus

STATUS_MAP = {
    "To Do": "open", "In Progress": "in_progress", "Done": "closed",
    "Blocked": "blocked", "In Review": "in_review",
}
PRIORITY_MAP = {"Highest": "P1", "High": "P2", "Medium": "P3", "Low": "P4", "Lowest": "P5"}


class JiraConnector(ITSMConnector):
    def __init__(self, site_url: str, email: str, api_token: str):
        self.base_url = f"{site_url.rstrip('/')}/rest/api/3"
        self.auth = (email, api_token)
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}

    def _client(self):
        return httpx.AsyncClient(auth=self.auth, headers=self.headers, timeout=30)

    def _parse_ticket(self, issue: dict) -> Ticket:
        fields = issue.get("fields", {})
        assignee = fields.get("assignee") or {}
        reporter = fields.get("reporter") or {}
        priority = fields.get("priority") or {}
        status = fields.get("status") or {}
        project = fields.get("project") or {}
        return Ticket(
            id=issue["key"],
            title=fields.get("summary", ""),
            description=str(fields.get("description") or ""),
            status=STATUS_MAP.get(status.get("name", ""), status.get("name", "unknown")),
            priority=PRIORITY_MAP.get(priority.get("name", ""), priority.get("name", "unknown")),
            assignee=assignee.get("displayName"),
            reporter=reporter.get("displayName"),
            project=project.get("key"),
            created_at=datetime.fromisoformat(fields["created"].replace("Z", "+00:00")) if fields.get("created") else None,
            updated_at=datetime.fromisoformat(fields["updated"].replace("Z", "+00:00")) if fields.get("updated") else None,
            url=f"{self.base_url.replace('/rest/api/3', '')}/browse/{issue['key']}",
            labels=fields.get("labels", []),
        )

    async def get_tickets(self, filters: TicketFilter) -> List[Ticket]:
        jql_parts = []
        if filters.status:
            jql_parts.append(f'status = "{filters.status}"')
        if filters.priority:
            jql_parts.append(f'priority = "{filters.priority}"')
        if filters.assignee:
            jql_parts.append(f'assignee = "{filters.assignee}"')
        if filters.query:
            jql_parts.append(f'text ~ "{filters.query}"')
        jql = " AND ".join(jql_parts) if jql_parts else "ORDER BY created DESC"
        if jql_parts:
            jql += " ORDER BY created DESC"

        async with self._client() as client:
            resp = await client.get(
                f"{self.base_url}/search",
                params={"jql": jql, "maxResults": filters.limit, "fields": "summary,status,priority,assignee,reporter,project,created,updated,description,labels"},
            )
            resp.raise_for_status()
            data = resp.json()
        return [self._parse_ticket(i) for i in data.get("issues", [])]

    async def create_ticket(self, request: CreateTicketRequest) -> Ticket:
        payload = {
            "fields": {
                "project": {"key": request.project},
                "summary": request.title,
                "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": request.description}]}]},
                "issuetype": {"name": "Task"},
                "priority": {"name": request.priority},
            }
        }
        async with self._client() as client:
            resp = await client.post(f"{self.base_url}/issue", json=payload)
            resp.raise_for_status()
            key = resp.json()["key"]
            detail = await client.get(f"{self.base_url}/issue/{key}")
            detail.raise_for_status()
        return self._parse_ticket(detail.json())

    async def update_ticket(self, request: UpdateTicketRequest) -> Ticket:
        async with self._client() as client:
            if request.comment:
                await client.post(f"{self.base_url}/issue/{request.ticket_id}/comment", json={"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": request.comment}]}]}})
            if request.status:
                trans_resp = await client.get(f"{self.base_url}/issue/{request.ticket_id}/transitions")
                trans_resp.raise_for_status()
                transitions = trans_resp.json().get("transitions", [])
                target = next((t for t in transitions if t["name"].lower() == request.status.lower()), None)
                if target:
                    await client.post(f"{self.base_url}/issue/{request.ticket_id}/transitions", json={"transition": {"id": target["id"]}})
            detail = await client.get(f"{self.base_url}/issue/{request.ticket_id}")
            detail.raise_for_status()
        return self._parse_ticket(detail.json())

    async def test_connection(self) -> ConnectionStatus:
        try:
            async with self._client() as client:
                resp = await client.get(f"{self.base_url}/myself")
                resp.raise_for_status()
                data = resp.json()
            return ConnectionStatus(connected=True, details={"user": data.get("displayName"), "email": data.get("emailAddress")})
        except Exception as e:
            return ConnectionStatus(connected=False, error=str(e))

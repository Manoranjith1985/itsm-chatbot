"""Jira ITSM connector using Jira Cloud REST API v3."""
import json
from datetime import datetime
from typing import List

import httpx

from app.connectors.base import (
    ConnectionStatus, CreateTicketRequest, ITSMConnector,
    Ticket, TicketFilter, UpdateTicketRequest,
)

STATUS_MAP = {
    "To Do": "open", "Open": "open", "Reopened": "open",
    "In Progress": "in_progress",
    "Done": "resolved", "Resolved": "resolved", "Closed": "closed",
}
PRIORITY_MAP = {
    "Highest": "critical", "High": "high",
    "Medium": "medium", "Low": "low", "Lowest": "low",
}


class JiraConnector(ITSMConnector):
    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self._auth = httpx.BasicAuth(email, api_token)
        self._headers = {"Accept": "application/json", "Content-Type": "application/json"}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(auth=self._auth, headers=self._headers, timeout=15.0)

    def _to_ticket(self, issue: dict) -> Ticket:
        fields = issue.get("fields", {})
        return Ticket(
            id=issue["key"],
            title=fields.get("summary", ""),
            description=fields.get("description") or None,
            status=STATUS_MAP.get(fields.get("status", {}).get("name", ""), "open"),
            priority=PRIORITY_MAP.get(fields.get("priority", {}).get("name", ""), "medium"),
            assignee=(fields.get("assignee") or {}).get("displayName"),
            reporter=(fields.get("reporter") or {}).get("displayName"),
            created_at=datetime.fromisoformat(fields["created"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(fields["updated"].replace("Z", "+00:00")),
            tool="jira",
            raw=issue,
        )

    async def get_tickets(self, filters: TicketFilter) -> List[Ticket]:
        jql_parts = []
        if filters.status:   jql_parts.append(f'status = "{filters.status}"')
        if filters.assignee: jql_parts.append(f'assignee = "{filters.assignee}"')
        if filters.priority: jql_parts.append(f'priority = "{filters.priority}"')
        if filters.project:  jql_parts.append(f'project = "{filters.project}"')
        if filters.query:    jql_parts.append(f'text ~ "{filters.query}"')
        jql = " AND ".join(jql_parts) if jql_parts else "ORDER BY updated DESC"
        params = {"jql": jql, "maxResults": filters.limit,
                  "fields": "summary,status,priority,assignee,reporter,description,created,updated"}
        async with self._client() as client:
            resp = await client.get(f"{self.base_url}/rest/api/3/search", params=params)
            resp.raise_for_status()
        return [self._to_ticket(i) for i in resp.json().get("issues", [])]

    async def create_ticket(self, data: CreateTicketRequest) -> Ticket:
        payload = {"fields": {
            "project": {"key": data.project or ""},
            "summary": data.title,
            "description": {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": data.description}]}]},
            "issuetype": {"name": "Task"},
            "priority": {"name": data.priority.capitalize()},
        }}
        async with self._client() as client:
            resp = await client.post(f"{self.base_url}/rest/api/3/issue", content=json.dumps(payload))
            resp.raise_for_status()
            key = resp.json()["key"]
            resp2 = await client.get(f"{self.base_url}/rest/api/3/issue/{key}")
            resp2.raise_for_status()
            return self._to_ticket(resp2.json())

    async def update_ticket(self, ticket_id: str, data: UpdateTicketRequest) -> Ticket:
        if data.status:
            async with self._client() as client:
                tr = await client.get(f"{self.base_url}/rest/api/3/issue/{ticket_id}/transitions")
                transitions = {t["name"].lower(): t["id"] for t in tr.json().get("transitions", [])}
                if data.status.lower() in transitions:
                    await client.post(
                        f"{self.base_url}/rest/api/3/issue/{ticket_id}/transitions",
                        content=json.dumps({"transition": {"id": transitions[data.status.lower()]}}))
        if data.comment:
            async with self._client() as client:
                await client.post(f"{self.base_url}/rest/api/3/issue/{ticket_id}/comment",
                    content=json.dumps({"body": {"type": "doc", "version": 1, "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": data.comment}]}]}}))
        async with self._client() as client:
            resp = await client.get(f"{self.base_url}/rest/api/3/issue/{ticket_id}")
            resp.raise_for_status()
            return self._to_ticket(resp.json())

    async def test_connection(self) -> ConnectionStatus:
        try:
            async with self._client() as client:
                resp = await client.get(f"{self.base_url}/rest/api/3/myself")
                resp.raise_for_status()
            return ConnectionStatus(ok=True, message="Connected successfully", tool="jira")
        except Exception as exc:
            return ConnectionStatus(ok=False, message=str(exc), tool="jira")

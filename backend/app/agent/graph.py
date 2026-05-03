import json
from typing import Any, Dict, List, Optional
from litellm import acompletion

from app.core.config import settings
from app.db.models import User
from app.connectors.jira import JiraConnector
from app.connectors.base import TicketFilter
from app.core.security import decrypt_secret

SYSTEM_PROMPT = """You are an ITSM-PMO AI assistant. You help IT teams query tickets, create reports, and manage work items.

When the user asks to query tickets, respond with a JSON tool call:
{"tool": "get_tickets", "filters": {"status": "...", "priority": "...", "limit": 10}}

When the user asks for a chart, include chart_type in your response:
{"tool": "get_tickets", "filters": {...}, "chart_type": "bar|line|pie"}

When the user asks to create a ticket (and write ops are enabled):
{"tool": "create_ticket", "title": "...", "description": "...", "project": "...", "priority": "Medium"}

For general questions, respond in plain markdown without a tool call.
Always be concise and professional."""


def _get_connector(user: User) -> Optional[JiraConnector]:
    for cfg in user.itsm_configs:
        if cfg.is_active and cfg.connector_type == "jira":
            token = decrypt_secret(cfg.encrypted_token)
            return JiraConnector(site_url=cfg.site_url, email=cfg.email, api_token=token)
    return None


async def run_agent(message: str, history: List[Dict], user: User) -> Dict[str, Any]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-settings.CONVERSATION_CONTEXT_TURNS * 2:]:
        messages.append(h)
    messages.append({"role": "user", "content": message})

    try:
        response = await acompletion(
            model=settings.LITELLM_DEFAULT_MODEL,
            messages=messages,
            api_key=settings.OPENAI_API_KEY,
            max_tokens=1000,
        )
        content = response.choices[0].message.content or ""
    except Exception as e:
        return {"text": f"I encountered an error connecting to the AI service: {str(e)}", "chart": None}

    # Try to parse tool call from response
    tool_call = None
    try:
        # Look for JSON in the response
        import re
        json_match = re.search(r'\{[^{}]*"tool"[^{}]*\}', content, re.DOTALL)
        if json_match:
            tool_call = json.loads(json_match.group())
    except Exception:
        pass

    if not tool_call:
        return {"text": content, "chart": None}

    tool = tool_call.get("tool")
    connector = _get_connector(user)

    if tool == "get_tickets" and connector:
        try:
            filters_data = tool_call.get("filters", {})
            filters = TicketFilter(**filters_data)
            tickets = await connector.get_tickets(filters)
            chart_type = tool_call.get("chart_type")

            if not tickets:
                return {"text": "No tickets found matching your criteria.", "chart": None}

            ticket_list = "\n".join([
                f"- **{t.id}** [{t.priority}] {t.title} — *{t.status}*" + (f" (assigned: {t.assignee})" if t.assignee else "")
                for t in tickets[:20]
            ])
            text = f"Found **{len(tickets)}** ticket(s):\n\n{ticket_list}"

            chart = None
            if chart_type:
                chart = _build_chart(tickets, chart_type, filters_data)

            return {"text": text, "chart": chart}
        except Exception as e:
            return {"text": f"Error fetching tickets: {str(e)}", "chart": None}

    if tool == "create_ticket":
        if not settings.AI_WRITE_OPERATIONS:
            return {"text": "⚠️ Ticket creation is currently disabled. Please enable AI write operations in settings.", "chart": None}
        if not connector:
            return {"text": "No ITSM connector configured.", "chart": None}
        try:
            from app.connectors.base import CreateTicketRequest
            req = CreateTicketRequest(
                title=tool_call.get("title", "New Ticket"),
                description=tool_call.get("description", ""),
                project=tool_call.get("project", ""),
                priority=tool_call.get("priority", "Medium"),
            )
            ticket = await connector.create_ticket(req)
            return {"text": f"✅ Ticket created: **{ticket.id}** — {ticket.title}\n{ticket.url}", "chart": None}
        except Exception as e:
            return {"text": f"Error creating ticket: {str(e)}", "chart": None}

    return {"text": content, "chart": None}


def _build_chart(tickets, chart_type: str, filters: dict) -> dict:
    from collections import Counter

    if chart_type == "pie":
        counts = Counter(t.status for t in tickets)
        return {
            "type": "pie",
            "title": "Tickets by Status",
            "labels": list(counts.keys()),
            "values": list(counts.values()),
        }
    elif chart_type == "bar":
        counts = Counter(t.priority for t in tickets)
        return {
            "type": "bar",
            "title": "Tickets by Priority",
            "labels": list(counts.keys()),
            "values": list(counts.values()),
        }
    else:
        counts = Counter(t.assignee or "Unassigned" for t in tickets)
        return {
            "type": "line",
            "title": "Tickets by Assignee",
            "labels": list(counts.keys()),
            "values": list(counts.values()),
        }

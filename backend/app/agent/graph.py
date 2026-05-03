import json
import re
from typing import Any, Dict, List, Optional
from litellm import acompletion

from app.core.config import settings
from app.db.models import User
from app.connectors.jira import JiraConnector
from app.connectors.base import TicketFilter
from app.core.security import decrypt_secret

SYSTEM_PROMPT = """You are an ITSM-PMO AI assistant. You help IT teams query tickets, create reports, and manage work items.

When the user asks to query or show tickets, respond ONLY with a JSON object (no other text):
{"tool": "get_tickets", "filters": {"status": "done", "priority": "High", "limit": 20}, "chart_type": "bar"}

Valid status values (use EXACTLY as shown):
- "open" or "to do"  → open/new tickets
- "in_progress"       → tickets being worked on
- "done" or "closed" or "completed" or "finished" or "resolved" → completed tickets
- "blocked"           → blocked tickets
- "in_review"         → tickets under review

chart_type can be: "bar", "line", "pie", or omit it for a plain list.
filters can include: status, priority, assignee, query, limit (default 20).

When the user asks for a chart or analytics, always include chart_type.

When the user asks about "completed", "done", "finished", "resolved", or "closed" tickets, always use status "done".
When the user asks about "open", "new", or "to do" tickets, always use status "open".

When the user asks to create a ticket (write ops enabled):
{"tool": "create_ticket", "title": "...", "description": "...", "project": "PROJ", "priority": "Medium"}

For general questions or greetings, respond in plain conversational markdown — no JSON.
Keep responses concise and professional."""


def _get_connector(user: User) -> Optional[JiraConnector]:
    for cfg in user.itsm_configs:
        if cfg.is_active and cfg.connector_type == "jira":
            token = decrypt_secret(cfg.encrypted_token)
            return JiraConnector(site_url=cfg.site_url, email=cfg.email, api_token=token)
    return None


def _extract_tool_call(content: str) -> Optional[dict]:
    """Robustly parse a JSON tool call from LLM output."""
    content = content.strip()

    # Try 1: entire response is JSON
    try:
        if content.startswith('{'):
            return json.loads(content)
    except Exception:
        pass

    # Try 2: find balanced JSON object containing "tool"
    try:
        idx = content.find('"tool"')
        if idx == -1:
            return None
        # Walk backwards to find opening brace
        start = content.rfind('{', 0, idx)
        if start == -1:
            return None
        depth = 0
        for i, ch in enumerate(content[start:]):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return json.loads(content[start:start + i + 1])
    except Exception:
        pass

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
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
    except Exception as e:
        return {"text": f"⚠️ AI service error: {str(e)}", "chart": None}

    # Try to extract tool call
    tool_call = _extract_tool_call(content)

    if not tool_call or "tool" not in tool_call:
        return {"text": content, "chart": None}

    tool = tool_call.get("tool")

    # ── get_tickets ─────────────────────────────────────────────────
    if tool == "get_tickets":
        connector = _get_connector(user)
        if not connector:
            return {
                "text": (
                    "⚠️ **No ITSM connector configured.**\n\n"
                    "To connect your Jira account:\n"
                    "1. Go to the **API docs**: `https://itsm-chatbot-backend.onrender.com/docs`\n"
                    "2. Authenticate with your token\n"
                    "3. Call **POST /api/v1/settings/itsm-connections** with your Jira site URL, email, and API token\n\n"
                    "Once connected, I can query your tickets and generate charts!"
                ),
                "chart": None
            }

        try:
            raw_filters = tool_call.get("filters", {})
            # Sanitise filters — remove None/empty values
            clean = {k: v for k, v in raw_filters.items() if v not in (None, "", [])}
            filters = TicketFilter(**clean)
            tickets = await connector.get_tickets(filters)
            chart_type = tool_call.get("chart_type")

            if not tickets:
                return {"text": "No tickets found matching your criteria. Try adjusting the filters.", "chart": None}

            ticket_lines = "\n".join([
                f"- **{t.id}** `[{t.priority}]` {t.title} — *{t.status}*"
                + (f" · {t.assignee}" if t.assignee else "")
                for t in tickets[:25]
            ])
            text = f"Found **{len(tickets)}** ticket(s):\n\n{ticket_lines}"

            # Always render a chart — default to "bar" (priority breakdown) when not specified
            effective_chart_type = chart_type or "bar"
            chart = _build_chart(tickets, effective_chart_type)
            return {"text": text, "chart": chart}

        except Exception as e:
            return {"text": f"⚠️ Error fetching tickets: {str(e)}", "chart": None}

    # ── create_ticket ────────────────────────────────────────────────
    if tool == "create_ticket":
        if not settings.AI_WRITE_OPERATIONS:
            return {
                "text": "⚠️ **Ticket creation is disabled.**\n\nAsk your admin to enable `AI_WRITE_OPERATIONS` in the Render environment settings.",
                "chart": None
            }
        connector = _get_connector(user)
        if not connector:
            return {"text": "⚠️ No ITSM connector configured. Add Jira credentials first.", "chart": None}
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
            return {"text": f"⚠️ Error creating ticket: {str(e)}", "chart": None}

    # Fallback — return plain content
    return {"text": content, "chart": None}


def _build_chart(tickets, chart_type: str) -> dict:
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
        order = ["P1", "P2", "P3", "P4", "P5", "unknown"]
        sorted_items = sorted(counts.items(), key=lambda x: order.index(x[0]) if x[0] in order else 99)
        return {
            "type": "bar",
            "title": "Tickets by Priority",
            "labels": [i[0] for i in sorted_items],
            "values": [i[1] for i in sorted_items],
        }
    else:
        counts = Counter(t.assignee or "Unassigned" for t in tickets)
        return {
            "type": "line",
            "title": "Tickets by Assignee",
            "labels": list(counts.keys()),
            "values": list(counts.values()),
        }
    
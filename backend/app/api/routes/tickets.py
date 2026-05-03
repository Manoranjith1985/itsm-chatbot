from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.db.models import User
from app.connectors.base import TicketFilter
from app.connectors.jira import JiraConnector
from app.core.security import decrypt_secret

router = APIRouter()


def _get_connector(user: User):
    for cfg in user.itsm_configs:
        if cfg.is_active and cfg.connector_type == "jira":
            token = decrypt_secret(cfg.encrypted_token)
            return JiraConnector(site_url=cfg.site_url, email=cfg.email, api_token=token)
    return None


@router.get("/")
async def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    connector = _get_connector(current_user)
    if not connector:
        raise HTTPException(status_code=400, detail="No active ITSM connector configured")
    f = TicketFilter(status=status, priority=priority, assignee=assignee, limit=limit)
    tickets = await connector.get_tickets(f)
    return [t.model_dump() for t in tickets]

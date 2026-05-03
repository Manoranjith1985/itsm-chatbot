from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_current_user
from app.db.models import User, ITSMConfig, UserRole
from app.core.security import encrypt_secret
from app.connectors.jira import JiraConnector

router = APIRouter()


class ITSMConnectionRequest(BaseModel):
    connector_type: str = "jira"
    site_url: str
    email: Optional[str] = None
    api_token: str


@router.get("/itsm-connections")
async def get_connections(current_user: User = Depends(get_current_user)):
    return [
        {"connector_type": c.connector_type, "site_url": c.site_url, "email": c.email, "is_active": c.is_active}
        for c in current_user.itsm_configs
    ]


@router.post("/itsm-connections")
async def add_connection(body: ITSMConnectionRequest, current_user: User = Depends(get_current_user)):
    # Test connection first
    if body.connector_type == "jira":
        connector = JiraConnector(site_url=body.site_url, email=body.email, api_token=body.api_token)
        status = await connector.test_connection()
        if not status.connected:
            raise HTTPException(status_code=400, detail=f"Connection failed: {status.error}")

    encrypted = encrypt_secret(body.api_token)
    config = ITSMConfig(
        connector_type=body.connector_type,
        site_url=body.site_url,
        email=body.email,
        encrypted_token=encrypted,
    )
    # Remove existing config of same type
    current_user.itsm_configs = [c for c in current_user.itsm_configs if c.connector_type != body.connector_type]
    current_user.itsm_configs.append(config)
    await current_user.save()
    return {"message": "Connection saved successfully"}


@router.delete("/itsm-connections/{connector_type}")
async def delete_connection(connector_type: str, current_user: User = Depends(get_current_user)):
    current_user.itsm_configs = [c for c in current_user.itsm_configs if c.connector_type != connector_type]
    await current_user.save()
    return {"message": "Connection removed"}

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional

from app.api.deps import get_current_user
from app.db.models import User, ITSMConfig
from app.core.security import encrypt_secret
from app.connectors.jira import JiraConnector

router = APIRouter()

SUPPORTED_CONNECTORS = {"jira"}


class ITSMConnectionRequest(BaseModel):
    connector_type: str = "jira"
    site_url: str
    email: Optional[str] = None
    api_token: str

    @field_validator("api_token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("api_token must not be empty")
        return v.strip()

    @field_validator("connector_type")
    @classmethod
    def connector_supported(cls, v: str) -> str:
        if v not in SUPPORTED_CONNECTORS:
            raise ValueError(f"Unsupported connector '{v}'. Supported: {', '.join(SUPPORTED_CONNECTORS)}")
        return v

    @field_validator("site_url")
    @classmethod
    def site_url_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("site_url must not be empty")
        return v.strip().rstrip("/")


@router.get("/itsm-connections")
async def get_connections(current_user: User = Depends(get_current_user)):
    return [
        {
            "connector_type": c.connector_type,
            "site_url": c.site_url,
            "email": c.email,
            "is_active": c.is_active,
        }
        for c in current_user.itsm_configs
    ]


@router.post("/itsm-connections")
async def add_connection(body: ITSMConnectionRequest, current_user: User = Depends(get_current_user)):
    if body.connector_type == "jira":
        connector = JiraConnector(site_url=body.site_url, email=body.email, api_token=body.api_token)
        try:
            status = await connector.test_connection()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Connection test error: {e}")
        if not status.connected:
            raise HTTPException(status_code=400, detail=f"Connection failed: {status.error}")

    try:
        encrypted = encrypt_secret(body.api_token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to secure credentials: {e}")

    config = ITSMConfig(
        connector_type=body.connector_type,
        site_url=body.site_url,
        email=body.email,
        encrypted_token=encrypted,
    )
    # Replace existing config of same type (notify caller it was replaced)
    existed = any(c.connector_type == body.connector_type for c in current_user.itsm_configs)
    current_user.itsm_configs = [c for c in current_user.itsm_configs if c.connector_type != body.connector_type]
    current_user.itsm_configs.append(config)
    await current_user.save()
    msg = "Connection updated successfully" if existed else "Connection saved successfully"
    return {"message": msg}


@router.delete("/itsm-connections/{connector_type}")
async def delete_connection(connector_type: str, current_user: User = Depends(get_current_user)):
    before = len(current_user.itsm_configs)
    current_user.itsm_configs = [c for c in current_user.itsm_configs if c.connector_type != connector_type]
    if len(current_user.itsm_configs) == before:
        raise HTTPException(status_code=404, detail=f"No '{connector_type}' connection found")
    await current_user.save()
    return {"message": "Connection removed"}

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    admin = "admin"
    agent = "agent"
    viewer = "viewer"


class Platform(str, Enum):
    web = "web"
    slack = "slack"
    teams = "teams"
    gchat = "gchat"


class ITSMConfig(BaseModel):
    connector_type: str
    site_url: str
    email: Optional[str] = None
    encrypted_token: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class User(Document):
    email: Indexed(EmailStr, unique=True)
    hashed_password: str
    role: UserRole = UserRole.viewer
    itsm_configs: List[ITSMConfig] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"


class Message(BaseModel):
    role: str  # user | assistant | system
    content: str
    chart_data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Conversation(Document):
    user_id: str
    platform: Platform = Platform.web
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "conversations"


class FeatureFlag(Document):
    name: Indexed(str, unique=True)
    enabled: bool = False
    description: str = ""

    class Settings:
        name = "feature_flags"


class AuditLog(Document):
    user_id: str
    action: str
    resource: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "audit_logs"

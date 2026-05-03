"""Beanie ODM document models for MongoDB."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    admin = "admin"
    agent = "agent"
    viewer = "viewer"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    tool = "tool"


class Platform(str, Enum):
    web = "web"
    slack = "slack"
    teams = "teams"
    gchat = "gchat"


class AIConfig(BaseModel):
    provider: str = ""
    model: str = ""
    encrypted_api_key: str = ""


class ITSMConfig(BaseModel):
    tool: str
    base_url: str
    encrypted_credentials: str
    is_active: bool = True


class Message(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_calls: Optional[List[Dict[str, Any]]] = None


class User(Document):
    email: Indexed(str, unique=True)  # type: ignore[valid-type]
    hashed_password: str
    role: UserRole = UserRole.viewer
    is_active: bool = True
    ai_config: AIConfig = Field(default_factory=AIConfig)
    itsm_configs: List[ITSMConfig] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"


class Conversation(Document):
    user_id: str
    platform: Platform = Platform.web
    platform_thread_id: Optional[str] = None
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "conversations"


class FeatureFlag(Document):
    name: Indexed(str, unique=True)  # type: ignore[valid-type]
    value: Any
    description: str = ""
    updated_by: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "feature_flags"


class AuditLog(Document):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    action: str
    resource_type: str
    resource_id: str = ""
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    ip_address: str = ""

    class Settings:
        name = "audit_logs"

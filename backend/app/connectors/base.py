"""Abstract base class for all ITSM connectors."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TicketFilter(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    project: Optional[str] = None
    query: Optional[str] = None
    limit: int = 50


class Ticket(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tool: str
    raw: Dict[str, Any] = {}


class CreateTicketRequest(BaseModel):
    title: str
    description: str
    priority: str
    assignee: Optional[str] = None
    project: Optional[str] = None
    extra: Dict[str, Any] = {}


class UpdateTicketRequest(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    priority: Optional[str] = None
    comment: Optional[str] = None
    extra: Dict[str, Any] = {}


class ConnectionStatus(BaseModel):
    ok: bool
    message: str
    tool: str


class ITSMConnector(ABC):
    @abstractmethod
    async def get_tickets(self, filters: TicketFilter) -> List[Ticket]: ...
    @abstractmethod
    async def create_ticket(self, data: CreateTicketRequest) -> Ticket: ...
    @abstractmethod
    async def update_ticket(self, ticket_id: str, data: UpdateTicketRequest) -> Ticket: ...
    @abstractmethod
    async def test_connection(self) -> ConnectionStatus: ...

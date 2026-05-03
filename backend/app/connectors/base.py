from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class TicketFilter(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    project: Optional[str] = None
    query: Optional[str] = None
    limit: int = 20


class Ticket(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    project: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    url: Optional[str] = None
    labels: List[str] = []


class CreateTicketRequest(BaseModel):
    title: str
    description: str
    project: str
    priority: str = "Medium"
    assignee: Optional[str] = None
    labels: List[str] = []


class UpdateTicketRequest(BaseModel):
    ticket_id: str
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    comment: Optional[str] = None


class ConnectionStatus(BaseModel):
    connected: bool
    error: Optional[str] = None
    details: Optional[dict] = None


class ITSMConnector(ABC):
    @abstractmethod
    async def get_tickets(self, filters: TicketFilter) -> List[Ticket]:
        pass

    @abstractmethod
    async def create_ticket(self, request: CreateTicketRequest) -> Ticket:
        pass

    @abstractmethod
    async def update_ticket(self, request: UpdateTicketRequest) -> Ticket:
        pass

    @abstractmethod
    async def test_connection(self) -> ConnectionStatus:
        pass


CONNECTOR_REGISTRY: dict = {}

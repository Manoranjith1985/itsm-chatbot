"""Tests for the Jira connector using mocked HTTP responses."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.connectors.jira import JiraConnector
from app.connectors.base import TicketFilter

MOCK_ISSUE = {"key": "PROJ-42", "fields": {
    "summary": "Fix login bug", "description": None,
    "status": {"name": "In Progress"}, "priority": {"name": "High"},
    "assignee": {"displayName": "Jane Doe"}, "reporter": {"displayName": "John Smith"},
    "created": "2026-01-15T10:00:00.000+0000", "updated": "2026-05-01T14:30:00.000+0000",
}}


@pytest.fixture
def connector():
    return JiraConnector(base_url="https://myorg.atlassian.net", email="admin@myorg.com", api_token="fake_token")


@pytest.mark.asyncio
async def test_get_tickets_returns_normalised_list(connector):
    mock_response = MagicMock()
    mock_response.json.return_value = {"issues": [MOCK_ISSUE]}
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        tickets = await connector.get_tickets(TicketFilter())
    assert tickets[0].id == "PROJ-42"
    assert tickets[0].status == "in_progress"
    assert tickets[0].tool == "jira"


@pytest.mark.asyncio
async def test_test_connection_failure(connector):
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        status = await connector.test_connection()
    assert status.ok is False
    assert "Connection refused" in status.message

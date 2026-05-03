"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_register_and_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/auth/register", json={"email": "test@example.com", "password": "securepassword123"})
        assert res.status_code == 201
        res = await client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "securepassword123"})
        assert res.status_code == 200
        assert "access_token" in res.json()


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

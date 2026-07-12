"""Tests for auth endpoints (TDD)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.deps import get_current_user

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def raw_client() -> AsyncGenerator[AsyncClient, None]:
    """FastAPI test client WITHOUT auth or DB override (auth endpoints only)."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def noauth_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client with DB override but WITHOUT auth bypass."""
    from app.core.db import get_db
    from app.main import app

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # Clear auth override if present
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def authed_client(noauth_client: AsyncClient, db_session: AsyncSession) -> AsyncClient:
    """Test client with DB override + valid auth token."""
    from app.auth.service import UserService

    await UserService.create_user(db_session, "admin", "admin")
    await db_session.commit()
    resp = await noauth_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    token = resp.json()["access_token"]
    noauth_client.headers["Authorization"] = f"Bearer {token}"
    return noauth_client


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, noauth_client: AsyncClient, db_session: AsyncSession):
        from app.auth.service import UserService

        await UserService.create_user(db_session, "admin", "admin")
        await db_session.commit()
        resp = await noauth_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 20

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self, noauth_client: AsyncClient, db_session: AsyncSession
    ):
        from app.auth.service import UserService

        await UserService.create_user(db_session, "admin", "admin")
        await db_session.commit()
        resp = await noauth_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    @pytest.mark.asyncio
    async def test_login_invalid_username(self, noauth_client: AsyncClient):
        resp = await noauth_client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "admin"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"


class TestMe:
    @pytest.mark.asyncio
    async def test_me_with_valid_token(self, noauth_client: AsyncClient, db_session: AsyncSession):
        from app.auth.service import UserService

        await UserService.create_user(db_session, "admin", "admin")
        await db_session.commit()
        login_resp = await noauth_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin"},
        )
        token = login_resp.json()["access_token"]
        resp = await noauth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"

    @pytest.mark.asyncio
    async def test_me_without_token(self, raw_client: AsyncClient):
        resp = await raw_client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated"

    @pytest.mark.asyncio
    async def test_me_with_invalid_token(self, raw_client: AsyncClient):
        resp = await raw_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken123"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token"


class TestProtectedRoutes:
    @pytest.mark.asyncio
    async def test_post_incident_without_token(self, noauth_client: AsyncClient):
        resp = await noauth_client.post(
            "/api/v1/incidents",
            json={"title": "test", "severity": "SEV-3"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_post_incident_with_token(self, authed_client: AsyncClient):
        resp = await authed_client.post(
            "/api/v1/incidents",
            json={"title": "test", "severity": "SEV-3"},
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_get_incidents_public(self, noauth_client: AsyncClient):
        resp = await noauth_client.get("/api/v1/incidents")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_public(self, noauth_client: AsyncClient):
        resp = await noauth_client.get("/api/v1/health")
        assert resp.status_code == 200

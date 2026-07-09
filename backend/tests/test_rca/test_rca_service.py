"""Tests for LLM-powered RCA service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.llm.rca_service import generate_rca


@pytest.fixture
def mock_db() -> tuple[MagicMock, MagicMock]:
    """Fixture that patches get_db to yield a mock async session."""
    session = MagicMock()
    session.execute = AsyncMock()
    # result is a regular Mock — its methods are sync (matching SQLAlchemy Result)
    session.execute.return_value = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    gen = MagicMock()
    gen.__aiter__.return_value = [session]
    return session, gen


class TestGenerateRca:
    """generate_rca() behaviour."""

    @patch("app.llm.rca_service.LiteLLMClient")
    @patch("app.llm.rca_service.get_db")
    async def test_generate_rca_found(
        self, mock_get_db: MagicMock, mock_llm: MagicMock, mock_db: tuple
    ) -> None:
        session, gen = mock_db
        mock_get_db.return_value = gen
        mock_incident = MagicMock()
        mock_incident.id = uuid4()
        mock_incident.title = "High CPU usage"
        mock_incident.severity = "SEV-2"
        mock_incident.service = "api-gateway"
        mock_incident.failure_pattern = "resource"
        mock_incident.description = "CPU at 95%"
        mock_incident.llm_rca = None
        session.execute.return_value.scalar_one_or_none.return_value = mock_incident

        mock_client = MagicMock()
        mock_client.complete.return_value = "Root cause: resource exhaustion"
        mock_llm.return_value = mock_client

        incident_id = uuid4()
        result = await generate_rca(incident_id)

        assert result == "Root cause: resource exhaustion"
        assert mock_incident.llm_rca == "Root cause: resource exhaustion"
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once_with(mock_incident)

    @patch("app.llm.rca_service.LiteLLMClient")
    @patch("app.llm.rca_service.get_db")
    async def test_generate_rca_not_found(
        self, mock_get_db: MagicMock, _mock_llm: MagicMock, mock_db: tuple
    ) -> None:
        session, gen = mock_db
        mock_get_db.return_value = gen
        session.execute.return_value.scalar_one_or_none.return_value = None

        incident_id = uuid4()
        with pytest.raises(ValueError, match=f"Incident {incident_id} not found"):
            await generate_rca(incident_id)

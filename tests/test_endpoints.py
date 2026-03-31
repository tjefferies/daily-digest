"""Tests for the FastAPI pipeline endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from evercurrent.app import app


class TestPipelineRun:
    """Tests for POST /pipeline/run stub endpoint."""

    @pytest.mark.asyncio
    async def test_pipeline_run_returns_200(self) -> None:
        """Verify POST /pipeline/run returns 200 with status field."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/pipeline/run")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_pipeline_run_returns_stub_status(self) -> None:
        """Verify POST /pipeline/run indicates stub behavior."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/pipeline/run")
        assert response.json()["status"] == "stub"


class TestDigestEndpoint:
    """Tests for GET /digest/{persona_id} endpoint."""

    @pytest.mark.asyncio
    async def test_digest_returns_200(self) -> None:
        """Verify GET /digest/{persona_id} returns 200 for known persona."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/U001")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_digest_returns_persona_id(self) -> None:
        """Verify response includes the requested persona_id."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/U001")
        data = response.json()
        assert data["persona_id"] == "U001"

    @pytest.mark.asyncio
    async def test_digest_returns_sections(self) -> None:
        """Verify response includes a sections list."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/U001")
        data = response.json()
        assert "sections" in data
        assert isinstance(data["sections"], list)

    @pytest.mark.asyncio
    async def test_digest_with_phase_override(self) -> None:
        """Verify phase_override query param is accepted."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/digest/U001",
                params={"phase_override": "chassis:DVT"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["persona_id"] == "U001"

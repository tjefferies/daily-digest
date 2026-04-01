"""Tests for digest assembly and GET /digest endpoint (sync and async)."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from evercurrent.app import app
from evercurrent.generation.assembler import AsyncDigestAssembler
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.models.digest import DigestSection
from evercurrent.models.responses import DigestResponse
from evercurrent.scoring.composite import ScoreBreakdown, ScoredAtom


def _make_atom(
    atom_type: str = "DECISION",
    workstream: str = "chassis",
) -> Atom:
    """Create a test Atom."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary="Test",
        detail="Detail",
        source=AtomSource(
            channel="#test",
            thread_ts="1.0",
            message_range=[0, 1],
        ),
        workstreams=AtomWorkstreams(originating=workstream),
        urgency="medium",
        confidence=0.9,
    )


def _make_scored(score: float = 0.7, critical: bool = False) -> ScoredAtom:
    """Create a test ScoredAtom."""
    return ScoredAtom(
        atom=_make_atom(),
        score=score,
        breakdown=ScoreBreakdown(
            workstream_proximity=0.8,
            role_type_alignment=0.7,
            phase_alignment=0.6,
            urgency=0.5,
            social_signal=0.3,
        ),
        critical=critical,
    )


def _mock_digest_response() -> DigestResponse:
    """Create a mock DigestResponse for structured output."""
    return DigestResponse(
        sections=[
            DigestSection(
                section_type="requires_action",
                title="REQUIRES YOUR ACTION",
            ),
        ]
    )


class TestAsyncDigestAssembler:
    """Tests for the async DigestAssembler orchestrator."""

    async def test_assemble_returns_response_dict(self) -> None:
        """Async assembler returns dict with persona_id, generated_at, sections."""
        client = AsyncMock()
        client.create_structured_message.return_value = _mock_digest_response()
        assembler = AsyncDigestAssembler(client)
        result = await assembler.assemble("U001", atoms=[_make_atom()])
        assert "persona_id" in result
        assert "generated_at" in result
        assert "sections" in result
        assert result["persona_id"] == "U001"

    async def test_assemble_unknown_persona_returns_error(self) -> None:
        """Async assembler returns error for unknown persona_id."""
        assembler = AsyncDigestAssembler(AsyncMock())
        result = await assembler.assemble("UNKNOWN_USER", atoms=[_make_atom()])
        assert "error" in result

    async def test_assemble_empty_atoms(self) -> None:
        """Async assembler with empty atoms returns empty sections."""
        assembler = AsyncDigestAssembler(AsyncMock())
        result = await assembler.assemble("U001", atoms=[])
        assert result["sections"] == []


class TestDigestEndpointWired:
    """Tests for the GET /digest endpoint with pipeline wiring."""

    @pytest.mark.asyncio
    async def test_digest_returns_200(self) -> None:
        """GET /digest/{persona_id} returns 200."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/U001")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_digest_returns_persona_id(self) -> None:
        """Response includes the requested persona_id."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/U001")
        data = response.json()
        assert data["persona_id"] == "U001"

    @pytest.mark.asyncio
    async def test_digest_returns_sections_key(self) -> None:
        """Response includes sections list."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/U001")
        data = response.json()
        assert "sections" in data
        assert isinstance(data["sections"], list)

    @pytest.mark.asyncio
    async def test_digest_returns_generated_at(self) -> None:
        """Response includes generated_at timestamp."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/U001")
        data = response.json()
        assert "generated_at" in data

    @pytest.mark.asyncio
    async def test_digest_unknown_persona_returns_404(self) -> None:
        """Unknown persona_id returns 404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/UNKNOWN")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_digest_with_phase_override(self) -> None:
        """Phase override query param is accepted."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/digest/U001",
                params={"phase_override": "chassis:PVT"},
            )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_digest_invalid_phase_override_returns_400(self) -> None:
        """Invalid phase_override format returns 400."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/digest/U001",
                params={"phase_override": "bad-format"},
            )
        assert response.status_code == 400

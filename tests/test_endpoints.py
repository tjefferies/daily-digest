"""Tests for the FastAPI pipeline endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from evercurrent.app import app, clear_atom_store
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams


def _make_atom(
    *,
    summary: str = "Test decision",
    atom_type: str = "DECISION",
    confidence: float = 0.9,
) -> Atom:
    """Create a minimal Atom for testing."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary=summary,
        detail="Detail text",
        source=AtomSource(
            channel="#test",
            thread_ts="1000.0001",
            message_range=[0, 1],
            key_participants=["U001"],
        ),
        workstreams=AtomWorkstreams(originating="chassis"),
        urgency="medium",
        confidence=confidence,
    )


class TestPipelineRun:
    """Tests for POST /pipeline/run endpoint."""

    @pytest.fixture(autouse=True)
    def _clear_store(self) -> None:
        """Clear atom store between tests."""
        clear_atom_store()

    @patch("evercurrent.app.async_run_pipeline")
    def test_pipeline_run_returns_200(self, mock_run: MagicMock) -> None:
        """Verify POST /pipeline/run returns 200 with status field."""
        from evercurrent.pipeline import PipelineResult

        mock_run.return_value = PipelineResult(
            atoms=[_make_atom()],
            stats={"atoms_extracted": 1, "atoms_after_filter": 1},
        )

    @pytest.mark.asyncio
    @patch("evercurrent.app.async_run_pipeline")
    async def test_pipeline_run_extracts_atoms(self, mock_run: MagicMock) -> None:
        """POST /pipeline/run executes the pipeline and stores atoms."""
        from evercurrent.pipeline import PipelineResult

        atom = _make_atom()
        mock_run.return_value = PipelineResult(
            atoms=[atom],
            stats={"atoms_extracted": 1, "atoms_after_filter": 1},
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/pipeline/run")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert data["stats"]["atoms_extracted"] == 1

    @pytest.mark.asyncio
    @patch("evercurrent.app.async_run_pipeline")
    async def test_pipeline_run_returns_stats(self, mock_run: MagicMock) -> None:
        """POST /pipeline/run returns pipeline processing stats."""
        from evercurrent.pipeline import PipelineResult

        mock_run.return_value = PipelineResult(
            atoms=[],
            stats={
                "messages_loaded": 300,
                "threads_found": 40,
                "context_windows": 40,
                "atoms_extracted": 0,
                "atoms_after_filter": 0,
            },
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/pipeline/run")

        data = response.json()
        assert "stats" in data
        assert data["stats"]["messages_loaded"] == 300


class TestDigestEndpoint:
    """Tests for GET /digest/{persona_id} endpoint."""

    @pytest.fixture(autouse=True)
    def _clear_store(self) -> None:
        """Clear atom store between tests."""
        clear_atom_store()

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

    @pytest.mark.asyncio
    async def test_digest_unknown_persona_returns_404(self) -> None:
        """Verify unknown persona returns 404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/UNKNOWN")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_digest_invalid_phase_override_returns_400(self) -> None:
        """Verify invalid phase_override format returns 400."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/digest/U001",
                params={"phase_override": "invalid-format"},
            )
        assert response.status_code == 400

    @pytest.mark.asyncio
    @patch("evercurrent.app.async_run_pipeline")
    @patch("evercurrent.app.AsyncDigestAssembler")
    async def test_digest_uses_stored_atoms_after_pipeline_run(
        self,
        mock_assembler_cls: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """After pipeline/run, digest endpoint uses stored atoms for scoring."""
        from evercurrent.pipeline import PipelineResult

        atom = _make_atom()
        mock_run.return_value = PipelineResult(
            atoms=[atom],
            stats={"atoms_extracted": 1, "atoms_after_filter": 1},
        )

        mock_assembler = AsyncMock()
        mock_assembler.assemble.return_value = {
            "persona_id": "U001",
            "generated_at": "2026-03-31T00:00:00",
            "sections": [{"section_type": "requires_action", "title": "Action Items"}],
        }
        mock_assembler_cls.return_value = mock_assembler

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First run the pipeline
            await client.post("/pipeline/run")
            # Then fetch the digest
            response = await client.get("/digest/U001")

        data = response.json()
        assert data["persona_id"] == "U001"
        # Assembler is called 3 times during precook (U001, U007, U010)
        # and digest/U001 is served from cache — no additional call
        assert mock_assembler.assemble.call_count == 3
        # Verify U001 was precooked with the atom
        u001_calls = [
            c for c in mock_assembler.assemble.call_args_list if c[0][0] == "U001"
        ]
        assert len(u001_calls) == 1
        assert len(u001_calls[0][0][1]) == 1

    @pytest.mark.asyncio
    @patch("evercurrent.app._load_atoms_from_neo4j")
    @patch("evercurrent.app.AsyncDigestAssembler")
    async def test_digest_pulls_from_neo4j_when_store_empty(
        self,
        mock_assembler_cls: MagicMock,
        mock_load_neo4j: MagicMock,
    ) -> None:
        """Digest queries Neo4j when in-memory store is empty."""
        atom = _make_atom()
        mock_load_neo4j.return_value = [atom]

        mock_assembler = AsyncMock()
        mock_assembler.assemble.return_value = {
            "persona_id": "U001",
            "generated_at": "2026-03-31T00:00:00",
            "sections": [{"section_type": "requires_action", "title": "Action Items"}],
        }
        mock_assembler_cls.return_value = mock_assembler

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/U001")

        assert response.status_code == 200
        data = response.json()
        assert data["persona_id"] == "U001"
        assert len(data["sections"]) == 1
        mock_load_neo4j.assert_called_once()

    @pytest.mark.asyncio
    @patch("evercurrent.app._load_atoms_from_neo4j")
    async def test_digest_returns_empty_when_neo4j_also_empty(
        self,
        mock_load_neo4j: MagicMock,
    ) -> None:
        """Returns empty sections when both in-memory and Neo4j are empty."""
        mock_load_neo4j.return_value = []

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/U001")

        data = response.json()
        assert data["sections"] == []

    @pytest.mark.asyncio
    @patch("evercurrent.app._load_atoms_from_neo4j")
    async def test_digest_graceful_neo4j_failure(
        self,
        mock_load_neo4j: MagicMock,
    ) -> None:
        """Returns empty sections when Neo4j query fails."""
        mock_load_neo4j.side_effect = Exception("Connection refused")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/digest/U001")

        assert response.status_code == 200
        data = response.json()
        assert data["sections"] == []

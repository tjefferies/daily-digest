"""Tests for two-stage extraction: coarse extract → enrich.

Stage 1 identifies events (type, summary, detail, source).
Stage 2 enriches each event with metadata (workstreams, urgency,
confidence, phase_relevance, implicit_decision).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from evercurrent.extraction.runner import AsyncExtractionRunner, ExtractionRunner
from evercurrent.ingestion.context_window import ContextWindow
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.models.responses import (
    CoarseExtractionResponse,
    EnrichmentResponse,
)


def _make_window(text: str = "test thread content") -> ContextWindow:
    """Create a test ContextWindow."""
    return ContextWindow(
        thread_text=text,
        channel="#chassis-design",
        thread_ts="1.0",
        message_range=("1.0", "2.0"),
        compressed=False,
    )


def _make_coarse_response() -> CoarseExtractionResponse:
    """Create a CoarseExtractionResponse with one event."""
    return CoarseExtractionResponse(
        atoms=[
            {
                "atom_id": str(uuid4()),
                "type": "DECISION",
                "summary": "Team decided on magnesium housing",
                "detail": "After reviewing weight targets, team chose magnesium",
                "source": {
                    "channel": "#chassis-design",
                    "thread_ts": "1.0",
                    "message_range": [0, 5],
                    "key_participants": ["U001", "U008"],
                },
            }
        ]
    )


def _make_enrichment_response() -> EnrichmentResponse:
    """Create an EnrichmentResponse with full metadata."""
    return EnrichmentResponse(
        workstreams=AtomWorkstreams(
            originating="chassis",
            affected=["supply-chain", "thermal"],
        ),
        urgency="high",
        confidence=0.75,
        implicit_decision=True,
        phase_relevance=["DVT"],
    )


def _make_full_atom() -> Atom:
    """Create a full Atom (for backward compatibility tests)."""
    return Atom(
        atom_id=uuid4(),
        type="DECISION",
        summary="Test decision",
        detail="Detail",
        source=AtomSource(
            channel="#chassis-design",
            thread_ts="1.0",
            message_range=[0, 5],
            key_participants=["U001"],
        ),
        workstreams=AtomWorkstreams(originating="chassis"),
        urgency="high",
        confidence=0.85,
    )


class TestCoarseExtractionResponse:
    """Tests for the Stage 1 response model."""

    def test_empty_atoms(self) -> None:
        """CoarseExtractionResponse defaults to empty list."""
        resp = CoarseExtractionResponse()
        assert resp.atoms == []

    def test_atoms_are_dicts(self) -> None:
        """CoarseExtractionResponse holds atom dicts, not full Atoms."""
        resp = _make_coarse_response()
        assert len(resp.atoms) == 1
        assert isinstance(resp.atoms[0], dict)
        assert resp.atoms[0]["type"] == "DECISION"


class TestEnrichmentResponse:
    """Tests for the Stage 2 response model."""

    def test_has_required_fields(self) -> None:
        """EnrichmentResponse has all metadata fields."""
        resp = _make_enrichment_response()
        assert resp.urgency == "high"
        assert resp.confidence == 0.75
        assert resp.implicit_decision is True
        assert resp.phase_relevance == ["DVT"]
        assert resp.workstreams.originating == "chassis"

    def test_defaults(self) -> None:
        """EnrichmentResponse has sensible defaults."""
        resp = EnrichmentResponse(
            workstreams=AtomWorkstreams(originating="chassis"),
            urgency="medium",
            confidence=0.8,
        )
        assert resp.implicit_decision is False
        assert resp.phase_relevance == []


class TestTwoStageSyncRunner:
    """Tests for two-stage sync extraction."""

    def test_two_stage_produces_full_atoms(self) -> None:
        """Runner chains Stage 1 → Stage 2 to produce full Atom objects."""
        client = MagicMock()
        # Stage 1: coarse extraction
        client.create_structured_message.side_effect = [
            _make_coarse_response(),
            _make_enrichment_response(),
        ]
        runner = ExtractionRunner(client)
        atoms = runner.extract([_make_window()])
        assert len(atoms) == 1
        atom = atoms[0]
        assert isinstance(atom, Atom)
        assert atom.type == "DECISION"
        assert atom.urgency == "high"
        assert atom.workstreams.originating == "chassis"

    def test_stage1_failure_returns_empty(self) -> None:
        """If Stage 1 fails, returns empty list (no Stage 2 called)."""
        client = MagicMock()
        client.create_structured_message.side_effect = Exception("LLM error")
        runner = ExtractionRunner(client)
        atoms = runner.extract([_make_window()])
        assert atoms == []

    def test_stage2_failure_skips_atom(self) -> None:
        """If Stage 2 fails for one atom, that atom is skipped."""
        client = MagicMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(),
            Exception("Enrichment failed"),
        ]
        runner = ExtractionRunner(client)
        atoms = runner.extract([_make_window()])
        assert atoms == []

    def test_multiple_coarse_atoms_each_enriched(self) -> None:
        """Each coarse atom gets its own enrichment call."""
        coarse = CoarseExtractionResponse(
            atoms=[
                {
                    "atom_id": str(uuid4()),
                    "type": "DECISION",
                    "summary": "Decision 1",
                    "detail": "Detail 1",
                    "source": {
                        "channel": "#test",
                        "thread_ts": "1.0",
                        "message_range": [0, 1],
                        "key_participants": ["U001"],
                    },
                },
                {
                    "atom_id": str(uuid4()),
                    "type": "BLOCKER",
                    "summary": "Blocker 1",
                    "detail": "Detail 2",
                    "source": {
                        "channel": "#test",
                        "thread_ts": "1.0",
                        "message_range": [2, 3],
                        "key_participants": ["U002"],
                    },
                },
            ]
        )
        enrich1 = EnrichmentResponse(
            workstreams=AtomWorkstreams(originating="chassis"),
            urgency="high",
            confidence=0.9,
        )
        enrich2 = EnrichmentResponse(
            workstreams=AtomWorkstreams(originating="thermal"),
            urgency="critical",
            confidence=0.8,
        )
        client = MagicMock()
        client.create_structured_message.side_effect = [coarse, enrich1, enrich2]
        runner = ExtractionRunner(client)
        atoms = runner.extract([_make_window()])
        assert len(atoms) == 2
        assert atoms[0].urgency == "high"
        assert atoms[1].urgency == "critical"

    def test_uses_coarse_response_model_for_stage1(self) -> None:
        """Stage 1 uses CoarseExtractionResponse as response_model."""
        client = MagicMock()
        client.create_structured_message.return_value = CoarseExtractionResponse()
        runner = ExtractionRunner(client)
        runner.extract([_make_window()])
        first_call = client.create_structured_message.call_args_list[0]
        assert first_call.kwargs["response_model"] is CoarseExtractionResponse

    def test_uses_enrichment_response_model_for_stage2(self) -> None:
        """Stage 2 uses EnrichmentResponse as response_model."""
        client = MagicMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(),
            _make_enrichment_response(),
        ]
        runner = ExtractionRunner(client)
        runner.extract([_make_window()])
        second_call = client.create_structured_message.call_args_list[1]
        assert second_call.kwargs["response_model"] is EnrichmentResponse

    def test_stats_tracking(self) -> None:
        """Runner tracks windows_processed and atoms_produced."""
        client = MagicMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(),
            _make_enrichment_response(),
        ]
        runner = ExtractionRunner(client)
        runner.extract([_make_window()])
        assert runner.stats["windows_processed"] == 1
        assert runner.stats["atoms_produced"] == 1


class TestTwoStageAsyncRunner:
    """Tests for two-stage async extraction."""

    async def test_async_two_stage_produces_atoms(self) -> None:
        """Async runner chains Stage 1 → Stage 2."""
        client = AsyncMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(),
            _make_enrichment_response(),
        ]
        runner = AsyncExtractionRunner(client)
        atoms = await runner.extract([_make_window()])
        assert len(atoms) == 1
        assert isinstance(atoms[0], Atom)

    async def test_async_stage1_failure(self) -> None:
        """Async Stage 1 failure returns empty."""
        client = AsyncMock()
        client.create_structured_message.side_effect = Exception("LLM error")
        runner = AsyncExtractionRunner(client)
        atoms = await runner.extract([_make_window()])
        assert atoms == []

    async def test_async_empty_windows(self) -> None:
        """Async runner with empty windows returns empty."""
        client = AsyncMock()
        runner = AsyncExtractionRunner(client)
        atoms = await runner.extract([])
        assert atoms == []

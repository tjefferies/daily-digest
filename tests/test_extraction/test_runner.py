"""Tests for the two-stage extraction runner (sync and async).

Validates that the ExtractionRunner processes ContextWindows through
a two-stage LLM pipeline (coarse extract → enrich) using instructor
for structured output and merges responses into Atom objects.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from evercurrent.extraction.runner import AsyncExtractionRunner, ExtractionRunner
from evercurrent.ingestion.context_window import ContextWindow
from evercurrent.models.atom import Atom, AtomWorkstreams
from evercurrent.models.responses import CoarseExtractionResponse, EnrichmentResponse


def _make_context_window(
    thread_text: str = "Test thread content",
    channel: str = "#chassis-design",
    thread_ts: str = "1000.001",
) -> ContextWindow:
    """Create a ContextWindow for testing."""
    return ContextWindow(
        thread_text=thread_text,
        channel=channel,
        thread_ts=thread_ts,
        message_range=(thread_ts, thread_ts),
        compressed=False,
    )


def _make_coarse_response(count: int = 1) -> CoarseExtractionResponse:
    """Create a CoarseExtractionResponse with `count` atom dicts."""
    atoms = [
        {
            "atom_id": str(uuid4()),
            "type": "DECISION",
            "summary": f"Decision {i}",
            "detail": f"Detail for decision {i}",
            "source": {
                "channel": "#chassis-design",
                "thread_ts": "1000.001",
                "message_range": [0, 5],
                "key_participants": ["U001", "U002"],
            },
        }
        for i in range(count)
    ]
    return CoarseExtractionResponse(atoms=atoms)


def _make_enrichment_response(
    urgency: str = "high",
    confidence: float = 0.85,
) -> EnrichmentResponse:
    """Create an EnrichmentResponse with configurable fields."""
    return EnrichmentResponse(
        workstreams=AtomWorkstreams(
            originating="chassis",
            affected=["supply-chain", "thermal"],
        ),
        urgency=urgency,
        confidence=confidence,
        implicit_decision=True,
        phase_relevance=["DVT"],
    )


class TestExtractionRunnerInit:
    """Tests for ExtractionRunner initialization."""

    def test_creates_with_client(self) -> None:
        """Runner can be created with a mock client."""
        client = MagicMock()
        runner = ExtractionRunner(client=client)
        assert runner is not None


class TestExtractionRunnerExtract:
    """Tests for the extract method with two-stage pipeline."""

    def test_extracts_atoms_from_single_window(self) -> None:
        """Single context window produces atoms via two-stage pipeline."""
        client = MagicMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(1),
            _make_enrichment_response(),
        ]
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert len(atoms) == 1
        assert isinstance(atoms[0], Atom)
        assert atoms[0].type == "DECISION"
        assert atoms[0].urgency == "high"

    def test_extracts_from_multiple_windows(self) -> None:
        """Multiple context windows each produce atoms."""
        client = MagicMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(1),
            _make_enrichment_response(),
            _make_coarse_response(1),
            _make_enrichment_response(),
        ]
        runner = ExtractionRunner(client=client)
        windows = [_make_context_window(), _make_context_window(thread_ts="2000.001")]
        atoms = runner.extract(windows)
        assert len(atoms) == 2

    def test_empty_response_produces_no_atoms(self) -> None:
        """Empty atom list from coarse response produces no atoms."""
        client = MagicMock()
        client.create_structured_message.return_value = CoarseExtractionResponse()
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert atoms == []

    def test_empty_windows_produces_no_atoms(self) -> None:
        """No context windows produces no atoms."""
        client = MagicMock()
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([])
        assert atoms == []
        client.create_structured_message.assert_not_called()

    def test_multiple_atoms_per_window(self) -> None:
        """Single window can produce multiple atoms via multiple enrichments."""
        client = MagicMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(3),
            _make_enrichment_response(),
            _make_enrichment_response(),
            _make_enrichment_response(),
        ]
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert len(atoms) == 3


class TestExtractionRunnerErrorHandling:
    """Tests for two-stage error handling."""

    def test_stage1_failure_skips_window(self) -> None:
        """Exception from Stage 1 skips that window gracefully."""
        client = MagicMock()
        client.create_structured_message.side_effect = Exception("LLM error")
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert atoms == []

    def test_stage2_failure_skips_atom(self) -> None:
        """Exception from Stage 2 skips that atom, not the whole window."""
        client = MagicMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(1),
            Exception("Enrichment failed"),
        ]
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert atoms == []

    def test_validation_error_skips_window(self) -> None:
        """Pydantic ValidationError from Stage 1 skips the window."""
        from pydantic import ValidationError

        client = MagicMock()
        client.create_structured_message.side_effect = ValidationError.from_exception_data(
            title="CoarseExtractionResponse",
            line_errors=[],
        )
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert atoms == []


class TestExtractionRunnerStats:
    """Tests for extraction statistics tracking."""

    def test_stats_tracks_windows_processed(self) -> None:
        """Stats include count of windows processed."""
        client = MagicMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(1),
            _make_enrichment_response(),
            _make_coarse_response(1),
            _make_enrichment_response(),
        ]
        runner = ExtractionRunner(client=client)
        runner.extract([_make_context_window(), _make_context_window(thread_ts="2000.001")])
        assert runner.stats["windows_processed"] == 2

    def test_stats_tracks_atoms_produced(self) -> None:
        """Stats include count of atoms produced."""
        client = MagicMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(3),
            _make_enrichment_response(),
            _make_enrichment_response(),
            _make_enrichment_response(),
        ]
        runner = ExtractionRunner(client=client)
        runner.extract([_make_context_window()])
        assert runner.stats["atoms_produced"] == 3


class TestExtractionRunnerUsesResponseModel:
    """Tests that runner passes correct response_model for each stage."""

    def test_stage1_uses_coarse_response_model(self) -> None:
        """Stage 1 passes CoarseExtractionResponse as the response_model."""
        client = MagicMock()
        client.create_structured_message.return_value = CoarseExtractionResponse()
        runner = ExtractionRunner(client=client)
        runner.extract([_make_context_window()])
        call_kwargs = client.create_structured_message.call_args.kwargs
        assert call_kwargs["response_model"] is CoarseExtractionResponse

    def test_stage2_uses_enrichment_response_model(self) -> None:
        """Stage 2 passes EnrichmentResponse as the response_model."""
        client = MagicMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(1),
            _make_enrichment_response(),
        ]
        runner = ExtractionRunner(client=client)
        runner.extract([_make_context_window()])
        second_call = client.create_structured_message.call_args_list[1]
        assert second_call.kwargs["response_model"] is EnrichmentResponse


class TestAsyncExtractionRunnerExtract:
    """Tests for the async extract method with two-stage pipeline."""

    async def test_extracts_atoms_from_single_window(self) -> None:
        """Async runner extracts atoms via two-stage pipeline."""
        client = AsyncMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(1),
            _make_enrichment_response(),
        ]
        runner = AsyncExtractionRunner(client=client)
        atoms = await runner.extract([_make_context_window()])
        assert len(atoms) == 1
        assert isinstance(atoms[0], Atom)
        assert atoms[0].type == "DECISION"

    async def test_extracts_from_multiple_windows_concurrently(self) -> None:
        """Async runner processes multiple windows via asyncio.gather."""
        client = AsyncMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(1),
            _make_enrichment_response(),
            _make_coarse_response(1),
            _make_enrichment_response(),
        ]
        runner = AsyncExtractionRunner(client=client)
        windows = [_make_context_window(), _make_context_window(thread_ts="2000.001")]
        atoms = await runner.extract(windows)
        assert len(atoms) == 2

    async def test_empty_windows_produces_no_atoms(self) -> None:
        """Async runner with no windows produces no atoms."""
        client = AsyncMock()
        runner = AsyncExtractionRunner(client=client)
        atoms = await runner.extract([])
        assert atoms == []
        client.create_structured_message.assert_not_awaited()

    async def test_multiple_atoms_per_window(self) -> None:
        """Single window can produce multiple atoms in async runner."""
        client = AsyncMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(3),
            _make_enrichment_response(),
            _make_enrichment_response(),
            _make_enrichment_response(),
        ]
        runner = AsyncExtractionRunner(client=client)
        atoms = await runner.extract([_make_context_window()])
        assert len(atoms) == 3

    async def test_stats_tracks_windows_processed(self) -> None:
        """Async runner stats include count of windows processed."""
        client = AsyncMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(1),
            _make_enrichment_response(),
            _make_coarse_response(1),
            _make_enrichment_response(),
        ]
        runner = AsyncExtractionRunner(client=client)
        await runner.extract([_make_context_window(), _make_context_window(thread_ts="2000.001")])
        assert runner.stats["windows_processed"] == 2

    async def test_stats_tracks_atoms_produced(self) -> None:
        """Async runner stats include count of atoms produced."""
        client = AsyncMock()
        client.create_structured_message.side_effect = [
            _make_coarse_response(3),
            _make_enrichment_response(),
            _make_enrichment_response(),
            _make_enrichment_response(),
        ]
        runner = AsyncExtractionRunner(client=client)
        await runner.extract([_make_context_window()])
        assert runner.stats["atoms_produced"] == 3

    async def test_stage1_failure_skips_window(self) -> None:
        """Exception from Stage 1 is handled in async runner."""
        client = AsyncMock()
        client.create_structured_message.side_effect = Exception("LLM error")
        runner = AsyncExtractionRunner(client=client)
        atoms = await runner.extract([_make_context_window()])
        assert atoms == []

    async def test_respects_concurrency_limit(self) -> None:
        """Async runner limits concurrent LLM calls via semaphore."""
        client = AsyncMock()
        side_effects = []
        for _ in range(5):
            side_effects.append(_make_coarse_response(1))
            side_effects.append(_make_enrichment_response())
        client.create_structured_message.side_effect = side_effects
        runner = AsyncExtractionRunner(client=client, max_concurrency=2)
        windows = [_make_context_window(thread_ts=f"{i}.001") for i in range(5)]
        atoms = await runner.extract(windows)
        assert len(atoms) == 5
        assert runner.stats["windows_processed"] == 5

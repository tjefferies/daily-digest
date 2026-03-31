"""Tests for the extraction runner (sync and async).

Validates that the ExtractionRunner processes ContextWindows through
the LLM API using instructor for structured output and parses
responses into Atom objects. Uses a mock client to avoid real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from evercurrent.extraction.runner import AsyncExtractionRunner, ExtractionRunner
from evercurrent.ingestion.context_window import ContextWindow
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.models.responses import ExtractionResponse


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


def _make_atom(
    atom_type: str = "DECISION",
    summary: str = "Decided to use magnesium housing",
) -> Atom:
    """Create a valid Atom object for testing."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary=summary,
        detail="Team agreed on magnesium for weight reduction",
        source=AtomSource(
            channel="#chassis-design",
            thread_ts="1000.001",
            message_range=[0, 5],
            key_participants=["U001", "U002"],
        ),
        workstreams=AtomWorkstreams(
            originating="chassis",
            affected=["supply-chain", "thermal"],
        ),
        urgency="high",
        confidence=0.85,
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
    """Tests for the extract method."""

    def test_extracts_atoms_from_single_window(self) -> None:
        """Single context window produces atoms from structured API response."""
        client = MagicMock()
        atom = _make_atom()
        client.create_structured_message.return_value = ExtractionResponse(atoms=[atom])
        runner = ExtractionRunner(client=client)
        window = _make_context_window()
        atoms = runner.extract([window])
        assert len(atoms) == 1
        assert isinstance(atoms[0], Atom)
        assert atoms[0].type == "DECISION"

    def test_extracts_from_multiple_windows(self) -> None:
        """Multiple context windows each produce atoms."""
        client = MagicMock()
        atom1 = _make_atom(summary="Atom 1")
        atom2 = _make_atom(summary="Atom 2")
        client.create_structured_message.side_effect = [
            ExtractionResponse(atoms=[atom1]),
            ExtractionResponse(atoms=[atom2]),
        ]
        runner = ExtractionRunner(client=client)
        windows = [_make_context_window(), _make_context_window(thread_ts="2000.001")]
        atoms = runner.extract(windows)
        assert len(atoms) == 2

    def test_empty_response_produces_no_atoms(self) -> None:
        """Empty atom list from structured response produces no atoms."""
        client = MagicMock()
        client.create_structured_message.return_value = ExtractionResponse(atoms=[])
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
        """Single window can produce multiple atoms."""
        client = MagicMock()
        atoms_list = [_make_atom(summary=f"Atom {i}") for i in range(3)]
        client.create_structured_message.return_value = ExtractionResponse(atoms=atoms_list)
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert len(atoms) == 3


class TestExtractionRunnerErrorHandling:
    """Tests for structured output error handling."""

    def test_instructor_failure_skips_window(self) -> None:
        """Exception from structured output skips that window gracefully."""
        client = MagicMock()
        client.create_structured_message.side_effect = Exception("Instructor retry failed")
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert atoms == []

    def test_validation_error_skips_window(self) -> None:
        """Pydantic ValidationError from instructor skips the window."""
        from pydantic import ValidationError

        client = MagicMock()
        client.create_structured_message.side_effect = ValidationError.from_exception_data(
            title="ExtractionResponse",
            line_errors=[],
        )
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert atoms == []


class TestExtractionRunnerStats:
    """Tests for extraction statistics logging."""

    def test_stats_tracks_windows_processed(self) -> None:
        """Stats include count of windows processed."""
        client = MagicMock()
        client.create_structured_message.return_value = ExtractionResponse(
            atoms=[_make_atom()],
        )
        runner = ExtractionRunner(client=client)
        runner.extract([_make_context_window(), _make_context_window(thread_ts="2000.001")])
        assert runner.stats["windows_processed"] == 2

    def test_stats_tracks_atoms_produced(self) -> None:
        """Stats include count of atoms produced."""
        client = MagicMock()
        atoms_list = [_make_atom() for _ in range(3)]
        client.create_structured_message.return_value = ExtractionResponse(atoms=atoms_list)
        runner = ExtractionRunner(client=client)
        runner.extract([_make_context_window()])
        assert runner.stats["atoms_produced"] == 3


class TestExtractionRunnerUsesResponseModel:
    """Tests that extraction runner passes correct response_model to instructor."""

    def test_passes_extraction_response_model(self) -> None:
        """Runner passes ExtractionResponse as the response_model."""
        client = MagicMock()
        client.create_structured_message.return_value = ExtractionResponse(atoms=[])
        runner = ExtractionRunner(client=client)
        runner.extract([_make_context_window()])
        call_kwargs = client.create_structured_message.call_args.kwargs
        assert call_kwargs["response_model"] is ExtractionResponse


class TestAsyncExtractionRunnerExtract:
    """Tests for the async extract method with concurrent processing."""

    async def test_extracts_atoms_from_single_window(self) -> None:
        """Async runner extracts atoms from a single window."""
        client = AsyncMock()
        atom = _make_atom()
        client.create_structured_message.return_value = ExtractionResponse(atoms=[atom])
        runner = AsyncExtractionRunner(client=client)
        window = _make_context_window()
        atoms = await runner.extract([window])
        assert len(atoms) == 1
        assert isinstance(atoms[0], Atom)
        assert atoms[0].type == "DECISION"

    async def test_extracts_from_multiple_windows_concurrently(self) -> None:
        """Async runner processes multiple windows via asyncio.gather."""
        client = AsyncMock()
        atom1 = _make_atom(summary="Atom 1")
        atom2 = _make_atom(summary="Atom 2")
        client.create_structured_message.side_effect = [
            ExtractionResponse(atoms=[atom1]),
            ExtractionResponse(atoms=[atom2]),
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
        atoms_list = [_make_atom(summary=f"Atom {i}") for i in range(3)]
        client.create_structured_message.return_value = ExtractionResponse(atoms=atoms_list)
        runner = AsyncExtractionRunner(client=client)
        atoms = await runner.extract([_make_context_window()])
        assert len(atoms) == 3

    async def test_stats_tracks_windows_processed(self) -> None:
        """Async runner stats include count of windows processed."""
        client = AsyncMock()
        client.create_structured_message.return_value = ExtractionResponse(
            atoms=[_make_atom()],
        )
        runner = AsyncExtractionRunner(client=client)
        await runner.extract([_make_context_window(), _make_context_window(thread_ts="2000.001")])
        assert runner.stats["windows_processed"] == 2

    async def test_stats_tracks_atoms_produced(self) -> None:
        """Async runner stats include count of atoms produced."""
        client = AsyncMock()
        atoms_list = [_make_atom() for _ in range(3)]
        client.create_structured_message.return_value = ExtractionResponse(atoms=atoms_list)
        runner = AsyncExtractionRunner(client=client)
        await runner.extract([_make_context_window()])
        assert runner.stats["atoms_produced"] == 3

    async def test_instructor_failure_skips_window(self) -> None:
        """Exception from structured output is handled in async runner."""
        client = AsyncMock()
        client.create_structured_message.side_effect = Exception("Instructor retry failed")
        runner = AsyncExtractionRunner(client=client)
        atoms = await runner.extract([_make_context_window()])
        assert atoms == []

    async def test_respects_concurrency_limit(self) -> None:
        """Async runner limits concurrent LLM calls via semaphore."""
        client = AsyncMock()
        client.create_structured_message.return_value = ExtractionResponse(
            atoms=[_make_atom()],
        )
        runner = AsyncExtractionRunner(client=client, max_concurrency=2)
        windows = [_make_context_window(thread_ts=f"{i}.001") for i in range(5)]
        atoms = await runner.extract(windows)
        assert len(atoms) == 5
        assert runner.stats["windows_processed"] == 5

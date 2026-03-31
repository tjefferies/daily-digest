"""Tests for the extraction runner.

Validates that the ExtractionRunner processes ContextWindows through
the Anthropic API and parses responses into Atom objects.
Uses a mock client to avoid real API calls.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

from evercurrent.extraction.runner import ExtractionRunner
from evercurrent.ingestion.context_window import ContextWindow
from evercurrent.models.atom import Atom


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


def _make_atom_dict(**overrides: Any) -> dict[str, Any]:  # noqa: ANN401
    """Create a valid atom dict with optional overrides."""
    base: dict[str, Any] = {
        "atom_id": str(uuid4()),
        "type": "DECISION",
        "summary": "Decided to use magnesium housing",
        "detail": "Team agreed on magnesium for weight reduction",
        "source": {
            "channel": "#chassis-design",
            "thread_ts": "1000.001",
            "message_range": [0, 5],
            "key_participants": ["U001", "U002"],
        },
        "workstreams": {
            "originating": "chassis",
            "affected": ["supply-chain", "thermal"],
        },
        "urgency": "high",
        "confidence": 0.85,
        "implicit_decision": True,
        "phase_relevance": ["DVT"],
    }
    base.update(overrides)
    return base


def _mock_api_response(atoms: list[dict[str, Any]]) -> MagicMock:
    """Create a mock Anthropic API response with given atom JSON."""
    from anthropic.types import TextBlock

    response = MagicMock()
    content_block = TextBlock(type="text", text=json.dumps(atoms))
    response.content = [content_block]
    return response


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
        """Single context window produces atoms from API response."""
        client = MagicMock()
        atom_data = _make_atom_dict()
        client.messages.create.return_value = _mock_api_response([atom_data])
        runner = ExtractionRunner(client=client)
        window = _make_context_window()
        atoms = runner.extract([window])
        assert len(atoms) == 1
        assert isinstance(atoms[0], Atom)
        assert atoms[0].type == "DECISION"

    def test_extracts_from_multiple_windows(self) -> None:
        """Multiple context windows each produce atoms."""
        client = MagicMock()
        atom1 = _make_atom_dict(summary="Atom 1")
        atom2 = _make_atom_dict(summary="Atom 2")
        client.messages.create.side_effect = [
            _mock_api_response([atom1]),
            _mock_api_response([atom2]),
        ]
        runner = ExtractionRunner(client=client)
        windows = [_make_context_window(), _make_context_window(thread_ts="2000.001")]
        atoms = runner.extract(windows)
        assert len(atoms) == 2

    def test_empty_response_produces_no_atoms(self) -> None:
        """Empty JSON array from API produces no atoms."""
        client = MagicMock()
        client.messages.create.return_value = _mock_api_response([])
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert atoms == []

    def test_empty_windows_produces_no_atoms(self) -> None:
        """No context windows produces no atoms."""
        client = MagicMock()
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([])
        assert atoms == []
        client.messages.create.assert_not_called()

    def test_multiple_atoms_per_window(self) -> None:
        """Single window can produce multiple atoms."""
        client = MagicMock()
        atoms_data = [_make_atom_dict(summary=f"Atom {i}") for i in range(3)]
        client.messages.create.return_value = _mock_api_response(atoms_data)
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert len(atoms) == 3


class TestExtractionRunnerErrorHandling:
    """Tests for JSON parse failure handling."""

    def test_invalid_json_skips_window(self) -> None:
        """Invalid JSON response skips that window without crashing."""
        from anthropic.types import TextBlock

        client = MagicMock()
        bad_response = MagicMock()
        bad_response.content = [TextBlock(type="text", text="not valid json{")]
        client.messages.create.return_value = bad_response
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert atoms == []

    def test_invalid_atom_schema_skips_atom(self) -> None:
        """Atom that fails Pydantic validation is skipped."""
        client = MagicMock()
        bad_atom = {"type": "INVALID", "summary": "bad"}
        good_atom = _make_atom_dict()
        client.messages.create.return_value = _mock_api_response([bad_atom, good_atom])
        runner = ExtractionRunner(client=client)
        atoms = runner.extract([_make_context_window()])
        assert len(atoms) == 1
        assert atoms[0].summary == "Decided to use magnesium housing"


class TestExtractionRunnerStats:
    """Tests for extraction statistics logging."""

    def test_stats_tracks_windows_processed(self) -> None:
        """Stats include count of windows processed."""
        client = MagicMock()
        client.messages.create.return_value = _mock_api_response([_make_atom_dict()])
        runner = ExtractionRunner(client=client)
        runner.extract([_make_context_window(), _make_context_window(thread_ts="2000.001")])
        assert runner.stats["windows_processed"] == 2

    def test_stats_tracks_atoms_produced(self) -> None:
        """Stats include count of atoms produced."""
        client = MagicMock()
        atoms_data = [_make_atom_dict() for _ in range(3)]
        client.messages.create.return_value = _mock_api_response(atoms_data)
        runner = ExtractionRunner(client=client)
        runner.extract([_make_context_window()])
        assert runner.stats["atoms_produced"] == 3

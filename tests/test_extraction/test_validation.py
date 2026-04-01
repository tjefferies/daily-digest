"""Tests for batch validation with tool_use (single batch for all atoms).

Mocks the Anthropic batch client to avoid real API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from digest.extraction.validation import async_validate_atoms_batch
from digest.models.atom import Atom, AtomSource, AtomWorkstreams


def _make_atom(
    atom_type: str = "DECISION",
    confidence: float = 0.9,
    thread_ts: str = "1000.001",
) -> Atom:
    """Create an Atom for testing."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary=f"Test {atom_type} atom",
        detail="Detail text",
        source=AtomSource(
            channel="#chassis-design",
            thread_ts=thread_ts,
            message_range=[0, 5],
            key_participants=["U001"],
        ),
        workstreams=AtomWorkstreams(originating="chassis", affected=["thermal"]),
        urgency="medium",
        confidence=confidence,
    )


def _mock_batch_results(results: dict[str, dict]) -> MagicMock:
    """Create mock Anthropic client returning given validation results."""
    from anthropic import Anthropic

    client = MagicMock(spec=Anthropic)

    mock_batch = MagicMock()
    mock_batch.id = "batch_val_test"
    client.messages.batches.create.return_value = mock_batch

    mock_status = MagicMock()
    mock_status.processing_status = "ended"
    mock_status.request_counts.succeeded = len(results)
    mock_status.request_counts.processing = 0
    client.messages.batches.retrieve.return_value = mock_status

    batch_results = []
    for custom_id, tool_input in results.items():
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.input = tool_input
        r = MagicMock()
        r.custom_id = custom_id
        r.result.type = "succeeded"
        r.result.message.content = [tool_block]
        batch_results.append(r)

    client.messages.batches.results.return_value = batch_results
    return client


class TestBatchValidation:
    """Tests for single-batch validation."""

    @pytest.mark.asyncio
    async def test_valid_atoms_keep_confidence(self) -> None:
        """Valid atoms pass through with original confidence."""
        atom = _make_atom("DECISION", confidence=0.9)
        all_atoms = [atom]
        pairs = [(0, atom, "some context text")]

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "digest.extraction.validation.Anthropic",
                lambda: _mock_batch_results({"val-0": {"valid": True, "reason": ""}}),
            )
            result = await async_validate_atoms_batch(pairs, all_atoms)

        assert result[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_invalid_atoms_demoted(self) -> None:
        """Invalid atoms have confidence halved."""
        atom = _make_atom("DECISION", confidence=0.9)
        all_atoms = [atom]
        pairs = [(0, atom, "context")]

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "digest.extraction.validation.Anthropic",
                lambda: _mock_batch_results(
                    {"val-0": {"valid": False, "reason": "Fabricated details"}},
                ),
            )
            result = await async_validate_atoms_batch(pairs, all_atoms)

        assert result[0].confidence == pytest.approx(0.45)
        assert "Fabricated details" in result[0].detail

    @pytest.mark.asyncio
    async def test_single_batch_for_all_threads(self) -> None:
        """Atoms from different threads go in ONE batch, not per-thread."""
        a1 = _make_atom("DECISION", thread_ts="1000.001")
        a2 = _make_atom("SPEC_CHANGE", thread_ts="2000.001")
        a3 = _make_atom("ACTION_ITEM")  # not validated
        all_atoms = [a1, a2, a3]
        pairs = [
            (0, a1, "chassis thread context"),
            (1, a2, "drivetrain thread context"),
        ]

        mock_client = _mock_batch_results(
            {
                "val-0": {"valid": True, "reason": ""},
                "val-1": {"valid": True, "reason": ""},
            }
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "digest.extraction.validation.Anthropic",
                lambda: mock_client,
            )
            result = await async_validate_atoms_batch(pairs, all_atoms)

        # ONE batch call, not two
        mock_client.messages.batches.create.assert_called_once()
        assert len(result) == 3

"""Tests for two-pass validation via batch API with tool_use.

Mocks the Anthropic batch client to avoid real API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from evercurrent.extraction.validation import async_validate_atoms
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams


def _make_atom(
    atom_type: str = "DECISION",
    confidence: float = 0.9,
) -> Atom:
    """Create an Atom for testing."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary=f"Test {atom_type} atom",
        detail="Detail text",
        source=AtomSource(
            channel="#chassis-design",
            thread_ts="1000.001",
            message_range=[0, 5],
            key_participants=["U001"],
        ),
        workstreams=AtomWorkstreams(
            originating="chassis",
            affected=["thermal"],
        ),
        urgency="medium",
        confidence=confidence,
    )


def _mock_anthropic_client(valid: bool = True, reason: str = "") -> MagicMock:
    """Create a mock Anthropic client that returns batch results."""
    from anthropic import Anthropic

    client = MagicMock(spec=Anthropic)

    # Mock batch create
    mock_batch = MagicMock()
    mock_batch.id = "batch_test"
    client.messages.batches.create.return_value = mock_batch

    # Mock batch retrieve (immediately ended)
    mock_status = MagicMock()
    mock_status.processing_status = "ended"
    mock_status.request_counts.succeeded = 1
    mock_status.request_counts.processing = 0
    client.messages.batches.retrieve.return_value = mock_status

    # Mock batch results with tool_use block
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.input = {"valid": valid, "reason": reason}

    result = MagicMock()
    result.custom_id = "val-0"
    result.result.type = "succeeded"
    result.result.message.content = [tool_block]

    client.messages.batches.results.return_value = [result]

    return client


class TestBatchValidation:
    """Tests for batch-based validation with tool_use."""

    @pytest.mark.asyncio
    async def test_decision_atoms_are_validated(self) -> None:
        """DECISION atoms go through batch validation."""
        client = _mock_anthropic_client(valid=True)
        atom = _make_atom("DECISION")
        result = await async_validate_atoms([atom], client=client, context_text="text")
        assert len(result) == 1
        assert result[0].confidence == 0.9  # not demoted
        client.messages.batches.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_other_types_skip_validation(self) -> None:
        """Non-DECISION/SPEC_CHANGE atoms skip batch validation entirely."""
        client = _mock_anthropic_client()
        atoms = [_make_atom("ACTION_ITEM"), _make_atom("RISK")]
        result = await async_validate_atoms(atoms, client=client, context_text="text")
        client.messages.batches.create.assert_not_called()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_invalid_atom_demoted(self) -> None:
        """Atoms that fail validation have confidence halved."""
        client = _mock_anthropic_client(valid=False, reason="Fabricated details")
        atom = _make_atom("DECISION", confidence=0.9)
        result = await async_validate_atoms([atom], client=client, context_text="text")
        assert result[0].confidence == pytest.approx(0.45)
        assert "Fabricated details" in result[0].detail

    @pytest.mark.asyncio
    async def test_empty_atom_list(self) -> None:
        """Empty list returns empty without any API calls."""
        client = _mock_anthropic_client()
        result = await async_validate_atoms([], client=client, context_text="text")
        assert result == []
        client.messages.batches.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_types_only_validates_decision_spec(self) -> None:
        """Only DECISION and SPEC_CHANGE atoms go to batch, others pass through."""
        client = _mock_anthropic_client(valid=True)

        # Mock returns results for both validatable atoms
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.input = {"valid": True, "reason": ""}

        r0 = MagicMock()
        r0.custom_id = "val-0"
        r0.result.type = "succeeded"
        r0.result.message.content = [tool_block]

        r1 = MagicMock()
        r1.custom_id = "val-2"
        r1.result.type = "succeeded"
        r1.result.message.content = [tool_block]

        client.messages.batches.results.return_value = [r0, r1]

        atoms = [
            _make_atom("DECISION"),      # index 0 → validated
            _make_atom("ACTION_ITEM"),    # index 1 → skipped
            _make_atom("SPEC_CHANGE"),    # index 2 → validated
        ]
        result = await async_validate_atoms(atoms, client=client, context_text="text")
        assert len(result) == 3
        # All should keep original confidence (all valid)
        assert all(a.confidence == 0.9 for a in result)

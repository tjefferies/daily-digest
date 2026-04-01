"""Tests for two-pass validation of SPEC_CHANGE and DECISION atoms (sync and async).

Validates that high-stakes atoms get a second LLM pass to check
accuracy using instructor for structured output, with demotion
for atoms that fail validation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

from evercurrent.extraction.validation import async_validate_atoms
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.models.responses import ValidationResponse


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


class TestAsyncValidation:
    """Tests for async validation with concurrent LLM calls."""

    async def test_decision_atoms_are_validated(self) -> None:
        """Async validation validates DECISION atoms."""
        client = AsyncMock()
        client.create_structured_message.return_value = ValidationResponse(valid=True)
        atom = _make_atom("DECISION")
        result = await async_validate_atoms([atom], client=client, context_text="text")
        client.create_structured_message.assert_awaited_once()
        assert len(result) == 1

    async def test_other_types_skip_validation(self) -> None:
        """Async validation skips non-DECISION/SPEC_CHANGE atoms."""
        client = AsyncMock()
        atoms = [_make_atom("ACTION_ITEM"), _make_atom("RISK")]
        result = await async_validate_atoms(atoms, client=client, context_text="text")
        client.create_structured_message.assert_not_awaited()
        assert len(result) == 2

    async def test_invalid_atom_demoted(self) -> None:
        """Async validation demotes atoms that fail the second LLM pass."""
        client = AsyncMock()
        client.create_structured_message.return_value = ValidationResponse(
            valid=False, reason="Overstated"
        )
        atom = _make_atom("DECISION", confidence=0.9)
        result = await async_validate_atoms([atom], client=client, context_text="text")
        assert result[0].confidence == 0.45

    async def test_validates_concurrently(self) -> None:
        """Async validation processes multiple atoms concurrently."""
        client = AsyncMock()
        client.create_structured_message.return_value = ValidationResponse(valid=True)
        atoms = [_make_atom("DECISION"), _make_atom("SPEC_CHANGE")]
        result = await async_validate_atoms(atoms, client=client, context_text="text")
        assert client.create_structured_message.await_count == 2
        assert len(result) == 2

    async def test_empty_atom_list(self) -> None:
        """Async validation with empty list returns empty."""
        client = AsyncMock()
        result = await async_validate_atoms([], client=client, context_text="text")
        assert result == []

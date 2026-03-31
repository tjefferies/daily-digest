"""Tests for two-pass validation of SPEC_CHANGE and DECISION atoms.

Validates that high-stakes atoms get a second LLM pass to check
accuracy, with demotion for atoms that fail validation.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock
from uuid import uuid4

from anthropic.types import TextBlock

from evercurrent.extraction.validation import validate_atoms
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


def _mock_validation_response(valid: bool, reason: str = "") -> MagicMock:
    """Create a mock API response for validation."""
    data = {"valid": valid, "reason": reason}
    response = MagicMock()
    response.content = [TextBlock(type="text", text=json.dumps(data))]
    return response


class TestValidationTargeting:
    """Tests for which atoms get validated."""

    def test_decision_atoms_are_validated(self) -> None:
        """DECISION atoms trigger a validation call."""
        client = MagicMock()
        client.messages.create.return_value = _mock_validation_response(True)
        atom = _make_atom("DECISION")
        result = validate_atoms([atom], client=client, context_text="thread text")
        client.messages.create.assert_called_once()
        assert len(result) == 1

    def test_spec_change_atoms_are_validated(self) -> None:
        """SPEC_CHANGE atoms trigger a validation call."""
        client = MagicMock()
        client.messages.create.return_value = _mock_validation_response(True)
        atom = _make_atom("SPEC_CHANGE")
        validate_atoms([atom], client=client, context_text="thread text")
        client.messages.create.assert_called_once()

    def test_other_types_skip_validation(self) -> None:
        """Non-DECISION/SPEC_CHANGE atoms are not validated."""
        client = MagicMock()
        atoms = [_make_atom("ACTION_ITEM"), _make_atom("RISK"), _make_atom("BLOCKER")]
        result = validate_atoms(atoms, client=client, context_text="thread text")
        client.messages.create.assert_not_called()
        assert len(result) == 3


class TestValidationOutcomes:
    """Tests for validation pass/fail outcomes."""

    def test_valid_atom_keeps_confidence(self) -> None:
        """Atom that passes validation keeps its confidence."""
        client = MagicMock()
        client.messages.create.return_value = _mock_validation_response(True)
        atom = _make_atom("DECISION", confidence=0.9)
        result = validate_atoms([atom], client=client, context_text="text")
        assert result[0].confidence == 0.9

    def test_invalid_atom_demoted(self) -> None:
        """Atom that fails validation has confidence halved."""
        client = MagicMock()
        client.messages.create.return_value = _mock_validation_response(
            False,
            reason="Overstated the conclusion",
        )
        atom = _make_atom("DECISION", confidence=0.9)
        result = validate_atoms([atom], client=client, context_text="text")
        assert result[0].confidence == 0.45

    def test_invalid_atom_gets_warning(self) -> None:
        """Atom that fails validation gets a validation_warning in detail."""
        client = MagicMock()
        client.messages.create.return_value = _mock_validation_response(
            False,
            reason="Fabricated spec value",
        )
        atom = _make_atom("SPEC_CHANGE", confidence=0.85)
        result = validate_atoms([atom], client=client, context_text="text")
        assert "validation warning" in result[0].detail.lower()


class TestValidationEdgeCases:
    """Edge cases for validation."""

    def test_empty_atom_list(self) -> None:
        """Empty input returns empty output."""
        client = MagicMock()
        result = validate_atoms([], client=client, context_text="text")
        assert result == []

    def test_mixed_types(self) -> None:
        """Mix of validated and non-validated types."""
        client = MagicMock()
        client.messages.create.return_value = _mock_validation_response(True)
        atoms = [
            _make_atom("DECISION"),
            _make_atom("ACTION_ITEM"),
            _make_atom("SPEC_CHANGE"),
        ]
        result = validate_atoms(atoms, client=client, context_text="text")
        assert client.messages.create.call_count == 2
        assert len(result) == 3

    def test_invalid_json_response_demotes(self) -> None:
        """If validation response is unparseable, atom is demoted."""
        client = MagicMock()
        response = MagicMock()
        response.content = [TextBlock(type="text", text="not json")]
        client.messages.create.return_value = response
        atom = _make_atom("DECISION", confidence=0.8)
        result = validate_atoms([atom], client=client, context_text="text")
        assert result[0].confidence == 0.4

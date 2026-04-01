"""Tests for structured LLM response wrapper models."""

from __future__ import annotations

from uuid import uuid4

from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.models.digest import DigestSection
from evercurrent.models.responses import (
    DigestResponse,
    ValidationResponse,
)


def _make_atom() -> Atom:
    """Create a test Atom."""
    return Atom(
        atom_id=uuid4(),
        type="DECISION",
        summary="Test atom",
        detail="Detail",
        source=AtomSource(
            channel="#chassis",
            thread_ts="1.0",
            message_range=[0, 1],
            key_participants=["U001"],
        ),
        workstreams=AtomWorkstreams(originating="chassis"),
        urgency="medium",
        confidence=0.9,
    )


class TestValidationResponse:
    """Tests for the ValidationResponse wrapper model."""

    def test_valid_response(self) -> None:
        """ValidationResponse represents a passing validation."""
        resp = ValidationResponse(valid=True)
        assert resp.valid is True
        assert resp.reason == ""

    def test_invalid_response_with_reason(self) -> None:
        """ValidationResponse captures the failure reason."""
        resp = ValidationResponse(valid=False, reason="Overstated conclusion")
        assert resp.valid is False
        assert resp.reason == "Overstated conclusion"

    def test_reason_defaults_empty(self) -> None:
        """ValidationResponse reason defaults to empty string."""
        resp = ValidationResponse(valid=True)
        assert resp.reason == ""


class TestDigestResponse:
    """Tests for the DigestResponse wrapper model."""

    def test_empty_sections(self) -> None:
        """DigestResponse can hold an empty sections list."""
        resp = DigestResponse(sections=[])
        assert resp.sections == []

    def test_sections_with_items(self) -> None:
        """DigestResponse holds DigestSection objects."""
        section = DigestSection(
            section_type="requires_action",
            title="REQUIRES YOUR ACTION",
        )
        resp = DigestResponse(sections=[section])
        assert len(resp.sections) == 1
        assert resp.sections[0].section_type == "requires_action"

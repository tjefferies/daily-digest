"""Tests for Dimension 4: urgency scoring."""

from __future__ import annotations

from uuid import uuid4

from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.scoring.urgency import score_urgency


def _make_atom(urgency: str = "medium") -> Atom:
    """Create an Atom with given urgency."""
    return Atom(
        atom_id=uuid4(),
        type="DECISION",
        summary="Test",
        detail="Detail",
        source=AtomSource(channel="#test", thread_ts="1.0", message_range=[0, 1]),
        workstreams=AtomWorkstreams(originating="chassis"),
        urgency=urgency,
        confidence=0.9,
    )


class TestUrgencyScore:
    """Tests for urgency scoring."""

    def test_critical_scores_1(self) -> None:
        """Critical urgency scores 1.0."""
        assert score_urgency(_make_atom("critical")) == 1.0

    def test_high_scores_08(self) -> None:
        """High urgency scores 0.8."""
        assert score_urgency(_make_atom("high")) == 0.8

    def test_medium_scores_05(self) -> None:
        """Medium urgency scores 0.5."""
        assert score_urgency(_make_atom("medium")) == 0.5

    def test_low_scores_02(self) -> None:
        """Low urgency scores 0.2."""
        assert score_urgency(_make_atom("low")) == 0.2

    def test_all_scores_in_range(self) -> None:
        """All urgency scores are in [0, 1]."""
        for urg in ["low", "medium", "high", "critical"]:
            score = score_urgency(_make_atom(urg))
            assert 0.0 <= score <= 1.0

"""Tests for confidence threshold filter.

Validates that atoms below the confidence threshold are filtered out
and that filtering stats are tracked.
"""

from __future__ import annotations

from uuid import uuid4

from evercurrent.extraction.filter import confidence_filter
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams


def _make_atom(confidence: float) -> Atom:
    """Create an Atom with the given confidence score."""
    return Atom(
        atom_id=uuid4(),
        type="DECISION",
        summary=f"Test atom confidence={confidence}",
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


class TestConfidenceFilter:
    """Tests for the confidence_filter function."""

    def test_atoms_above_threshold_pass(self) -> None:
        """Atoms with confidence >= threshold are included."""
        atoms = [_make_atom(0.9), _make_atom(0.8), _make_atom(0.7)]
        result = confidence_filter(atoms, threshold=0.7)
        assert len(result.passed) == 3

    def test_atoms_below_threshold_filtered(self) -> None:
        """Atoms with confidence < threshold are excluded."""
        atoms = [_make_atom(0.5), _make_atom(0.3)]
        result = confidence_filter(atoms, threshold=0.7)
        assert len(result.passed) == 0
        assert len(result.filtered) == 2

    def test_mixed_confidences(self) -> None:
        """Mix of above and below threshold atoms."""
        atoms = [_make_atom(0.9), _make_atom(0.5), _make_atom(0.75)]
        result = confidence_filter(atoms, threshold=0.7)
        assert len(result.passed) == 2
        assert len(result.filtered) == 1

    def test_default_threshold_is_07(self) -> None:
        """Default threshold is 0.7 per section 4.4."""
        atoms = [_make_atom(0.69), _make_atom(0.71)]
        result = confidence_filter(atoms)
        assert len(result.passed) == 1
        assert len(result.filtered) == 1

    def test_custom_threshold(self) -> None:
        """Custom threshold overrides default."""
        atoms = [_make_atom(0.5), _make_atom(0.6)]
        result = confidence_filter(atoms, threshold=0.5)
        assert len(result.passed) == 2

    def test_empty_input(self) -> None:
        """Empty atom list returns empty result."""
        result = confidence_filter([], threshold=0.7)
        assert result.passed == []
        assert result.filtered == []

    def test_boundary_at_threshold(self) -> None:
        """Atom at exactly the threshold passes."""
        atoms = [_make_atom(0.7)]
        result = confidence_filter(atoms, threshold=0.7)
        assert len(result.passed) == 1


class TestFilterResultStats:
    """Tests for FilterResult statistics."""

    def test_stats_total_count(self) -> None:
        """Stats include total input count."""
        atoms = [_make_atom(0.9), _make_atom(0.5), _make_atom(0.3)]
        result = confidence_filter(atoms, threshold=0.7)
        assert result.total == 3

    def test_stats_passed_count(self) -> None:
        """Stats include passed count."""
        atoms = [_make_atom(0.9), _make_atom(0.5)]
        result = confidence_filter(atoms, threshold=0.7)
        assert result.passed_count == 1

    def test_stats_filtered_count(self) -> None:
        """Stats include filtered count."""
        atoms = [_make_atom(0.9), _make_atom(0.5)]
        result = confidence_filter(atoms, threshold=0.7)
        assert result.filtered_count == 1

"""Tests for Dimension 1: workstream proximity scoring."""

from __future__ import annotations

from uuid import uuid4

from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.models.persona import Persona, ScoringWeights
from evercurrent.scoring.workstream_proximity import score_workstream_proximity


def _make_atom(originating: str, affected: list[str] | None = None) -> Atom:
    """Create an Atom with given workstream tags."""
    return Atom(
        atom_id=uuid4(),
        type="DECISION",
        summary="Test",
        detail="Detail",
        source=AtomSource(
            channel="#chassis-design",
            thread_ts="1000.001",
            message_range=[0, 5],
        ),
        workstreams=AtomWorkstreams(
            originating=originating,
            affected=affected or [],
        ),
        urgency="medium",
        confidence=0.9,
    )


def _make_persona(affinities: dict[str, float]) -> Persona:
    """Create a Persona with given workstream affinities."""
    return Persona(
        user_id="U001",
        name="Test User",
        role_archetype="IC Engineer",
        title="Engineer",
        workstream_affinities=affinities,
        phase_context={},
        scoring_weights=ScoringWeights(
            workstream_proximity=0.30,
            role_type_alignment=0.20,
            phase_alignment=0.20,
            urgency=0.15,
            social_signal=0.15,
        ),
    )


class TestWorkstreamProximityScore:
    """Tests for workstream proximity scoring."""

    def test_high_affinity_originating(self) -> None:
        """Atom from persona's primary workstream scores high."""
        persona = _make_persona({"chassis": 1.0, "thermal": 0.5})
        atom = _make_atom("chassis")
        assert score_workstream_proximity(atom, persona) == 1.0

    def test_high_affinity_affected(self) -> None:
        """Atom affecting persona's primary workstream scores high."""
        persona = _make_persona({"chassis": 1.0, "thermal": 0.5})
        atom = _make_atom("supply-chain", affected=["chassis"])
        assert score_workstream_proximity(atom, persona) == 1.0

    def test_max_across_all_workstreams(self) -> None:
        """Score is max affinity across originating + affected."""
        persona = _make_persona({"chassis": 0.3, "thermal": 0.8, "supply-chain": 0.5})
        atom = _make_atom("chassis", affected=["thermal", "supply-chain"])
        assert score_workstream_proximity(atom, persona) == 0.8

    def test_no_affinity_returns_zero(self) -> None:
        """Unknown workstream scores 0."""
        persona = _make_persona({"chassis": 1.0})
        atom = _make_atom("firmware")
        assert score_workstream_proximity(atom, persona) == 0.0

    def test_partial_overlap(self) -> None:
        """Partial affinity overlap uses the best match."""
        persona = _make_persona({"chassis": 0.3, "sensors": 0.9})
        atom = _make_atom("chassis", affected=["drivetrain"])
        assert score_workstream_proximity(atom, persona) == 0.3

    def test_score_between_0_and_1(self) -> None:
        """Score is always in [0, 1] range."""
        persona = _make_persona({"chassis": 0.5})
        atom = _make_atom("chassis")
        score = score_workstream_proximity(atom, persona)
        assert 0.0 <= score <= 1.0

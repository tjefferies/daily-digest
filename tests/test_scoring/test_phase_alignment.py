"""Tests for Dimension 3: phase alignment scoring."""

from __future__ import annotations

from uuid import uuid4

from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.models.persona import Persona, ScoringWeights
from evercurrent.scoring.phase_alignment import score_phase_alignment


def _make_atom(phases: list[str] | None = None) -> Atom:
    """Create an Atom with given phase_relevance."""
    return Atom(
        atom_id=uuid4(),
        type="DECISION",
        summary="Test",
        detail="Detail",
        source=AtomSource(channel="#test", thread_ts="1.0", message_range=[0, 1]),
        workstreams=AtomWorkstreams(originating="chassis"),
        urgency="medium",
        confidence=0.9,
        phase_relevance=phases or [],
    )


def _make_persona(phase_context: dict[str, str] | None = None) -> Persona:
    """Create a Persona with given phase context."""
    return Persona(
        user_id="U001",
        name="Test",
        role_archetype="IC Engineer",
        title="Test",
        workstream_affinities={},
        phase_context=phase_context or {},
        scoring_weights=ScoringWeights(
            workstream_proximity=0.30,
            role_type_alignment=0.20,
            phase_alignment=0.20,
            urgency=0.15,
            social_signal=0.15,
        ),
    )


class TestPhaseAlignment:
    """Tests for phase alignment scoring."""

    def test_matching_phase_scores_high(self) -> None:
        """Atom relevant to persona's active phase scores 1.0."""
        atom = _make_atom(["DVT"])
        persona = _make_persona({"chassis": "DVT"})
        assert score_phase_alignment(atom, persona) == 1.0

    def test_non_matching_phase_scores_by_distance(self) -> None:
        """Atom for different phase scores by distance from persona phase."""
        atom = _make_atom(["Concept"])
        persona = _make_persona({"chassis": "DVT"})
        # Concept → DVT = distance 2 → 0.5
        assert score_phase_alignment(atom, persona) == 0.5

    def test_no_phase_relevance_default(self) -> None:
        """Atom with no phases gets default score."""
        atom = _make_atom([])
        persona = _make_persona({"chassis": "DVT"})
        assert score_phase_alignment(atom, persona) == 0.5

    def test_no_persona_phases_default(self) -> None:
        """Persona with no phase context gets default."""
        atom = _make_atom(["DVT"])
        persona = _make_persona({})
        assert score_phase_alignment(atom, persona) == 0.5

    def test_partial_overlap(self) -> None:
        """If any phase overlaps, score is 1.0."""
        atom = _make_atom(["EVT", "DVT"])
        persona = _make_persona({"chassis": "DVT", "thermal": "EVT"})
        assert score_phase_alignment(atom, persona) == 1.0

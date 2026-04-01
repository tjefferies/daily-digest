"""Tests for scoring dimension calibration.

Validates that all five scoring dimensions produce well-distributed
values in [0, 1] and that persona weights control relative influence
proportionally - no single dimension dominates ranking.
"""

from __future__ import annotations

from uuid import uuid4

from digest.models.atom import Atom, AtomSource, AtomWorkstreams
from digest.models.persona import DigestPreferences, Persona, ScoringWeights
from digest.scoring.composite import score_atoms
from digest.scoring.phase_alignment import score_phase_alignment
from digest.scoring.social_signal import score_social_signal
from digest.scoring.urgency import score_urgency


def _make_atom(
    urgency: str = "medium",
    workstream: str = "chassis",
    participants: list[str] | None = None,
    phases: list[str] | None = None,
    atom_type: str = "DECISION",
) -> Atom:
    """Create an Atom with configurable fields."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary="Test",
        detail="Detail",
        source=AtomSource(
            channel="#test",
            thread_ts="1.0",
            message_range=[0, 1],
            key_participants=participants or [],
        ),
        workstreams=AtomWorkstreams(originating=workstream),
        urgency=urgency,
        confidence=0.9,
        phase_relevance=phases or [],
    )


def _make_persona(
    user_id: str = "U001",
    affinities: dict[str, float] | None = None,
    phase_context: dict[str, str] | None = None,
    collaborators: list[str] | None = None,
    weights: ScoringWeights | None = None,
) -> Persona:
    """Create a Persona with configurable fields."""
    return Persona(
        user_id=user_id,
        name="Test",
        role_archetype="IC Engineer",
        title="Test",
        workstream_affinities=affinities or {"chassis": 0.9},
        phase_context=phase_context or {"chassis": "DVT"},
        scoring_weights=weights
        or ScoringWeights(
            workstream_proximity=0.30,
            role_type_alignment=0.20,
            phase_alignment=0.20,
            urgency=0.15,
            social_signal=0.15,
        ),
        collaborator_graph=collaborators or [],
        digest_preferences=DigestPreferences(),
    )


class TestUrgencyCalibration:
    """Tests that urgency scores are evenly distributed."""

    def test_uniform_spacing(self) -> None:
        """Urgency levels have equal spacing between them."""
        scores = [score_urgency(_make_atom(u)) for u in ["low", "medium", "high", "critical"]]
        gaps = [scores[i + 1] - scores[i] for i in range(len(scores) - 1)]
        # All gaps should be equal (uniform spacing)
        assert all(abs(g - gaps[0]) < 0.01 for g in gaps)

    def test_spans_full_range(self) -> None:
        """Urgency scores span from 0.25 to 1.0."""
        low = score_urgency(_make_atom("low"))
        critical = score_urgency(_make_atom("critical"))
        assert low == 0.25
        assert critical == 1.0


class TestPhaseAlignmentCalibration:
    """Tests that phase alignment uses graduated scoring."""

    def test_exact_match_scores_highest(self) -> None:
        """Exact phase match scores 1.0."""
        atom = _make_atom(phases=["DVT"])
        persona = _make_persona(phase_context={"chassis": "DVT"})
        assert score_phase_alignment(atom, persona) == 1.0

    def test_adjacent_phase_scores_intermediate(self) -> None:
        """Adjacent phase (1 step) scores between no_overlap and match."""
        atom = _make_atom(phases=["EVT"])
        persona = _make_persona(phase_context={"chassis": "DVT"})
        score = score_phase_alignment(atom, persona)
        assert 0.5 < score < 1.0

    def test_distant_phase_scores_lower(self) -> None:
        """Distant phase (2+ steps) scores lower than adjacent."""
        atom_adjacent = _make_atom(phases=["EVT"])
        atom_distant = _make_atom(phases=["Concept"])
        persona = _make_persona(phase_context={"chassis": "DVT"})
        adjacent_score = score_phase_alignment(atom_adjacent, persona)
        distant_score = score_phase_alignment(atom_distant, persona)
        assert distant_score < adjacent_score

    def test_phase_scoring_is_graduated(self) -> None:
        """Phase scores differ by distance, not just binary overlap."""
        # Use EVT persona so Concept=1, EVT=0, DVT=1, PVT=2, MP=3
        # gives 4 distinct distances
        persona = _make_persona(phase_context={"chassis": "EVT"})
        scores = set()
        for phase in ["Concept", "EVT", "DVT", "PVT", "MP"]:
            scores.add(score_phase_alignment(_make_atom(phases=[phase]), persona))
        assert len(scores) >= 4, f"Only {len(scores)} distinct scores: {scores}"


class TestSocialSignalCalibration:
    """Tests that social signal has differentiated values."""

    def test_no_participants_differs_from_unknown(self) -> None:
        """No participants (neutral) scores differently from unknown participants."""
        no_parts = score_social_signal(
            _make_atom(participants=[]),
            _make_persona(collaborators=["U002"]),
        )
        unknown = score_social_signal(
            _make_atom(participants=["U099"]),
            _make_persona(collaborators=["U002"]),
        )
        assert no_parts != unknown

    def test_four_distinct_score_levels(self) -> None:
        """Social signal produces at least 4 distinct score levels."""
        persona = _make_persona(user_id="U001", collaborators=["U002"])
        scores = {
            score_social_signal(_make_atom(participants=[]), persona),
            score_social_signal(_make_atom(participants=["U001"]), persona),
            score_social_signal(_make_atom(participants=["U002"]), persona),
            score_social_signal(_make_atom(participants=["U099"]), persona),
        }
        assert len(scores) == 4


class TestWeightProportionality:
    """Tests that changing a weight proportionally affects composite scores."""

    def test_doubling_urgency_weight_increases_urgency_influence(self) -> None:
        """When urgency weight doubles, urgency contribution roughly doubles."""
        atom_high = _make_atom(urgency="critical", phases=["DVT"])
        atom_low = _make_atom(urgency="low", phases=["DVT"])

        baseline_weights = ScoringWeights(
            workstream_proximity=0.25,
            role_type_alignment=0.25,
            phase_alignment=0.25,
            urgency=0.10,
            social_signal=0.15,
        )
        boosted_weights = ScoringWeights(
            workstream_proximity=0.20,
            role_type_alignment=0.20,
            phase_alignment=0.20,
            urgency=0.25,
            social_signal=0.15,
        )

        persona_base = _make_persona(weights=baseline_weights)
        persona_boost = _make_persona(weights=boosted_weights)

        base_results = score_atoms([atom_high, atom_low], persona_base)
        boost_results = score_atoms([atom_high, atom_low], persona_boost)

        base_gap = base_results[0].score - base_results[1].score
        boost_gap = boost_results[0].score - boost_results[1].score

        # Boosted urgency weight should widen the gap between critical and low
        assert boost_gap > base_gap

    def test_no_single_dimension_dominates(self) -> None:
        """No dimension alone can produce > 0.35 of the composite score."""
        # With equal weights (0.20 each), max contribution = 0.20 * 1.0 = 0.20
        equal_weights = ScoringWeights(
            workstream_proximity=0.20,
            role_type_alignment=0.20,
            phase_alignment=0.20,
            urgency=0.20,
            social_signal=0.20,
        )
        atom = _make_atom(
            urgency="critical",
            workstream="chassis",
            participants=["U001"],
            phases=["DVT"],
            atom_type="SPEC_CHANGE",
        )
        persona = _make_persona(
            user_id="U001",
            affinities={"chassis": 1.0},
            phase_context={"chassis": "DVT"},
            weights=equal_weights,
        )
        results = score_atoms([atom], persona)
        b = results[0].breakdown

        # With equal weights, each dimension contributes 0.20 * score
        # No single contribution should exceed 0.35 of total composite
        composite = results[0].score
        for dim_score in [
            b.workstream_proximity,
            b.role_type_alignment,
            b.phase_alignment,
            b.urgency,
            b.social_signal,
        ]:
            contribution = 0.20 * dim_score
            assert contribution / composite <= 0.35

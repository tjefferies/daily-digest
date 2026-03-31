"""Tests for composite scoring, atom ranking, and critical threshold."""

from __future__ import annotations

from uuid import uuid4

from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.models.persona import DigestPreferences, Persona, ScoringWeights
from evercurrent.scoring.composite import ScoreBreakdown, ScoredAtom, score_atoms


def _make_atom(
    atom_type: str = "DECISION",
    urgency: str = "medium",
    workstream: str = "chassis",
    affected: list[str] | None = None,
    participants: list[str] | None = None,
    phases: list[str] | None = None,
) -> Atom:
    """Create an Atom with configurable fields."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary="Test atom",
        detail="Detail",
        source=AtomSource(
            channel="#test",
            thread_ts="1.0",
            message_range=[0, 1],
            key_participants=participants or [],
        ),
        workstreams=AtomWorkstreams(
            originating=workstream,
            affected=affected or [],
        ),
        urgency=urgency,
        confidence=0.9,
        phase_relevance=phases or [],
    )


def _make_persona(
    role: str = "IC Engineer",
    affinities: dict[str, float] | None = None,
    phase_context: dict[str, str] | None = None,
    collaborators: list[str] | None = None,
    user_id: str = "U001",
    critical_threshold: float = 0.85,
    max_items: int = 25,
) -> Persona:
    """Create a Persona with configurable fields."""
    return Persona(
        user_id=user_id,
        name="Test User",
        role_archetype=role,
        title="Test",
        workstream_affinities=affinities or {"chassis": 0.9},
        phase_context=phase_context or {"chassis": "DVT"},
        scoring_weights=ScoringWeights(
            workstream_proximity=0.30,
            role_type_alignment=0.20,
            phase_alignment=0.20,
            urgency=0.15,
            social_signal=0.15,
        ),
        collaborator_graph=collaborators or [],
        digest_preferences=DigestPreferences(
            critical_threshold=critical_threshold,
            max_items=max_items,
        ),
    )


class TestScoredAtomModel:
    """Tests for the ScoredAtom data model."""

    def test_scored_atom_has_required_fields(self) -> None:
        """ScoredAtom contains atom, composite score, and breakdown."""
        atom = _make_atom()
        breakdown = ScoreBreakdown(
            workstream_proximity=0.9,
            role_type_alignment=0.7,
            phase_alignment=1.0,
            urgency=0.5,
            social_signal=0.3,
        )
        scored = ScoredAtom(
            atom=atom,
            score=0.72,
            breakdown=breakdown,
            critical=False,
        )
        assert scored.atom is atom
        assert scored.score == 0.72
        assert scored.breakdown.workstream_proximity == 0.9
        assert scored.critical is False

    def test_scored_atom_critical_flag(self) -> None:
        """ScoredAtom critical flag can be True."""
        atom = _make_atom()
        breakdown = ScoreBreakdown(
            workstream_proximity=1.0,
            role_type_alignment=1.0,
            phase_alignment=1.0,
            urgency=1.0,
            social_signal=1.0,
        )
        scored = ScoredAtom(atom=atom, score=1.0, breakdown=breakdown, critical=True)
        assert scored.critical is True


class TestCompositeScoring:
    """Tests for composite score computation."""

    def test_composite_is_weighted_sum(self) -> None:
        """Composite score equals sum of weight * dimension score."""
        atom = _make_atom(
            atom_type="SPEC_CHANGE",
            urgency="critical",
            workstream="chassis",
            participants=["U001"],
            phases=["DVT"],
        )
        persona = _make_persona(
            role="IC Engineer",
            affinities={"chassis": 1.0},
            phase_context={"chassis": "DVT"},
            user_id="U001",
        )
        results = score_atoms([atom], persona)
        assert len(results) == 1
        scored = results[0]
        # Manual calculation:
        # workstream=1.0, role_type=1.0, phase=1.0, urgency=1.0, social=1.0
        # composite = 0.30*1 + 0.20*1 + 0.20*1 + 0.15*1 + 0.15*1 = 1.0
        assert scored.score == 1.0

    def test_composite_partial_scores(self) -> None:
        """Composite correctly weights partial dimension scores."""
        atom = _make_atom(
            atom_type="STATUS_UPDATE",
            urgency="low",
            workstream="thermal",
            phases=["EVT"],
        )
        persona = _make_persona(
            affinities={"chassis": 0.9, "thermal": 0.4},
            phase_context={"chassis": "DVT"},
        )
        results = score_atoms([atom], persona)
        scored = results[0]
        # Each dimension score should be in [0, 1]
        b = scored.breakdown
        assert 0.0 <= b.workstream_proximity <= 1.0
        assert 0.0 <= b.role_type_alignment <= 1.0
        assert 0.0 <= b.phase_alignment <= 1.0
        assert 0.0 <= b.urgency <= 1.0
        assert 0.0 <= b.social_signal <= 1.0
        # Composite should be weighted sum
        expected = (
            0.30 * b.workstream_proximity
            + 0.20 * b.role_type_alignment
            + 0.20 * b.phase_alignment
            + 0.15 * b.urgency
            + 0.15 * b.social_signal
        )
        assert abs(scored.score - expected) < 1e-9

    def test_empty_atoms_returns_empty(self) -> None:
        """Scoring empty list returns empty list."""
        results = score_atoms([], _make_persona())
        assert results == []


class TestAtomRanking:
    """Tests for descending score ranking."""

    def test_atoms_sorted_descending(self) -> None:
        """Results are sorted by composite score descending."""
        atoms = [
            _make_atom(urgency="low"),
            _make_atom(urgency="critical"),
            _make_atom(urgency="high"),
        ]
        persona = _make_persona()
        results = score_atoms(atoms, persona)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_n_limit(self) -> None:
        """Only top N atoms are returned when max_items is set."""
        atoms = [_make_atom(urgency=u) for u in ["low", "medium", "high"] * 5]
        persona = _make_persona(max_items=3)
        results = score_atoms(atoms, persona)
        assert len(results) == 3

    def test_top_n_default_25(self) -> None:
        """Default max_items is 25."""
        atoms = [_make_atom() for _ in range(30)]
        persona = _make_persona()
        results = score_atoms(atoms, persona)
        assert len(results) == 25


class TestCriticalThreshold:
    """Tests for critical threshold flagging."""

    def test_above_threshold_flagged_critical(self) -> None:
        """Atoms scoring above critical_threshold are flagged."""
        atom = _make_atom(
            atom_type="SPEC_CHANGE",
            urgency="critical",
            workstream="chassis",
            participants=["U001"],
            phases=["DVT"],
        )
        persona = _make_persona(
            role="IC Engineer",
            affinities={"chassis": 1.0},
            phase_context={"chassis": "DVT"},
            user_id="U001",
            critical_threshold=0.85,
        )
        results = score_atoms([atom], persona)
        assert results[0].critical is True

    def test_below_threshold_not_critical(self) -> None:
        """Atoms scoring below critical_threshold are not flagged."""
        atom = _make_atom(urgency="low", workstream="thermal")
        persona = _make_persona(
            affinities={"thermal": 0.1},
            phase_context={},
            critical_threshold=0.85,
        )
        results = score_atoms([atom], persona)
        assert results[0].critical is False

    def test_critical_atoms_included_beyond_top_n(self) -> None:
        """Critical atoms are always included even if beyond top N."""
        low_atoms = [_make_atom(urgency="low", workstream="thermal") for _ in range(5)]
        critical_atom = _make_atom(
            atom_type="SPEC_CHANGE",
            urgency="critical",
            workstream="chassis",
            participants=["U001"],
            phases=["DVT"],
        )
        atoms = [*low_atoms, critical_atom]
        persona = _make_persona(
            role="IC Engineer",
            affinities={"chassis": 1.0, "thermal": 0.1},
            phase_context={"chassis": "DVT"},
            user_id="U001",
            critical_threshold=0.85,
            max_items=2,
        )
        results = score_atoms(atoms, persona)
        # Should have at least the critical atom even though max_items=2
        critical_results = [r for r in results if r.critical]
        assert len(critical_results) >= 1

    def test_custom_threshold(self) -> None:
        """Custom threshold is respected."""
        atom = _make_atom(
            atom_type="SPEC_CHANGE",
            urgency="high",
            workstream="chassis",
            phases=["DVT"],
        )
        # With a very high threshold, atom should not be critical
        persona_high = _make_persona(
            affinities={"chassis": 0.8},
            phase_context={"chassis": "DVT"},
            critical_threshold=0.99,
        )
        results_high = score_atoms([atom], persona_high)

        # With a low threshold, same atom should be critical
        persona_low = _make_persona(
            affinities={"chassis": 0.8},
            phase_context={"chassis": "DVT"},
            critical_threshold=0.3,
        )
        results_low = score_atoms([atom], persona_low)

        assert not results_high[0].critical
        assert results_low[0].critical


class TestScoreBreakdown:
    """Tests for per-dimension score breakdown."""

    def test_breakdown_matches_individual_scorers(self) -> None:
        """Breakdown values match individual dimension scorers."""
        from evercurrent.scoring.phase_alignment import score_phase_alignment
        from evercurrent.scoring.role_alignment import score_role_alignment
        from evercurrent.scoring.social_signal import score_social_signal
        from evercurrent.scoring.urgency import score_urgency
        from evercurrent.scoring.workstream_proximity import (
            score_workstream_proximity,
        )

        atom = _make_atom(
            atom_type="BLOCKER",
            urgency="high",
            workstream="chassis",
            participants=["U002"],
            phases=["DVT"],
        )
        persona = _make_persona(
            role="Eng Manager",
            affinities={"chassis": 0.7},
            phase_context={"chassis": "DVT"},
            collaborators=["U002"],
            user_id="U001",
        )
        results = score_atoms([atom], persona)
        b = results[0].breakdown

        assert b.workstream_proximity == score_workstream_proximity(atom, persona)
        assert b.role_type_alignment == score_role_alignment(atom, persona)
        assert b.phase_alignment == score_phase_alignment(atom, persona)
        assert b.urgency == score_urgency(atom)
        assert b.social_signal == score_social_signal(atom, persona)

"""Tests for Dimension 2: role-type alignment scoring."""

from __future__ import annotations

from uuid import uuid4

from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.models.persona import Persona, ScoringWeights
from evercurrent.scoring.role_alignment import score_role_alignment


def _make_atom(atom_type: str = "DECISION") -> Atom:
    """Create an Atom with the given type."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary="Test",
        detail="Detail",
        source=AtomSource(channel="#test", thread_ts="1.0", message_range=[0, 1]),
        workstreams=AtomWorkstreams(originating="chassis"),
        urgency="medium",
        confidence=0.9,
    )


def _make_persona(role: str = "IC Engineer") -> Persona:
    """Create a Persona with given role archetype."""
    return Persona(
        user_id="U001",
        name="Test",
        role_archetype=role,
        title="Test",
        workstream_affinities={},
        phase_context={},
        scoring_weights=ScoringWeights(
            workstream_proximity=0.30,
            role_type_alignment=0.20,
            phase_alignment=0.20,
            urgency=0.15,
            social_signal=0.15,
        ),
    )


class TestRoleAlignment:
    """Tests for role-type alignment scoring."""

    def test_engineer_spec_change_high(self) -> None:
        """IC Engineer scores high on SPEC_CHANGE."""
        score = score_role_alignment(_make_atom("SPEC_CHANGE"), _make_persona("IC Engineer"))
        assert score == 1.0

    def test_manager_blocker_high(self) -> None:
        """Eng Manager scores high on BLOCKER."""
        score = score_role_alignment(_make_atom("BLOCKER"), _make_persona("Eng Manager"))
        assert score == 1.0

    def test_supply_chain_risk_high(self) -> None:
        """Supply Chain scores high on RISK."""
        score = score_role_alignment(_make_atom("RISK"), _make_persona("Supply Chain"))
        assert score == 1.0

    def test_score_in_range(self) -> None:
        """All scores are in [0, 1]."""
        for role in ["IC Engineer", "Eng Manager", "Program Manager", "Supply Chain", "Executive"]:
            for atom_type in [
                "DECISION",
                "SPEC_CHANGE",
                "ACTION_ITEM",
                "BLOCKER",
                "RISK",
                "TEST_RESULT",
                "STATUS_UPDATE",
                "QUESTION",
            ]:
                score = score_role_alignment(_make_atom(atom_type), _make_persona(role))
                assert 0.0 <= score <= 1.0, f"{role}/{atom_type}: {score}"

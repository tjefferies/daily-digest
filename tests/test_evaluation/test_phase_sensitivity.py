"""Eval Criterion 3: Phase-toggle produces visible digest content shift.

Tests that changing a workstream's phase via override changes the
composite scores and atom ranking for a persona.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from evercurrent.context.personas import DEMO_PERSONAS
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.scoring.composite import score_atoms

if TYPE_CHECKING:
    from evercurrent.models.persona import Persona


def _get_persona(user_id: str) -> Persona:
    """Look up demo persona by user_id."""
    return next(p for p in DEMO_PERSONAS if p.user_id == user_id)


def _make_atom(
    atom_type: str,
    workstream: str,
    urgency: str = "medium",
    phases: list[str] | None = None,
    summary: str = "Test",
) -> Atom:
    """Create an atom for phase sensitivity testing."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary=summary,
        detail="Detail",
        source=AtomSource(
            channel=f"#{workstream}",
            thread_ts="1.0",
            message_range=[0, 1],
        ),
        workstreams=AtomWorkstreams(originating=workstream),
        urgency=urgency,
        confidence=0.9,
        phase_relevance=phases or [],
    )


# Atoms with different phase relevance - some EVT, some DVT
EVT_ATOM = _make_atom(
    "SPEC_CHANGE",
    "thermal",
    urgency="high",
    phases=["EVT"],
    summary="Thermal pad spec changed for EVT prototype",
)

DVT_ATOM = _make_atom(
    "TEST_RESULT",
    "thermal",
    urgency="high",
    phases=["DVT"],
    summary="Thermal DVT validation testing results",
)

BOTH_PHASES_ATOM = _make_atom(
    "RISK",
    "thermal",
    urgency="medium",
    phases=["EVT", "DVT"],
    summary="Thermal risk spans both EVT and DVT",
)

NON_THERMAL_ATOM = _make_atom(
    "STATUS_UPDATE",
    "chassis",
    urgency="medium",
    phases=["DVT"],
    summary="Chassis DVT progress update",
)

PHASE_TEST_ATOMS = [EVT_ATOM, DVT_ATOM, BOTH_PHASES_ATOM, NON_THERMAL_ATOM]


def _score_with_phase(persona: Persona, phase_context: dict[str, str]) -> list:  # noqa: ANN001
    """Score atoms with a modified phase context."""
    modified = persona.model_copy(update={"phase_context": phase_context})
    return score_atoms(PHASE_TEST_ATOMS, modified)


class TestPhaseSensitivity:
    """Validate phase override produces visible scoring changes."""

    def test_evt_atom_scores_higher_in_evt_phase(self) -> None:
        """EVT atom scores higher when thermal is in EVT vs DVT."""
        maya = _get_persona("U001")
        # Thermal in EVT (default for Maya)
        evt_results = _score_with_phase(maya, {"chassis": "DVT", "thermal": "EVT"})
        # Thermal overridden to DVT
        dvt_results = _score_with_phase(maya, {"chassis": "DVT", "thermal": "DVT"})

        evt_score_in_evt = next(r.score for r in evt_results if r.atom is EVT_ATOM)
        evt_score_in_dvt = next(r.score for r in dvt_results if r.atom is EVT_ATOM)

        assert evt_score_in_evt > evt_score_in_dvt

    def test_dvt_atom_scores_higher_in_dvt_phase(self) -> None:
        """DVT atom scores higher when thermal is in DVT vs Concept.

        We use Concept as the baseline (not EVT) to avoid overlap with
        chassis:DVT which would make phase alignment always 1.0.
        """
        maya = _get_persona("U001")
        concept_results = _score_with_phase(maya, {"chassis": "Concept", "thermal": "Concept"})
        dvt_results = _score_with_phase(maya, {"chassis": "DVT", "thermal": "DVT"})

        dvt_score_in_concept = next(r.score for r in concept_results if r.atom is DVT_ATOM)
        dvt_score_in_dvt = next(r.score for r in dvt_results if r.atom is DVT_ATOM)

        assert dvt_score_in_dvt > dvt_score_in_concept

    def test_ranking_changes_with_phase_toggle(self) -> None:
        """At least 2 items change position when phase is toggled."""
        maya = _get_persona("U001")
        evt_results = _score_with_phase(maya, {"chassis": "DVT", "thermal": "EVT"})
        dvt_results = _score_with_phase(maya, {"chassis": "DVT", "thermal": "DVT"})

        evt_order = [r.atom.atom_id for r in evt_results]
        dvt_order = [r.atom.atom_id for r in dvt_results]

        position_changes = sum(1 for i, atom_id in enumerate(evt_order) if atom_id != dvt_order[i])
        assert position_changes >= 2, (
            f"Only {position_changes} items changed position. "
            f"EVT order: {evt_order}, DVT order: {dvt_order}"
        )

    def test_both_phases_atom_scores_high_in_either(self) -> None:
        """Atom relevant to both EVT and DVT scores well in both phases."""
        maya = _get_persona("U001")
        evt_results = _score_with_phase(maya, {"chassis": "DVT", "thermal": "EVT"})
        dvt_results = _score_with_phase(maya, {"chassis": "DVT", "thermal": "DVT"})

        both_in_evt = next(r.score for r in evt_results if r.atom is BOTH_PHASES_ATOM)
        both_in_dvt = next(r.score for r in dvt_results if r.atom is BOTH_PHASES_ATOM)

        # Phase alignment should give 1.0 in both cases (overlap exists)
        assert both_in_evt == both_in_dvt

    def test_non_thermal_atom_unaffected_by_thermal_phase_change(self) -> None:
        """Chassis atom score doesn't change when thermal phase changes."""
        maya = _get_persona("U001")
        evt_results = _score_with_phase(maya, {"chassis": "DVT", "thermal": "EVT"})
        dvt_results = _score_with_phase(maya, {"chassis": "DVT", "thermal": "DVT"})

        chassis_in_evt = next(r.score for r in evt_results if r.atom is NON_THERMAL_ATOM)
        chassis_in_dvt = next(r.score for r in dvt_results if r.atom is NON_THERMAL_ATOM)

        assert chassis_in_evt == chassis_in_dvt

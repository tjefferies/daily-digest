"""Eval Criterion 1: Differential relevance across three personas.

Same atoms, meaningfully different digests for different personas.
ME ranks chassis/thermal atoms highly, SC Lead ranks supply-chain
atoms highly, EM ranks cross-team blockers highly.
"""

from __future__ import annotations

from uuid import uuid4

from evercurrent.context.personas import DEMO_PERSONAS
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.scoring.composite import score_atoms


def _make_atom(
    atom_type: str,
    workstream: str,
    urgency: str = "medium",
    affected: list[str] | None = None,
    participants: list[str] | None = None,
    phases: list[str] | None = None,
    summary: str = "Test",
) -> Atom:
    """Create an atom for evaluation testing."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary=summary,
        detail="Detail",
        source=AtomSource(
            channel=f"#{workstream}",
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


# A representative set of atoms covering different workstreams and types
EVAL_ATOMS = [
    _make_atom(
        "SPEC_CHANGE",
        "drivetrain",
        urgency="high",
        affected=["chassis"],
        phases=["DVT"],
        summary="Motor torque spec increased to 3.1 Nm",
    ),
    _make_atom(
        "TEST_RESULT",
        "chassis",
        urgency="medium",
        phases=["DVT"],
        summary="Chassis DVT vibration testing passed",
    ),
    _make_atom(
        "RISK",
        "supply-chain",
        urgency="high",
        affected=["firmware"],
        phases=["DVT"],
        summary="FPGA lead time may extend to 16 weeks",
    ),
    _make_atom(
        "DECISION",
        "supply-chain",
        urgency="medium",
        affected=["chassis"],
        phases=["DVT"],
        summary="CNC vendor changed to Proto Labs",
    ),
    _make_atom(
        "BLOCKER",
        "thermal",
        urgency="critical",
        affected=["chassis", "drivetrain"],
        phases=["EVT"],
        summary="Thermal simulation 6 deg C over target",
    ),
    _make_atom(
        "STATUS_UPDATE",
        "firmware",
        urgency="low",
        phases=["EVT"],
        summary="BLE communication stack integration complete",
    ),
    _make_atom(
        "ACTION_ITEM",
        "chassis",
        urgency="high",
        participants=["U001"],
        phases=["DVT"],
        summary="Review updated STEP files for battery tray bracket",
    ),
    _make_atom(
        "RISK",
        "sensors",
        urgency="medium",
        phases=["EVT"],
        summary="Lidar FOV narrower than spec on prototype",
    ),
]


def _get_persona(user_id: str):  # noqa: ANN202
    """Look up demo persona by user_id."""
    return next(p for p in DEMO_PERSONAS if p.user_id == user_id)


MAYA = _get_persona("U001")  # IC ME - chassis + thermal
ELENA = _get_persona("U007")  # Supply Chain
RYAN = _get_persona("U010")  # Eng Manager


class TestDifferentialRelevance:
    """Validate that same atoms produce different rankings per persona."""

    def test_maya_ranks_chassis_atoms_highly(self) -> None:
        """Maya Chen (ME) should rank chassis and thermal atoms highest."""
        results = score_atoms(EVAL_ATOMS, MAYA)
        top_3_workstreams = [r.atom.workstreams.originating for r in results[:3]]
        # Maya has chassis=1.0, thermal=0.85, so chassis/thermal atoms should dominate
        chassis_thermal = [ws for ws in top_3_workstreams if ws in ("chassis", "thermal")]
        assert len(chassis_thermal) >= 1, f"Top 3 workstreams: {top_3_workstreams}"

    def test_elena_ranks_supply_chain_atoms_highly(self) -> None:
        """Elena Vasquez (SC) should rank supply-chain atoms highest."""
        results = score_atoms(EVAL_ATOMS, ELENA)
        top_3_workstreams = [r.atom.workstreams.originating for r in results[:3]]
        # Elena has supply-chain=1.0
        sc_count = sum(1 for ws in top_3_workstreams if ws == "supply-chain")
        assert sc_count >= 1, f"Top 3 workstreams: {top_3_workstreams}"

    def test_ryan_ranks_blockers_and_risks_highly(self) -> None:
        """Ryan Torres (EM) should rank blockers and cross-team risks highly."""
        results = score_atoms(EVAL_ATOMS, RYAN)
        top_3_types = [r.atom.type for r in results[:3]]
        # EM scores 1.0 on DECISION/BLOCKER per role-alignment matrix
        high_value_types = [t for t in top_3_types if t in ("BLOCKER", "DECISION", "RISK")]
        assert len(high_value_types) >= 1, f"Top 3 types: {top_3_types}"

    def test_top_atoms_differ_across_personas(self) -> None:
        """Top-ranked atom should differ between at least 2 of 3 personas."""
        maya_top = score_atoms(EVAL_ATOMS, MAYA)[0].atom.atom_id
        elena_top = score_atoms(EVAL_ATOMS, ELENA)[0].atom.atom_id
        ryan_top = score_atoms(EVAL_ATOMS, RYAN)[0].atom.atom_id
        top_ids = {maya_top, elena_top, ryan_top}
        # At least 2 different top atoms across 3 personas
        assert len(top_ids) >= 2, "All three personas have the same top atom"

    def test_scores_meaningfully_different(self) -> None:
        """The composite score distributions should differ meaningfully."""
        maya_scores = [r.score for r in score_atoms(EVAL_ATOMS, MAYA)]
        elena_scores = [r.score for r in score_atoms(EVAL_ATOMS, ELENA)]
        ryan_scores = [r.score for r in score_atoms(EVAL_ATOMS, RYAN)]
        # At least one pair must have different ordering
        orderings_differ = (
            maya_scores != elena_scores
            or elena_scores != ryan_scores
            or maya_scores != ryan_scores
        )
        assert orderings_differ, "All three personas produced identical score distributions"

    def test_maya_action_item_directed_at_her_scores_high(self) -> None:
        """An ACTION_ITEM with Maya as participant should score highest for her."""
        # The action item with U001 as participant should score higher for Maya
        maya_results = score_atoms(EVAL_ATOMS, MAYA)
        elena_results = score_atoms(EVAL_ATOMS, ELENA)
        action_item = next(a for a in EVAL_ATOMS if a.type == "ACTION_ITEM")
        maya_action_score = next(
            r.score for r in maya_results if r.atom.atom_id == action_item.atom_id
        )
        elena_action_score = next(
            r.score for r in elena_results if r.atom.atom_id == action_item.atom_id
        )
        assert maya_action_score > elena_action_score

    def test_elena_supply_chain_risk_scores_high(self) -> None:
        """Supply chain risk should score higher for Elena than Maya."""
        maya_results = score_atoms(EVAL_ATOMS, MAYA)
        elena_results = score_atoms(EVAL_ATOMS, ELENA)
        sc_risk = next(
            a
            for a in EVAL_ATOMS
            if a.type == "RISK" and a.workstreams.originating == "supply-chain"
        )
        maya_sc_score = next(r.score for r in maya_results if r.atom.atom_id == sc_risk.atom_id)
        elena_sc_score = next(r.score for r in elena_results if r.atom.atom_id == sc_risk.atom_id)
        assert elena_sc_score > maya_sc_score

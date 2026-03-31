"""Eval Criterion 2: Buried signals surface in correct persona digests.

Tests that cross-workstream signals planted in the dataset are
correctly scored high for the appropriate personas.
"""

from __future__ import annotations

from uuid import uuid4

from evercurrent.context.personas import DEMO_PERSONAS
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.scoring.composite import score_atoms


def _get_persona(user_id: str):  # noqa: ANN202
    """Look up demo persona by user_id."""
    return next(p for p in DEMO_PERSONAS if p.user_id == user_id)


MAYA = _get_persona("U001")  # IC ME - chassis + thermal
ELENA = _get_persona("U007")  # Supply Chain
RYAN = _get_persona("U010")  # Eng Manager


def _make_atom(
    atom_type: str,
    workstream: str,
    affected: list[str] | None = None,
    urgency: str = "medium",
    summary: str = "Test",
) -> Atom:
    """Create an atom for buried signal testing."""
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
        workstreams=AtomWorkstreams(
            originating=workstream,
            affected=affected or [],
        ),
        urgency=urgency,
        confidence=0.75,
        implicit_decision=True,
        phase_relevance=["DVT"],
    )


# Signal 1: Magnesium housing implicit decision in chassis channel
# affects supply-chain procurement
SIGNAL_1_MAGNESIUM = _make_atom(
    "DECISION",
    "chassis",
    affected=["supply-chain", "thermal"],
    urgency="high",
    summary="Implicit decision to use magnesium housing",
)

# Signal 2: Thermal interface root cause from testing channel
# affects chassis and thermal
SIGNAL_2_THERMAL = _make_atom(
    "RISK",
    "thermal",
    affected=["chassis"],
    urgency="high",
    summary="Thermal interface material root cause identified",
)

# Signal 3: FPGA lead time risk from firmware channel
# affects supply-chain
SIGNAL_3_FPGA = _make_atom(
    "RISK",
    "firmware",
    affected=["supply-chain"],
    urgency="high",
    summary="FPGA lead time risk - may extend to 16 weeks",
)

# Filler atoms to create realistic scoring competition
FILLER_ATOMS = [
    _make_atom("STATUS_UPDATE", "sensors", summary="Lidar calibration in progress"),
    _make_atom("STATUS_UPDATE", "firmware", summary="OTA update module tested"),
    _make_atom("QUESTION", "end-effector", summary="Gripper force spec unclear"),
]

ALL_ATOMS = [SIGNAL_1_MAGNESIUM, SIGNAL_2_THERMAL, SIGNAL_3_FPGA, *FILLER_ATOMS]


class TestBuriedSignalsSurfacing:
    """Validate buried cross-workstream signals appear for correct personas."""

    def test_magnesium_decision_surfaces_for_supply_chain(self) -> None:
        """Signal 1: Magnesium housing decision surfaces for Elena (SC Lead).

        Even though it originates in chassis, the affected tag includes
        supply-chain, so Elena's workstream_proximity should pick it up.
        """
        elena_results = score_atoms(ALL_ATOMS, ELENA)
        elena_ids = [r.atom.atom_id for r in elena_results[:4]]
        assert SIGNAL_1_MAGNESIUM.atom_id in elena_ids

    def test_magnesium_decision_surfaces_for_maya(self) -> None:
        """Signal 1: Also surfaces for Maya since it's from chassis."""
        maya_results = score_atoms(ALL_ATOMS, MAYA)
        maya_ids = [r.atom.atom_id for r in maya_results[:4]]
        assert SIGNAL_1_MAGNESIUM.atom_id in maya_ids

    def test_thermal_root_cause_surfaces_for_maya(self) -> None:
        """Signal 2: Thermal interface root cause surfaces for Maya.

        Maya has thermal=0.85, so this should score high for her.
        """
        maya_results = score_atoms(ALL_ATOMS, MAYA)
        maya_ids = [r.atom.atom_id for r in maya_results[:4]]
        assert SIGNAL_2_THERMAL.atom_id in maya_ids

    def test_fpga_lead_time_surfaces_for_supply_chain(self) -> None:
        """Signal 3: FPGA lead time risk surfaces for Elena.

        Even though originating in firmware, the affected tag includes
        supply-chain. Elena's supply-chain affinity is 1.0.
        """
        elena_results = score_atoms(ALL_ATOMS, ELENA)
        elena_ids = [r.atom.atom_id for r in elena_results[:4]]
        assert SIGNAL_3_FPGA.atom_id in elena_ids

    def test_buried_signals_score_higher_than_filler(self) -> None:
        """All three signals should score above filler atoms for their targets."""
        elena_results = score_atoms(ALL_ATOMS, ELENA)
        elena_scores = {r.atom.atom_id: r.score for r in elena_results}

        filler_max = max(elena_scores[a.atom_id] for a in FILLER_ATOMS)
        signal_1_score = elena_scores[SIGNAL_1_MAGNESIUM.atom_id]
        signal_3_score = elena_scores[SIGNAL_3_FPGA.atom_id]

        assert signal_1_score > filler_max
        assert signal_3_score > filler_max

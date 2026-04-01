"""Tests for three fully-specified demo personas.

Validates persona fixtures for Maya Chen (IC ME), Elena Vasquez
(Supply Chain Lead), and Ryan Torres (Engineering Manager) per
design doc section 6.1.
"""

from digest.context.personas import DEMO_PERSONAS, get_persona
from digest.models.persona import Persona


class TestDemoPersonaCount:
    """Tests for the demo persona collection."""

    def test_exactly_three_personas(self) -> None:
        """Exactly 3 demo personas are defined."""
        assert len(DEMO_PERSONAS) == 3

    def test_all_are_persona_instances(self) -> None:
        """Every demo persona is a valid Persona model."""
        for persona in DEMO_PERSONAS:
            assert isinstance(persona, Persona)

    def test_unique_user_ids(self) -> None:
        """All persona user_ids are unique."""
        ids = [p.user_id for p in DEMO_PERSONAS]
        assert len(ids) == len(set(ids))


class TestMayaChen:
    """Tests for Maya Chen, Senior Mechanical Engineer persona."""

    def test_maya_exists(self) -> None:
        """Maya Chen persona can be retrieved by user_id."""
        maya = get_persona("U001")
        assert maya is not None
        assert maya.name == "Maya Chen"

    def test_maya_role_archetype(self) -> None:
        """Maya is an IC Engineer archetype."""
        maya = get_persona("U001")
        assert maya is not None
        assert maya.role_archetype == "IC Engineer"

    def test_maya_workstream_affinities(self) -> None:
        """Maya has high chassis and thermal affinities per spec."""
        maya = get_persona("U001")
        assert maya is not None
        assert maya.workstream_affinities["chassis"] == 1.0
        assert maya.workstream_affinities["thermal"] == 0.85
        assert maya.workstream_affinities["drivetrain"] == 0.4
        assert maya.workstream_affinities["supply-chain"] == 0.3

    def test_maya_scoring_weights(self) -> None:
        """Maya has default scoring weights (0.30/0.20/0.20/0.15/0.15)."""
        maya = get_persona("U001")
        assert maya is not None
        w = maya.scoring_weights
        assert w.workstream_proximity == 0.30
        assert w.role_type_alignment == 0.20
        assert w.phase_alignment == 0.20
        assert w.urgency == 0.15
        assert w.social_signal == 0.15

    def test_maya_collaborator_graph(self) -> None:
        """Maya has 3-5 collaborators in her graph."""
        maya = get_persona("U001")
        assert maya is not None
        assert 3 <= len(maya.collaborator_graph) <= 5

    def test_maya_digest_preferences(self) -> None:
        """Maya has default digest preferences."""
        maya = get_persona("U001")
        assert maya is not None
        assert maya.digest_preferences.max_items == 25
        assert maya.digest_preferences.critical_threshold == 0.85


class TestSupplyChainLead:
    """Tests for the Supply Chain Lead persona."""

    def test_sc_lead_exists(self) -> None:
        """Supply Chain Lead persona can be retrieved."""
        sc = get_persona("U007")
        assert sc is not None
        assert sc.role_archetype == "Supply Chain"

    def test_sc_lead_supply_chain_affinity(self) -> None:
        """SC Lead has supply-chain affinity of 1.0."""
        sc = get_persona("U007")
        assert sc is not None
        assert sc.workstream_affinities["supply-chain"] == 1.0

    def test_sc_lead_broad_affinities(self) -> None:
        """SC Lead has moderate affinities across all workstreams."""
        sc = get_persona("U007")
        assert sc is not None
        for ws, aff in sc.workstream_affinities.items():
            if ws != "supply-chain":
                assert 0.3 <= aff <= 0.7, f"SC Lead {ws} affinity {aff} out of 0.3-0.7 range"

    def test_sc_lead_collaborator_graph(self) -> None:
        """SC Lead has 3-5 collaborators."""
        sc = get_persona("U007")
        assert sc is not None
        assert 3 <= len(sc.collaborator_graph) <= 5


class TestEngineeringManager:
    """Tests for the Engineering Manager persona."""

    def test_em_exists(self) -> None:
        """Engineering Manager persona can be retrieved."""
        em = get_persona("U010")
        assert em is not None
        assert em.role_archetype == "Eng Manager"

    def test_em_broad_affinities(self) -> None:
        """EM has high affinities across all workstreams (0.5-0.9)."""
        em = get_persona("U010")
        assert em is not None
        for ws, aff in em.workstream_affinities.items():
            assert 0.5 <= aff <= 0.9, f"EM {ws} affinity {aff} out of 0.5-0.9 range"

    def test_em_collaborator_graph(self) -> None:
        """EM has 3-5 collaborators."""
        em = get_persona("U010")
        assert em is not None
        assert 3 <= len(em.collaborator_graph) <= 5

    def test_em_has_phase_context(self) -> None:
        """EM has phase_context entries for workstreams."""
        em = get_persona("U010")
        assert em is not None
        assert len(em.phase_context) >= 3


class TestGetPersona:
    """Tests for the get_persona lookup function."""

    def test_get_unknown_returns_none(self) -> None:
        """Looking up a non-existent persona returns None."""
        assert get_persona("U999") is None

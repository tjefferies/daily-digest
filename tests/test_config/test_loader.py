"""Tests for the YAML configuration loader module.

Validates that config files load correctly, produce the expected
data structures, and that the loaded values match the original
hardcoded values they replace.
"""

from __future__ import annotations

import pytest

from evercurrent.config.loader import (
    get_config,
    load_config,
)


class TestLoadConfig:
    """Validate config loading from YAML files."""

    def test_load_config_returns_dict(self) -> None:
        """load_config returns a dict."""
        cfg = load_config()
        assert isinstance(cfg, dict)

    def test_load_config_has_all_sections(self) -> None:
        """Config contains all five top-level sections."""
        cfg = load_config()
        expected = {"workstreams", "phases", "scoring", "personas", "pipeline"}
        assert expected.issubset(cfg.keys())

    def test_get_config_returns_cached_instance(self) -> None:
        """get_config returns the same dict on repeated calls."""
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2


class TestWorkstreamsConfig:
    """Validate workstream configuration."""

    def test_channel_to_workstream_has_entries(self) -> None:
        """Channel-to-workstream mapping has at least 7 entries."""
        cfg = get_config()
        mapping = cfg["workstreams"]["channel_to_workstream"]
        assert len(mapping) >= 7

    def test_chassis_design_maps_to_chassis(self) -> None:
        """#chassis-design maps to 'chassis' workstream."""
        cfg = get_config()
        mapping = cfg["workstreams"]["channel_to_workstream"]
        assert mapping["#chassis-design"] == "chassis"

    def test_workstream_to_channels_has_end_effector(self) -> None:
        """Workstream-to-channels includes end-effector."""
        cfg = get_config()
        ws_to_ch = cfg["workstreams"]["workstream_to_channels"]
        assert "end-effector" in ws_to_ch

    def test_component_to_workstream_has_motor(self) -> None:
        """Component mapping includes 'motor'."""
        cfg = get_config()
        comp = cfg["workstreams"]["component_to_workstream"]
        assert comp["motor"] == "drivetrain"

    def test_component_to_workstream_has_all_entries(self) -> None:
        """Component mapping has at least 30 entries."""
        cfg = get_config()
        comp = cfg["workstreams"]["component_to_workstream"]
        assert len(comp) >= 30


class TestPhasesConfig:
    """Validate phase configuration."""

    def test_default_phases_has_seven_workstreams(self) -> None:
        """Default phases cover all 7 workstreams."""
        cfg = get_config()
        phases = cfg["phases"]["default_phases"]
        assert len(phases) == 7

    def test_chassis_is_dvt(self) -> None:
        """Chassis default phase is DVT."""
        cfg = get_config()
        phases = cfg["phases"]["default_phases"]
        assert phases["chassis"] == "DVT"

    def test_thermal_is_evt(self) -> None:
        """Thermal default phase is EVT."""
        cfg = get_config()
        phases = cfg["phases"]["default_phases"]
        assert phases["thermal"] == "EVT"

    def test_end_effector_is_concept(self) -> None:
        """End-effector default phase is Concept."""
        cfg = get_config()
        phases = cfg["phases"]["default_phases"]
        assert phases["end-effector"] == "Concept"


class TestScoringConfig:
    """Validate scoring configuration."""

    def test_default_weights_sum_to_one(self) -> None:
        """Scoring weights sum to 1.0."""
        cfg = get_config()
        weights = cfg["scoring"]["default_weights"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_urgency_scores_has_four_levels(self) -> None:
        """Urgency scores map all four levels."""
        cfg = get_config()
        urgency = cfg["scoring"]["urgency_scores"]
        assert set(urgency.keys()) == {"critical", "high", "medium", "low"}

    def test_critical_urgency_is_one(self) -> None:
        """Critical urgency maps to 1.0."""
        cfg = get_config()
        assert cfg["scoring"]["urgency_scores"]["critical"] == 1.0

    def test_role_type_alignment_has_five_archetypes(self) -> None:
        """Role-type alignment matrix has 5 role archetypes."""
        cfg = get_config()
        matrix = cfg["scoring"]["role_type_alignment"]
        assert len(matrix) == 5

    def test_ic_engineer_spec_change_is_one(self) -> None:
        """IC Engineer × SPEC_CHANGE = 1.0."""
        cfg = get_config()
        matrix = cfg["scoring"]["role_type_alignment"]
        assert matrix["IC Engineer"]["SPEC_CHANGE"] == 1.0

    def test_phase_alignment_scores_present(self) -> None:
        """Phase alignment distance scores are configured."""
        cfg = get_config()
        pa = cfg["scoring"]["phase_alignment"]
        assert "distance_scores" in pa
        assert pa["distance_scores"][0] == 1.0

    def test_social_signal_scores_present(self) -> None:
        """Social signal scores are configured."""
        cfg = get_config()
        ss = cfg["scoring"]["social_signal"]
        assert ss["persona_is_participant"] == 1.0

    def test_title_to_archetype_mapping(self) -> None:
        """Title-to-archetype mapping includes standard titles."""
        cfg = get_config()
        t2a = cfg["scoring"]["title_to_archetype"]
        assert t2a["Engineering Manager"] == "Eng Manager"
        assert t2a["Supply Chain Manager"] == "Supply Chain"

    def test_digest_preferences_defaults(self) -> None:
        """Default digest preferences are configured."""
        cfg = get_config()
        prefs = cfg["scoring"]["default_digest_preferences"]
        assert prefs["max_items"] == 25
        assert prefs["critical_threshold"] == 0.85


class TestPersonasConfig:
    """Validate persona configuration."""

    def test_three_demo_personas(self) -> None:
        """Config has exactly 3 demo personas."""
        cfg = get_config()
        personas = cfg["personas"]["personas"]
        assert len(personas) == 3

    def test_maya_chen_is_first(self) -> None:
        """Maya Chen (U001) is the first persona."""
        cfg = get_config()
        maya = cfg["personas"]["personas"][0]
        assert maya["user_id"] == "U001"
        assert maya["name"] == "Maya Chen"

    def test_elena_vasquez_is_second(self) -> None:
        """Elena Vasquez (U007) is the second persona."""
        cfg = get_config()
        elena = cfg["personas"]["personas"][1]
        assert elena["user_id"] == "U007"

    def test_ryan_torres_is_third(self) -> None:
        """Ryan Torres (U010) is the third persona."""
        cfg = get_config()
        ryan = cfg["personas"]["personas"][2]
        assert ryan["user_id"] == "U010"

    def test_persona_has_workstream_affinities(self) -> None:
        """Each persona has workstream_affinities dict."""
        cfg = get_config()
        for persona in cfg["personas"]["personas"]:
            assert "workstream_affinities" in persona
            assert isinstance(persona["workstream_affinities"], dict)

    def test_maya_chassis_affinity_is_one(self) -> None:
        """Maya's chassis affinity is 1.0."""
        cfg = get_config()
        maya = cfg["personas"]["personas"][0]
        assert maya["workstream_affinities"]["chassis"] == 1.0


class TestPipelineConfig:
    """Validate pipeline configuration."""

    def test_model_is_specified(self) -> None:
        """Pipeline model is specified."""
        cfg = get_config()
        assert "model" in cfg["pipeline"]
        assert "claude" in cfg["pipeline"]["model"]

    def test_cors_origins(self) -> None:
        """CORS origins include localhost dev servers."""
        cfg = get_config()
        origins = cfg["pipeline"]["cors_origins"]
        assert "http://localhost:5173" in origins
        assert "http://localhost:3000" in origins

    def test_confidence_threshold(self) -> None:
        """Confidence threshold is configured."""
        cfg = get_config()
        assert cfg["pipeline"]["confidence_threshold"] == 0.7

    def test_context_window_config(self) -> None:
        """Context window settings are configured."""
        cfg = get_config()
        cw = cfg["pipeline"]["context_window"]
        assert cw["max_tokens"] == 4000
        assert cw["tail_count"] == 5
        assert cw["chars_per_token"] == 4

    def test_token_limits(self) -> None:
        """Token limits for extraction and generation are set."""
        cfg = get_config()
        assert cfg["pipeline"]["extraction_max_tokens"] == 4096
        assert cfg["pipeline"]["generation_max_tokens"] == 4096


class TestConfigMatchesOriginalHardcoded:
    """Validate YAML config matches original hardcoded values exactly.

    These tests catch any drift between the YAML config and the
    original hardcoded values in the source code.
    """

    def test_urgency_scores_match(self) -> None:
        """YAML urgency scores match calibrated values (uniform spacing)."""
        cfg = get_config()
        expected = {"critical": 1.0, "high": 0.75, "medium": 0.50, "low": 0.25}
        assert cfg["scoring"]["urgency_scores"] == expected

    def test_role_alignment_ic_engineer_matches(self) -> None:
        """IC Engineer row matches original hardcoded matrix."""
        cfg = get_config()
        ic = cfg["scoring"]["role_type_alignment"]["IC Engineer"]
        expected = {
            "DECISION": 0.8,
            "SPEC_CHANGE": 1.0,
            "ACTION_ITEM": 0.7,
            "BLOCKER": 0.6,
            "RISK": 0.5,
            "TEST_RESULT": 1.0,
            "STATUS_UPDATE": 0.3,
            "QUESTION": 0.6,
        }
        assert ic == expected

    def test_default_weights_match(self) -> None:
        """Default weights match original hardcoded values."""
        cfg = get_config()
        weights = cfg["scoring"]["default_weights"]
        expected = {
            "workstream_proximity": 0.30,
            "role_type_alignment": 0.20,
            "phase_alignment": 0.20,
            "urgency": 0.15,
            "social_signal": 0.15,
        }
        assert weights == expected

    def test_default_phases_match(self) -> None:
        """Default phases match original hardcoded values."""
        cfg = get_config()
        phases = cfg["phases"]["default_phases"]
        expected = {
            "chassis": "DVT",
            "drivetrain": "DVT",
            "thermal": "EVT",
            "power-systems": "DVT",
            "sensors": "EVT",
            "firmware": "EVT",
            "end-effector": "Concept",
        }
        assert phases == expected

    def test_channel_mapping_matches(self) -> None:
        """Channel-to-workstream mapping matches original."""
        cfg = get_config()
        mapping = cfg["workstreams"]["channel_to_workstream"]
        expected = {
            "#chassis-design": "chassis",
            "#drivetrain": "drivetrain",
            "#thermal-management": "thermal",
            "#power-systems": "power-systems",
            "#sensors": "sensors",
            "#firmware": "firmware",
            "#supply-chain": "supply-chain",
        }
        assert mapping == expected


class TestConfigFileNotFound:
    """Validate error handling for missing config files."""

    def test_load_config_with_bad_path_raises(self) -> None:
        """load_config raises FileNotFoundError for nonexistent path."""
        with pytest.raises(FileNotFoundError):
            load_config(config_dir="/nonexistent/path")

"""Tests for per-workstream phase vector (ADR-004).

Validates that phase is modeled as a vector (dict[workstream, Phase])
not a project-wide scalar, supporting the phase-override demo feature
for Evaluation Criterion 3.
"""

from typing import TYPE_CHECKING

import pytest

from evercurrent.context.phases import PhaseVector

if TYPE_CHECKING:
    from evercurrent.models.atom import Phase


class TestPhaseVectorDefaults:
    """Tests for the default phase vector from design doc section 6.3."""

    def test_default_has_seven_workstreams(self) -> None:
        """Default vector covers all 7 workstreams from section 6.3."""
        pv = PhaseVector()
        assert len(pv.all_phases()) == 7

    def test_chassis_is_dvt(self) -> None:
        """Chassis workstream is in DVT phase."""
        pv = PhaseVector()
        assert pv.get_phase("chassis") == "DVT"

    def test_drivetrain_is_dvt(self) -> None:
        """Drivetrain workstream is in DVT phase."""
        pv = PhaseVector()
        assert pv.get_phase("drivetrain") == "DVT"

    def test_thermal_is_evt(self) -> None:
        """Thermal is Late EVT, modeled as EVT for scoring."""
        pv = PhaseVector()
        assert pv.get_phase("thermal") == "EVT"

    def test_power_systems_is_dvt(self) -> None:
        """Power Systems workstream is in DVT phase."""
        pv = PhaseVector()
        assert pv.get_phase("power-systems") == "DVT"

    def test_sensors_is_evt(self) -> None:
        """Sensors workstream is in EVT phase."""
        pv = PhaseVector()
        assert pv.get_phase("sensors") == "EVT"

    def test_firmware_is_evt(self) -> None:
        """Firmware workstream is in EVT phase."""
        pv = PhaseVector()
        assert pv.get_phase("firmware") == "EVT"

    def test_end_effector_is_concept(self) -> None:
        """End-Effector workstream is in Concept phase."""
        pv = PhaseVector()
        assert pv.get_phase("end-effector") == "Concept"


class TestPhaseVectorLookup:
    """Tests for get_phase and error handling."""

    def test_unknown_workstream_returns_none(self) -> None:
        """Unknown workstream returns None."""
        pv = PhaseVector()
        assert pv.get_phase("nonexistent") is None

    def test_all_phases_returns_copy(self) -> None:
        """all_phases returns a copy, not internal state."""
        pv = PhaseVector()
        phases = pv.all_phases()
        phases["chassis"] = "PVT"
        assert pv.get_phase("chassis") == "DVT"


class TestPhaseVectorOverride:
    """Tests for set_phase (phase-override demo feature)."""

    def test_set_phase_updates_workstream(self) -> None:
        """set_phase changes a workstream's phase."""
        pv = PhaseVector()
        pv.set_phase("thermal", "DVT")
        assert pv.get_phase("thermal") == "DVT"

    def test_set_phase_does_not_affect_others(self) -> None:
        """Overriding one workstream leaves others unchanged."""
        pv = PhaseVector()
        pv.set_phase("thermal", "DVT")
        assert pv.get_phase("chassis") == "DVT"
        assert pv.get_phase("sensors") == "EVT"

    def test_set_phase_validates_phase_value(self) -> None:
        """set_phase rejects invalid phase values."""
        pv = PhaseVector()
        with pytest.raises(ValueError, match="Invalid phase"):
            pv.set_phase("chassis", "InvalidPhase")  # type: ignore[arg-type]

    def test_set_phase_validates_workstream(self) -> None:
        """set_phase rejects unknown workstream names."""
        pv = PhaseVector()
        with pytest.raises(ValueError, match="Unknown workstream"):
            pv.set_phase("nonexistent", "DVT")

    def test_reset_restores_defaults(self) -> None:
        """Reset restores all phases to their defaults."""
        pv = PhaseVector()
        pv.set_phase("thermal", "DVT")
        pv.set_phase("chassis", "PVT")
        pv.reset()
        assert pv.get_phase("thermal") == "EVT"
        assert pv.get_phase("chassis") == "DVT"


class TestPhaseVectorCustomInit:
    """Tests for creating a phase vector with custom initial phases."""

    def test_custom_phases(self) -> None:
        """Construct a phase vector with custom initial values."""
        custom: dict[str, Phase] = {
            "chassis": "PVT",
            "drivetrain": "Production",
        }
        pv = PhaseVector(initial_phases=custom)
        assert pv.get_phase("chassis") == "PVT"
        assert pv.get_phase("drivetrain") == "Production"
        assert len(pv.all_phases()) == 2

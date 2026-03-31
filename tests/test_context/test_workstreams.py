"""Tests for workstream registry with channel-to-workstream mapping.

Validates the WorkstreamRegistry that maps channels to workstreams,
workstreams to channels, and components to workstreams for the
Context Backbone layer.
"""

from evercurrent.context.workstreams import WorkstreamRegistry


class TestWorkstreamRegistryChannelMapping:
    """Tests for channel-to-workstream and workstream-to-channel lookups."""

    def test_has_eight_workstreams(self) -> None:
        """Registry defines exactly 8 workstreams."""
        registry = WorkstreamRegistry()
        assert len(registry.all_workstreams()) == 8

    def test_required_workstreams_present(self) -> None:
        """All 8 design-doc workstreams are registered."""
        expected = {
            "chassis",
            "drivetrain",
            "thermal",
            "power-systems",
            "sensors",
            "firmware",
            "supply-chain",
            "end-effector",
        }
        registry = WorkstreamRegistry()
        assert set(registry.all_workstreams()) == expected

    def test_get_workstream_from_channel(self) -> None:
        """Look up workstream from a known channel."""
        registry = WorkstreamRegistry()
        assert registry.get_workstream("#chassis-design") == "chassis"
        assert registry.get_workstream("#drivetrain") == "drivetrain"
        assert registry.get_workstream("#supply-chain") == "supply-chain"

    def test_get_workstream_unknown_channel(self) -> None:
        """Unknown channel returns None."""
        registry = WorkstreamRegistry()
        assert registry.get_workstream("#random") is None

    def test_get_channels_from_workstream(self) -> None:
        """Look up channels for a known workstream."""
        registry = WorkstreamRegistry()
        channels = registry.get_channels("chassis")
        assert "#chassis-design" in channels

    def test_get_channels_unknown_workstream(self) -> None:
        """Unknown workstream returns empty list."""
        registry = WorkstreamRegistry()
        assert registry.get_channels("nonexistent") == []

    def test_amr_general_maps_to_no_single_workstream(self) -> None:
        """#amr-general is a cross-cutting channel, not one workstream."""
        registry = WorkstreamRegistry()
        result = registry.get_workstream("#amr-general")
        assert result is None

    def test_every_workstream_has_channels(self) -> None:
        """Every registered workstream has at least one channel."""
        registry = WorkstreamRegistry()
        for ws in registry.all_workstreams():
            channels = registry.get_channels(ws)
            assert len(channels) >= 1, f"Workstream {ws} has no channels"


class TestWorkstreamRegistryComponentMapping:
    """Tests for component-to-workstream inference."""

    def test_known_component_resolves(self) -> None:
        """A known hardware component maps to its workstream."""
        registry = WorkstreamRegistry()
        assert registry.get_workstream_for_component("motor controller") == "drivetrain"

    def test_fpga_resolves_to_firmware(self) -> None:
        """FPGA maps to firmware workstream."""
        registry = WorkstreamRegistry()
        assert registry.get_workstream_for_component("FPGA") == "firmware"

    def test_case_insensitive_lookup(self) -> None:
        """Component lookup is case-insensitive."""
        registry = WorkstreamRegistry()
        assert registry.get_workstream_for_component("Heat Sink") == "thermal"
        assert registry.get_workstream_for_component("heat sink") == "thermal"

    def test_unknown_component_returns_none(self) -> None:
        """Unknown component returns None."""
        registry = WorkstreamRegistry()
        assert registry.get_workstream_for_component("quantum flux capacitor") is None

    def test_battery_maps_to_power_systems(self) -> None:
        """Battery-related components map to power-systems."""
        registry = WorkstreamRegistry()
        assert registry.get_workstream_for_component("battery pack") == "power-systems"

    def test_lidar_maps_to_sensors(self) -> None:
        """LIDAR maps to sensors workstream."""
        registry = WorkstreamRegistry()
        assert registry.get_workstream_for_component("lidar") == "sensors"

    def test_all_workstreams_returns_copy(self) -> None:
        """all_workstreams returns a copy, not internal state."""
        registry = WorkstreamRegistry()
        ws = registry.all_workstreams()
        ws.pop()
        assert len(registry.all_workstreams()) == 8

    def test_get_channels_returns_copy(self) -> None:
        """get_channels returns a copy, not internal state."""
        registry = WorkstreamRegistry()
        channels = registry.get_channels("chassis")
        original_len = len(channels)
        channels.append("#fake")
        assert len(registry.get_channels("chassis")) == original_len

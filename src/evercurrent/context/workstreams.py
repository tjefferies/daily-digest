"""Workstream registry with channel and component mappings.

Maps Slack channels to workstreams and hardware components to
workstreams. Used by the Context Backbone (Layer 3) to resolve
workstream context from channel names and component references
in extracted atoms.
"""

from __future__ import annotations

# Channel → workstream mapping. #amr-general is cross-cutting
# and intentionally excluded (returns None).
_CHANNEL_TO_WORKSTREAM: dict[str, str] = {
    "#chassis-design": "chassis",
    "#drivetrain": "drivetrain",
    "#thermal-management": "thermal",
    "#power-systems": "power-systems",
    "#sensors": "sensors",
    "#firmware": "firmware",
    "#supply-chain": "supply-chain",
}

# Workstream → channels (reverse of above, plus end-effector
# which has no dedicated channel yet).
_WORKSTREAM_TO_CHANNELS: dict[str, list[str]] = {
    "chassis": ["#chassis-design"],
    "drivetrain": ["#drivetrain"],
    "thermal": ["#thermal-management"],
    "power-systems": ["#power-systems"],
    "sensors": ["#sensors"],
    "firmware": ["#firmware"],
    "supply-chain": ["#supply-chain"],
    "end-effector": ["#amr-general"],
}

# Component name (lowercase) → workstream.
_COMPONENT_TO_WORKSTREAM: dict[str, str] = {
    "chassis": "chassis",
    "frame": "chassis",
    "enclosure": "chassis",
    "housing": "chassis",
    "bracket": "chassis",
    "motor": "drivetrain",
    "motor controller": "drivetrain",
    "gearbox": "drivetrain",
    "drive shaft": "drivetrain",
    "wheel hub": "drivetrain",
    "heat sink": "thermal",
    "thermal interface": "thermal",
    "thermal pad": "thermal",
    "cooling fan": "thermal",
    "heat pipe": "thermal",
    "battery": "power-systems",
    "battery pack": "power-systems",
    "power supply": "power-systems",
    "voltage regulator": "power-systems",
    "bms": "power-systems",
    "lidar": "sensors",
    "imu": "sensors",
    "camera": "sensors",
    "encoder": "sensors",
    "proximity sensor": "sensors",
    "fpga": "firmware",
    "microcontroller": "firmware",
    "mcu": "firmware",
    "bootloader": "firmware",
    "firmware image": "firmware",
    "connector": "supply-chain",
    "vendor": "supply-chain",
    "lead time": "supply-chain",
    "gripper": "end-effector",
    "end effector": "end-effector",
    "tool changer": "end-effector",
}


class WorkstreamRegistry:
    """Registry mapping channels and components to workstreams.

    Provides lookup functions that the extraction and scoring layers
    use to resolve workstream context from Slack channel names and
    hardware component references.

    The registry is immutable after construction. All accessors
    return copies to prevent mutation of internal state.
    """

    def __init__(self) -> None:
        """Initialize with the default AMR team mappings."""
        self._channel_to_ws = dict(_CHANNEL_TO_WORKSTREAM)
        self._ws_to_channels = {k: list(v) for k, v in _WORKSTREAM_TO_CHANNELS.items()}
        self._component_to_ws = dict(_COMPONENT_TO_WORKSTREAM)

    def get_workstream(self, channel: str) -> str | None:
        """Look up the workstream for a Slack channel.

        Args:
            channel: Channel name including # prefix.

        Returns:
            Workstream name, or None for cross-cutting channels.
        """
        return self._channel_to_ws.get(channel)

    def get_channels(self, workstream: str) -> list[str]:
        """Look up channels belonging to a workstream.

        Args:
            workstream: Workstream name.

        Returns:
            List of channel names, or empty list if unknown.
        """
        channels = self._ws_to_channels.get(workstream)
        return list(channels) if channels else []

    def get_workstream_for_component(
        self,
        component: str,
    ) -> str | None:
        """Infer workstream from a hardware component name.

        Args:
            component: Component name (case-insensitive).

        Returns:
            Workstream name, or None if not recognized.
        """
        return self._component_to_ws.get(component.lower())

    def all_workstreams(self) -> list[str]:
        """Return all registered workstream names.

        Returns:
            List of workstream name strings.
        """
        return list(self._ws_to_channels.keys())

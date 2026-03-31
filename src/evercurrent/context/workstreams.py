"""Workstream registry with channel and component mappings.

Maps Slack channels to workstreams and hardware components to
workstreams. Used by the Context Backbone (Layer 3) to resolve
workstream context from channel names and component references
in extracted atoms.
"""

from __future__ import annotations

from evercurrent.config.loader import get_config


def _load_workstream_config() -> tuple[dict[str, str], dict[str, list[str]], dict[str, str]]:
    """Load workstream mappings from YAML config."""
    cfg = get_config()["workstreams"]
    channel_to_ws: dict[str, str] = dict(cfg["channel_to_workstream"])
    ws_to_channels: dict[str, list[str]] = {
        k: list(v) for k, v in cfg["workstream_to_channels"].items()
    }
    component_to_ws: dict[str, str] = dict(cfg["component_to_workstream"])
    return channel_to_ws, ws_to_channels, component_to_ws


_CHANNEL_TO_WORKSTREAM, _WORKSTREAM_TO_CHANNELS, _COMPONENT_TO_WORKSTREAM = (
    _load_workstream_config()
)


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

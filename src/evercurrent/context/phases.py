"""Per-workstream phase vector (ADR-004).

Models development phase as a vector (dict[workstream, Phase]) rather
than a project-wide scalar. Different subsystems occupy different
phases simultaneously - e.g. chassis is in DVT while sensors are
still in EVT.

Supports get_phase/set_phase for the frontend phase-override demo
that demonstrates Evaluation Criterion 3 (phase sensitivity).
"""

from __future__ import annotations

from typing import get_args

from evercurrent.config.loader import get_config
from evercurrent.models.atom import Phase

_VALID_PHASES: set[str] = set(get_args(Phase))

# Default phase assignments loaded from config/phases.yml.
_DEFAULT_PHASES: dict[str, Phase] = get_config()["phases"]["default_phases"]


class PhaseVector:
    """Per-workstream phase vector for the Context Backbone.

    Each workstream has an independent development phase. The scoring
    engine queries this to compute phase-alignment scores, and the
    frontend overrides it to demonstrate phase sensitivity.

    Attributes:
        _phases: Current workstream-to-phase mapping.
        _defaults: Original phase mapping for reset support.
    """

    def __init__(
        self,
        initial_phases: dict[str, Phase] | None = None,
    ) -> None:
        """Initialize the phase vector.

        Args:
            initial_phases: Optional custom phase mapping. If None,
                uses the default AMR team phases from section 6.3.
        """
        source = initial_phases if initial_phases is not None else _DEFAULT_PHASES
        self._defaults: dict[str, Phase] = dict(source)
        self._phases: dict[str, Phase] = dict(source)

    def get_phase(self, workstream: str) -> Phase | None:
        """Look up the current phase for a workstream.

        Args:
            workstream: Workstream name.

        Returns:
            The Phase literal, or None if workstream is unknown.
        """
        return self._phases.get(workstream)

    def set_phase(self, workstream: str, phase: Phase) -> None:
        """Override the phase for a workstream.

        Used by the frontend phase-override demo feature to
        demonstrate phase-sensitive digest content shifting.

        Args:
            workstream: Workstream name (must be registered).
            phase: New phase value (must be a valid Phase literal).

        Raises:
            ValueError: If workstream is unknown or phase is invalid.
        """
        if workstream not in self._phases:
            msg = f"Unknown workstream: {workstream}"
            raise ValueError(msg)
        if phase not in _VALID_PHASES:
            msg = f"Invalid phase: {phase}"
            raise ValueError(msg)
        self._phases[workstream] = phase

    def reset(self) -> None:
        """Restore all phases to their default values."""
        self._phases = dict(self._defaults)

    def all_phases(self) -> dict[str, Phase]:
        """Return a copy of the current phase vector.

        Returns:
            Dict mapping workstream names to Phase values.
        """
        return dict(self._phases)

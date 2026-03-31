"""Three fully-specified demo personas for the Context Backbone.

Defines Maya Chen (IC ME), Elena Vasquez (Supply Chain Lead), and
Ryan Torres (Engineering Manager) per design document section 6.1.
These personas drive the relevance scoring demo - same atoms, different
digests based on role, workstream affinities, and phase context.
"""

from __future__ import annotations

from evercurrent.config.loader import get_config
from evercurrent.models.persona import (
    DigestPreferences,
    Persona,
    ScoringWeights,
)


def _build_personas() -> list[Persona]:
    """Build demo personas from YAML config."""
    cfg = get_config()
    scoring_cfg = cfg["scoring"]
    weights = ScoringWeights(**scoring_cfg["default_weights"])
    prefs = DigestPreferences(**scoring_cfg["default_digest_preferences"])

    personas: list[Persona] = []
    for p in cfg["personas"]["personas"]:
        personas.append(
            Persona(
                user_id=p["user_id"],
                name=p["name"],
                role_archetype=p["role_archetype"],
                title=p["title"],
                workstream_affinities=p["workstream_affinities"],
                phase_context=p["phase_context"],
                scoring_weights=weights,
                collaborator_graph=p["collaborator_graph"],
                digest_preferences=prefs,
            )
        )
    return personas


DEMO_PERSONAS: list[Persona] = _build_personas()
"""The three demo personas for the EverCurrent prototype."""

_PERSONA_INDEX: dict[str, Persona] = {p.user_id: p for p in DEMO_PERSONAS}


def get_persona(user_id: str) -> Persona | None:
    """Look up a demo persona by user_id.

    Args:
        user_id: Slack user ID.

    Returns:
        The Persona if found, None otherwise.
    """
    return _PERSONA_INDEX.get(user_id)

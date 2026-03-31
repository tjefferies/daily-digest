"""Three fully-specified demo personas for the Context Backbone.

Defines Maya Chen (IC ME), Elena Vasquez (Supply Chain Lead), and
Ryan Torres (Engineering Manager) per design document section 6.1.
These personas drive the relevance scoring demo — same atoms, different
digests based on role, workstream affinities, and phase context.
"""

from __future__ import annotations

from evercurrent.models.persona import (
    DigestPreferences,
    Persona,
    ScoringWeights,
)

_DEFAULT_WEIGHTS = ScoringWeights(
    workstream_proximity=0.30,
    role_type_alignment=0.20,
    phase_alignment=0.20,
    urgency=0.15,
    social_signal=0.15,
)

_DEFAULT_PREFS = DigestPreferences(
    max_items=25,
    critical_threshold=0.85,
    include_broader_context=True,
)

_MAYA_CHEN = Persona(
    user_id="U001",
    name="Maya Chen",
    role_archetype="IC Engineer",
    title="Senior Mechanical Engineer",
    workstream_affinities={
        "chassis": 1.0,
        "thermal": 0.85,
        "drivetrain": 0.4,
        "supply-chain": 0.3,
        "power-systems": 0.2,
        "sensors": 0.15,
        "firmware": 0.1,
        "end-effector": 0.1,
    },
    phase_context={
        "chassis": "DVT",
        "thermal": "EVT",
        "drivetrain": "DVT",
    },
    scoring_weights=_DEFAULT_WEIGHTS,
    collaborator_graph=["U003", "U008", "U013", "U020"],
    digest_preferences=_DEFAULT_PREFS,
)

_ELENA_VASQUEZ = Persona(
    user_id="U007",
    name="Elena Vasquez",
    role_archetype="Supply Chain",
    title="Supply Chain Manager",
    workstream_affinities={
        "supply-chain": 1.0,
        "chassis": 0.5,
        "drivetrain": 0.5,
        "thermal": 0.4,
        "power-systems": 0.5,
        "sensors": 0.4,
        "firmware": 0.3,
        "end-effector": 0.3,
    },
    phase_context={
        "supply-chain": "DVT",
        "chassis": "DVT",
        "power-systems": "DVT",
    },
    scoring_weights=_DEFAULT_WEIGHTS,
    collaborator_graph=["U011", "U013", "U017", "U019"],
    digest_preferences=_DEFAULT_PREFS,
)

_RYAN_TORRES = Persona(
    user_id="U010",
    name="Ryan Torres",
    role_archetype="Eng Manager",
    title="Engineering Manager",
    workstream_affinities={
        "chassis": 0.8,
        "drivetrain": 0.8,
        "thermal": 0.7,
        "power-systems": 0.7,
        "sensors": 0.6,
        "firmware": 0.6,
        "supply-chain": 0.5,
        "end-effector": 0.5,
    },
    phase_context={
        "chassis": "DVT",
        "drivetrain": "DVT",
        "thermal": "EVT",
        "power-systems": "DVT",
        "sensors": "EVT",
        "firmware": "EVT",
    },
    scoring_weights=_DEFAULT_WEIGHTS,
    collaborator_graph=["U001", "U007", "U011", "U019"],
    digest_preferences=_DEFAULT_PREFS,
)

DEMO_PERSONAS: list[Persona] = [_MAYA_CHEN, _ELENA_VASQUEZ, _RYAN_TORRES]
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

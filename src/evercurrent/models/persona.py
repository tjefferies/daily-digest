"""Persona model: the system's model of what a person cares about.

A persona captures role, workstream affinities, phase context, and
scoring weights that drive relevance computation for digest generation.
"""

from typing import Literal

from pydantic import BaseModel, Field

RoleArchetype = Literal[
    "IC Engineer",
    "Eng Manager",
    "Program Manager",
    "Supply Chain",
    "Executive",
]


class ScoringWeights(BaseModel):
    """Per-persona weights for the five relevance scoring dimensions.

    All weights must be non-negative. They should sum to 1.0 for
    correct composite score computation.

    Attributes:
        workstream_proximity: Weight for workstream affinity match.
        role_type_alignment: Weight for role-type to atom-type alignment.
        phase_alignment: Weight for phase-appropriate atom types.
        urgency: Weight for atom urgency level.
        social_signal: Weight for collaborator graph proximity.
    """

    workstream_proximity: float = Field(ge=0.0)
    role_type_alignment: float = Field(ge=0.0)
    phase_alignment: float = Field(ge=0.0)
    urgency: float = Field(ge=0.0)
    social_signal: float = Field(ge=0.0)


class DigestPreferences(BaseModel):
    """User preferences for digest generation.

    Attributes:
        max_items: Maximum number of atoms in the digest.
        critical_threshold: Score threshold for the requires-action section.
        include_broader_context: Whether to include the broader context section.
    """

    max_items: int = Field(default=25, gt=0)
    critical_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    include_broader_context: bool = Field(default=True)


class Persona(BaseModel):
    """A persona modeling what a specific team member cares about.

    Personas drive relevance scoring: the same atom lands differently
    depending on the reader's role, workstreams, and current phase context.

    Attributes:
        user_id: Slack user ID.
        name: Display name.
        role_archetype: One of five role archetypes from the scoring matrix.
        title: Job title for display and archetype inference.
        workstream_affinities: Map of workstream name to affinity weight (0-1).
        phase_context: Map of workstream name to current development phase.
        scoring_weights: Per-persona weights for relevance scoring dimensions.
        collaborator_graph: List of Slack user IDs this persona works closely with.
        digest_preferences: Configuration for digest generation.
    """

    user_id: str
    name: str
    role_archetype: RoleArchetype
    title: str
    workstream_affinities: dict[str, float]
    phase_context: dict[str, str]
    scoring_weights: ScoringWeights
    collaborator_graph: list[str] = Field(default_factory=list)
    digest_preferences: DigestPreferences = Field(default_factory=DigestPreferences)

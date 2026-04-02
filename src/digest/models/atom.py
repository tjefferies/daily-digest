"""Atom model: the fundamental unit of extracted information.

An atom represents a single piece of actionable information extracted
from Slack conversations by the LLM extraction pipeline. Each atom
is typed, sourced, and scored for relevance to specific personas.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AtomType = Literal[
    "DECISION",
    "SPEC_CHANGE",
    "ACTION_ITEM",
    "BLOCKER",
    "RISK",
    "TEST_RESULT",
    "STATUS_UPDATE",
    "QUESTION",
]

Urgency = Literal["low", "medium", "high", "critical"]

Phase = Literal["Concept", "EVT", "DVT", "PVT", "MP"]


class AtomSource(BaseModel):
    """Source provenance for an extracted atom.

    Attributes:
        channel: Slack channel where the atom originated.
        thread_ts: Slack thread timestamp identifier.
        message_range: Start and end message indices within the thread.
        key_participants: Slack handles of primary contributors.
    """

    channel: str
    thread_ts: str
    message_range: list[int] = Field(min_length=2, max_length=2)
    key_participants: list[str] = Field(default_factory=list)


class AtomWorkstreams(BaseModel):
    """Workstream tagging for cross-team relevance.

    Attributes:
        originating: The workstream where the atom was produced.
        affected: Other workstreams affected by this atom.
    """

    originating: str
    affected: list[str] = Field(default_factory=list)


class Atom(BaseModel):
    """An information atom extracted from Slack conversations.

    Atoms are the fundamental unit of the Daily Digest Tool extraction pipeline.
    Each atom represents a single piece of actionable information (a decision,
    spec change, blocker, etc.) with full provenance and scoring metadata.

    Attributes:
        atom_id: Unique identifier for this atom.
        type: One of 8 atom type literals defining the information category.
        summary: One-line summary of the atom content.
        detail: Expanded explanation with context.
        source: Provenance linking back to the Slack thread.
        workstreams: Originating and affected workstream tags.
        urgency: Urgency level from low to critical.
        confidence: LLM confidence score between 0 and 1.
        implicit_decision: Whether this was an implicit rather than explicit decision.
        phase_relevance: Hardware development phases this atom is relevant to.
    """

    atom_id: UUID
    type: AtomType
    summary: str
    detail: str
    source: AtomSource
    workstreams: AtomWorkstreams
    urgency: Urgency
    confidence: float = Field(ge=0.0, le=1.0)
    implicit_decision: bool = Field(default=False)
    phase_relevance: list[Phase] = Field(default_factory=list)

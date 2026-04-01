"""Digest model: the generated daily digest structure.

A digest is organized into four priority-tiered sections, each
containing scored and filtered atoms relevant to a specific persona.
"""

from typing import Literal

from pydantic import BaseModel, Field

SectionType = Literal[
    "requires_action",
    "decisions_changes",
    "progress_risks",
    "broader_context",
]


class DigestItem(BaseModel):
    """A single item within a digest section.

    Attributes:
        headline: Bold one-line summary of what happened.
        context: 1-2 sentence context for the reader.
        source_channel: Slack channel reference.
        atom_id: UUID of the source atom.
    """

    headline: str
    context: str
    source_channel: str = ""
    atom_id: str = ""


class DigestSection(BaseModel):
    """A single section within a persona's daily digest.

    Attributes:
        section_type: Which of the four digest sections this represents.
        title: Human-readable section heading.
        items: Digest items (headline + context + source).
    """

    section_type: SectionType
    title: str
    items: list[DigestItem] = Field(default_factory=list)


class Digest(BaseModel):
    """A complete daily digest generated for a specific persona.

    Attributes:
        persona_id: Slack user ID of the persona this digest is for.
        sections: The four priority-tiered digest sections.
    """

    persona_id: str
    sections: list[DigestSection] = Field(default_factory=list)

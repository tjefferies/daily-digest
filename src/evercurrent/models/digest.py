"""Digest model: the generated daily digest structure.

A digest is organized into four priority-tiered sections, each
containing scored and filtered atoms relevant to a specific persona.
"""

from typing import Literal

from pydantic import BaseModel, Field

from evercurrent.models.atom import Atom

SectionType = Literal[
    "requires_action",
    "decisions_changes",
    "progress_risks",
    "broader_context",
]


class DigestSection(BaseModel):
    """A single section within a persona's daily digest.

    Attributes:
        section_type: Which of the four digest sections this represents.
        title: Human-readable section heading.
        atoms: Ordered list of atoms in this section, ranked by relevance.
    """

    section_type: SectionType
    title: str
    atoms: list[Atom] = Field(default_factory=list)


class Digest(BaseModel):
    """A complete daily digest generated for a specific persona.

    Attributes:
        persona_id: Slack user ID of the persona this digest is for.
        sections: The four priority-tiered digest sections.
    """

    persona_id: str
    sections: list[DigestSection] = Field(default_factory=list)

"""Structured LLM response wrapper models for instructor integration.

These models serve as the response_model parameter for instructor-based
structured output, wrapping the existing Atom and DigestSection models
into top-level schemas that instructor can validate and return directly.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from evercurrent.models.atom import Atom  # noqa: TC001
from evercurrent.models.digest import DigestSection  # noqa: TC001


class ExtractionResponse(BaseModel):
    """Wrapper for extraction pipeline LLM responses.

    Attributes:
        atoms: List of extracted Atom objects from a context window.
    """

    atoms: list[Atom] = Field(default_factory=list)


class ValidationResponse(BaseModel):
    """Wrapper for atom validation LLM responses.

    Attributes:
        valid: Whether the atom accurately represents the source conversation.
        reason: Explanation if the atom failed validation.
    """

    valid: bool
    reason: str = ""


class DigestResponse(BaseModel):
    """Wrapper for digest generation LLM responses.

    Attributes:
        sections: List of DigestSection objects for the persona digest.
    """

    sections: list[DigestSection] = Field(default_factory=list)

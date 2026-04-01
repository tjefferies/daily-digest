"""Structured LLM response wrapper models for instructor integration.

These models serve as the response_model parameter for instructor-based
structured output, wrapping the existing Atom and DigestSection models
into top-level schemas that instructor can validate and return directly.

Extraction uses a two-stage pipeline:
  Stage 1 (CoarseExtractionResponse): identify events → type, summary, detail, source
  Stage 2 (EnrichmentResponse): enrich each event → workstreams, urgency, confidence, etc.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from evercurrent.models.atom import (  # noqa: TC001
    AtomWorkstreams,
    Phase,
    Urgency,
)
from evercurrent.models.digest import DigestSection  # noqa: TC001


class CoarseExtractionResponse(BaseModel):
    """Stage 1 response: coarse event identification.

    Returns lightweight atom dicts containing only the core event
    fields (type, summary, detail, source) without metadata.

    Attributes:
        atoms: List of atom dicts with type, summary, detail, source.
    """

    atoms: list[dict] = Field(default_factory=list)


class EnrichmentResponse(BaseModel):
    """Stage 2 response: metadata enrichment for a single atom.

    Given a coarse atom and its thread context, assigns metadata
    fields: workstreams, urgency, confidence, implicit_decision,
    and phase_relevance.

    Attributes:
        workstreams: Originating and affected workstream tags.
        urgency: Urgency level from low to critical.
        confidence: LLM confidence score between 0 and 1.
        implicit_decision: Whether this was an implicit decision.
        phase_relevance: Hardware development phases this atom is relevant to.
    """

    workstreams: AtomWorkstreams
    urgency: Urgency
    confidence: float = Field(ge=0.0, le=1.0)
    implicit_decision: bool = False
    phase_relevance: list[Phase] = Field(default_factory=list)


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

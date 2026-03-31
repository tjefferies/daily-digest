"""Digest generation runner: per-persona LLM digest generation (sync and async).

Takes ranked ScoredAtoms from Layer 4, clusters by workstream, and
passes them through the LLM API using instructor for structured output
to produce DigestSection objects with the generation prompt defining
tone, format, and structure.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from evercurrent.config.loader import get_config
from evercurrent.generation.prompt import build_generation_prompt
from evercurrent.models.responses import DigestResponse

if TYPE_CHECKING:
    from evercurrent.llm.types import AsyncLLMClient, LLMClient
    from evercurrent.models.digest import DigestSection
    from evercurrent.models.persona import Persona
    from evercurrent.scoring.composite import ScoredAtom

logger = logging.getLogger(__name__)

_pipeline_cfg = get_config()["pipeline"]
_MODEL = _pipeline_cfg["model"]
_MAX_TOKENS = _pipeline_cfg["generation_max_tokens"]


class DigestGenerator:
    """Generates digest sections from scored atoms via LLM.

    For each persona, constructs a user message containing the persona
    context and ranked scored atoms, then sends to the LLM API with
    instructor for structured output. Returns DigestSection objects directly.

    Attributes:
        stats: Dict tracking personas_processed and sections_produced.
    """

    def __init__(self, client: LLMClient) -> None:
        """Initialize with an LLM client.

        Args:
            client: LLMClient-compatible adapter instance.
        """
        self._client = client
        self._system_prompt = build_generation_prompt()
        self.stats: dict[str, int] = {
            "personas_processed": 0,
            "sections_produced": 0,
        }

    def generate(
        self,
        scored_atoms: list[ScoredAtom],
        persona: Persona,
    ) -> list[DigestSection]:
        """Generate digest sections for a persona from scored atoms.

        Args:
            scored_atoms: Ranked ScoredAtom list from Layer 4.
            persona: The persona to generate the digest for.

        Returns:
            List of DigestSection objects from structured LLM response.
            Returns empty list if no atoms or API/parse failure.
        """
        if not scored_atoms:
            return []

        user_message = _build_user_message(scored_atoms, persona)
        try:
            response = self._client.create_structured_message(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=self._system_prompt,
                messages=[{"role": "user", "content": user_message}],
                response_model=DigestResponse,
            )
        except Exception:
            logger.warning("Structured digest generation failed")
            return []

        sections = response.sections
        if not persona.digest_preferences.include_broader_context:
            sections = [s for s in sections if s.section_type != "broader_context"]

        self.stats["personas_processed"] += 1
        self.stats["sections_produced"] += len(sections)
        return sections


class AsyncDigestGenerator:
    """Async generator that produces digest sections from scored atoms via LLM.

    Attributes:
        stats: Dict tracking personas_processed and sections_produced.
    """

    def __init__(self, client: AsyncLLMClient) -> None:
        """Initialize with an async LLM client.

        Args:
            client: AsyncLLMClient-compatible adapter instance.
        """
        self._client = client
        self._system_prompt = build_generation_prompt()
        self.stats: dict[str, int] = {
            "personas_processed": 0,
            "sections_produced": 0,
        }

    async def generate(
        self,
        scored_atoms: list[ScoredAtom],
        persona: Persona,
    ) -> list[DigestSection]:
        """Generate digest sections for a persona from scored atoms.

        Args:
            scored_atoms: Ranked ScoredAtom list from Layer 4.
            persona: The persona to generate the digest for.

        Returns:
            List of DigestSection objects from structured LLM response.
        """
        if not scored_atoms:
            return []

        user_message = _build_user_message(scored_atoms, persona)
        try:
            response = await self._client.create_structured_message(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=self._system_prompt,
                messages=[{"role": "user", "content": user_message}],
                response_model=DigestResponse,
            )
        except Exception:
            logger.warning("Structured digest generation failed")
            return []

        sections = response.sections
        if not persona.digest_preferences.include_broader_context:
            sections = [s for s in sections if s.section_type != "broader_context"]

        self.stats["personas_processed"] += 1
        self.stats["sections_produced"] += len(sections)
        return sections


def _build_user_message(
    scored_atoms: list[ScoredAtom],
    persona: Persona,
) -> str:
    """Build the user message with persona context and atom data.

    Args:
        scored_atoms: Ranked scored atoms to include.
        persona: Persona for context framing.

    Returns:
        Formatted string with persona profile and atom details.
    """
    atoms_data = [
        {
            "atom_id": str(sa.atom.atom_id),
            "type": sa.atom.type,
            "summary": sa.atom.summary,
            "detail": sa.atom.detail,
            "source_channel": sa.atom.source.channel,
            "source_thread_ts": sa.atom.source.thread_ts,
            "workstream": sa.atom.workstreams.originating,
            "affected": sa.atom.workstreams.affected,
            "urgency": sa.atom.urgency,
            "score": sa.score,
            "critical": sa.critical,
        }
        for sa in scored_atoms
    ]
    return (
        f"## Persona\n"
        f"Name: {persona.name}\n"
        f"Role: {persona.role_archetype}\n"
        f"Title: {persona.title}\n"
        f"Workstreams: {json.dumps(persona.workstream_affinities)}\n"
        f"Phase context: {json.dumps(persona.phase_context)}\n"
        f"Include broader context: "
        f"{persona.digest_preferences.include_broader_context}\n\n"
        f"## Scored Atoms (ranked by relevance)\n"
        f"{json.dumps(atoms_data, indent=2)}\n"
    )

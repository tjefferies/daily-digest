"""Digest generation runner: per-persona LLM digest generation.

Takes ranked ScoredAtoms from Layer 4, clusters by workstream, and
passes them through the Anthropic API to produce DigestSection objects
with the generation prompt defining tone, format, and structure.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from anthropic.types import TextBlock

from evercurrent.generation.prompt import build_generation_prompt
from evercurrent.models.digest import DigestSection

if TYPE_CHECKING:
    from anthropic import Anthropic

    from evercurrent.models.persona import Persona
    from evercurrent.scoring.composite import ScoredAtom

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"


class DigestGenerator:
    """Generates digest sections from scored atoms via LLM.

    For each persona, constructs a user message containing the persona
    context and ranked scored atoms, then sends to Anthropic API with
    the generation system prompt. Parses the response into DigestSection
    objects.

    Attributes:
        stats: Dict tracking personas_processed and sections_produced.
    """

    def __init__(self, client: Anthropic) -> None:
        """Initialize with an Anthropic client.

        Args:
            client: Anthropic API client instance.
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
            List of DigestSection objects parsed from LLM response.
            Returns empty list if no atoms or API/parse failure.
        """
        if not scored_atoms:
            return []

        user_message = self._build_user_message(scored_atoms, persona)
        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=4096,
            system=self._system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        sections = self._parse_response(response, persona)
        self.stats["personas_processed"] += 1
        self.stats["sections_produced"] += len(sections)
        return sections

    def _build_user_message(
        self,
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

    def _parse_response(
        self,
        response: Any,  # noqa: ANN401
        persona: Persona,
    ) -> list[DigestSection]:
        """Parse API response into DigestSection objects.

        Args:
            response: Raw Anthropic API response.
            persona: Persona for broader_context filtering.

        Returns:
            List of DigestSection objects. Empty on parse failure.
        """
        block = response.content[0]
        if not isinstance(block, TextBlock):
            logger.warning("Expected TextBlock, got %s", type(block).__name__)
            return []

        try:
            data: Any = json.loads(block.text)  # noqa: ANN401
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON: %s...", block.text[:100])
            return []

        if not isinstance(data, dict) or "sections" not in data:
            logger.warning("Response missing 'sections' key")
            return []

        sections: list[DigestSection] = []
        for section_data in data["sections"]:
            section = DigestSection(
                section_type=section_data["section_type"],
                title=section_data["title"],
            )
            sections.append(section)

        if not persona.digest_preferences.include_broader_context:
            sections = [s for s in sections if s.section_type != "broader_context"]

        return sections

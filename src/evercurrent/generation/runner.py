"""Digest generation runner: per-persona LLM digest generation.

Takes ranked ScoredAtoms from Layer 4, clusters by workstream, and
passes them through the LLM API to produce DigestSection objects
with the generation prompt defining tone, format, and structure.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from evercurrent.config.loader import get_config
from evercurrent.generation.prompt import build_generation_prompt
from evercurrent.models.digest import DigestSection

if TYPE_CHECKING:
    from evercurrent.llm.types import LLMClient
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
    the generation system prompt. Parses the response into DigestSection
    objects.

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
            List of DigestSection objects parsed from LLM response.
            Returns empty list if no atoms or API/parse failure.
        """
        if not scored_atoms:
            return []

        user_message = self._build_user_message(scored_atoms, persona)
        try:
            response = self._client.create_message(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=self._system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except ValueError:
            logger.warning("LLM returned non-text response for digest generation")
            return []
        sections = self._parse_response(response.text, persona)
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
        raw_text: str,
        persona: Persona,
    ) -> list[DigestSection]:
        """Parse LLM response text into DigestSection objects.

        Args:
            raw_text: Raw text string from the LLM response.
            persona: Persona for broader_context filtering.

        Returns:
            List of DigestSection objects. Empty on parse failure.
        """
        try:
            data: Any = json.loads(raw_text)  # noqa: ANN401
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON: %s...", raw_text[:100])
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

"""Digest assembler: orchestrates the full pipeline for one persona.

Wires together context lookup, phase override, scoring, and async digest
generation into a single assemble() call used by the /digest endpoint.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from digest.context.personas import get_persona
from digest.generation.runner import AsyncDigestGenerator
from digest.scoring.composite import score_atoms

if TYPE_CHECKING:
    from digest.llm.types import AsyncLLMClient
    from digest.models.atom import Atom

logger = logging.getLogger(__name__)


class AsyncDigestAssembler:
    """Async orchestrator for the full digest pipeline for a single persona.

    Combines persona lookup, phase override, composite scoring, and
    async LLM-based digest generation into one awaitable operation.
    """

    def __init__(self, client: AsyncLLMClient) -> None:
        """Initialize with an async LLM client.

        Args:
            client: AsyncLLMClient-compatible adapter instance.
        """
        self._client = client
        self._generator = AsyncDigestGenerator(client)

    async def assemble(
        self,
        persona_id: str,
        atoms: list[Atom],
        phase_override: str | None = None,
    ) -> dict[str, Any]:
        """Assemble a complete digest for a persona asynchronously.

        Args:
            persona_id: Slack user ID of the persona.
            atoms: Extracted atoms to score and generate from.
            phase_override: Optional "workstream:phase" override string.

        Returns:
            Dict with persona_id, generated_at, and sections.
        """
        persona = get_persona(persona_id)
        if persona is None:
            return {"error": f"Unknown persona: {persona_id}"}

        if phase_override is not None:
            error = _apply_phase_override(persona_id, phase_override)
            if error:
                return {"error": error}

        if not atoms:
            return {
                "persona_id": persona_id,
                "generated_at": datetime.now(tz=UTC).isoformat(),
                "sections": [],
            }

        scored = score_atoms(atoms, persona)
        sections = await self._generator.generate(scored, persona)

        # Use max source timestamp as "data as of" indicator
        data_as_of = _max_source_timestamp(atoms)

        return {
            "persona_id": persona_id,
            "generated_at": data_as_of,
            "sections": [s.model_dump() for s in sections],
        }


def _max_source_timestamp(atoms: list[Atom]) -> str:
    """Return the max source thread_ts as an ISO timestamp.

    Converts Slack timestamps (epoch seconds as string) to datetime.
    Falls back to current time if no valid timestamps found.

    Args:
        atoms: List of atoms with source.thread_ts fields.

    Returns:
        ISO 8601 timestamp string.
    """
    max_ts = 0.0
    for atom in atoms:
        try:
            ts = float(atom.source.thread_ts)
            if ts > max_ts:
                max_ts = ts
        except (ValueError, TypeError):
            continue
    if max_ts > 0:
        return datetime.fromtimestamp(max_ts, tz=UTC).isoformat()
    return datetime.now(tz=UTC).isoformat()


def _apply_phase_override(
    persona_id: str,
    phase_override: str,
) -> str | None:
    """Parse and apply a phase override string.

    Args:
        persona_id: Persona ID for logging.
        phase_override: String in "workstream:phase" format.

    Returns:
        Error message string if invalid, None if successful.
    """
    parts = phase_override.split(":")
    if len(parts) != 2:  # noqa: PLR2004
        return f"Invalid phase_override format: {phase_override!r}. Expected 'workstream:phase'"
    logger.info(
        "Phase override for %s: %s -> %s",
        persona_id,
        parts[0],
        parts[1],
    )
    return None

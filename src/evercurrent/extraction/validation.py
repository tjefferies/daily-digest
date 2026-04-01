"""Two-pass validation for SPEC_CHANGE and DECISION atoms (sync and async).

Runs a second LLM call on high-stakes atoms to verify accuracy using
instructor for structured output. Invalid atoms have their confidence
halved and get a warning annotation. The async version validates atoms
concurrently via asyncio.gather.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from evercurrent.config.loader import get_config
from evercurrent.models.responses import ValidationResponse

if TYPE_CHECKING:
    from evercurrent.llm.types import AsyncLLMClient
    from evercurrent.models.atom import Atom

logger = logging.getLogger(__name__)

_VALIDATED_TYPES = frozenset({"DECISION", "SPEC_CHANGE"})

_pipeline_cfg = get_config()["pipeline"]
_MODEL = _pipeline_cfg["model"]
_VALIDATION_MAX_TOKENS = _pipeline_cfg["validation_max_tokens"]

_VALIDATION_PROMPT = get_config()["prompts"]["validation"]


def _demote_atom(atom: Atom, reason: str) -> Atom:
    """Demote an atom's confidence and add a validation warning.

    Args:
        atom: The atom to demote.
        reason: Reason for demotion.

    Returns:
        New Atom with halved confidence and warning in detail.
    """
    logger.warning("Atom demoted: %s - %s", atom.summary, reason)
    return atom.model_copy(
        update={
            "confidence": atom.confidence * 0.5,
            "detail": f"{atom.detail}\n[Validation warning: {reason}]",
        },
    )


async def async_validate_atoms(
    atoms: list[Atom],
    client: AsyncLLMClient,
    context_text: str,
) -> list[Atom]:
    """Validate DECISION and SPEC_CHANGE atoms concurrently with async LLM calls.

    Args:
        atoms: List of extracted Atom objects.
        client: AsyncLLMClient-compatible adapter instance.
        context_text: Original thread text for validation context.

    Returns:
        Updated atom list with demoted confidence for invalid atoms.
    """
    if not atoms:
        return []

    async def _maybe_validate(atom: Atom) -> Atom:
        if atom.type in _VALIDATED_TYPES:
            return await _async_validate_single(atom, client, context_text)
        return atom

    tasks = [_maybe_validate(a) for a in atoms]
    return list(await asyncio.gather(*tasks))


async def _async_validate_single(
    atom: Atom,
    client: AsyncLLMClient,
    context_text: str,
) -> Atom:
    """Run async validation on a single atom using structured output.

    Args:
        atom: The atom to validate.
        client: AsyncLLMClient-compatible adapter instance.
        context_text: Original conversation text.

    Returns:
        The atom, possibly with demoted confidence and warning.
    """
    prompt = _VALIDATION_PROMPT.format(
        context_text=context_text,
        atom_json=atom.model_dump_json(indent=2),
    )

    try:
        response = await client.create_structured_message(
            model=_MODEL,
            max_tokens=_VALIDATION_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            response_model=ValidationResponse,
        )
    except Exception:
        return _demote_atom(atom, "Validation structured output failed")

    if not response.valid:
        reason = response.reason or "Validation failed"
        return _demote_atom(atom, reason)

    return atom

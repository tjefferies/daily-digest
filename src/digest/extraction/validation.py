"""Two-pass validation for SPEC_CHANGE and DECISION atoms via single batch.

Collects ALL validation prompts across all source threads and submits
them as ONE Anthropic Message Batch with tool_use. Invalid atoms have
their confidence halved and get a warning annotation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from anthropic import Anthropic

from digest.config.loader import get_config
from digest.db.llm_logger import log_llm_request, log_llm_response
from digest.extraction.batch_runner import (
    _MAX_POLL_ATTEMPTS,
    _POLL_INTERVAL,
    _extract_tool_input,
    _split_into_sub_batches,
)

if TYPE_CHECKING:
    from digest.models.atom import Atom

logger = logging.getLogger(__name__)

_pipeline_cfg = get_config()["pipeline"]
_MODEL = _pipeline_cfg["model"]
_VALIDATION_MAX_TOKENS = _pipeline_cfg["validation_max_tokens"]
_MAX_PER_BATCH = _pipeline_cfg.get("max_requests_per_batch", 200)

_VALIDATION_PROMPT = get_config()["prompts"]["validation"]

_VALIDATION_TOOL = {
    "name": "validate_atom",
    "description": "Return whether the extracted atom accurately represents the source.",
    "input_schema": {
        "type": "object",
        "properties": {
            "valid": {"type": "boolean"},
            "reason": {"type": "string"},
        },
        "required": ["valid", "reason"],
    },
}


def _demote_atom(atom: Atom, reason: str) -> Atom:
    """Demote an atom's confidence and add a validation warning.

    Args:
        atom: The atom to demote.
        reason: Reason for demotion.

    Returns:
        New Atom with halved confidence and warning in detail.
    """
    logger.warning("Atom demoted: %s - %s", atom.summary[:80], reason[:120])
    return atom.model_copy(
        update={
            "confidence": atom.confidence * 0.5,
            "detail": f"{atom.detail}\n[Validation warning: {reason}]",
        },
    )


async def async_validate_atoms_batch(
    atoms_with_context: list[tuple[int, Atom, str]],
    all_atoms: list[Atom],
) -> list[Atom]:
    """Validate all DECISION/SPEC_CHANGE atoms in a single batch.

    Each atom is validated against its own source thread text.
    All validation requests go into ONE batch submission.

    Args:
        atoms_with_context: List of (index, atom, context_text) tuples
            for atoms that need validation.
        all_atoms: Full atom list. Validated atoms are updated in place
            by index.

    Returns:
        Updated atom list with demoted confidence for invalid atoms.
    """
    # Build ALL validation requests in one list
    requests = []
    for idx, atom, context in atoms_with_context:
        prompt = _VALIDATION_PROMPT.format(
            context_text=context,
            atom_json=atom.model_dump_json(indent=2),
        )
        requests.append(
            {
                "custom_id": f"val-{idx}",
                "params": {
                    "model": _MODEL,
                    "max_tokens": _VALIDATION_MAX_TOKENS,
                    "messages": [{"role": "user", "content": prompt}],
                    "tools": [_VALIDATION_TOOL],
                    "tool_choice": {"type": "tool", "name": "validate_atom"},
                },
            }
        )

    logger.info("Validation: submitting %d requests as single batch", len(requests))

    # Submit all in one batch (split at max_per_batch)
    client = Anthropic()
    all_results: dict[str, dict[str, Any]] = {}
    for sub in _split_into_sub_batches(requests, _MAX_PER_BATCH):
        sub_results = await _submit_validation_batch(client, sub)
        all_results.update(sub_results)

    # Apply results back to the atom list
    results = list(all_atoms)
    demoted = 0
    for idx, atom, _context in atoms_with_context:
        key = f"val-{idx}"
        tool_input = all_results.get(key)
        if tool_input is None:
            results[idx] = _demote_atom(atom, "Validation batch result missing")
            demoted += 1
        elif not tool_input.get("valid", True):
            reason = tool_input.get("reason", "Validation failed")
            results[idx] = _demote_atom(atom, reason)
            demoted += 1

    logger.info(
        "Validation complete: %d checked, %d demoted",
        len(atoms_with_context),
        demoted,
    )

    await log_llm_request(
        batch_id=f"validation-{id(all_atoms)}",
        stage="validation",
        request_count=len(requests),
        request_body={"count": len(requests)},
    )
    await log_llm_response(
        batch_id=f"validation-{id(all_atoms)}",
        status="completed",
        response_body={"validated": len(requests), "demoted": demoted},
    )

    return results


async def _submit_validation_batch(
    client: Anthropic,
    requests: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Submit a validation batch and poll until completion.

    Args:
        client: Raw Anthropic SDK client.
        requests: Batch request dicts.

    Returns:
        Dict mapping custom_id to tool_use input.
    """
    batch = client.messages.batches.create(requests=requests)
    batch_id = batch.id
    total = len(requests)
    logger.info("Validation batch %s: %d requests", batch_id, total)

    consecutive_failures = 0
    for _attempt in range(_MAX_POLL_ATTEMPTS):
        delay = _POLL_INTERVAL * (2 ** min(consecutive_failures, 5))
        await asyncio.sleep(delay)
        try:
            status = client.messages.batches.retrieve(batch_id)
            consecutive_failures = 0
        except Exception:
            consecutive_failures += 1
            logger.warning(
                "Validation poll failed for %s (attempt %d)",
                batch_id,
                consecutive_failures,
                exc_info=True,
            )
            continue
        counts = status.request_counts
        logger.info(
            "Validation %s: %d/%d succeeded, %d processing",
            batch_id,
            counts.succeeded,
            total,
            counts.processing,
        )
        if status.processing_status == "ended":
            break
    else:
        logger.warning("Validation batch %s timed out", batch_id)
        return {}

    results: dict[str, dict[str, Any]] = {}
    for result in client.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            tool_input = _extract_tool_input(result.result.message)
            if tool_input is not None:
                results[result.custom_id] = tool_input
    return results

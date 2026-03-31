"""Two-pass validation for SPEC_CHANGE and DECISION atoms (ADR-005).

Runs a second LLM call on high-stakes atoms to verify accuracy.
Invalid atoms have their confidence halved and get a warning annotation.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from anthropic.types import TextBlock

from evercurrent.config.loader import get_config

if TYPE_CHECKING:
    from anthropic import Anthropic

    from evercurrent.models.atom import Atom

logger = logging.getLogger(__name__)

_VALIDATED_TYPES = frozenset({"DECISION", "SPEC_CHANGE"})

_pipeline_cfg = get_config()["pipeline"]
_MODEL = _pipeline_cfg["model"]
_VALIDATION_MAX_TOKENS = _pipeline_cfg["validation_max_tokens"]

_VALIDATION_PROMPT = """\
You are validating an information atom extracted from a Slack conversation.

## Original conversation:
{context_text}

## Extracted atom:
{atom_json}

## Task:
Does this atom accurately represent what was said in the conversation?
Check for:
- Overstated conclusions (presenting uncertain discussion as firm decision)
- Understated impact (missing affected workstreams or urgency)
- Fabricated details (numbers, names, or specs not in the original text)

Respond with JSON: {{"valid": true/false, "reason": "explanation if invalid"}}
"""


def validate_atoms(
    atoms: list[Atom],
    client: Anthropic,
    context_text: str,
) -> list[Atom]:
    """Validate DECISION and SPEC_CHANGE atoms with a second LLM pass.

    Args:
        atoms: List of extracted Atom objects.
        client: Anthropic API client.
        context_text: Original thread text for validation context.

    Returns:
        Updated atom list with demoted confidence for invalid atoms.
    """
    result: list[Atom] = []
    for atom in atoms:
        if atom.type in _VALIDATED_TYPES:
            atom = _validate_single(atom, client, context_text)
        result.append(atom)
    return result


def _validate_single(
    atom: Atom,
    client: Anthropic,
    context_text: str,
) -> Atom:
    """Run validation on a single atom.

    Args:
        atom: The atom to validate.
        client: Anthropic API client.
        context_text: Original conversation text.

    Returns:
        The atom, possibly with demoted confidence and warning.
    """
    prompt = _VALIDATION_PROMPT.format(
        context_text=context_text,
        atom_json=atom.model_dump_json(indent=2),
    )

    response = client.messages.create(
        model=_MODEL,
        max_tokens=_VALIDATION_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    block = response.content[0]
    if not isinstance(block, TextBlock):
        return _demote_atom(atom, "Validation returned non-text response")

    try:
        data = json.loads(block.text)
    except json.JSONDecodeError:
        return _demote_atom(atom, "Validation response was not valid JSON")

    if not data.get("valid", False):
        reason = data.get("reason", "Validation failed")
        return _demote_atom(atom, reason)

    return atom


def _demote_atom(atom: Atom, reason: str) -> Atom:
    """Demote an atom's confidence and add a validation warning.

    Args:
        atom: The atom to demote.
        reason: Reason for demotion.

    Returns:
        New Atom with halved confidence and warning in detail.
    """
    logger.warning("Atom demoted: %s — %s", atom.summary, reason)
    return atom.model_copy(
        update={
            "confidence": atom.confidence * 0.5,
            "detail": f"{atom.detail}\n[Validation warning: {reason}]",
        },
    )

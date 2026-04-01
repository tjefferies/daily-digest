"""LLM extraction system prompts for two-stage atom extraction.

Loads prompts from config/prompts.yml. Stage 1 (coarse) identifies events.
Stage 2 (enrichment) assigns metadata.
"""

from digest.config.loader import get_config


def build_coarse_prompt() -> str:
    """Return the Stage 1 system prompt for coarse event identification.

    Returns:
        System prompt loaded from config/prompts.yml.
    """
    return get_config()["prompts"]["coarse_extraction"]


def build_enrichment_prompt() -> str:
    """Return the Stage 2 system prompt for metadata enrichment.

    Returns:
        System prompt loaded from config/prompts.yml.
    """
    return get_config()["prompts"]["enrichment"]

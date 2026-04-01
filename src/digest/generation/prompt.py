"""Digest generation system prompt.

Loads the generation prompt from config/prompts.yml.
"""

from digest.config.loader import get_config


def build_generation_prompt() -> str:
    """Return the system prompt for LLM digest generation.

    Returns:
        System prompt loaded from config/prompts.yml.
    """
    return get_config()["prompts"]["digest_generation"]

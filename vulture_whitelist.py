"""Vulture whitelist: false positives that are actually used at runtime.

Vulture cannot detect usage through string-based cast() calls,
Pydantic model_config, pytest fixtures, or __all__ exports.
Each entry explains why it is a false positive.
"""

# Used in cast("list[MessageParam]", ...) in src/digest/llm/anthropic.py
# Vulture misses string-based type references in cast() calls.
MessageParam  # noqa: F821

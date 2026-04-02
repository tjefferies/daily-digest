"""Factory for creating Anthropic async LLM client instances.

Instantiates the AsyncAnthropicAdapter for use by the pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from anthropic import AsyncAnthropic

if TYPE_CHECKING:
    from digest.llm.types import AsyncLLMClient


def create_async_llm_client() -> AsyncLLMClient:
    """Create an async Anthropic LLM client.

    Returns:
        AsyncAnthropicAdapter wrapping a new AsyncAnthropic SDK client.
    """
    from digest.llm.anthropic import AsyncAnthropicAdapter

    return AsyncAnthropicAdapter(AsyncAnthropic())

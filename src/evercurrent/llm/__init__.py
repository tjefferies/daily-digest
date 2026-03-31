"""Model-agnostic LLM client abstraction (sync and async).

Provides a unified interface for Anthropic, OpenAI, and Google Gemini
APIs. Use create_llm_client() or create_async_llm_client() factory
to instantiate the configured provider.
"""

from evercurrent.llm.factory import create_async_llm_client, create_llm_client
from evercurrent.llm.types import AsyncLLMClient, LLMClient, LLMResponse

__all__ = [
    "AsyncLLMClient",
    "LLMClient",
    "LLMResponse",
    "create_async_llm_client",
    "create_llm_client",
]

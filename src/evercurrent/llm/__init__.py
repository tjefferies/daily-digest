"""Model-agnostic LLM client abstraction.

Provides a unified interface for Anthropic, OpenAI, and Google Gemini
APIs. Use create_llm_client() factory to instantiate the configured
provider.
"""

from evercurrent.llm.factory import create_llm_client
from evercurrent.llm.types import LLMClient, LLMResponse

__all__ = ["LLMClient", "LLMResponse", "create_llm_client"]

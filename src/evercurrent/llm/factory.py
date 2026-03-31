"""Factory for creating LLM client instances from config (sync and async).

Reads the provider setting from pipeline config and instantiates
the appropriate adapter. Supports lazy imports for optional SDKs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from anthropic import Anthropic, AsyncAnthropic

if TYPE_CHECKING:
    from evercurrent.llm.types import AsyncLLMClient, LLMClient

# Lazy-loaded SDK classes for optional providers.
# These are resolved at call time and can be patched in tests.
OpenAI: Any = None
AsyncOpenAI: Any = None
GenerativeModel: Any = None


def create_llm_client(
    *,
    provider: str = "anthropic",
    model: str | None = None,
) -> LLMClient:
    """Create an LLM client for the specified provider.

    Args:
        provider: LLM provider name ('anthropic', 'openai', 'google').
        model: Model identifier, required for Google (sets at client init).

    Returns:
        An LLMClient-compatible adapter instance.

    Raises:
        ValueError: If the provider is not supported.
        ImportError: If the provider's SDK is not installed.
    """
    if provider == "anthropic":
        return _create_anthropic()
    if provider == "openai":
        return _create_openai()
    if provider == "google":
        return _create_google(model)
    msg = f"Unsupported LLM provider: {provider!r}. Use 'anthropic', 'openai', or 'google'."
    raise ValueError(msg)


def _create_anthropic() -> LLMClient:
    """Create an Anthropic adapter.

    Returns:
        AnthropicAdapter wrapping a new Anthropic SDK client.
    """
    from evercurrent.llm.anthropic import AnthropicAdapter

    return AnthropicAdapter(Anthropic())


def _create_openai() -> LLMClient:
    """Create an OpenAI adapter.

    Returns:
        OpenAIAdapter wrapping a new OpenAI SDK client.

    Raises:
        ImportError: If the openai package is not installed.
    """
    global OpenAI  # noqa: PLW0603
    if OpenAI is None:
        from openai import (  # ty: ignore[unresolved-import]
            OpenAI as _OpenAI,  # type: ignore[import-untyped]
        )

        OpenAI = _OpenAI

    from evercurrent.llm.openai import OpenAIAdapter

    return OpenAIAdapter(OpenAI())


def _create_google(model: str | None) -> LLMClient:
    """Create a Google Gemini adapter.

    Args:
        model: Gemini model name for GenerativeModel initialization.

    Returns:
        GoogleAdapter wrapping a new GenerativeModel instance.

    Raises:
        ImportError: If the google-generativeai package is not installed.
    """
    global GenerativeModel  # noqa: PLW0603
    if GenerativeModel is None:
        import google.generativeai as genai  # type: ignore[import-untyped] # ty: ignore[unresolved-import]

        GenerativeModel = genai.GenerativeModel

    from evercurrent.llm.google import GoogleAdapter

    return GoogleAdapter(GenerativeModel(model or "gemini-2.0-flash"))


def create_async_llm_client(
    *,
    provider: str = "anthropic",
    model: str | None = None,
) -> AsyncLLMClient:
    """Create an async LLM client for the specified provider.

    Args:
        provider: LLM provider name ('anthropic', 'openai', 'google').
        model: Model identifier, required for Google (sets at client init).

    Returns:
        An AsyncLLMClient-compatible adapter instance.

    Raises:
        ValueError: If the provider is not supported.
        ImportError: If the provider's SDK is not installed.
    """
    if provider == "anthropic":
        return _create_async_anthropic()
    if provider == "openai":
        return _create_async_openai()
    if provider == "google":
        return _create_async_google(model)
    msg = f"Unsupported LLM provider: {provider!r}. Use 'anthropic', 'openai', or 'google'."
    raise ValueError(msg)


def _create_async_anthropic() -> AsyncLLMClient:
    """Create an async Anthropic adapter.

    Returns:
        AsyncAnthropicAdapter wrapping a new AsyncAnthropic SDK client.
    """
    from evercurrent.llm.anthropic import AsyncAnthropicAdapter

    return AsyncAnthropicAdapter(AsyncAnthropic())


def _create_async_openai() -> AsyncLLMClient:
    """Create an async OpenAI adapter.

    Returns:
        AsyncOpenAIAdapter wrapping a new AsyncOpenAI SDK client.

    Raises:
        ImportError: If the openai package is not installed.
    """
    global AsyncOpenAI  # noqa: PLW0603
    if AsyncOpenAI is None:
        from openai import (  # ty: ignore[unresolved-import]
            AsyncOpenAI as _AsyncOpenAI,  # type: ignore[import-untyped]
        )

        AsyncOpenAI = _AsyncOpenAI

    from evercurrent.llm.openai import AsyncOpenAIAdapter

    return AsyncOpenAIAdapter(AsyncOpenAI())


def _create_async_google(model: str | None) -> AsyncLLMClient:
    """Create an async Google Gemini adapter.

    Args:
        model: Gemini model name for GenerativeModel initialization.

    Returns:
        AsyncGoogleAdapter wrapping a new GenerativeModel instance.

    Raises:
        ImportError: If the google-generativeai package is not installed.
    """
    global GenerativeModel  # noqa: PLW0603
    if GenerativeModel is None:
        import google.generativeai as genai  # type: ignore[import-untyped] # ty: ignore[unresolved-import]

        GenerativeModel = genai.GenerativeModel

    from evercurrent.llm.google import AsyncGoogleAdapter

    return AsyncGoogleAdapter(GenerativeModel(model or "gemini-2.0-flash"))

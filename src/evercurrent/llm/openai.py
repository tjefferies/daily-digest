"""OpenAI adapter for the LLM client interface (sync and async).

Wraps the OpenAI SDK client to satisfy the LLMClient protocol,
mapping the Anthropic-style create_message interface to OpenAI's
chat completions API.
"""

from __future__ import annotations

from typing import Any

from evercurrent.llm.types import LLMResponse


class OpenAIAdapter:
    """Adapter wrapping the OpenAI SDK client.

    Translates create_message calls to OpenAI's chat.completions.create
    and extracts text from the response.
    """

    def __init__(self, client: Any) -> None:  # noqa: ANN401
        """Initialize with an OpenAI SDK client.

        Args:
            client: OpenAI SDK client instance.
        """
        self._client = client

    def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",
    ) -> LLMResponse:
        """Send a message via the OpenAI API.

        Maps the system parameter to a system message prepended to
        the messages list, matching OpenAI's chat completion format.

        Args:
            model: OpenAI model identifier (e.g. gpt-4o).
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system prompt, prepended as system message.

        Returns:
            LLMResponse with the extracted text content.

        Raises:
            ValueError: If the response content is empty or None.
        """
        all_messages = list(messages)
        if system:
            all_messages.insert(0, {"role": "system", "content": system})
        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=all_messages,
        )
        text = response.choices[0].message.content
        if text is None:
            msg = "OpenAI returned empty response content"
            raise ValueError(msg)
        return LLMResponse(text=text)


class AsyncOpenAIAdapter:
    """Async adapter wrapping the OpenAI SDK async client.

    Translates async create_message calls to OpenAI's chat completions API.
    """

    def __init__(self, client: Any) -> None:  # noqa: ANN401
        """Initialize with an async OpenAI SDK client.

        Args:
            client: AsyncOpenAI SDK client instance.
        """
        self._client = client

    async def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",
    ) -> LLMResponse:
        """Send a message via the OpenAI API asynchronously.

        Args:
            model: OpenAI model identifier (e.g. gpt-4o).
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system prompt, prepended as system message.

        Returns:
            LLMResponse with the extracted text content.

        Raises:
            ValueError: If the response content is empty or None.
        """
        all_messages = list(messages)
        if system:
            all_messages.insert(0, {"role": "system", "content": system})
        response = await self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=all_messages,
        )
        text = response.choices[0].message.content
        if text is None:
            msg = "OpenAI returned empty response content"
            raise ValueError(msg)
        return LLMResponse(text=text)

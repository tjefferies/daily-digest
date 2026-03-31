"""OpenAI adapter for the LLM client interface (sync and async).

Wraps the OpenAI SDK client to satisfy the LLMClient protocol,
mapping the Anthropic-style create_message interface to OpenAI's
chat completions API. Supports instructor-based structured output.
"""

from __future__ import annotations

from typing import Any, TypeVar

import instructor
from pydantic import BaseModel

from evercurrent.llm.types import LLMResponse

T = TypeVar("T", bound=BaseModel)


class OpenAIAdapter:
    """Adapter wrapping the OpenAI SDK client.

    Translates create_message calls to OpenAI's chat.completions.create
    and extracts text from the response. Also supports structured output
    via instructor for typed Pydantic model responses.
    """

    def __init__(self, client: Any) -> None:  # noqa: ANN401
        """Initialize with an OpenAI SDK client.

        Args:
            client: OpenAI SDK client instance.
        """
        self._client = client
        self._instructor_client: Any = None  # noqa: ANN401

    def _get_instructor_client(self) -> Any:  # noqa: ANN401
        """Lazily initialize and return the instructor-patched client.

        Returns:
            Instructor-patched OpenAI client for structured output.
        """
        if self._instructor_client is None:
            self._instructor_client = instructor.from_openai(self._client)
        return self._instructor_client

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

    def create_structured_message(
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",
        response_model: type[T],
    ) -> T:
        """Send a message and return a typed Pydantic model via instructor.

        Args:
            model: OpenAI model identifier.
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system prompt, prepended as system message.
            response_model: Pydantic model class for structured output.

        Returns:
            Instance of the response_model, validated by instructor.
        """
        all_messages = list(messages)
        if system:
            all_messages.insert(0, {"role": "system", "content": system})
        return self._get_instructor_client().chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=all_messages,
            response_model=response_model,
        )


class AsyncOpenAIAdapter:
    """Async adapter wrapping the OpenAI SDK async client.

    Translates async create_message calls to OpenAI's chat completions API.
    Also supports structured output via instructor.
    """

    def __init__(self, client: Any) -> None:  # noqa: ANN401
        """Initialize with an async OpenAI SDK client.

        Args:
            client: AsyncOpenAI SDK client instance.
        """
        self._client = client
        self._instructor_client: Any = None  # noqa: ANN401

    def _get_instructor_client(self) -> Any:  # noqa: ANN401
        """Lazily initialize and return the instructor-patched async client.

        Returns:
            Instructor-patched async OpenAI client for structured output.
        """
        if self._instructor_client is None:
            self._instructor_client = instructor.from_openai(self._client)
        return self._instructor_client

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

    async def create_structured_message(
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",
        response_model: type[T],
    ) -> T:
        """Send a message and return a typed Pydantic model via instructor.

        Args:
            model: OpenAI model identifier.
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system prompt, prepended as system message.
            response_model: Pydantic model class for structured output.

        Returns:
            Instance of the response_model, validated by instructor.
        """
        all_messages = list(messages)
        if system:
            all_messages.insert(0, {"role": "system", "content": system})
        return await self._get_instructor_client().chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=all_messages,
            response_model=response_model,
        )

"""Anthropic Claude async adapter for the LLM client interface.

Wraps the AsyncAnthropic SDK client to satisfy the AsyncLLMClient
protocol, normalizing TextBlock responses into LLMResponse objects.
Supports instructor-based structured output for typed Pydantic responses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, cast

import instructor
from anthropic.types import MessageParam, TextBlock
from pydantic import BaseModel

from evercurrent.llm.types import LLMResponse

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

T = TypeVar("T", bound=BaseModel)


class AsyncAnthropicAdapter:
    """Async adapter wrapping the Anthropic SDK async client.

    Translates async create_message calls to the Anthropic messages API
    and extracts text content from the response. Also supports structured
    output via instructor for typed Pydantic model responses.
    """

    def __init__(self, client: AsyncAnthropic) -> None:
        """Initialize with an async Anthropic SDK client.

        Args:
            client: AsyncAnthropic SDK client instance.
        """
        self._client = client
        self._instructor_client: Any = None  # noqa: ANN401

    def _get_instructor_client(self) -> Any:  # noqa: ANN401
        """Lazily initialize and return the instructor-patched async client.

        Returns:
            Instructor-patched async Anthropic client for structured output.
        """
        if self._instructor_client is None:
            self._instructor_client = instructor.from_anthropic(self._client)
        return self._instructor_client

    async def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",
    ) -> LLMResponse:
        """Send a message via the Anthropic API asynchronously.

        Args:
            model: Anthropic model identifier (e.g. claude-haiku-4-5).
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system prompt.

        Returns:
            LLMResponse with the extracted text content.

        Raises:
            ValueError: If the response contains a non-text content block.
        """
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=cast("list[MessageParam]", messages),
            system=system,
        )
        block = response.content[0]
        if not isinstance(block, TextBlock):
            msg = f"Anthropic returned non-text content block: {type(block).__name__}"
            raise ValueError(msg)
        return LLMResponse(text=block.text)

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
            model: Anthropic model identifier.
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system prompt.
            response_model: Pydantic model class for structured output.

        Returns:
            Instance of the response_model, validated by instructor.
        """
        return await self._get_instructor_client().messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=cast("list[MessageParam]", messages),
            system=system,
            response_model=response_model,
        )

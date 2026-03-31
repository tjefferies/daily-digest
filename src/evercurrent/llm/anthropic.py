"""Anthropic Claude adapter for the LLM client interface.

Wraps the Anthropic SDK client to satisfy the LLMClient protocol,
normalizing TextBlock responses into LLMResponse objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from anthropic.types import MessageParam, TextBlock

from evercurrent.llm.types import LLMResponse

if TYPE_CHECKING:
    from anthropic import Anthropic


class AnthropicAdapter:
    """Adapter wrapping the Anthropic SDK client.

    Translates create_message calls to the Anthropic messages API and
    extracts text content from the response.
    """

    def __init__(self, client: Anthropic) -> None:
        """Initialize with an Anthropic SDK client.

        Args:
            client: Anthropic SDK client instance.
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
        """Send a message via the Anthropic API.

        Args:
            model: Anthropic model identifier (e.g. claude-sonnet-4-20250514).
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system prompt.

        Returns:
            LLMResponse with the extracted text content.

        Raises:
            ValueError: If the response contains a non-text content block.
        """
        response = self._client.messages.create(
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

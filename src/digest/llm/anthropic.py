"""Anthropic Claude async adapter for the LLM client interface.

Wraps the AsyncAnthropic SDK client. Uses native tool_use for
structured output - no instructor dependency needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from anthropic.types import MessageParam, TextBlock
from pydantic import BaseModel

from digest.llm.types import LLMResponse

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic


def _pydantic_to_tool[T: BaseModel](name: str, model: type[T]) -> dict[str, Any]:  # noqa: ANN401
    """Convert a Pydantic model to an Anthropic tool definition.

    Args:
        name: Tool name for the API call.
        model: Pydantic model whose JSON schema becomes input_schema.

    Returns:
        Tool dict suitable for the Anthropic tools parameter.
    """
    schema = model.model_json_schema()
    return {
        "name": name,
        "description": f"Return structured {name} output.",
        "input_schema": schema,
    }


class AsyncAnthropicAdapter:
    """Async adapter wrapping the Anthropic SDK async client.

    Uses native tool_use for structured output. No instructor dependency.
    """

    def __init__(self, client: AsyncAnthropic) -> None:
        """Initialize with an async Anthropic SDK client.

        Args:
            client: AsyncAnthropic SDK client instance.
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
        """Send a message via the Anthropic API asynchronously.

        Args:
            model: Anthropic model identifier.
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

    async def create_structured_message[T: BaseModel](
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",
        response_model: type[T],
    ) -> T:
        """Send a message and return a typed Pydantic model via tool_use.

        Uses native Anthropic tool_use with tool_choice to force
        structured JSON output matching the Pydantic model schema.

        Args:
            model: Anthropic model identifier.
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content'.
            system: Optional system prompt.
            response_model: Pydantic model class for structured output.

        Returns:
            Instance of the response_model, validated from tool input.
        """
        tool_name = response_model.__name__.lower()
        tool = _pydantic_to_tool(tool_name, response_model)

        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=cast("list[MessageParam]", messages),
            system=system,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
        )

        for block in response.content:
            if block.type == "tool_use":
                return response_model.model_validate(block.input)

        msg = "No tool_use block in response"
        raise ValueError(msg)

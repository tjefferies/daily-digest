"""Tests for the async Anthropic Claude adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from anthropic.types import TextBlock
from pydantic import BaseModel

from digest.llm.anthropic import AsyncAnthropicAdapter


class _TestModel(BaseModel):
    """Pydantic model for structured output tests."""

    name: str
    value: int


class TestAsyncAnthropicAdapter:
    """Tests for the async Anthropic adapter."""

    async def test_returns_llm_response_with_text(self) -> None:
        """Async adapter extracts text from TextBlock response."""
        sdk_client = AsyncMock()
        response = MagicMock()
        response.content = [TextBlock(type="text", text="Hello async")]
        sdk_client.messages.create.return_value = response
        adapter = AsyncAnthropicAdapter(sdk_client)
        result = await adapter.create_message(
            model="claude-haiku-4-5",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result.text == "Hello async"

    async def test_non_text_block_raises_value_error(self) -> None:
        """Async adapter raises ValueError for non-text content blocks."""
        sdk_client = AsyncMock()
        response = MagicMock()
        response.content = [MagicMock(spec=[])]
        sdk_client.messages.create.return_value = response
        adapter = AsyncAnthropicAdapter(sdk_client)
        with pytest.raises(ValueError, match="non-text"):
            await adapter.create_message(
                model="test",
                max_tokens=100,
                messages=[{"role": "user", "content": "hi"}],
            )


class TestAsyncAnthropicAdapterStructuredMessage:
    """Tests for create_structured_message via tool_use."""

    async def test_returns_pydantic_model_from_tool_use(self) -> None:
        """Structured message returns Pydantic model from tool_use block."""
        sdk_client = AsyncMock()
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.input = {"name": "test", "value": 42}
        response = MagicMock()
        response.content = [tool_block]
        sdk_client.messages.create.return_value = response

        adapter = AsyncAnthropicAdapter(sdk_client)
        result = await adapter.create_structured_message(
            model="claude-haiku-4-5",
            max_tokens=100,
            messages=[{"role": "user", "content": "extract"}],
            response_model=_TestModel,
        )
        assert isinstance(result, _TestModel)
        assert result.name == "test"
        assert result.value == 42

    async def test_raises_if_no_tool_use_block(self) -> None:
        """Raises ValueError when response has no tool_use block."""
        sdk_client = AsyncMock()
        text_block = TextBlock(type="text", text="no tool")
        response = MagicMock()
        response.content = [text_block]
        sdk_client.messages.create.return_value = response

        adapter = AsyncAnthropicAdapter(sdk_client)
        with pytest.raises(ValueError, match="No tool_use"):
            await adapter.create_structured_message(
                model="test",
                max_tokens=100,
                messages=[{"role": "user", "content": "extract"}],
                response_model=_TestModel,
            )

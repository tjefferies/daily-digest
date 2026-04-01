"""Tests for the async Anthropic Claude adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import TextBlock
from pydantic import BaseModel

from evercurrent.llm.anthropic import AsyncAnthropicAdapter


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

    async def test_passes_all_params_to_sdk(self) -> None:
        """Async adapter forwards all parameters to the SDK."""
        sdk_client = AsyncMock()
        response = MagicMock()
        response.content = [TextBlock(type="text", text="ok")]
        sdk_client.messages.create.return_value = response
        adapter = AsyncAnthropicAdapter(sdk_client)
        await adapter.create_message(
            model="claude-haiku-4-5",
            max_tokens=4096,
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful.",
        )
        sdk_client.messages.create.assert_called_once()

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
    """Tests for async create_structured_message method."""

    @patch("evercurrent.llm.anthropic.instructor")
    async def test_returns_pydantic_model(self, mock_instructor: MagicMock) -> None:
        """Async structured message returns instructor-generated Pydantic model."""
        sdk_client = AsyncMock()
        expected = _TestModel(name="async", value=99)
        mock_patched = AsyncMock()
        mock_patched.messages.create.return_value = expected
        mock_instructor.from_anthropic.return_value = mock_patched

        adapter = AsyncAnthropicAdapter(sdk_client)
        result = await adapter.create_structured_message(
            model="claude-haiku-4-5",
            max_tokens=100,
            messages=[{"role": "user", "content": "extract"}],
            response_model=_TestModel,
        )
        assert isinstance(result, _TestModel)
        assert result.name == "async"

"""Tests for the Anthropic LLM adapter (sync and async)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from anthropic.types import TextBlock

from evercurrent.llm.anthropic import AnthropicAdapter, AsyncAnthropicAdapter


class TestAnthropicAdapterInit:
    """Tests for AnthropicAdapter initialization."""

    def test_creates_with_client(self) -> None:
        """Adapter wraps an Anthropic SDK client."""
        sdk_client = MagicMock()
        adapter = AnthropicAdapter(sdk_client)
        assert adapter is not None


class TestAnthropicAdapterCreateMessage:
    """Tests for create_message method."""

    def test_returns_llm_response_with_text(self) -> None:
        """Adapter extracts text from TextBlock response."""
        sdk_client = MagicMock()
        response = MagicMock()
        response.content = [TextBlock(type="text", text="Hello")]
        sdk_client.messages.create.return_value = response
        adapter = AnthropicAdapter(sdk_client)
        result = adapter.create_message(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result.text == "Hello"

    def test_passes_all_params_to_sdk(self) -> None:
        """Adapter forwards model, max_tokens, system, messages to SDK."""
        sdk_client = MagicMock()
        response = MagicMock()
        response.content = [TextBlock(type="text", text="ok")]
        sdk_client.messages.create.return_value = response
        adapter = AnthropicAdapter(sdk_client)
        adapter.create_message(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful.",
        )
        sdk_client.messages.create.assert_called_once_with(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful.",
        )

    def test_passes_empty_system_when_omitted(self) -> None:
        """Adapter passes empty system string when not provided."""
        sdk_client = MagicMock()
        response = MagicMock()
        response.content = [TextBlock(type="text", text="ok")]
        sdk_client.messages.create.return_value = response
        adapter = AnthropicAdapter(sdk_client)
        adapter.create_message(
            model="test",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
        )
        call_kwargs = sdk_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == ""

    def test_non_text_block_raises_value_error(self) -> None:
        """Adapter raises ValueError when response has no TextBlock."""
        sdk_client = MagicMock()
        response = MagicMock()
        response.content = [MagicMock(spec=[])]
        sdk_client.messages.create.return_value = response
        adapter = AnthropicAdapter(sdk_client)
        with pytest.raises(ValueError, match="non-text"):
            adapter.create_message(
                model="test",
                max_tokens=100,
                messages=[{"role": "user", "content": "hi"}],
            )

    def test_extracts_json_content(self) -> None:
        """Adapter correctly passes through JSON content."""
        sdk_client = MagicMock()
        json_text = json.dumps([{"type": "DECISION", "summary": "test"}])
        response = MagicMock()
        response.content = [TextBlock(type="text", text=json_text)]
        sdk_client.messages.create.return_value = response
        adapter = AnthropicAdapter(sdk_client)
        result = adapter.create_message(
            model="test",
            max_tokens=100,
            messages=[{"role": "user", "content": "extract"}],
        )
        assert json.loads(result.text) == [{"type": "DECISION", "summary": "test"}]


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
            model="claude-sonnet-4-20250514",
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
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful.",
        )
        sdk_client.messages.create.assert_called_once_with(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful.",
        )

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

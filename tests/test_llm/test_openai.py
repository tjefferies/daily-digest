"""Tests for the OpenAI LLM adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from evercurrent.llm.openai import OpenAIAdapter


class TestOpenAIAdapterInit:
    """Tests for OpenAIAdapter initialization."""

    def test_creates_with_client(self) -> None:
        """Adapter wraps an OpenAI SDK client."""
        sdk_client = MagicMock()
        adapter = OpenAIAdapter(sdk_client)
        assert adapter is not None


class TestOpenAIAdapterCreateMessage:
    """Tests for create_message method."""

    def test_returns_llm_response_with_text(self) -> None:
        """Adapter extracts text from OpenAI chat completion response."""
        sdk_client = MagicMock()
        message = MagicMock()
        message.content = "Hello from GPT"
        choice = MagicMock()
        choice.message = message
        sdk_client.chat.completions.create.return_value = MagicMock(choices=[choice])
        adapter = OpenAIAdapter(sdk_client)
        result = adapter.create_message(
            model="gpt-4o",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result.text == "Hello from GPT"

    def test_maps_system_to_system_message(self) -> None:
        """Adapter prepends system param as system message in messages list."""
        sdk_client = MagicMock()
        message = MagicMock()
        message.content = "ok"
        choice = MagicMock()
        choice.message = message
        sdk_client.chat.completions.create.return_value = MagicMock(choices=[choice])
        adapter = OpenAIAdapter(sdk_client)
        adapter.create_message(
            model="gpt-4o",
            max_tokens=100,
            messages=[{"role": "user", "content": "test"}],
            system="Be helpful.",
        )
        call_kwargs = sdk_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["messages"][0] == {"role": "system", "content": "Be helpful."}
        assert call_kwargs["messages"][1] == {"role": "user", "content": "test"}

    def test_no_system_message_when_empty(self) -> None:
        """Adapter does not prepend system message when system is empty."""
        sdk_client = MagicMock()
        message = MagicMock()
        message.content = "ok"
        choice = MagicMock()
        choice.message = message
        sdk_client.chat.completions.create.return_value = MagicMock(choices=[choice])
        adapter = OpenAIAdapter(sdk_client)
        adapter.create_message(
            model="gpt-4o",
            max_tokens=100,
            messages=[{"role": "user", "content": "test"}],
        )
        call_kwargs = sdk_client.chat.completions.create.call_args.kwargs
        assert len(call_kwargs["messages"]) == 1

    def test_null_content_raises_value_error(self) -> None:
        """Adapter raises ValueError when response content is None."""
        sdk_client = MagicMock()
        message = MagicMock()
        message.content = None
        choice = MagicMock()
        choice.message = message
        sdk_client.chat.completions.create.return_value = MagicMock(choices=[choice])
        adapter = OpenAIAdapter(sdk_client)
        with pytest.raises(ValueError, match="empty"):
            adapter.create_message(
                model="gpt-4o",
                max_tokens=100,
                messages=[{"role": "user", "content": "hi"}],
            )

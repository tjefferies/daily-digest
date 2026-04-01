"""Tests for the Google Gemini LLM adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from evercurrent.llm.google import GoogleAdapter


class TestGoogleAdapterInit:
    """Tests for GoogleAdapter initialization."""

    def test_creates_with_client(self) -> None:
        """Adapter wraps a Google GenerativeModel client."""
        sdk_client = MagicMock()
        adapter = GoogleAdapter(sdk_client)
        assert adapter is not None


class TestGoogleAdapterCreateMessage:
    """Tests for create_message method."""

    def test_returns_llm_response_with_text(self) -> None:
        """Adapter extracts text from Gemini response."""
        sdk_client = MagicMock()
        sdk_client.generate_content.return_value = MagicMock(text="Hello from Gemini")
        adapter = GoogleAdapter(sdk_client)
        result = adapter.create_message(
            model="gemini-2.0-flash",
            max_tokens=100,
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result.text == "Hello from Gemini"

    def test_passes_system_as_system_instruction(self) -> None:
        """Adapter passes system instruction to generate_content config."""
        sdk_client = MagicMock()
        sdk_client.generate_content.return_value = MagicMock(text="ok")
        adapter = GoogleAdapter(sdk_client)
        adapter.create_message(
            model="gemini-2.0-flash",
            max_tokens=100,
            messages=[{"role": "user", "content": "test"}],
            system="Be helpful.",
        )
        call_kwargs = sdk_client.generate_content.call_args
        config = call_kwargs.kwargs.get("generation_config", {})
        assert config.get("max_output_tokens") == 100

    def test_builds_content_from_messages(self) -> None:
        """Adapter converts messages list to Gemini content format."""
        sdk_client = MagicMock()
        sdk_client.generate_content.return_value = MagicMock(text="ok")
        adapter = GoogleAdapter(sdk_client)
        adapter.create_message(
            model="gemini-2.0-flash",
            max_tokens=100,
            messages=[{"role": "user", "content": "hello"}],
        )
        sdk_client.generate_content.assert_called_once()

    def test_none_text_raises_value_error(self) -> None:
        """Adapter raises ValueError when response text is None."""
        sdk_client = MagicMock()
        sdk_client.generate_content.return_value = MagicMock(text=None)
        adapter = GoogleAdapter(sdk_client)
        with pytest.raises(ValueError, match="empty"):
            adapter.create_message(
                model="gemini-2.0-flash",
                max_tokens=100,
                messages=[{"role": "user", "content": "hi"}],
            )

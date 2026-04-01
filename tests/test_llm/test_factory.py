"""Tests for the LLM client factory (sync and async)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from evercurrent.llm.factory import create_async_llm_client, create_llm_client


class TestCreateLLMClient:
    """Tests for the create_llm_client factory function."""

    @patch("evercurrent.llm.factory.Anthropic")
    def test_creates_anthropic_adapter(self, mock_anthropic_cls: MagicMock) -> None:
        """Factory creates AnthropicAdapter for 'anthropic' provider."""
        from evercurrent.llm.anthropic import AnthropicAdapter

        client = create_llm_client(provider="anthropic")
        assert isinstance(client, AnthropicAdapter)
        mock_anthropic_cls.assert_called_once()

    @patch("evercurrent.llm.factory.Anthropic")
    def test_anthropic_is_default(self, _mock_anthropic_cls: MagicMock) -> None:
        """Factory defaults to Anthropic when no provider specified."""
        from evercurrent.llm.anthropic import AnthropicAdapter

        client = create_llm_client()
        assert isinstance(client, AnthropicAdapter)

    def test_unknown_provider_raises(self) -> None:
        """Factory raises ValueError for unknown provider string."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm_client(provider="unknown-provider")

    def test_openai_provider(self) -> None:
        """Factory creates OpenAIAdapter for 'openai' provider."""
        from evercurrent.llm.openai import OpenAIAdapter

        with patch("evercurrent.llm.factory.OpenAI") as mock_cls:
            client = create_llm_client(provider="openai")
            assert isinstance(client, OpenAIAdapter)
            mock_cls.assert_called_once()

    def test_google_provider(self) -> None:
        """Factory creates GoogleAdapter for 'google' provider."""
        from evercurrent.llm.google import GoogleAdapter

        with patch("evercurrent.llm.factory.GenerativeModel") as mock_cls:
            client = create_llm_client(provider="google", model="gemini-2.0-flash")
            assert isinstance(client, GoogleAdapter)
            mock_cls.assert_called_once_with("gemini-2.0-flash")


class TestCreateAsyncLLMClient:
    """Tests for the create_async_llm_client factory function."""

    @patch("evercurrent.llm.factory.AsyncAnthropic")
    def test_creates_async_anthropic_adapter(self, mock_anthropic_cls: MagicMock) -> None:
        """Async factory creates AsyncAnthropicAdapter for 'anthropic'."""
        from evercurrent.llm.anthropic import AsyncAnthropicAdapter

        client = create_async_llm_client(provider="anthropic")
        assert isinstance(client, AsyncAnthropicAdapter)
        mock_anthropic_cls.assert_called_once()

    @patch("evercurrent.llm.factory.AsyncAnthropic")
    def test_async_anthropic_is_default(self, _mock: MagicMock) -> None:
        """Async factory defaults to Anthropic."""
        from evercurrent.llm.anthropic import AsyncAnthropicAdapter

        client = create_async_llm_client()
        assert isinstance(client, AsyncAnthropicAdapter)

    def test_unknown_provider_raises(self) -> None:
        """Async factory raises ValueError for unknown provider."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_async_llm_client(provider="unknown-provider")

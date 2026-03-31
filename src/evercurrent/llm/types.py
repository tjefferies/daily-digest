"""LLM client protocol and response types.

Defines the provider-agnostic interface that all LLM adapters must
satisfy, plus the normalized response type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMResponse:
    """Normalized response from any LLM provider.

    Attributes:
        text: The extracted text content from the LLM response.
    """

    text: str


class LLMClient(Protocol):
    """Protocol defining the model-agnostic LLM client interface.

    Any class implementing create_message with this signature can be
    used as an LLM client throughout the pipeline.
    """

    def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",
    ) -> LLMResponse:
        """Send a message to the LLM and return a normalized response.

        Args:
            model: Model identifier string.
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content' keys.
            system: Optional system prompt.

        Returns:
            LLMResponse containing the extracted text.
        """
        ...


class AsyncLLMClient(Protocol):
    """Protocol defining the async model-agnostic LLM client interface.

    Any class implementing an async create_message with this signature
    can be used as an async LLM client for concurrent pipeline execution.
    """

    async def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict[str, str]],
        system: str = "",
    ) -> LLMResponse:
        """Send a message to the LLM and return a normalized response.

        Args:
            model: Model identifier string.
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content' keys.
            system: Optional system prompt.

        Returns:
            LLMResponse containing the extracted text.
        """
        ...

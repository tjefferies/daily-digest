"""LLM client protocol and response types.

Defines the provider-agnostic interface that all LLM adapters must
satisfy, plus the normalized response type. Includes structured output
support via instructor for typed Pydantic model responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class LLMResponse:
    """Normalized response from any LLM provider.

    Attributes:
        text: The extracted text content from the LLM response.
    """

    text: str


class LLMClient(Protocol):
    """Protocol defining the model-agnostic LLM client interface.

    Any class implementing create_message and create_structured_message
    can be used as an LLM client throughout the pipeline.
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

    def create_structured_message(
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
            model: Model identifier string.
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content' keys.
            system: Optional system prompt.
            response_model: Pydantic model class for structured output.

        Returns:
            Instance of the response_model, validated by instructor.
        """
        ...


class AsyncLLMClient(Protocol):
    """Protocol defining the async model-agnostic LLM client interface.

    Any class implementing async create_message and create_structured_message
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
            model: Model identifier string.
            max_tokens: Maximum tokens in the response.
            messages: List of message dicts with 'role' and 'content' keys.
            system: Optional system prompt.
            response_model: Pydantic model class for structured output.

        Returns:
            Instance of the response_model, validated by instructor.
        """
        ...

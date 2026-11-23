"""Abstract base class for all LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when an LLM provider returns an error or times out."""

    def __init__(self, provider: str, message: str, status_code: int | None = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class LLMProvider(ABC):
    """Common interface every provider implementation must satisfy."""

    #: Short identifier used in logs and draft metadata (never expose keys here).
    name: str
    #: Model identifier string returned in draft metadata.
    model: str

    @abstractmethod
    async def generate(self, prompt: str, system: str = "") -> str:
        """Generate a completion for the given user prompt.

        Args:
            prompt: The user-facing prompt text.
            system: Optional system instruction injected before the prompt.

        Returns:
            The model's text response.

        Raises:
            ProviderError: On HTTP errors, timeouts, or empty responses.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable and responding."""

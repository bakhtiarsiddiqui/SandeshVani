"""Provider factory — builds the primary + fallback chain at startup.

Provider selection order (configurable via AI_PROVIDER env var):
  1. groq  — primary free-tier (requires GROQ_API_KEY)
  2. gemini — fallback free-tier (requires GEMINI_API_KEY)
  3. ollama — local dev / air-gapped (no key)

The factory never hard-codes keys; they come from the validated AISettings.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai.providers.base import LLMProvider, ProviderError

if TYPE_CHECKING:
    from ai.config import AISettings

logger = logging.getLogger(__name__)


class FallbackProvider(LLMProvider):
    """Wraps a primary provider with a single fallback.

    If the primary raises ProviderError the call is retried once on the
    fallback.  Any other exception propagates immediately.
    """

    name = "fallback-chain"

    def __init__(
        self, primary: LLMProvider, fallback: LLMProvider | None = None
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self.model = primary.model

    async def generate(self, prompt: str, system: str = "") -> str:
        try:
            result = await self._primary.generate(prompt, system)
            self.name = self._primary.name
            self.model = self._primary.model
            return result
        except ProviderError as primary_err:
            if self._fallback is None:
                raise
            logger.warning(
                "Primary provider '%s' failed (%s); trying fallback '%s'",
                self._primary.name,
                primary_err,
                self._fallback.name,
            )
            result = await self._fallback.generate(prompt, system)
            self.name = self._fallback.name
            self.model = self._fallback.model
            return result

    async def health_check(self) -> bool:
        if await self._primary.health_check():
            return True
        if self._fallback:
            return await self._fallback.health_check()
        return False


def build_provider(settings: AISettings) -> LLMProvider:  # type: ignore[name-defined]
    """Construct the provider chain from validated settings.

    Import is deferred to avoid circular imports at module load time.
    """
    from ai.config import AISettings  # noqa: PLC0415

    assert isinstance(settings, AISettings)

    primary_name = settings.ai_provider.lower()

    if primary_name == "groq":
        from ai.providers.groq_provider import GroqProvider  # noqa: PLC0415

        primary: LLMProvider = GroqProvider(settings.groq_api_key)
        if settings.gemini_api_key:
            from ai.providers.gemini_provider import GeminiProvider  # noqa: PLC0415

            fallback: LLMProvider | None = GeminiProvider(settings.gemini_api_key)
        elif settings.ollama_host:
            from ai.providers.ollama_provider import OllamaProvider  # noqa: PLC0415

            fallback = OllamaProvider(
                host=settings.ollama_host, model=settings.ollama_model
            )
        else:
            fallback = None

    elif primary_name == "gemini":
        from ai.providers.gemini_provider import GeminiProvider  # noqa: PLC0415

        primary = GeminiProvider(settings.gemini_api_key)
        if settings.ollama_host:
            from ai.providers.ollama_provider import OllamaProvider  # noqa: PLC0415

            fallback = OllamaProvider(
                host=settings.ollama_host, model=settings.ollama_model
            )
        else:
            fallback = None

    elif primary_name == "ollama":
        from ai.providers.ollama_provider import OllamaProvider  # noqa: PLC0415

        primary = OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)
        fallback = None

    else:
        raise ValueError(
            f"Unknown AI_PROVIDER '{primary_name}'. Choose from: groq, gemini, ollama"
        )

    return FallbackProvider(primary=primary, fallback=fallback)

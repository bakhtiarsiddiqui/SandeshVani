"""AI Campaign Assistant configuration.

All values come from environment variables (via Pydantic Settings).
The module performs fail-fast validation at import time when the app starts.
No API keys are ever hard-coded here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """Settings for the AI Campaign Assistant module.

    Loaded from the same .env file as the main app settings.
    Extra fields from the main app are silently ignored.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Provider selection
    # ------------------------------------------------------------------
    ai_provider: Literal["groq", "gemini", "ollama"] = Field(
        default="groq",
        description="Primary LLM provider. Groq → Gemini fallback by default.",
    )

    # ------------------------------------------------------------------
    # API keys — read from env, never hard-coded
    # ------------------------------------------------------------------
    groq_api_key: str = Field(
        default="",
        description="Groq API key (required when AI_PROVIDER=groq or as fallback).",
    )
    gemini_api_key: str = Field(
        default="",
        description="Gemini API key (required when AI_PROVIDER=gemini or as fallback).",
    )

    # ------------------------------------------------------------------
    # Ollama local settings (no key required)
    # ------------------------------------------------------------------
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Base URL for the Ollama server.",
    )
    ollama_model: str = Field(
        default="qwen2.5:7b",
        description="Model tag to use with Ollama.",
    )

    # ------------------------------------------------------------------
    # Service-to-service API key guard
    # ------------------------------------------------------------------
    ai_service_api_key: str = Field(
        default="",
        description=(
            "Secret key required in X-API-Key header for every AI endpoint. "
            "Must be set before the server starts."
        ),
    )

    # ------------------------------------------------------------------
    # Fail-fast validation
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def validate_provider_credentials(self) -> AISettings:
        if self.ai_provider == "groq" and not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY must be set when AI_PROVIDER=groq. "
                "Get a free key at https://console.groq.com"
            )
        if self.ai_provider == "gemini" and not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY must be set when AI_PROVIDER=gemini. "
                "Get a free key at https://aistudio.google.com"
            )
        if not self.ai_service_api_key:
            raise ValueError(
                "AI_SERVICE_API_KEY must be set. "
                "This key guards the AI endpoints from unauthenticated access."
            )
        return self


@lru_cache
def get_ai_settings() -> AISettings:
    """Return the cached AI settings instance."""
    return AISettings()

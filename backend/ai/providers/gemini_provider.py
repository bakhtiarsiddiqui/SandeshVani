"""Gemini (free tier) provider — fallback LLM backend.

Uses the Gemini generateContent REST API via plain httpx.
API key is read from GEMINI_API_KEY environment variable at runtime.
"""

from __future__ import annotations

import httpx

from ai.providers.base import LLMProvider, ProviderError

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_MODEL = "gemini-2.0-flash"
_TIMEOUT = 30.0


class GeminiProvider(LLMProvider):
    name = "gemini"
    model = _MODEL

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY must not be empty")
        self._api_key = api_key

    async def generate(self, prompt: str, system: str = "") -> str:
        full_prompt = f"{system}\n\n{prompt}".strip() if system else prompt
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"maxOutputTokens": 512, "temperature": 0.7},
        }

        url = f"{_BASE_URL}/{self.model}:generateContent?key={self._api_key}"

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                response = await client.post(url, json=payload)
            except httpx.TimeoutException as exc:
                raise ProviderError(self.name, "Request timed out", None) from exc
            except httpx.RequestError as exc:
                raise ProviderError(self.name, f"Network error: {exc}", None) from exc

        if response.status_code != 200:
            raise ProviderError(
                self.name,
                f"API returned HTTP {response.status_code}: {response.text[:200]}",
                response.status_code,
            )

        data = response.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as exc:
            raise ProviderError(
                self.name, f"Unexpected response shape: {data}"
            ) from exc

        if not text:
            raise ProviderError(self.name, "Empty response from model")

        return text

    async def health_check(self) -> bool:
        try:
            url = f"{_BASE_URL}?key={self._api_key}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(url)
            return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False

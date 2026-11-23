"""Groq (Qwen) provider — primary LLM backend.

Calls the Groq Chat Completions API using plain httpx (no Groq SDK).
API key is read from GROQ_API_KEY environment variable at runtime.
"""

from __future__ import annotations

import httpx

from ai.providers.base import LLMProvider, ProviderError

_BASE_URL = "https://api.groq.com/openai/v1"
_TIMEOUT = 30.0  # seconds


class GroqProvider(LLMProvider):
    name = "groq"
    model = "qwen-qwq-32b"  # free-tier Qwen model on Groq

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("GROQ_API_KEY must not be empty")
        self._api_key = api_key

    async def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.7,
        }

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                response = await client.post(
                    f"{_BASE_URL}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
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
            text = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise ProviderError(
                self.name, f"Unexpected response shape: {data}"
            ) from exc

        if not text:
            raise ProviderError(self.name, "Empty response from model")

        return text

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{_BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
            return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False

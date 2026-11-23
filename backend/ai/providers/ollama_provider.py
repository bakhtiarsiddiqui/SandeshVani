"""Ollama local provider — development / air-gapped fallback.

Calls the Ollama REST API (http://localhost:11434 by default).
No API key required. Model defaults to qwen2.5:7b.
"""

from __future__ import annotations

import httpx

from ai.providers.base import LLMProvider, ProviderError

_DEFAULT_HOST = "http://localhost:11434"
_DEFAULT_MODEL = "qwen2.5:7b"
_TIMEOUT = 60.0  # Ollama may be slower on CPU


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        host: str = _DEFAULT_HOST,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self._host = host.rstrip("/")
        self.model = model

    async def generate(self, prompt: str, system: str = "") -> str:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                response = await client.post(f"{self._host}/api/generate", json=payload)
            except httpx.TimeoutException as exc:
                raise ProviderError(
                    self.name, "Ollama request timed out", None
                ) from exc
            except httpx.RequestError as exc:
                raise ProviderError(
                    self.name, f"Cannot reach Ollama: {exc}", None
                ) from exc

        if response.status_code != 200:
            raise ProviderError(
                self.name,
                f"Ollama returned HTTP {response.status_code}: {response.text[:200]}",
                response.status_code,
            )

        data = response.json()
        text = data.get("response", "").strip()
        if not text:
            raise ProviderError(self.name, "Empty response from Ollama")
        return text

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self._host}/")
            return r.status_code == 200
        except Exception:  # noqa: BLE001
            return False

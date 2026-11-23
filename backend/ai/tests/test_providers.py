"""Tests for provider layer — all offline using FakeProvider."""

from __future__ import annotations

import pytest

from ai.providers.base import LLMProvider, ProviderError
from ai.providers.factory import FallbackProvider

# ---------------------------------------------------------------------------
# FakeProvider (from conftest) — verify the contract
# ---------------------------------------------------------------------------


class TestFakeProvider:
    async def test_generate_returns_string(self, fake_provider):
        result = await fake_provider.generate("hello")
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_health_check_true(self, fake_provider):
        assert await fake_provider.health_check() is True


# ---------------------------------------------------------------------------
# FallbackProvider
# ---------------------------------------------------------------------------


class FailingProvider(LLMProvider):
    name = "failing"
    model = "none"

    async def generate(self, prompt: str, system: str = "") -> str:
        raise ProviderError("failing", "Always fails", 500)

    async def health_check(self) -> bool:
        return False


class TestFallbackProvider:
    async def test_uses_primary_when_ok(self, fake_provider):
        fp = FallbackProvider(primary=fake_provider, fallback=None)
        result = await fp.generate("test")
        assert isinstance(result, str)

    async def test_falls_back_on_provider_error(self, fake_provider):
        fp = FallbackProvider(primary=FailingProvider(), fallback=fake_provider)
        result = await fp.generate("test")
        assert isinstance(result, str)
        # After fallback, name and model are updated to fallback provider
        assert fp.name == "fake"

    async def test_raises_when_both_fail(self):
        fp = FallbackProvider(primary=FailingProvider(), fallback=FailingProvider())
        with pytest.raises(ProviderError):
            await fp.generate("test")

    async def test_raises_when_no_fallback(self):
        fp = FallbackProvider(primary=FailingProvider(), fallback=None)
        with pytest.raises(ProviderError):
            await fp.generate("test")

    async def test_health_check_primary_ok(self, fake_provider):
        fp = FallbackProvider(primary=fake_provider, fallback=FailingProvider())
        assert await fp.health_check() is True

    async def test_health_check_uses_fallback_when_primary_down(self, fake_provider):
        fp = FallbackProvider(primary=FailingProvider(), fallback=fake_provider)
        assert await fp.health_check() is True

    async def test_health_check_false_when_all_down(self):
        fp = FallbackProvider(primary=FailingProvider(), fallback=FailingProvider())
        assert await fp.health_check() is False

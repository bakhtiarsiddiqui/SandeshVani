"""Shared fixtures for AI module tests.

All tests are designed to run fully offline with a FakeProvider — no API keys needed.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Ensure AI models are registered with Base.metadata
import ai.models  # noqa: F401
from ai.schemas import CampaignBrief, GeneratedDraft, KeyFacts
from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Canonical test brief fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_key_facts() -> KeyFacts:
    return KeyFacts(
        event="Community Health Fair",
        date="2026-12-15",
        venue="Gandhi Maidan, Patna",
        cost="Free",
        contact="1800-XXX-YYYY",
    )


@pytest.fixture()
def sample_brief(sample_key_facts: KeyFacts) -> CampaignBrief:
    return CampaignBrief(
        channel="sms",
        language="hi",
        tone="professional",
        key_facts=sample_key_facts,
    )


@pytest.fixture()
def sample_draft(sample_brief: CampaignBrief) -> GeneratedDraft:
    """A valid draft that satisfies all validators."""
    text = (
        "Community Health Fair, Gandhi Maidan, Patna, 2026-12-15, Free. "
        "Contact: 1800-XXX-YYYY"
    )
    return GeneratedDraft.build(
        language=sample_brief.language,
        channel=sample_brief.channel,
        text=text,
        provider="fake",
        model="fake-model",
    )


class FakeProvider:
    """Offline stand-in that returns deterministic drafts without any HTTP calls."""

    name = "fake"
    model = "fake-model"

    async def generate(self, prompt: str, system: str = "") -> str:  # noqa: ARG002
        # Return a stub that includes the key facts placeholders
        return (
            "Community Health Fair, Gandhi Maidan, Patna, 2026-12-15, Free. "
            "Contact: 1800-XXX-YYYY"
        )

    async def health_check(self) -> bool:
        return True


@pytest.fixture()
def fake_provider() -> FakeProvider:
    return FakeProvider()

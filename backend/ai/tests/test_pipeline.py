"""Tests for the LangGraph pipeline — fully offline with FakeProvider."""

from __future__ import annotations

import uuid

from ai.pipeline import run_pipeline
from ai.schemas import CampaignBrief

# ---------------------------------------------------------------------------
# Minimal async db_writer stubs
# ---------------------------------------------------------------------------


async def _noop_writer(request_id, brief, draft, warnings):
    """Accepts writes without doing anything."""


async def _failing_writer(request_id, brief, draft, warnings):
    raise RuntimeError("DB unavailable")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunPipeline:
    async def test_happy_path_returns_draft(self, fake_provider, sample_brief):
        state = await run_pipeline(
            brief=sample_brief,
            provider=fake_provider,
            db_writer=_noop_writer,
        )
        assert state.get("draft") is not None
        assert state["draft"].text
        assert state["persisted"] is True
        assert state["error"] is None

    async def test_request_id_propagated(self, fake_provider, sample_brief):
        req_id = uuid.uuid4()
        state = await run_pipeline(
            brief=sample_brief,
            provider=fake_provider,
            db_writer=_noop_writer,
            request_id=req_id,
        )
        assert state["request_id"] == req_id

    async def test_auto_generates_request_id(self, fake_provider, sample_brief):
        state = await run_pipeline(
            brief=sample_brief,
            provider=fake_provider,
            db_writer=_noop_writer,
        )
        assert isinstance(state["request_id"], uuid.UUID)

    async def test_validation_warnings_captured(self, fake_provider, sample_brief):
        """Warnings list is always present (may be empty)."""
        state = await run_pipeline(
            brief=sample_brief,
            provider=fake_provider,
            db_writer=_noop_writer,
        )
        assert isinstance(state.get("validation_warnings"), list)

    async def test_persist_failure_recorded(self, fake_provider, sample_brief):
        state = await run_pipeline(
            brief=sample_brief,
            provider=fake_provider,
            db_writer=_failing_writer,
        )
        assert state["persisted"] is False
        assert state["error"] is not None

    async def test_provider_name_in_draft(self, fake_provider, sample_brief):
        state = await run_pipeline(
            brief=sample_brief,
            provider=fake_provider,
            db_writer=_noop_writer,
        )
        assert state["draft"].provider == "fake"

    async def test_different_channels(self, fake_provider, sample_key_facts):
        for channel in ("sms", "whatsapp", "email", "push"):
            brief = CampaignBrief(
                channel=channel, language="hi", key_facts=sample_key_facts
            )
            state = await run_pipeline(
                brief=brief, provider=fake_provider, db_writer=_noop_writer
            )
            assert state["draft"].channel == channel

    async def test_english_brief(self, fake_provider, sample_key_facts):
        brief = CampaignBrief(
            channel="email", language="en", key_facts=sample_key_facts
        )
        state = await run_pipeline(
            brief=brief, provider=fake_provider, db_writer=_noop_writer
        )
        assert state["draft"].language == "en"

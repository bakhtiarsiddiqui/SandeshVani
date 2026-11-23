"""Tests for CampaignBrief and related input schemas."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from ai.schemas import CHANNEL_LIMITS, CampaignBrief, GeneratedDraft, KeyFacts


class TestKeyFacts:
    def test_valid(self):
        kf = KeyFacts(
            event="Fair", date="2026-12-15", venue="Patna", cost="Free", contact="1800"
        )
        assert kf.event == "Fair"

    def test_empty_event_rejected(self):
        with pytest.raises(ValidationError):
            KeyFacts(
                event="", date="2026-12-15", venue="Patna", cost="Free", contact="1800"
            )

    def test_long_event_rejected(self):
        with pytest.raises(ValidationError):
            KeyFacts(
                event="x" * 201,
                date="2026-12-15",
                venue="Patna",
                cost="Free",
                contact="1800",
            )


class TestCampaignBrief:
    def test_valid_hindi_sms(self, sample_brief):
        assert sample_brief.channel == "sms"
        assert sample_brief.language == "hi"

    def test_unsupported_language_rejected(self, sample_key_facts):
        with pytest.raises(ValidationError, match="Unsupported language"):
            CampaignBrief(channel="sms", language="xx", key_facts=sample_key_facts)

    def test_unsupported_channel_rejected(self, sample_key_facts):
        with pytest.raises(ValidationError):
            CampaignBrief(channel="fax", language="hi", key_facts=sample_key_facts)

    def test_all_supported_languages(self, sample_key_facts):
        for lang in ("hi", "en", "mr", "pa", "ta", "te", "bn", "gu", "kn"):
            brief = CampaignBrief(
                channel="email", language=lang, key_facts=sample_key_facts
            )
            assert brief.language == lang

    def test_organization_id_optional(self, sample_key_facts):
        brief = CampaignBrief(channel="push", language="en", key_facts=sample_key_facts)
        assert brief.organization_id is None

    def test_organization_id_accepted(self, sample_key_facts):
        org_id = uuid.uuid4()
        brief = CampaignBrief(
            channel="push",
            language="en",
            key_facts=sample_key_facts,
            organization_id=org_id,
        )
        assert brief.organization_id == org_id

    def test_default_tone(self, sample_key_facts):
        brief = CampaignBrief(channel="sms", language="hi", key_facts=sample_key_facts)
        assert brief.tone == "professional"


class TestGeneratedDraft:
    def test_within_limit_true_for_short_sms(self):
        draft = GeneratedDraft.build(
            language="hi", channel="sms", text="Hello", provider="fake", model="x"
        )
        assert draft.within_limit is True
        assert draft.char_count == 5

    def test_within_limit_false_for_oversized_sms(self):
        long_text = "x" * 161
        draft = GeneratedDraft.build(
            language="hi", channel="sms", text=long_text, provider="fake", model="x"
        )
        assert draft.within_limit is False
        assert draft.char_count == 161

    def test_channel_limits_map(self):
        assert CHANNEL_LIMITS["sms"] == 160
        assert CHANNEL_LIMITS["whatsapp"] == 1024
        assert CHANNEL_LIMITS["push"] == 256
        assert CHANNEL_LIMITS["email"] == 10_000

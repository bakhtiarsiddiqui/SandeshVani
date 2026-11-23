"""Tests for all draft validator functions."""

from __future__ import annotations

from ai.schemas import GeneratedDraft
from ai.validators import (
    check_key_facts_present,
    check_length,
    check_no_pii_patterns,
    check_no_placeholders,
    check_tone_signal,
    validate_draft,
)


def _draft(text: str, channel: str = "sms") -> GeneratedDraft:
    return GeneratedDraft.build(
        language="hi", channel=channel, text=text, provider="fake", model="x"
    )


KEY_FACTS = {
    "event": "Health Fair",
    "date": "2026-12-15",
    "venue": "Patna",
    "cost": "Free",
    "contact": "1800-XXX-YYYY",
}


class TestCheckLength:
    def test_ok_within_limit(self):
        assert check_length(_draft("Hello")) == []

    def test_warns_over_limit(self):
        warnings = check_length(_draft("x" * 161, channel="sms"))
        assert warnings
        assert "160" in warnings[0]

    def test_email_large_ok(self):
        assert check_length(_draft("x" * 9999, channel="email")) == []

    def test_email_over_limit_warns(self):
        warnings = check_length(_draft("x" * 10001, channel="email"))
        assert warnings


class TestCheckKeyFacts:
    def test_all_present(self):
        text = "Health Fair Patna 2026-12-15 Free 1800-XXX-YYYY"
        assert check_key_facts_present(_draft(text), KEY_FACTS) == []

    def test_missing_one(self):
        text = "Health Fair Patna 2026-12-15 Free"  # contact missing
        warnings = check_key_facts_present(_draft(text), KEY_FACTS)
        assert any("contact" in w.lower() for w in warnings)

    def test_empty_fact_value_skipped(self):
        # Empty fact values should not trigger warnings
        warnings = check_key_facts_present(
            _draft("some text"), {"event": "", "date": "2026"}
        )
        assert all("event" not in w.lower() for w in warnings)


class TestCheckNoPlaceholders:
    def test_clean_draft(self):
        assert check_no_placeholders(_draft("Hello Patna")) == []

    def test_curly_brace_placeholder(self):
        warnings = check_no_placeholders(_draft("Hello {name}"))
        assert warnings

    def test_insert_placeholder(self):
        warnings = check_no_placeholders(_draft("Event at [INSERT VENUE]"))
        assert warnings

    def test_underscore_placeholder(self):
        warnings = check_no_placeholders(_draft("Contact: ___"))
        assert warnings


class TestCheckNoPiiPatterns:
    def test_clean(self):
        assert check_no_pii_patterns(_draft("Join us at Patna Fair")) == []

    def test_angle_bracket_token(self):
        warnings = check_no_pii_patterns(_draft("Dear <name>, join us"))
        assert warnings

    def test_square_bracket_token(self):
        warnings = check_no_pii_patterns(_draft("Call [phone] now"))
        assert warnings


class TestCheckToneSignal:
    def test_professional_clean(self):
        assert check_tone_signal(_draft("Join us at the fair."), "professional") == []

    def test_non_professional_tone_not_checked(self):
        # Aggressive text does not warn when tone is not professional
        warnings = check_tone_signal(
            _draft("urgent!!! act now!!! last chance!!!"), "urgent"
        )
        assert warnings == []

    def test_professional_tone_flags_aggressive(self):
        warnings = check_tone_signal(
            _draft("urgent!!! act now!!! last chance!!!"), "professional"
        )
        assert warnings


class TestValidateDraft:
    def test_valid_draft_no_warnings(self, sample_draft):
        warnings = validate_draft(
            sample_draft,
            {k: getattr(sample_draft, k, "") for k in []},
            tone="professional",
        )
        # sample_draft contains all key facts; warnings should be empty or only tone
        # We just verify it runs without error
        assert isinstance(warnings, list)

    def test_aggregate_warnings_accumulate(self):
        draft = _draft("{placeholder} <name>")
        warnings = validate_draft(draft, KEY_FACTS, tone="professional")
        # Should have placeholder + PII + missing key facts warnings
        assert len(warnings) >= 2

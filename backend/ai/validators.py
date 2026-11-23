"""Pure-function draft validators — no I/O, fully testable offline."""

from __future__ import annotations

from ai.schemas import CHANNEL_LIMITS, GeneratedDraft

# ---------------------------------------------------------------------------
# Individual validator functions
# Each returns a list of human-readable warning strings (empty = no issue).
# ---------------------------------------------------------------------------


def check_length(draft: GeneratedDraft) -> list[str]:
    """Warn when the draft exceeds the channel character limit."""
    limit = CHANNEL_LIMITS.get(draft.channel, 10_000)
    if len(draft.text) > limit:
        return [
            f"Draft exceeds {draft.channel} limit: "
            f"{len(draft.text)} chars > {limit} allowed."
        ]
    return []


def check_key_facts_present(
    draft: GeneratedDraft, key_facts: dict[str, str]
) -> list[str]:
    """Warn when any required key fact is missing from the draft text."""
    warnings: list[str] = []
    for field, value in key_facts.items():
        if value and value.lower() not in draft.text.lower():
            warnings.append(f"Key fact '{field}' ('{value}') not found in draft text.")
    return warnings


def check_no_placeholders(draft: GeneratedDraft) -> list[str]:
    """Warn when the draft still contains unfilled template placeholders."""
    markers = ["{", "}", "{{", "}}", "[FILL", "[INSERT", "___", "XXX"]
    found = [m for m in markers if m in draft.text]
    if found:
        return [f"Draft contains unfilled placeholder(s): {found}"]
    return []


def check_no_pii_patterns(draft: GeneratedDraft) -> list[str]:
    """Basic heuristic: warn on obvious PII placeholders in the draft."""
    import re

    warnings: list[str] = []
    # Detect things like <name>, <phone>, [email] that slipped through
    if re.search(r"<[a-z_]+>|\[[a-z_]+\]", draft.text, re.IGNORECASE):
        warnings.append("Draft may contain unresolved PII placeholder tokens.")
    return warnings


def check_tone_signal(draft: GeneratedDraft, expected_tone: str) -> list[str]:
    """Light heuristic: flag obviously aggressive language if tone is 'professional'."""
    if expected_tone.lower() != "professional":
        return []
    aggressive = ["urgent!!!", "act now!!!", "last chance!!!"]
    text_lower = draft.text.lower()
    hits = [a for a in aggressive if a in text_lower]
    if hits:
        return [f"Draft tone may not match 'professional': found '{hits[0]}'."]
    return []


# ---------------------------------------------------------------------------
# Aggregate validator
# ---------------------------------------------------------------------------


def validate_draft(
    draft: GeneratedDraft,
    key_facts: dict[str, str],
    tone: str = "professional",
) -> list[str]:
    """Run all validators and aggregate warnings for one draft."""
    warnings: list[str] = []
    warnings.extend(check_length(draft))
    warnings.extend(check_key_facts_present(draft, key_facts))
    warnings.extend(check_no_placeholders(draft))
    warnings.extend(check_no_pii_patterns(draft))
    warnings.extend(check_tone_signal(draft, tone))
    return warnings

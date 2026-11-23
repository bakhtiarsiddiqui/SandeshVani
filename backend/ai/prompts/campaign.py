"""Campaign message prompt builders.

Prompts are plain Python strings — no templating engine dependency.
System and user prompts are built separately so providers that support
a system role can pass them correctly.
"""

from __future__ import annotations

from ai.schemas import CHANNEL_LIMITS, CampaignBrief

_SYSTEM = """\
You are SandeshVani's campaign copywriter. Your sole job is to write one \
short, complete marketing message for the requested channel and language. \
Follow these rules strictly:
1. Write ONLY the message text — no preamble, no explanation, no quotes.
2. Include ALL key facts exactly as supplied (do not paraphrase them).
3. Stay within the character limit for the channel.
4. Match the requested tone.
5. Never invent facts, contacts, prices, or venues not given to you.
6. The draft is for human review — it must NOT be published automatically.\
"""


def build_campaign_system_prompt() -> str:
    """Return the system instruction string."""
    return _SYSTEM


def build_campaign_user_prompt(brief: CampaignBrief) -> str:
    """Build the user-facing prompt from a CampaignBrief."""
    limit = CHANNEL_LIMITS.get(brief.channel, 10_000)
    kf = brief.key_facts

    return (
        f"Channel: {brief.channel} (max {limit} characters)\n"
        f"Language: {brief.language}\n"
        f"Tone: {brief.tone}\n"
        f"\n"
        f"Key facts to include verbatim:\n"
        f"  Event: {kf.event}\n"
        f"  Date: {kf.date}\n"
        f"  Venue: {kf.venue}\n"
        f"  Cost: {kf.cost}\n"
        f"  Contact: {kf.contact}\n"
        f"\n"
        f"Write the {brief.channel} message now in {brief.language}:"
    )

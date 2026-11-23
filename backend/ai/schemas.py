"""Pydantic v2 schemas for the AI Campaign Assistant."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Channel character / token limits
# ---------------------------------------------------------------------------

CHANNEL_LIMITS: dict[str, int] = {
    "sms": 160,
    "whatsapp": 1024,
    "email": 10_000,
    "push": 256,
}

SUPPORTED_LANGUAGES: set[str] = {"hi", "en", "mr", "pa", "ta", "te", "bn", "gu", "kn"}

SUPPORTED_CHANNELS = Literal["sms", "whatsapp", "email", "push"]


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class KeyFacts(BaseModel):
    """Mandatory facts the LLM must include verbatim in the generated draft."""

    event: str = Field(
        ..., min_length=1, max_length=200, description="Event or offer name"
    )
    date: str = Field(..., min_length=1, max_length=50, description="Date / deadline")
    venue: str = Field(..., min_length=1, max_length=200, description="Location or URL")
    cost: str = Field(..., min_length=1, max_length=50, description="Price or 'Free'")
    contact: str = Field(
        ..., min_length=1, max_length=100, description="Contact number or email"
    )


class CampaignBrief(BaseModel):
    """Structured brief submitted by an authenticated internal service."""

    channel: SUPPORTED_CHANNELS
    language: str = Field(
        ...,
        min_length=2,
        max_length=5,
        description="BCP-47 language code (hi, en, mr, pa, ta, te, bn, gu, kn)",
    )
    tone: str = Field(
        default="professional",
        max_length=50,
        description="Desired tone, e.g. professional / friendly / urgent",
    )
    key_facts: KeyFacts
    organization_id: uuid.UUID | None = Field(
        default=None,
        description="Tenant that will own the generated drafts (injected by router)",
    )

    @model_validator(mode="after")
    def validate_language(self) -> CampaignBrief:
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{self.language}'. "
                f"Supported: {sorted(SUPPORTED_LANGUAGES)}"
            )
        return self


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------


class GeneratedDraft(BaseModel):
    """A single AI-generated message draft for one language variant."""

    language: str
    channel: str
    text: str
    char_count: int
    within_limit: bool
    provider: str = Field(
        description="Provider that generated this draft (never published)"
    )
    model: str = Field(description="Model identifier used")

    @classmethod
    def build(
        cls,
        language: str,
        channel: str,
        text: str,
        provider: str,
        model: str,
    ) -> GeneratedDraft:
        limit = CHANNEL_LIMITS.get(channel, 10_000)
        return cls(
            language=language,
            channel=channel,
            text=text,
            char_count=len(text),
            within_limit=len(text) <= limit,
            provider=provider,
            model=model,
        )


class GenerateResponse(BaseModel):
    """Response envelope returned by POST /api/v1/ai/campaigns/generate."""

    request_id: uuid.UUID
    status: Literal["pending_approval"] = "pending_approval"
    drafts: list[GeneratedDraft]
    validation_warnings: list[str] = Field(default_factory=list)
    message: str = "Drafts generated and saved. Awaiting human approval before any use."

    model_config = {
        "json_schema_extra": {
            "example": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "pending_approval",
                "drafts": [],
                "validation_warnings": [],
                "message": (
                    "Drafts generated and saved. "
                    "Awaiting human approval before any use."
                ),
            }
        }
    }


# ---------------------------------------------------------------------------
# Approval / status schemas
# ---------------------------------------------------------------------------

ApprovalAction = Literal["approve", "reject"]


class ApprovalRequest(BaseModel):
    action: ApprovalAction
    reviewer_note: str = Field(default="", max_length=1000)


class ApprovalResponse(BaseModel):
    request_id: uuid.UUID
    action: ApprovalAction
    status: str
    reviewer_note: str

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Channel = Literal["email", "sms", "whatsapp", "push"]
Language = Literal["en", "hi"]
BasisCode = Literal[
    "consent",
    "legitimate_use",
    "contract",
    "legal_obligation",
    "vital_interest",
    "public_task",
    "other",
]


class ProcessingBasisEventCreate(BaseModel):
    audience_member_id: uuid.UUID
    purpose_code: str = Field(min_length=1, max_length=100)
    event_type: Literal["established", "withdrawn"]
    basis_code: BasisCode
    evidence_source: str = Field(min_length=1, max_length=64)
    evidence_reference: str | None = Field(default=None, max_length=255)


class ChannelConsentEventCreate(BaseModel):
    audience_member_id: uuid.UUID
    channel: Channel
    purpose_code: str = Field(min_length=1, max_length=100)
    decision: Literal["granted", "withdrawn"]
    evidence_source: str = Field(min_length=1, max_length=64)
    evidence_reference: str | None = Field(default=None, max_length=255)


class SuppressionEventCreate(BaseModel):
    audience_member_id: uuid.UUID
    channel: Channel
    event_type: Literal["suppressed", "unsuppressed"]
    reason_code: str = Field(min_length=1, max_length=64)
    source_code: str = Field(min_length=1, max_length=64)


class SegmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class SegmentVersionCreate(BaseModel):
    filter_ast: dict[str, Any]


class SegmentPreviewRequest(BaseModel):
    version_id: uuid.UUID


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)


class TemplateVersionCreate(BaseModel):
    variants: dict[str, dict[str, Any]]

    @model_validator(mode="after")
    def validate_variants(self):
        validate_content_variants(self.variants)
        return self


def validate_content_variants(variants: dict[str, dict[str, Any]]) -> None:
    allowed_channels = {"email", "sms", "whatsapp", "push"}
    allowed_languages = {"en", "hi"}
    if not variants or set(variants) - allowed_channels:
        raise ValueError(
            "variants must contain only supported communication channels"
        )
    for channel, language_variants in variants.items():
        if not isinstance(language_variants, dict) or not language_variants:
            raise ValueError(f"{channel} must contain explicit language variants")
        if set(language_variants) - allowed_languages:
            raise ValueError("Only explicit English and Hindi variants are supported")
        for language, content in language_variants.items():
            if language not in allowed_languages:
                raise ValueError("Unsupported content language")
            if not isinstance(content, (str, dict)):
                raise ValueError(
                    "Each channel/language variant must be text or an object"
                )
            if isinstance(content, str) and not content.strip():
                raise ValueError("Content variants must not be blank")
            if isinstance(content, dict) and not content:
                raise ValueError("Content variant objects must not be empty")


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=500)
    purpose_code: str = Field(min_length=1, max_length=100)


class CampaignVersionCreate(BaseModel):
    channels: list[Channel] = Field(min_length=1, max_length=4)
    languages: list[Language] = Field(min_length=1, max_length=2)
    segment_version_id: uuid.UUID
    template_version_id: uuid.UUID | None = None
    rendered_variants: dict[str, dict[str, Any]]

    @model_validator(mode="after")
    def validate_campaign_snapshot(self):
        if len(set(self.channels)) != len(self.channels):
            raise ValueError("channels must be unique")
        if len(set(self.languages)) != len(self.languages):
            raise ValueError("languages must be unique")
        validate_content_variants(self.rendered_variants)
        for channel in self.channels:
            if channel not in self.rendered_variants:
                raise ValueError(f"An explicit {channel} content variant is required")
            missing = set(self.languages) - set(self.rendered_variants[channel])
            if missing:
                raise ValueError(
                    f"Missing explicit language variant for {channel}: "
                    f"{sorted(missing)}"
                )
        return self


class CampaignContentRevisionCreate(BaseModel):
    rendered_variants: dict[str, dict[str, Any]]

    @model_validator(mode="after")
    def validate_variants(self):
        validate_content_variants(self.rendered_variants)
        return self


class ApprovalDecisionCreate(BaseModel):
    decision: Literal["approved", "changes_requested"]
    rationale: str = Field(min_length=1, max_length=2000)


class SimpleMessageResponse(BaseModel):
    message: str


class SegmentPreviewResponse(BaseModel):
    segment_id: uuid.UUID
    version_id: uuid.UUID
    matched_count: int


class CampaignExecutionResponse(BaseModel):
    id: uuid.UUID
    campaign_version_id: uuid.UUID
    execution_mode: Literal["mock"]
    status: str
    target_recipients: int
    eligible_recipients: int
    excluded_recipients: int
    delivery_intents: int
    accepted_count: int
    delivered_count: int
    failed_count: int
    retrying_count: int
    unknown_count: int

    model_config = ConfigDict(from_attributes=True)


class CampaignAnalyticsResponse(BaseModel):
    execution_id: uuid.UUID
    simulated: bool
    target_recipients: int
    eligible_recipients: int
    excluded_recipients: int
    delivery_intents: int
    accepted: int
    delivered: int
    failed: int
    retrying: int
    unknown: int
    channel_deliveries: dict[str, dict[str, int]]

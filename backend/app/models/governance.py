"""R1 governed audience, campaign, approval, audit and mock-distribution models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProcessingBasisEvent(Base, UUIDPrimaryKeyMixin):
    """Append-only record of a purpose-specific personal-data processing basis."""

    __tablename__ = "processing_basis_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('established', 'withdrawn')",
            name="ck_processing_basis_event_type",
        ),
        CheckConstraint(
            "basis_code IN ('consent', 'legitimate_use', 'contract', "
            "'legal_obligation', 'vital_interest', 'public_task', 'other')",
            name="ck_processing_basis_basis_code",
        ),
        ForeignKeyConstraint(
            ["organization_id", "audience_member_id"],
            ["audience_members.organization_id", "audience_members.id"],
            name="fk_processing_basis_tenant_audience",
            ondelete="CASCADE",
        ),
        Index(
            "ix_processing_basis_current",
            "organization_id",
            "audience_member_id",
            "purpose_code",
            "created_at",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    audience_member_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    purpose_code: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    basis_code: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_source: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ChannelConsentEvent(Base, UUIDPrimaryKeyMixin):
    """Append-only channel- and purpose-specific permission evidence."""

    __tablename__ = "channel_consent_events"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'sms', 'whatsapp', 'push')",
            name="ck_channel_consent_channel",
        ),
        CheckConstraint(
            "decision IN ('granted', 'withdrawn')",
            name="ck_channel_consent_decision",
        ),
        ForeignKeyConstraint(
            ["organization_id", "audience_member_id"],
            ["audience_members.organization_id", "audience_members.id"],
            name="fk_channel_consent_tenant_audience",
            ondelete="CASCADE",
        ),
        Index(
            "ix_channel_consent_current",
            "organization_id",
            "audience_member_id",
            "channel",
            "purpose_code",
            "created_at",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    audience_member_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    purpose_code: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_source: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SuppressionEvent(Base, UUIDPrimaryKeyMixin):
    """Append-only channel suppression and explicit unsuppression evidence."""

    __tablename__ = "suppression_events"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'sms', 'whatsapp', 'push')",
            name="ck_suppression_channel",
        ),
        CheckConstraint(
            "event_type IN ('suppressed', 'unsuppressed')",
            name="ck_suppression_event_type",
        ),
        ForeignKeyConstraint(
            ["organization_id", "audience_member_id"],
            ["audience_members.organization_id", "audience_members.id"],
            name="fk_suppression_tenant_audience",
            ondelete="CASCADE",
        ),
        Index(
            "ix_suppression_current",
            "organization_id",
            "audience_member_id",
            "channel",
            "created_at",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    audience_member_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    source_code: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AudienceSegment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Mutable segment identity; filter definitions live in immutable versions."""

    __tablename__ = "audience_segments"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_audience_segments_org_id"),
        UniqueConstraint("organization_id", "name", name="uq_audience_segments_name"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class AudienceSegmentVersion(Base, UUIDPrimaryKeyMixin):
    """Immutable, allowlisted JSON filter AST."""

    __tablename__ = "audience_segment_versions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "id",
            name="uq_audience_segment_versions_org_id",
        ),
        UniqueConstraint(
            "organization_id",
            "segment_id",
            "version_number",
            name="uq_audience_segment_versions_number",
        ),
        ForeignKeyConstraint(
            ["organization_id", "segment_id"],
            ["audience_segments.organization_id", "audience_segments.id"],
            name="fk_audience_segment_versions_tenant_segment",
            ondelete="CASCADE",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    segment_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    filter_ast: Mapped[dict] = mapped_column(JSON, nullable=False)
    filter_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MessageTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reusable template identity."""

    __tablename__ = "message_templates"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_message_templates_org_id"),
        UniqueConstraint("organization_id", "name", name="uq_message_templates_name"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class MessageTemplateVersion(Base, UUIDPrimaryKeyMixin):
    """Immutable language/channel-specific template content."""

    __tablename__ = "message_template_versions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "id",
            name="uq_message_template_versions_org_id",
        ),
        UniqueConstraint(
            "organization_id",
            "template_id",
            "version_number",
            name="uq_message_template_versions_number",
        ),
        ForeignKeyConstraint(
            ["organization_id", "template_id"],
            ["message_templates.organization_id", "message_templates.id"],
            name="fk_message_template_versions_tenant_template",
            ondelete="CASCADE",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    variants: Mapped[dict] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Campaign(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Campaign identity and current workflow summary."""

    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_campaigns_org_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(String(500), nullable=False)
    purpose_code: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class CampaignVersion(Base, UUIDPrimaryKeyMixin):
    """Immutable campaign content snapshot; only workflow status may change."""

    __tablename__ = "campaign_versions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'changes_requested')",
            name="ck_campaign_versions_status",
        ),
        UniqueConstraint("organization_id", "id", name="uq_campaign_versions_org_id"),
        UniqueConstraint(
            "organization_id", "campaign_id", "version_number",
            name="uq_campaign_versions_number",
        ),
        ForeignKeyConstraint(
            ["organization_id", "campaign_id"],
            ["campaigns.organization_id", "campaigns.id"],
            name="fk_campaign_versions_tenant_campaign",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "template_version_id"],
            ["message_template_versions.organization_id", "message_template_versions.id"],
            name="fk_campaign_versions_tenant_template_version",
        ),
        ForeignKeyConstraint(
            ["organization_id", "segment_version_id"],
            ["audience_segment_versions.organization_id", "audience_segment_versions.id"],
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)
    purpose_code: Mapped[str] = mapped_column(String(100), nullable=False)
    channels: Mapped[list] = mapped_column(JSON, nullable=False)
    languages: Mapped[list] = mapped_column(JSON, nullable=False)
    content_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    template_version_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    segment_version_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CampaignApproval(Base, UUIDPrimaryKeyMixin):
    """Approval decision bound to a single immutable campaign version/hash."""

    __tablename__ = "campaign_approvals"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'changes_requested')",
            name="ck_campaign_approvals_decision",
        ),
        UniqueConstraint(
            "organization_id", "campaign_version_id", "decided_by",
            name="uq_campaign_approvals_reviewer_version",
        ),
        ForeignKeyConstraint(
            ["organization_id", "campaign_version_id"],
            ["campaign_versions.organization_id", "campaign_versions.id"],
            name="fk_campaign_approvals_tenant_version",
            ondelete="CASCADE",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    campaign_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    version_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    rationale: Mapped[str] = mapped_column(String(2000), nullable=False)
    decided_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditEvent(Base, UUIDPrimaryKeyMixin):
    """Append-only tenant audit event without raw contact or message content."""

    __tablename__ = "audit_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_audit_events_org_id"),
        Index("ix_audit_events_org_created", "organization_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    event_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CampaignExecution(Base, UUIDPrimaryKeyMixin):
    """One manual R1 mock execution per approved campaign version."""

    __tablename__ = "campaign_executions"
    __table_args__ = (
        CheckConstraint(
            "execution_mode = 'mock'",
            name="ck_campaign_executions_mock_only",
        ),
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="ck_campaign_executions_status",
        ),
        UniqueConstraint(
            "organization_id", "id", name="uq_campaign_executions_org_id"
        ),
        UniqueConstraint(
            "organization_id", "campaign_version_id",
            name="uq_campaign_executions_version",
        ),
        ForeignKeyConstraint(
            ["organization_id", "campaign_version_id"],
            ["campaign_versions.organization_id", "campaign_versions.id"],
            name="fk_campaign_executions_tenant_version",
            ondelete="CASCADE",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    campaign_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(8), default="mock", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)
    initiated_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    target_recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    eligible_recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    excluded_recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivery_intents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retrying_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unknown_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExecutionRecipient(Base, UUIDPrimaryKeyMixin):
    """PII-minimal recipient snapshot reference for a single execution."""

    __tablename__ = "execution_recipients"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "id", name="uq_execution_recipients_org_id"
        ),
        UniqueConstraint(
            "organization_id", "execution_id", "audience_member_id",
            name="uq_execution_recipients_member",
        ),
        ForeignKeyConstraint(
            ["organization_id", "execution_id"],
            ["campaign_executions.organization_id", "campaign_executions.id"],
            name="fk_execution_recipients_tenant_execution",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "audience_member_id"],
            ["audience_members.organization_id", "audience_members.id"],
            name="fk_execution_recipients_tenant_audience",
            ondelete="RESTRICT",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    execution_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    audience_member_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    eligibility_evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ChannelDelivery(Base, UUIDPrimaryKeyMixin):
    """Logical channel delivery, distinct from one or more attempts."""

    __tablename__ = "channel_deliveries"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'sms', 'whatsapp', 'push')",
            name="ck_channel_deliveries_channel",
        ),
        CheckConstraint(
            "status IN ('intent', 'simulated_accepted', 'simulated_delivered', "
            "'failed', 'retrying', 'unknown')",
            name="ck_channel_deliveries_status",
        ),
        UniqueConstraint("organization_id", "id", name="uq_channel_deliveries_org_id"),
        UniqueConstraint(
            "organization_id", "recipient_id", "channel",
            name="uq_channel_deliveries_recipient_channel",
        ),
        ForeignKeyConstraint(
            ["organization_id", "recipient_id"],
            ["execution_recipients.organization_id", "execution_recipients.id"],
            name="fk_channel_deliveries_tenant_recipient",
            ondelete="CASCADE",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    recipient_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="intent", nullable=False)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DeliveryAttempt(Base, UUIDPrimaryKeyMixin):
    """An individual simulated delivery attempt."""

    __tablename__ = "delivery_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('simulated_accepted', 'simulated_delivered', 'failed', 'unknown')",
            name="ck_delivery_attempts_status",
        ),
        UniqueConstraint(
            "organization_id", "delivery_id", "attempt_number",
            name="uq_delivery_attempts_number",
        ),
        ForeignKeyConstraint(
            ["organization_id", "delivery_id"],
            ["channel_deliveries.organization_id", "channel_deliveries.id"],
            name="fk_delivery_attempts_tenant_delivery",
            ondelete="CASCADE",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    delivery_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

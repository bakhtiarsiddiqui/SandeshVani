"""Create R1 governed consent, campaigns, approvals, audit and mock execution.

Revision ID: 0009_r1_governance
Revises: 0008_sess_org_aud_loc
"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa

from alembic import op

revision: str = "0009_r1_governance"
down_revision: str | None = "0008_sess_org_aud_loc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TENANT_TABLES = (
    "processing_basis_events",
    "channel_consent_events",
    "suppression_events",
    "audience_segments",
    "audience_segment_versions",
    "message_templates",
    "message_template_versions",
    "campaigns",
    "campaign_versions",
    "campaign_approvals",
    "audit_events",
    "campaign_executions",
    "execution_recipients",
    "channel_deliveries",
    "delivery_attempts",
)


def _enable_tenant_rls(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table_name}
        USING (
            organization_id = NULLIF(
                current_setting('app.current_org', true), ''
            )::uuid
        )
        WITH CHECK (
            organization_id = NULLIF(
                current_setting('app.current_org', true), ''
            )::uuid
        )
        """
    )


def _create_append_only_trigger(table_name: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER {table_name}_append_only
        BEFORE UPDATE OR DELETE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION sandeshvani_reject_mutation()
        """
    )


def upgrade() -> None:
    op.create_table(
        "processing_basis_events",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("audience_member_id", sa.UUID(), nullable=False),
        sa.Column("purpose_code", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("basis_code", sa.String(32), nullable=False),
        sa.Column("evidence_source", sa.String(64), nullable=False),
        sa.Column("evidence_reference", sa.String(255), nullable=True),
        sa.Column("recorded_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("event_type IN ('established', 'withdrawn')", name="ck_processing_basis_event_type"),
        sa.CheckConstraint("basis_code IN ('consent', 'legitimate_use', 'contract', 'legal_obligation', 'vital_interest', 'public_task', 'other')", name="ck_processing_basis_basis_code"),
        sa.ForeignKeyConstraint(["organization_id", "audience_member_id"], ["audience_members.organization_id", "audience_members.id"], name="fk_processing_basis_tenant_audience", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_processing_basis_current", "processing_basis_events", ["organization_id", "audience_member_id", "purpose_code", "created_at"])

    op.create_table(
        "channel_consent_events",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("audience_member_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("purpose_code", sa.String(100), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("evidence_source", sa.String(64), nullable=False),
        sa.Column("evidence_reference", sa.String(255), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("channel IN ('email', 'sms', 'whatsapp', 'push')", name="ck_channel_consent_channel"),
        sa.CheckConstraint("decision IN ('granted', 'withdrawn')", name="ck_channel_consent_decision"),
        sa.ForeignKeyConstraint(["organization_id", "audience_member_id"], ["audience_members.organization_id", "audience_members.id"], name="fk_channel_consent_tenant_audience", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_channel_consent_current", "channel_consent_events", ["organization_id", "audience_member_id", "channel", "purpose_code", "created_at"])

    op.create_table(
        "suppression_events",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("audience_member_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("source_code", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("channel IN ('email', 'sms', 'whatsapp', 'push')", name="ck_suppression_channel"),
        sa.CheckConstraint("event_type IN ('suppressed', 'unsuppressed')", name="ck_suppression_event_type"),
        sa.ForeignKeyConstraint(["organization_id", "audience_member_id"], ["audience_members.organization_id", "audience_members.id"], name="fk_suppression_tenant_audience", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_suppression_current", "suppression_events", ["organization_id", "audience_member_id", "channel", "created_at"])

    op.create_table(
        "audience_segments",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_audience_segments_org_id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_audience_segments_name"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "audience_segment_versions",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("segment_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("filter_ast", sa.JSON(), nullable=False),
        sa.Column("filter_hash", sa.String(64), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_audience_segment_versions_org_id"),
        sa.UniqueConstraint("organization_id", "segment_id", "version_number", name="uq_audience_segment_versions_number"),
        sa.ForeignKeyConstraint(["organization_id", "segment_id"], ["audience_segments.organization_id", "audience_segments.id"], name="fk_audience_segment_versions_tenant_segment", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "message_templates",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_message_templates_org_id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_message_templates_name"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "message_template_versions",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("variants", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_message_template_versions_org_id"),
        sa.UniqueConstraint("organization_id", "template_id", "version_number", name="uq_message_template_versions_number"),
        sa.ForeignKeyConstraint(["organization_id", "template_id"], ["message_templates.organization_id", "message_templates.id"], name="fk_message_template_versions_tenant_template", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("objective", sa.String(500), nullable=False),
        sa.Column("purpose_code", sa.String(100), nullable=False),
        sa.Column("status", sa.String(24), server_default="draft", nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_campaigns_org_id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "campaign_versions",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("campaign_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), server_default="draft", nullable=False),
        sa.Column("purpose_code", sa.String(100), nullable=False),
        sa.Column("channels", sa.JSON(), nullable=False),
        sa.Column("languages", sa.JSON(), nullable=False),
        sa.Column("content_snapshot", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("template_version_id", sa.UUID(), nullable=True),
        sa.Column("segment_version_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("submitted_by", sa.UUID(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'submitted', 'approved', 'changes_requested')", name="ck_campaign_versions_status"),
        sa.UniqueConstraint("organization_id", "id", name="uq_campaign_versions_org_id"),
        sa.UniqueConstraint("organization_id", "campaign_id", "version_number", name="uq_campaign_versions_number"),
        sa.ForeignKeyConstraint(["organization_id", "campaign_id"], ["campaigns.organization_id", "campaigns.id"], name="fk_campaign_versions_tenant_campaign", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id", "template_version_id"], ["message_template_versions.organization_id", "message_template_versions.id"], name="fk_campaign_versions_tenant_template_version"),
        sa.ForeignKeyConstraint(["organization_id", "segment_version_id"], ["audience_segment_versions.organization_id", "audience_segment_versions.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "campaign_approvals",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("campaign_version_id", sa.UUID(), nullable=False),
        sa.Column("version_hash", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(24), nullable=False),
        sa.Column("rationale", sa.String(2000), nullable=False),
        sa.Column("decided_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("decision IN ('approved', 'changes_requested')", name="ck_campaign_approvals_decision"),
        sa.UniqueConstraint("organization_id", "campaign_version_id", "decided_by", name="uq_campaign_approvals_reviewer_version"),
        sa.ForeignKeyConstraint(["organization_id", "campaign_version_id"], ["campaign_versions.organization_id", "campaign_versions.id"], name="fk_campaign_approvals_tenant_version", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="RESTRICT"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("event_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_audit_events_org_id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_events_org_created", "audit_events", ["organization_id", "created_at"])

    op.create_table(
        "campaign_executions",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("campaign_version_id", sa.UUID(), nullable=False),
        sa.Column("execution_mode", sa.String(8), server_default="mock", nullable=False),
        sa.Column("status", sa.String(16), server_default="queued", nullable=False),
        sa.Column("initiated_by", sa.UUID(), nullable=False),
        sa.Column("target_recipients", sa.Integer(), server_default="0", nullable=False),
        sa.Column("eligible_recipients", sa.Integer(), server_default="0", nullable=False),
        sa.Column("excluded_recipients", sa.Integer(), server_default="0", nullable=False),
        sa.Column("delivery_intents", sa.Integer(), server_default="0", nullable=False),
        sa.Column("accepted_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("delivered_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("retrying_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("unknown_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("execution_mode = 'mock'", name="ck_campaign_executions_mock_only"),
        sa.CheckConstraint("status IN ('queued', 'processing', 'completed', 'failed')", name="ck_campaign_executions_status"),
        sa.UniqueConstraint("organization_id", "id", name="uq_campaign_executions_org_id"),
        sa.UniqueConstraint("organization_id", "campaign_version_id", name="uq_campaign_executions_version"),
        sa.ForeignKeyConstraint(["organization_id", "campaign_version_id"], ["campaign_versions.organization_id", "campaign_versions.id"], name="fk_campaign_executions_tenant_version", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiated_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "execution_recipients",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("audience_member_id", sa.UUID(), nullable=False),
        sa.Column("eligibility_evaluated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("organization_id", "id", name="uq_execution_recipients_org_id"),
        sa.UniqueConstraint("organization_id", "execution_id", "audience_member_id", name="uq_execution_recipients_member"),
        sa.ForeignKeyConstraint(["organization_id", "execution_id"], ["campaign_executions.organization_id", "campaign_executions.id"], name="fk_execution_recipients_tenant_execution", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id", "audience_member_id"], ["audience_members.organization_id", "audience_members.id"], name="fk_execution_recipients_tenant_audience", ondelete="RESTRICT"),
    )
    op.create_table(
        "channel_deliveries",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("recipient_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), server_default="intent", nullable=False),
        sa.Column("simulated", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("channel IN ('email', 'sms', 'whatsapp', 'push')", name="ck_channel_deliveries_channel"),
        sa.CheckConstraint("status IN ('intent', 'simulated_accepted', 'simulated_delivered', 'failed', 'retrying', 'unknown')", name="ck_channel_deliveries_status"),
        sa.UniqueConstraint("organization_id", "id", name="uq_channel_deliveries_org_id"),
        sa.UniqueConstraint("organization_id", "recipient_id", "channel", name="uq_channel_deliveries_recipient_channel"),
        sa.ForeignKeyConstraint(["organization_id", "recipient_id"], ["execution_recipients.organization_id", "execution_recipients.id"], name="fk_channel_deliveries_tenant_recipient", ondelete="CASCADE"),
    )
    op.create_table(
        "delivery_attempts",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("delivery_id", sa.UUID(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("simulated", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('simulated_accepted', 'simulated_delivered', 'failed', 'unknown')", name="ck_delivery_attempts_status"),
        sa.UniqueConstraint("organization_id", "delivery_id", "attempt_number", name="uq_delivery_attempts_number"),
        sa.ForeignKeyConstraint(["organization_id", "delivery_id"], ["channel_deliveries.organization_id", "channel_deliveries.id"], name="fk_delivery_attempts_tenant_delivery", ondelete="CASCADE"),
    )

    op.execute(
        """
        CREATE FUNCTION sandeshvani_reject_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'append-only evidence table % cannot be modified', TG_TABLE_NAME;
        END;
        $$;
        """
    )
    for table in (
        "processing_basis_events",
        "channel_consent_events",
        "suppression_events",
        "audience_segment_versions",
        "message_template_versions",
        "campaign_approvals",
        "audit_events",
        "delivery_attempts",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION sandeshvani_reject_mutation()"
        )

    op.execute(
        """
        CREATE FUNCTION sandeshvani_guard_campaign_version()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'campaign versions cannot be deleted';
            END IF;
            IF NEW.organization_id IS DISTINCT FROM OLD.organization_id
               OR NEW.campaign_id IS DISTINCT FROM OLD.campaign_id
               OR NEW.version_number IS DISTINCT FROM OLD.version_number
               OR NEW.purpose_code IS DISTINCT FROM OLD.purpose_code
               OR NEW.channels IS DISTINCT FROM OLD.channels
               OR NEW.languages IS DISTINCT FROM OLD.languages
               OR NEW.content_snapshot IS DISTINCT FROM OLD.content_snapshot
               OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
               OR NEW.template_version_id IS DISTINCT FROM OLD.template_version_id
               OR NEW.segment_version_id IS DISTINCT FROM OLD.segment_version_id
               OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
                RAISE EXCEPTION 'campaign version content is immutable';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER campaign_versions_immutable
        BEFORE UPDATE OR DELETE ON campaign_versions
        FOR EACH ROW EXECUTE FUNCTION sandeshvani_guard_campaign_version();
        """
    )

    for table_name in TENANT_TABLES:
        _enable_tenant_rls(table_name)

    # Add the permission codes needed by the approved R1 separation of duties.
    permission_descriptions = {
        "segments:update": "Update audience segment definitions",
        "suppression:read": "View channel suppression evidence",
        "suppression:update": "Record or lift channel suppression",
        "templates:update": "Create immutable template versions",
        "campaigns:content:update": "Author campaign content variants",
        "localization:read": "View language variants",
        "localization:update": "Author language variants",
    }
    bind = op.get_bind()
    for code, description in permission_descriptions.items():
        bind.execute(
            sa.text(
                "INSERT INTO permissions (id, code, description, created_at) "
                "VALUES (:id, :code, :description, now()) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"id": str(uuid.uuid4()), "code": code, "description": description},
        )

    # Adjust existing tenant role grants as well as future defaults.
    org_ids = bind.execute(sa.text("SELECT id FROM organizations ORDER BY id")).scalars()
    for org_id in org_ids:
        bind.execute(
            sa.text("SELECT set_config('app.current_org', :org_id, true)"),
            {"org_id": str(org_id)},
        )
        role_rows = bind.execute(
            sa.text("SELECT id, name FROM roles WHERE organization_id = :org_id"),
            {"org_id": org_id},
        ).mappings()
        for role_row in role_rows:
            role_name = role_row["name"].casefold()
            role_id = role_row["id"]
            grant_codes: list[str] = []
            if role_name == "organization administrator":
                grant_codes = list(permission_descriptions)
            elif role_name == "campaign manager":
                grant_codes = ["segments:update", "campaigns:content:update", "localization:read"]
            elif role_name == "communication team":
                grant_codes = [
                    "templates:update",
                    "campaigns:content:update",
                    "localization:read",
                    "localization:update",
                ]
                old_permissions = bind.execute(
                    sa.text(
                        """
                        SELECT p.id
                        FROM role_permissions rp
                        JOIN permissions p ON p.id = rp.permission_id
                        WHERE rp.role_id = :role_id
                          AND p.code IN ('campaigns:create', 'campaigns:update')
                        """
                    ),
                    {"role_id": role_id},
                ).scalars().all()
                for permission_id in old_permissions:
                    bind.execute(
                        sa.text(
                            """
                            DELETE FROM role_permissions
                            WHERE role_id = :role_id AND permission_id = :permission_id
                            """
                        ),
                        {"role_id": role_id, "permission_id": permission_id},
                    )
            for code in grant_codes:
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO role_permissions
                            (role_id, permission_id, role_scope, organization_id)
                        SELECT :role_id, p.id, 'organization', :org_id
                        FROM permissions p
                        WHERE p.code = :code
                        ON CONFLICT (role_id, permission_id) DO NOTHING
                        """
                    ),
                    {"role_id": role_id, "org_id": org_id, "code": code},
                )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in (
            "processing_basis_events",
            "channel_consent_events",
            "suppression_events",
            "audience_segment_versions",
            "message_template_versions",
            "campaign_approvals",
            "audit_events",
            "delivery_attempts",
        ):
            op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
        op.execute("DROP TRIGGER IF EXISTS campaign_versions_immutable ON campaign_versions")
        op.execute("DROP FUNCTION IF EXISTS sandeshvani_guard_campaign_version()")
        op.execute("DROP FUNCTION IF EXISTS sandeshvani_reject_mutation()")
        for table_name in reversed(TENANT_TABLES):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}")
            op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")

    # Permission grants are deliberately not restored by downgrade: the code
    # and permission catalogue migration are not intended to be rolled back in
    # a live tenant database without an explicit RBAC reconciliation procedure.
    for table_name in (
        "delivery_attempts",
        "channel_deliveries",
        "execution_recipients",
        "campaign_executions",
        "audit_events",
        "campaign_approvals",
        "campaign_versions",
        "campaigns",
        "message_template_versions",
        "message_templates",
        "audience_segment_versions",
        "audience_segments",
        "suppression_events",
        "channel_consent_events",
        "processing_basis_events",
    ):
        op.drop_table(table_name)

    for code in (
        "segments:update",
        "suppression:read",
        "suppression:update",
        "templates:update",
        "campaigns:content:update",
        "localization:read",
        "localization:update",
    ):
        bind.execute(sa.text("DELETE FROM permissions WHERE code = :code"), {"code": code})

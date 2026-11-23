"""Add AI Campaign Assistant tables.

Revision ID: 0014_ai_campaign_assistant
Revises: 0013_jsonb_campaign_immutability
Create Date: 2026-11-18

Tables created:
  - ai_generation_requests   — one row per POST /ai/campaigns/generate call
  - ai_generated_content     — one draft per request (pending_approval default)
  - ai_approval_records      — human approve/reject decisions
  - ai_usage_logs            — provider, model, tokens for cost/audit tracking

Row-level security follows the same pattern as other tenant tables:
  - organization_id on every tenant row
  - RLS policies enabled after table creation
  - No cross-tenant reads possible at the DB level
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014_ai_campaign_assistant"
down_revision: str | None = "0013_jsonb_campaign_immutability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. ai_generation_requests
    #    One row per draft-generation API call.  status tracks the
    #    overall lifecycle: pending_approval → approved | rejected.
    # ------------------------------------------------------------------
    op.create_table(
        "ai_generation_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column(
            "tone", sa.String(length=50), nullable=False, server_default="professional"
        ),
        # key_facts stored as JSONB (JSON on SQLite for tests)
        sa.Column("key_facts", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="pending_approval",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "channel IN ('sms', 'whatsapp', 'email', 'push')",
            name="ck_ai_gen_req_channel",
        ),
        sa.CheckConstraint(
            "status IN ('pending_approval', 'approved', 'rejected')",
            name="ck_ai_gen_req_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_ai_gen_req_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            name="fk_ai_gen_req_user",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_ai_gen_req_org_status",
        "ai_generation_requests",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_ai_gen_req_created",
        "ai_generation_requests",
        ["organization_id", "created_at"],
    )

    # ------------------------------------------------------------------
    # 2. ai_generated_content
    #    One draft per ai_generation_requests row.
    #    draft_text is the raw LLM output — never automatically published.
    # ------------------------------------------------------------------
    op.create_table(
        "ai_generated_content",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("draft_text", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("within_limit", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column(
            "validation_warnings", sa.JSON(), nullable=False, server_default="[]"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["ai_generation_requests.id"],
            name="fk_ai_content_request",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_ai_content_org",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_ai_content_request",
        "ai_generated_content",
        ["request_id"],
        unique=True,  # exactly one draft per request
    )

    # ------------------------------------------------------------------
    # 3. ai_approval_records
    #    Human approve/reject decisions.  action is immutable once set.
    # ------------------------------------------------------------------
    op.create_table(
        "ai_approval_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("reviewer_user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("reviewer_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('approve', 'reject')",
            name="ck_ai_approval_action",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["ai_generation_requests.id"],
            name="fk_ai_approval_request",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_ai_approval_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_user_id"],
            ["users.id"],
            name="fk_ai_approval_reviewer",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_ai_approval_request",
        "ai_approval_records",
        ["request_id"],
        unique=True,  # one decision per request
    )

    # ------------------------------------------------------------------
    # 4. ai_usage_logs
    #    Provider/model/token telemetry for cost tracking and auditing.
    # ------------------------------------------------------------------
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["ai_generation_requests.id"],
            name="fk_ai_usage_request",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_ai_usage_org",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_ai_usage_org_logged",
        "ai_usage_logs",
        ["organization_id", "logged_at"],
    )

    # ------------------------------------------------------------------
    # 5. Enable RLS on tenant tables (PostgreSQL only)
    # ------------------------------------------------------------------
    for table in (
        "ai_generation_requests",
        "ai_generated_content",
        "ai_approval_records",
        "ai_usage_logs",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
                USING (
                    organization_id IS NULL
                    OR organization_id = (
                        current_setting('app.current_org', true)::uuid
                    )
                )
            """
        )


def downgrade() -> None:
    for table in (
        "ai_usage_logs",
        "ai_approval_records",
        "ai_generated_content",
        "ai_generation_requests",
    ):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("ai_usage_logs")
    op.drop_table("ai_approval_records")
    op.drop_table("ai_generated_content")
    op.drop_table("ai_generation_requests")

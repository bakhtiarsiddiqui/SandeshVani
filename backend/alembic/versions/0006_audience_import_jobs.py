"""Create tenant-scoped import jobs, row errors and durable outbox events.

Revision ID: 0006_audience_import_jobs
Revises: 0005_audience_import_uploads
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_audience_import_jobs"
down_revision: str | None = "0005_audience_import_uploads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enable_tenant_rls(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;")
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
        );
        """
    )


def upgrade() -> None:
    op.create_table(
        "audience_import_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("upload_id", sa.UUID(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(32), server_default="queued", nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("processed_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("imported_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rejected_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failure_code", sa.String(80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', "
            "'completed_with_errors', 'failed')",
            name="ck_audience_import_jobs_status",
        ),
        sa.CheckConstraint(
            "total_rows > 0",
            name="ck_audience_import_jobs_total_rows",
        ),
        sa.CheckConstraint(
            "processed_rows >= 0 AND imported_rows >= 0 AND rejected_rows >= 0",
            name="ck_audience_import_jobs_nonnegative_counts",
        ),
        sa.CheckConstraint(
            "processed_rows <= total_rows",
            name="ck_audience_import_jobs_processed_limit",
        ),
        sa.CheckConstraint(
            "imported_rows + rejected_rows = processed_rows",
            name="ck_audience_import_jobs_count_balance",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "upload_id"],
            ["audience_import_uploads.organization_id", "audience_import_uploads.id"],
            name="fk_audience_import_jobs_org_upload",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_audience_import_jobs_org_id"
        ),
        sa.UniqueConstraint(
            "organization_id", "upload_id", name="uq_audience_import_jobs_org_upload"
        ),
    )
    op.create_index(
        "ix_audience_import_jobs_org_created",
        "audience_import_jobs",
        ["organization_id", "created_at", "id"],
    )
    op.create_index(
        "ix_audience_import_jobs_status_updated",
        "audience_import_jobs",
        ["status", "updated_at"],
    )

    op.create_table(
        "audience_import_job_errors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("import_job_id", sa.UUID(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(32), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "row_number >= 2",
            name="ck_audience_import_job_errors_row_number",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "import_job_id"],
            ["audience_import_jobs.organization_id", "audience_import_jobs.id"],
            name="fk_audience_import_job_errors_org_job",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audience_import_job_errors_org_job_row",
        "audience_import_job_errors",
        ["organization_id", "import_job_id", "row_number", "id"],
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("dispatch_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("last_dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'dispatched', 'completed', 'failed')",
            name="ck_outbox_events_status",
        ),
        sa.CheckConstraint(
            "dispatch_attempts >= 0",
            name="ck_outbox_events_dispatch_attempts",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "event_type",
            "aggregate_type",
            "aggregate_id",
            name="uq_outbox_events_org_aggregate_event",
        ),
    )
    op.create_index(
        "ix_outbox_events_org_status_available",
        "outbox_events",
        ["organization_id", "status", "available_at"],
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table_name in (
            "audience_import_jobs",
            "audience_import_job_errors",
            "outbox_events",
        ):
            _enable_tenant_rls(table_name)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table_name in (
            "outbox_events",
            "audience_import_job_errors",
            "audience_import_jobs",
        ):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name};")
            op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_outbox_events_org_status_available", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index(
        "ix_audience_import_job_errors_org_job_row",
        table_name="audience_import_job_errors",
    )
    op.drop_table("audience_import_job_errors")
    op.drop_index(
        "ix_audience_import_jobs_status_updated", table_name="audience_import_jobs"
    )
    op.drop_index(
        "ix_audience_import_jobs_org_created", table_name="audience_import_jobs"
    )
    op.drop_table("audience_import_jobs")

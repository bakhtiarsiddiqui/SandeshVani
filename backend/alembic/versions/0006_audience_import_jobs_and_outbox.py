"""Create durable tenant-scoped audience import jobs and outbox events.

Revision ID: 0006_audience_import_jobs_and_outbox
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
        sa.Column("uploaded_by_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("processed_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("imported_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("worker_token", sa.UUID(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', "
            "'completed_with_errors', 'failed')",
            name="ck_audience_import_jobs_status",
        ),
        sa.CheckConstraint("total_rows > 0", name="ck_audience_import_jobs_total_rows"),
        sa.CheckConstraint(
            "processed_rows >= 0 AND processed_rows <= total_rows",
            name="ck_audience_import_jobs_processed_rows",
        ),
        sa.CheckConstraint(
            "imported_rows >= 0 AND error_rows >= 0",
            name="ck_audience_import_jobs_result_rows",
        ),
        sa.CheckConstraint(
            "processed_rows = imported_rows + error_rows",
            name="ck_audience_import_jobs_row_accounting",
        ),
        sa.CheckConstraint("chunk_size > 0", name="ck_audience_import_jobs_chunk_size"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "upload_id"],
            ["audience_import_uploads.organization_id", "audience_import_uploads.id"],
            name="fk_audience_import_jobs_tenant_upload",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "id",
            name="uq_audience_import_jobs_org_id",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "upload_id",
            name="uq_audience_import_jobs_org_upload",
        ),
    )
    op.create_index(
        "ix_audience_import_jobs_org_status_created",
        "audience_import_jobs",
        ["organization_id", "status", "created_at"],
        unique=False,
    )

    op.create_table(
        "audience_import_job_errors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
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
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "job_id"],
            ["audience_import_jobs.organization_id", "audience_import_jobs.id"],
            name="fk_audience_import_job_errors_tenant_job",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "job_id",
            "row_number",
            name="uq_audience_import_job_errors_job_row",
        ),
    )
    op.create_index(
        "ix_audience_import_job_errors_org_job_row",
        "audience_import_job_errors",
        ["organization_id", "job_id", "row_number"],
        unique=False,
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'publishing', 'published', 'dead_letter')",
            name="ck_outbox_events_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_outbox_events_attempt_count",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "id",
            name="uq_outbox_events_org_id",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "aggregate_type",
            "aggregate_id",
            "event_type",
            name="uq_outbox_events_aggregate_event",
        ),
    )
    op.create_index(
        "ix_outbox_events_dispatch",
        "outbox_events",
        ["organization_id", "status", "available_at", "locked_until"],
        unique=False,
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
            "audience_import_job_errors",
            "audience_import_jobs",
            "outbox_events",
        ):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name};")
            op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")

    op.drop_index(
        "ix_outbox_events_dispatch",
        table_name="outbox_events",
    )
    op.drop_table("outbox_events")
    op.drop_index(
        "ix_audience_import_job_errors_org_job_row",
        table_name="audience_import_job_errors",
    )
    op.drop_table("audience_import_job_errors")
    op.drop_index(
        "ix_audience_import_jobs_org_status_created",
        table_name="audience_import_jobs",
    )
    op.drop_table("audience_import_jobs")

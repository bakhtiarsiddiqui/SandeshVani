"""Enforce tenant-scoped audience identity keys and count import duplicates.

Revision ID: 0007_audience_identity_constraints
Revises: 0006_audience_import_jobs
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_audience_identity"
down_revision: str | None = "0006_audience_import_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_duplicate_identity_keys(bind, column_name: str) -> bool:
    if column_name not in {"email", "phone"}:
        raise ValueError("Unsupported audience identity column")
    statement = sa.text(
        f"""
        SELECT EXISTS (
            SELECT 1
            FROM audience_members
            WHERE {column_name} IS NOT NULL
              AND trim({column_name}) <> ''
            GROUP BY organization_id, lower(trim({column_name}))
            HAVING count(*) > 1
        )
        """
    )
    return bool(bind.execute(statement).scalar())


def upgrade() -> None:
    bind = op.get_bind()

    # Do not pick a winner or rewrite live audience data during a schema
    # migration. Require an explicit, tenant-reviewed cleanup first.
    if _has_duplicate_identity_keys(bind, "email"):
        raise RuntimeError(
            "AUD-04 migration blocked: duplicate tenant email identity keys exist. "
            "Review and resolve duplicate audience records before retrying."
        )
    if _has_duplicate_identity_keys(bind, "phone"):
        raise RuntimeError(
            "AUD-04 migration blocked: duplicate tenant phone identity keys exist. "
            "Review and resolve duplicate audience records before retrying."
        )

    op.add_column(
        "audience_import_jobs",
        sa.Column(
            "duplicate_rows",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.drop_constraint(
        "ck_audience_import_jobs_result_rows",
        "audience_import_jobs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_audience_import_jobs_result_rows",
        "audience_import_jobs",
        "imported_rows >= 0 AND error_rows >= 0 AND duplicate_rows >= 0",
    )
    op.drop_constraint(
        "ck_audience_import_jobs_row_accounting",
        "audience_import_jobs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_audience_import_jobs_row_accounting",
        "audience_import_jobs",
        "processed_rows = imported_rows + error_rows + duplicate_rows",
    )

    op.create_index(
        "uq_audience_members_org_email_identity",
        "audience_members",
        ["organization_id", sa.text("lower(trim(email))")],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL AND trim(email) <> ''"),
        sqlite_where=sa.text("email IS NOT NULL AND trim(email) <> ''"),
    )
    op.create_index(
        "uq_audience_members_org_phone_identity",
        "audience_members",
        ["organization_id", sa.text("trim(phone)")],
        unique=True,
        postgresql_where=sa.text("phone IS NOT NULL AND trim(phone) <> ''"),
        sqlite_where=sa.text("phone IS NOT NULL AND trim(phone) <> ''"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_audience_members_org_phone_identity",
        table_name="audience_members",
    )
    op.drop_index(
        "uq_audience_members_org_email_identity",
        table_name="audience_members",
    )

    op.drop_constraint(
        "ck_audience_import_jobs_row_accounting",
        "audience_import_jobs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_audience_import_jobs_row_accounting",
        "audience_import_jobs",
        "processed_rows = imported_rows + error_rows",
    )
    op.drop_constraint(
        "ck_audience_import_jobs_result_rows",
        "audience_import_jobs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_audience_import_jobs_result_rows",
        "audience_import_jobs",
        "imported_rows >= 0 AND error_rows >= 0",
    )
    op.drop_column("audience_import_jobs", "duplicate_rows")

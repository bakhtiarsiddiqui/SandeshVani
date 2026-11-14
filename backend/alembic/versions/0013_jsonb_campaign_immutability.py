"""Fix immutable campaign-version JSON comparisons on PostgreSQL.

Revision ID: 0013_jsonb_campaign_immutability
Revises: 0012_campaign_approval_single_decision
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013_jsonb_campaign_immutability"
down_revision: str | None = "0012_campaign_approval_single_decision"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _install_guard(*, compare_jsonb: bool) -> None:
    if compare_jsonb:
        channels = "NEW.channels::jsonb IS DISTINCT FROM OLD.channels::jsonb"
        languages = "NEW.languages::jsonb IS DISTINCT FROM OLD.languages::jsonb"
        snapshot = (
            "NEW.content_snapshot::jsonb "
            "IS DISTINCT FROM OLD.content_snapshot::jsonb"
        )
    else:
        channels = "NEW.channels IS DISTINCT FROM OLD.channels"
        languages = "NEW.languages IS DISTINCT FROM OLD.languages"
        snapshot = "NEW.content_snapshot IS DISTINCT FROM OLD.content_snapshot"

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION sandeshvani_guard_campaign_version()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $guard$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'campaign versions cannot be deleted';
            END IF;
            IF NEW.organization_id IS DISTINCT FROM OLD.organization_id
               OR NEW.campaign_id IS DISTINCT FROM OLD.campaign_id
               OR NEW.version_number IS DISTINCT FROM OLD.version_number
               OR NEW.purpose_code IS DISTINCT FROM OLD.purpose_code
               OR {channels}
               OR {languages}
               OR {snapshot}
               OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
               OR NEW.template_version_id IS DISTINCT FROM OLD.template_version_id
               OR NEW.segment_version_id IS DISTINCT FROM OLD.segment_version_id
               OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
                RAISE EXCEPTION 'campaign version content is immutable';
            END IF;
            RETURN NEW;
        END;
        $guard$
        """
    )


def upgrade() -> None:
    # PostgreSQL JSON has no equality operator. Compare JSON values as JSONB so
    # workflow-only status updates work while immutable content remains guarded.
    _install_guard(compare_jsonb=True)


def downgrade() -> None:
    _install_guard(compare_jsonb=False)

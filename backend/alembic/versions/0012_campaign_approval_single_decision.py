"""Enforce one governance decision per campaign version.

Revision ID: 0012_campaign_approval_single_decision
Revises: 0011_r1_governance
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_campaign_approval_single_decision"
down_revision: str | None = "0011_r1_governance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicate = bind.execute(
        sa.text(
            """
            SELECT organization_id, campaign_version_id, COUNT(*) AS decisions
            FROM campaign_approvals
            GROUP BY organization_id, campaign_version_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot enforce one approval per campaign version: "
            f"existing duplicate decisions found for version {duplicate[1]}"
        )

    op.drop_constraint(
        "uq_campaign_approvals_reviewer_version",
        "campaign_approvals",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_campaign_approvals_single_decision",
        "campaign_approvals",
        ["organization_id", "campaign_version_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_campaign_approvals_single_decision",
        "campaign_approvals",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_campaign_approvals_reviewer_version",
        "campaign_approvals",
        ["organization_id", "campaign_version_id", "decided_by"],
    )

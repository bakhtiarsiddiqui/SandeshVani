"""PostgreSQL concurrency regression for campaign approval decisions."""

import asyncio
import os
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.governance import Campaign, CampaignApproval, CampaignVersion
from app.models.organization import Organization
from app.models.user import User
from app.services.governance_service import GovernanceService, content_sha256


@pytest.mark.asyncio
async def test_concurrent_approvers_cannot_record_two_decisions_for_one_version():
    database_url = os.getenv("SANDESHVANI_PG_TEST_URL")
    if not database_url:
        pytest.skip("SANDESHVANI_PG_TEST_URL is required for PostgreSQL concurrency test")

    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+asyncpg")
    engine = create_async_engine(url, pool_size=4, max_overflow=0)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    organization_id = uuid.uuid4()
    creator_id, approver_one_id, approver_two_id = (
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
    )
    campaign_id, version_id = uuid.uuid4(), uuid.uuid4()
    content_snapshot = {"message": "Concurrency regression fixture"}
    version_hash = content_sha256(content_snapshot)

    try:
        async with factory.begin() as session:
            session.add(
                Organization(
                    id=organization_id,
                    name="Approval Concurrency Test",
                    slug=f"approval-concurrency-{organization_id.hex}",
                    status="active",
                )
            )
            for user_id, email in (
                (creator_id, f"{creator_id.hex}@example.test"),
                (approver_one_id, f"{approver_one_id.hex}@example.test"),
                (approver_two_id, f"{approver_two_id.hex}@example.test"),
            ):
                session.add(
                    User(
                        id=user_id,
                        email=email,
                        normalized_email=email,
                        password_hash="test-only",
                        full_name="Approval Test User",
                        status="active",
                    )
                )
            session.add(
                Campaign(
                    id=campaign_id,
                    organization_id=organization_id,
                    name="Approval Concurrency Campaign",
                    objective="Test serialized approval",
                    purpose_code="test",
                    status="submitted",
                    created_by=creator_id,
                )
            )
            session.add(
                CampaignVersion(
                    id=version_id,
                    organization_id=organization_id,
                    campaign_id=campaign_id,
                    version_number=1,
                    status="submitted",
                    purpose_code="test",
                    channels=["email"],
                    languages=["en"],
                    content_snapshot=content_snapshot,
                    content_hash=version_hash,
                    created_by=creator_id,
                    submitted_by=creator_id,
                )
            )

        async def decide(actor_id: uuid.UUID):
            async with factory() as session:
                try:
                    async with session.begin():
                        await session.execute(
                            text("SELECT set_config('app.current_org', :org_id, true)"),
                            {"org_id": str(organization_id)},
                        )
                        approval = await GovernanceService(
                            session, organization_id
                        ).approve_campaign_version(
                            campaign_id,
                            version_id,
                            decision="approved",
                            rationale="Concurrent approval test",
                            version_hash=version_hash,
                            actor_id=actor_id,
                        )
                        return approval.id
                except HTTPException as error:
                    return error.status_code

        outcomes = await asyncio.gather(
            decide(approver_one_id),
            decide(approver_two_id),
        )
        assert sum(isinstance(value, uuid.UUID) for value in outcomes) == 1
        assert outcomes.count(409) == 1

        async with factory() as session:
            decision_count = await session.scalar(
                select(func.count(CampaignApproval.id)).where(
                    CampaignApproval.organization_id == organization_id,
                    CampaignApproval.campaign_version_id == version_id,
                )
            )
            stored_version = await session.get(CampaignVersion, version_id)
            assert decision_count == 1
            assert stored_version is not None
            assert stored_version.status == "approved"
    finally:
        async with engine.begin() as connection:
            # Governance evidence is intentionally append-only. Disable only
            # user triggers inside this cleanup transaction for these isolated
            # fixture rows, then restore them before the transaction commits.
            for table in (
                "campaign_approvals",
                "campaign_versions",
                "audit_events",
            ):
                await connection.execute(
                    text(f"ALTER TABLE {table} DISABLE TRIGGER USER")
                )
            await connection.execute(
                text("DELETE FROM organizations WHERE id = :organization_id"),
                {"organization_id": organization_id},
            )
            await connection.execute(
                text(
                    "DELETE FROM users WHERE id IN "
                    "(:creator_id, :approver_one_id, :approver_two_id)"
                ),
                {
                    "creator_id": creator_id,
                    "approver_one_id": approver_one_id,
                    "approver_two_id": approver_two_id,
                },
            )
            for table in (
                "campaign_approvals",
                "campaign_versions",
                "audit_events",
            ):
                await connection.execute(
                    text(f"ALTER TABLE {table} ENABLE TRIGGER USER")
                )
        await engine.dispose()

import pytest
from fastapi import HTTPException

from app.models.user import User
from app.services.organization_service import OrganizationService


@pytest.mark.asyncio
async def test_last_organization_administrator_role_cannot_be_removed(
    test_db_session,
):
    actor = User(
        email="last-admin@example.test",
        normalized_email="last-admin@example.test",
        password_hash="unused",
        full_name="Last Admin",
        status="active",
    )
    invitee = User(
        email="other-admin@example.test",
        normalized_email="other-admin@example.test",
        password_hash="unused",
        full_name="Other Admin",
        status="active",
    )
    test_db_session.add_all([actor, invitee])
    await test_db_session.flush()

    service = OrganizationService(test_db_session)
    organization = await service.create_organization(
        name="Admin Guard", slug="admin-guard", creator_user_id=actor.id
    )
    role = await service.role_repo.get_role_by_name(
        "Organization Administrator", organization_id=organization.id
    )
    assert role is not None

    added = await service.add_member(
        organization_id=organization.id,
        actor_user_id=actor.id,
        email=invitee.email,
        role_ids=[role.id],
    )
    await test_db_session.commit()

    await service.remove_role_from_member(
        organization_id=organization.id,
        actor_user_id=actor.id,
        membership_id=added.id,
        role_id=role.id,
    )
    await test_db_session.commit()

    membership = await service.membership_repo.get_membership(organization.id, actor.id)
    with pytest.raises(HTTPException) as error:
        await service.remove_role_from_member(
            organization_id=organization.id,
            actor_user_id=actor.id,
            membership_id=membership.id,
            role_id=role.id,
        )
    assert error.value.status_code == 409

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.models.audience_import_job import AudienceImportJob
from app.models.audience_import_job_error import AudienceImportJobError
from app.models.audience_member import AudienceMember
from app.models.outbox_event import OutboxEvent
from app.workers.audience_imports import process_import_job_in_session

PASSWORD = "CommonPassword123!"


async def _register_and_login(
    client: AsyncClient, email: str, development_mail_sink
) -> tuple[str, str]:
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "CSV Worker Test User",
        },
    )
    assert registration.status_code == 201, registration.text
    message = development_mail_sink.consume_latest(email, "email-verification")
    assert message is not None and message.token is not None
    verification = await client.post(
        "/api/v1/auth/verify-email",
        json={"token": message.token},
    )
    assert verification.status_code == 200
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    payload = login.json()
    return payload["access_token"], payload["csrf_token"]


async def _create_org(client: AsyncClient, token: str) -> dict:
    response = await client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "CSV Worker Org", "slug": "csv-worker-org"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_import_worker_processes_chunks_and_safe_row_errors(
    async_client,
    test_app,
    development_mail_sink,
    test_db_session,
    tmp_path,
    monkeypatch,
):
    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
        audience_import_storage_dir=tmp_path,
        audience_import_chunk_size=2,
    )
    monkeypatch.setitem(
        test_app.dependency_overrides,
        get_settings,
        lambda: settings,
    )
    token, csrf = await _register_and_login(
        async_client,
        "csv-worker@example.org",
        development_mail_sink,
    )
    organization = await _create_org(async_client, token)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": organization["id"],
        "X-CSRF-Token": csrf,
    }
    csv_content = (
        b"full_name,email,phone,preferred_language,district\n"
        b"Asha Sharma,asha@example.org,,hi,Meerut\n"
        b"Bad Email,not-an-email,,hi,Agra\n"
        b"Rahul Verma,,+919876543210,,Delhi\n"
        b"Bad Phone,,12345,en,Noida\n"
    )
    uploaded = await async_client.post(
        "/api/v1/audiences/imports",
        headers=headers,
        files={"file": ("contacts.csv", csv_content, "text/csv")},
    )
    assert uploaded.status_code == 202, uploaded.text
    job_id = uuid.UUID(uploaded.json()["id"])
    organization_id = uuid.UUID(organization["id"])

    await test_db_session.commit()
    await process_import_job_in_session(
        test_db_session,
        organization_id=organization_id,
        job_id=job_id,
        settings=settings,
    )
    await test_db_session.commit()

    job = await test_db_session.scalar(
        select(AudienceImportJob).where(AudienceImportJob.id == job_id)
    )
    assert job is not None
    assert job.status == "completed_with_errors"
    assert job.total_rows == 4
    assert job.processed_rows == 4
    assert job.imported_rows == 2
    assert job.rejected_rows == 2

    member_count = await test_db_session.scalar(
        select(func.count())
        .select_from(AudienceMember)
        .where(AudienceMember.organization_id == organization_id)
    )
    assert member_count == 2

    errors = list(
        (
            await test_db_session.scalars(
                select(AudienceImportJobError)
                .where(AudienceImportJobError.import_job_id == job_id)
                .order_by(AudienceImportJobError.row_number)
            )
        ).all()
    )
    assert len(errors) == 2
    assert {error.error_code for error in errors} == {
        "invalid_email",
        "invalid_phone",
    }
    assert {error.field_name for error in errors} == {"email", "phone"}

    outbox = await test_db_session.scalar(
        select(OutboxEvent).where(OutboxEvent.aggregate_id == job_id)
    )
    assert outbox is not None and outbox.status == "completed"

    # Re-delivery after completion is a no-op and cannot duplicate contacts.
    await process_import_job_in_session(
        test_db_session,
        organization_id=organization_id,
        job_id=job_id,
        settings=settings,
    )
    await test_db_session.commit()
    member_count_after_replay = await test_db_session.scalar(
        select(func.count())
        .select_from(AudienceMember)
        .where(AudienceMember.organization_id == organization_id)
    )
    assert member_count_after_replay == 2

    status_response = await async_client.get(
        f"/api/v1/audiences/imports/{job_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-ID": organization["id"],
        },
    )
    assert status_response.status_code == 200
    assert status_response.json()["processed_rows"] == 4

    error_response = await async_client.get(
        f"/api/v1/audiences/imports/{job_id}/errors?limit=1",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-ID": organization["id"],
        },
    )
    assert error_response.status_code == 200
    error_payload = error_response.json()
    assert len(error_payload["data"]) == 1
    assert error_payload["pagination"]["has_more"] is True
    assert "not-an-email" not in error_response.text
    assert "12345" not in error_response.text

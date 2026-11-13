import hashlib
import os
import stat
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.db.session import set_tenant_context
from app.main import create_app
from app.models.audience_import_job import AudienceImportJob
from app.models.audience_import_job_error import AudienceImportJobError
from app.models.audience_import_upload import AudienceImportUpload
from app.models.outbox_event import OutboxEvent

PASSWORD = "CommonPassword123!"


async def _register_login(
    client: AsyncClient,
    email: str,
    development_mail_sink,
) -> tuple[str, str]:
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "CSV Upload Test User",
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


async def _create_org(client: AsyncClient, token: str, slug: str) -> dict:
    response = await client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"Import {slug}", "slug": slug},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _tenant_headers(token: str, organization_id: str, csrf: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": organization_id,
        "X-CSRF-Token": csrf,
    }


def _override_upload_settings(
    monkeypatch, directory, application, **overrides
) -> Settings:
    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
        audience_import_storage_dir=directory,
        **overrides,
    )
    monkeypatch.setitem(
        application.dependency_overrides, get_settings, lambda: settings
    )
    return settings


@pytest.mark.asyncio
async def test_csv_upload_is_tenant_scoped_and_stored_privately(
    async_client,
    test_app,
    development_mail_sink,
    test_db_session,
    tmp_path,
    monkeypatch,
):
    _override_upload_settings(monkeypatch, tmp_path, test_app)
    token, csrf = await _register_login(
        async_client, "csv-upload@example.org", development_mail_sink
    )
    organization = await _create_org(async_client, token, "csv-upload-org")
    csv_content = (
        b"full_name,email,phone,preferred_language,district\r\n"
        b"Asha Sharma,asha@example.org,+919876543210,hi,Meerut\r\n"
        b"Rahul Verma,rahul@example.org,,en,Agra\r\n"
    )

    response = await async_client.post(
        "/api/v1/audiences/imports",
        headers=_tenant_headers(token, organization["id"], csrf),
        files={"file": ("../../untrusted-name.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 202, response.text
    payload = response.json()
    upload_id = uuid.UUID(payload["id"])
    stored = await test_db_session.scalar(
        select(AudienceImportUpload).where(AudienceImportUpload.id == upload_id)
    )
    assert stored is not None
    assert stored.organization_id == uuid.UUID(organization["id"])
    assert stored.uploaded_by_id is not None
    assert payload["organization_id"] == organization["id"]
    assert payload["byte_size"] == len(csv_content)
    assert payload["row_count"] == 2
    assert payload["sha256"] == hashlib.sha256(csv_content).hexdigest()
    assert payload["created_at"]
    assert payload["status"] == "queued"
    assert payload["total_rows"] == 2
    assert payload["processed_rows"] == 0
    assert payload["imported_rows"] == 0
    assert payload["error_rows"] == 0

    job_id = uuid.UUID(payload["job_id"])
    job = await test_db_session.scalar(
        select(AudienceImportJob).where(AudienceImportJob.id == job_id)
    )
    assert job is not None
    assert job.organization_id == uuid.UUID(organization["id"])
    assert job.upload_id == upload_id
    assert job.status == "queued"
    assert job.chunk_size == 500

    outbox_event = await test_db_session.scalar(
        select(OutboxEvent).where(
            OutboxEvent.organization_id == uuid.UUID(organization["id"]),
            OutboxEvent.aggregate_id == job_id,
        )
    )
    assert outbox_event is not None
    assert outbox_event.status == "pending"
    assert outbox_event.event_type == "audience_import.queued"

    status_response = await async_client.get(
        f"/api/v1/audiences/imports/{job_id}",
        headers=_tenant_headers(token, organization["id"], csrf),
    )
    assert status_response.status_code == 200, status_response.text
    assert status_response.json()["status"] == "queued"

    errors_response = await async_client.get(
        f"/api/v1/audiences/imports/{job_id}/errors",
        headers=_tenant_headers(token, organization["id"], csrf),
    )
    assert errors_response.status_code == 200, errors_response.text
    assert errors_response.json()["data"] == []
    assert errors_response.json()["pagination"]["has_more"] is False

    stored_path = tmp_path / f"{upload_id.hex}.csv"
    assert stored_path.is_file()
    assert stored_path.read_bytes() == csv_content
    if os.name == "posix":
        assert stat.S_IMODE(stored_path.stat().st_mode) == 0o600


@pytest.mark.asyncio
async def test_csv_upload_rejects_invalid_structure_and_encoding(
    async_client,
    test_app,
    development_mail_sink,
    tmp_path,
    monkeypatch,
):
    _override_upload_settings(monkeypatch, tmp_path, test_app)
    token, csrf = await _register_login(
        async_client, "csv-invalid@example.org", development_mail_sink
    )
    organization = await _create_org(async_client, token, "csv-invalid-org")
    headers = _tenant_headers(token, organization["id"], csrf)
    invalid_files = [
        ("contacts.txt", b"full_name,email\nAsha,asha@example.org\n", "text/csv"),
        ("contacts.csv", b"", "text/csv"),
        ("contacts.csv", b"\xff\xfe", "text/csv"),
        ("contacts.csv", b"name,email\nAsha,asha@example.org\n", "text/csv"),
        (
            "contacts.csv",
            b"full_name,email,email\nAsha,asha@example.org,other@example.org\n",
            "text/csv",
        ),
        (
            "contacts.csv",
            b'full_name,email\n"Unclosed,asha@example.org\n',
            "text/csv",
        ),
        (
            "contacts.csv",
            b"full_name,email\nAsha,asha@example.org,extra\n",
            "text/csv",
        ),
        ("contacts.csv", b"full_name,email\n", "text/csv"),
        (
            "contacts.csv",
            b"full_name,email,unsupported\nAsha,asha@example.org,x\n",
            "text/csv",
        ),
        (
            "contacts.csv",
            b"full_name,email\nAsha,asha@example.org\n",
            "application/pdf",
        ),
    ]

    for filename, content, media_type in invalid_files:
        response = await async_client.post(
            "/api/v1/audiences/imports",
            headers=headers,
            files={"file": (filename, content, media_type)},
        )
        assert response.status_code in {422, 415}, (
            filename,
            media_type,
            response.status_code,
            response.text,
        )


@pytest.mark.asyncio
async def test_csv_upload_enforces_file_and_row_limits(
    async_client,
    test_app,
    development_mail_sink,
    tmp_path,
    monkeypatch,
):
    _override_upload_settings(
        monkeypatch,
        tmp_path,
        test_app,
        audience_import_max_bytes=20,
        audience_import_max_rows=1,
    )
    token, csrf = await _register_login(
        async_client, "csv-limits@example.org", development_mail_sink
    )
    organization = await _create_org(async_client, token, "csv-limits-org")
    headers = _tenant_headers(token, organization["id"], csrf)

    too_large = await async_client.post(
        "/api/v1/audiences/imports",
        headers=headers,
        files={
            "file": (
                "contacts.csv",
                b"full_name,email\nAsha,asha@example.org\n",
                "text/csv",
            )
        },
    )
    assert too_large.status_code == 413

    row_limited_settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
        audience_import_storage_dir=tmp_path,
        audience_import_max_bytes=1024,
        audience_import_max_rows=1,
    )
    monkeypatch.setitem(
        test_app.dependency_overrides,
        get_settings,
        lambda: row_limited_settings,
    )
    too_many_rows = await async_client.post(
        "/api/v1/audiences/imports",
        headers=headers,
        files={
            "file": (
                "contacts.csv",
                (b"full_name,email\nAsha,asha@example.org\nRahul,rahul@example.org\n"),
                "text/csv",
            )
        },
    )
    assert too_many_rows.status_code == 413


@pytest.mark.asyncio
async def test_csv_upload_rejects_cross_tenant_request(
    async_client,
    test_app,
    development_mail_sink,
    tmp_path,
    monkeypatch,
):
    _override_upload_settings(monkeypatch, tmp_path, test_app)
    token_a, _ = await _register_login(
        async_client, "csv-tenant-a@example.org", development_mail_sink
    )
    token_b, csrf_b = await _register_login(
        async_client, "csv-tenant-b@example.org", development_mail_sink
    )
    organization_a = await _create_org(async_client, token_a, "csv-tenant-a-org")

    response = await async_client.post(
        "/api/v1/audiences/imports",
        headers=_tenant_headers(token_b, organization_a["id"], csrf_b),
        files={
            "file": (
                "contacts.csv",
                b"full_name,email\nAsha,asha@example.org\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 403
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_upload_body_limit_applies_to_chunked_multipart_requests():
    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
        audience_import_max_bytes=16,
    )
    limited_app = create_app(settings)
    transport = ASGITransport(app=limited_app)
    boundary = "sandeshvani-test-boundary"
    body = (
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="contacts.csv"\r\n'
            "Content-Type: text/csv\r\n\r\n"
        ).encode()
        + (b"x" * 70_000)
        + f"\r\n--{boundary}--\r\n".encode()
    )

    async def body_stream():
        yield body[:4096]
        yield body[4096:]

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Origin": "http://localhost:5173"},
    ) as client:
        response = await client.post(
            "/api/v1/audiences/imports",
            content=body_stream(),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_import_error_cursor_paginates_multiple_issues_on_same_row(
    async_client,
    test_app,
    development_mail_sink,
    test_db_session,
    tmp_path,
    monkeypatch,
):
    _override_upload_settings(monkeypatch, tmp_path, test_app)
    token, csrf = await _register_login(
        async_client, "csv-errors-cursor@example.org", development_mail_sink
    )
    organization = await _create_org(async_client, token, "csv-errors-cursor-org")
    organization_id = uuid.UUID(organization["id"])
    upload = await async_client.post(
        "/api/v1/audiences/imports",
        headers=_tenant_headers(token, organization["id"], csrf),
        files={
            "file": (
                "contacts.csv",
                b"full_name,email\nAsha,asha@example.org\n",
                "text/csv",
            )
        },
    )
    assert upload.status_code == 202, upload.text
    job_id = uuid.UUID(upload.json()["job_id"])

    await set_tenant_context(test_db_session, organization_id)
    test_db_session.add_all(
        [
            AudienceImportJobError(
                id=uuid.UUID(int=1),
                organization_id=organization_id,
                job_id=job_id,
                row_number=2,
                field_name="email",
                error_code="INVALID_EMAIL",
            ),
            AudienceImportJobError(
                id=uuid.UUID(int=2),
                organization_id=organization_id,
                job_id=job_id,
                row_number=2,
                field_name="preferred_language",
                error_code="UNSUPPORTED_LANGUAGE",
            ),
            AudienceImportJobError(
                id=uuid.UUID(int=3),
                organization_id=organization_id,
                job_id=job_id,
                row_number=3,
                field_name="phone",
                error_code="INVALID_PHONE",
            ),
        ]
    )
    await test_db_session.commit()

    first = await async_client.get(
        f"/api/v1/audiences/imports/{job_id}/errors",
        headers=_tenant_headers(token, organization["id"], csrf),
        params={"limit": 1},
    )
    assert first.status_code == 200, first.text
    first_payload = first.json()
    assert [
        (item["row_number"], item["field_name"], item["error_code"])
        for item in first_payload["data"]
    ] == [(2, "email", "INVALID_EMAIL")]
    cursor = first_payload["pagination"]["next_cursor"]
    assert cursor is not None

    second = await async_client.get(
        f"/api/v1/audiences/imports/{job_id}/errors",
        headers=_tenant_headers(token, organization["id"], csrf),
        params={"limit": 1, "cursor": cursor},
    )
    assert second.status_code == 200, second.text
    second_payload = second.json()
    assert [
        (item["row_number"], item["field_name"], item["error_code"])
        for item in second_payload["data"]
    ] == [(2, "preferred_language", "UNSUPPORTED_LANGUAGE")]
    next_cursor = second_payload["pagination"]["next_cursor"]
    assert next_cursor is not None

    third = await async_client.get(
        f"/api/v1/audiences/imports/{job_id}/errors",
        headers=_tenant_headers(token, organization["id"], csrf),
        params={"limit": 1, "cursor": next_cursor},
    )
    assert third.status_code == 200, third.text
    third_payload = third.json()
    assert [
        (item["row_number"], item["field_name"], item["error_code"])
        for item in third_payload["data"]
    ] == [(3, "phone", "INVALID_PHONE")]
    assert third_payload["pagination"]["has_more"] is False
    assert third_payload["pagination"]["next_cursor"] is None

    malformed = await async_client.get(
        f"/api/v1/audiences/imports/{job_id}/errors",
        headers=_tenant_headers(token, organization["id"], csrf),
        params={"cursor": "not-a-valid-cursor"},
    )
    assert malformed.status_code == 422

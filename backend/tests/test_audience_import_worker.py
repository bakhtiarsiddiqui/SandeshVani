import hashlib
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.audience_import_job import AudienceImportJob
from app.models.audience_import_job_error import AudienceImportJobError
from app.models.audience_import_upload import AudienceImportUpload
from app.models.audience_member import AudienceMember
from app.models.base import Base
from app.models.organization import Organization
from app.models.user import User
from app.workers.audience_import_worker import AudienceImportWorker


def _create_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _seed_job(session_factory, storage_dir, content, *, chunk_size=2, digest=None):
    organization_id = uuid.uuid4()
    user_id = uuid.uuid4()
    upload_id = uuid.uuid4()
    job_id = uuid.uuid4()
    with session_factory.begin() as session:
        session.add(
            Organization(
                id=organization_id,
                name="Import Test",
                slug=f"import-{organization_id.hex[:10]}",
                status="active",
            )
        )
        session.add(
            User(
                id=user_id,
                email=f"{user_id.hex}@example.org",
                normalized_email=f"{user_id.hex}@example.org",
                password_hash="test-hash",
                full_name="Import Actor",
                status="active",
            )
        )
        session.flush()
        session.add(
            AudienceImportUpload(
                id=upload_id,
                organization_id=organization_id,
                uploaded_by_id=user_id,
                byte_size=len(content),
                row_count=4,
                sha256=digest or hashlib.sha256(content).hexdigest(),
            )
        )
        session.add(
            AudienceImportJob(
                id=job_id,
                organization_id=organization_id,
                upload_id=upload_id,
                uploaded_by_id=user_id,
                status="queued",
                total_rows=4,
                processed_rows=0,
                imported_rows=0,
                error_rows=0,
                chunk_size=chunk_size,
            )
        )

    (storage_dir / f"{upload_id.hex}.csv").write_bytes(content)
    return organization_id, upload_id, job_id


@pytest.fixture
def import_db(tmp_path):
    engine, session_factory = _create_database()
    yield engine, session_factory, tmp_path
    engine.dispose()


def test_worker_processes_bounded_chunks_and_records_safe_row_errors(import_db):
    _, session_factory, storage_dir = import_db
    content = (
        b"full_name,email,phone,preferred_language,district,state_code,city\n"
        b"Asha Sharma,ASHA@example.org,,hi,Meerut,up,Meerut\n"
        b"Broken Input,not-an-email,,fr,Agra,up,Agra\n"
        b"No Contact,,,,Agra,up,Agra\n"
        b"Rahul Verma,,+919876543210,en,Agra,up,Agra\n"
    )
    organization_id, _, job_id = _seed_job(
        session_factory, storage_dir, content, chunk_size=2
    )
    worker = AudienceImportWorker(session_factory, storage_dir, lease_seconds=30)

    result = worker.process(job_id, organization_id)

    assert result == {"status": "completed_with_errors", "processed_rows": 4}
    with session_factory() as session:
        job = session.get(AudienceImportJob, job_id)
        members = list(
            session.scalars(
                select(AudienceMember).where(
                    AudienceMember.organization_id == organization_id
                )
            )
        )
        errors = list(
            session.scalars(
                select(AudienceImportJobError)
                .where(AudienceImportJobError.organization_id == organization_id)
                .order_by(
                    AudienceImportJobError.row_number,
                    AudienceImportJobError.field_name,
                )
            )
        )

    assert job.status == "completed_with_errors"
    assert job.processed_rows == 4
    assert job.imported_rows == 2
    assert job.error_rows == 2
    assert len(members) == 2
    assert {member.email for member in members if member.email} == {"asha@example.org"}
    asha = next(member for member in members if member.email == "asha@example.org")
    assert asha.state_code == "UP"
    assert asha.city == "Meerut"
    assert {member.phone for member in members if member.phone} == {"+919876543210"}
    assert [
        (error.row_number, error.field_name, error.error_code) for error in errors
    ] == [
        (3, "email", "INVALID_EMAIL"),
        (3, "preferred_language", "UNSUPPORTED_LANGUAGE"),
        (4, None, "CONTACT_POINT_REQUIRED"),
    ]
    error_text = str([(error.field_name, error.error_code) for error in errors])
    assert "not-an-email" not in error_text
    assert "No Contact" not in error_text

    # Repeated delivery after completion must not insert the contacts again.
    assert worker.process(job_id, organization_id) == {"status": "not_claimed"}
    with session_factory() as session:
        members_after_redelivery = list(
            session.scalars(
                select(AudienceMember).where(
                    AudienceMember.organization_id == organization_id
                )
            )
        )
    assert len(members_after_redelivery) == 2


def test_worker_fails_closed_when_private_upload_checksum_changes(import_db):
    _, session_factory, storage_dir = import_db
    original = b"full_name,email\nAsha,asha@example.org\n"
    organization_id, upload_id, job_id = _seed_job(
        session_factory, storage_dir, original, chunk_size=1
    )
    (storage_dir / f"{upload_id.hex}.csv").write_bytes(
        b"full_name,email\nMallory,mallory@example.org\n"
    )

    worker = AudienceImportWorker(session_factory, storage_dir)
    result = worker.process(job_id, organization_id)

    assert result == {"status": "failed", "error_code": "UPLOAD_CHECKSUM_MISMATCH"}
    with session_factory() as session:
        job = session.get(AudienceImportJob, job_id)
        members = list(session.scalars(select(AudienceMember)))
    assert job.status == "failed"
    assert job.last_error_code == "UPLOAD_CHECKSUM_MISMATCH"
    assert members == []

# Agent — Backend Engineer

**Mission:** implement FastAPI behaviour while preserving modularity, tenant isolation and domain invariants.

## Required context
Read root `AGENTS.md`, docs index/status/decision register, then the relevant API, data-model and security documents. Inspect current routes, schemas, services, models, migrations and tests before editing.

## Responsibilities
- Keep `/api/v1` route handlers thin; put business rules in services/domain modules.
- Use Pydantic API schemas, SQLAlchemy 2.x and tenant-aware repositories.
- Preserve validation, bounded pagination and consistent error semantics.
- Update generated OpenAPI/contract inventory for route/schema changes.
- Add unit and integration tests, including PostgreSQL/RLS tests for tenant-owned changes.
- For every tenant table, define `organization_id`, RLS, transaction-local context, non-owner runtime privileges and tenant-safe relationships.
- Preserve the MVP mock-only boundary.

## Must not
- Invent endpoints from the planning API inventory or frontend props.
- Query tenant tables without verified tenant context or bypass RLS.
- Treat upload acceptance as completed import processing.
- Introduce Celery/Redis until the AUD-03 design is selected and approved.
- Add live provider SDKs, credentials, endpoints or dispatch.
- Store raw tokens, secrets, CSV values or unnecessary PII in logs/errors.

## Deliver
Code, migrations, tests, OpenAPI updates, setup/documentation notes, exact commands/results, tenant/security implications and remaining risks.

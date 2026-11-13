# Agent — Data / Infrastructure Engineer

**Mission:** provide safe PostgreSQL, Alembic, RLS and reproducible infrastructure foundations.

## Required context
Read root \`AGENTS.md\`, docs index/status/decision register, then the data model, threat model, security review gates and backend setup docs relevant to the task.

## Responsibilities
- Preserve SQLAlchemy 2.x and Alembic migration discipline.
- Tenant-owned tables require forced RLS, transaction-local tenant context, tenant-safe constraints and a runtime DB role that is not table owner and has no \`BYPASSRLS\`.
- Test both runtime role and owner-role RLS behaviour using an isolated disposable PostgreSQL database.
- Treat PostgreSQL as source of truth; Celery/Redis is selected target transport, not current main implementation.
- Before integrating AUD-03, reconcile PR #18/#19 schema and migration differences; maintain one canonical revision path, unique IDs, ownership/grants, RLS and recovery semantics.
- Add health checks and safe environment examples when local infrastructure is actually introduced.

## Must not
- Treat Redis/Celery or Docker Compose as already operational on main.
- Use superuser/owner credentials as application runtime.
- Commit secrets or production data.
- Run destructive migration/reset commands against shared/production databases.
- Create uncoordinated migrations or rewrite applied history.
- Introduce Kubernetes/Kafka or broad infrastructure not justified by requirements.

## Deliver
Migration(s), RLS/role tests, environment/setup changes, upgrade/downgrade evidence, operational caveats and exact verification results.

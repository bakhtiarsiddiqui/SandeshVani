# Agent 4 — Data / Infrastructure Engineer

Mission: provide reproducible local infrastructure and safe database/worker foundations.

- Configure PostgreSQL, Redis, Celery and Docker Compose.
- Implement SQLAlchemy 2.x persistence and Alembic migrations when assigned.
- Preserve tenant-safe relationships, composite foreign keys and RLS.
- Runtime application DB role must not own tenant tables or have BYPASSRLS.
- Test RLS using the actual non-owner application role.
- PostgreSQL is authoritative for outbox; Redis/Celery is transport/execution.
- Add health checks, environment examples, safe local scripts and setup docs.

Must not: use owner/superuser as runtime role, commit secrets, create destructive shared/production reset scripts, introduce Kubernetes/Kafka or uncoordinated schema changes.

Deliver configs, migrations, role/policy tests, setup docs and exact verification results.

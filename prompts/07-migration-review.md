# PostgreSQL / Alembic migration review

Read root `AGENTS.md`, `agents/data-infrastructure.md` and `agents/qa-security.md`.

Migration [revision/path]; models [paths]; affected tenant tables [list].

Check upgrade/downgrade, backfill safety, locking, nullability/defaults, uniqueness, composite tenant-safe FKs, indexes, RLS policies, runtime role grants, no historical migration rewrite and tenant data integrity. Run against disposable DB. Report risks and exact commands/results. Human approval is mandatory before merge.

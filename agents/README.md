# Specialist agent instructions

Every agent reads root `AGENTS.md` first. These files add role-specific responsibilities and never override project-wide rules.
- `architect.md`: plans, contracts and ADR proposals.
- `backend.md`: FastAPI/domain implementation.
- `frontend.md`: React UI.
- `data-infrastructure.md`: PostgreSQL, Alembic, Celery, Redis and Docker.
- `qa-security.md`: independent tests and security verification.
- `integration-reviewer.md`: cross-component integration and PR review.

One tool may perform multiple roles in separate tasks. Role boundaries matter more than product names.

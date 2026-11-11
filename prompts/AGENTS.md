# AGENTS.md — SandeshVani

Mandatory instructions for every coding agent. Read before editing. If a task conflicts with this file or an approved ADR, stop and ask the human owner.

## Product
SandeshVani (संदेशवाणी) is a multi-tenant public-awareness and institutional communication platform. Tagline: “Har zaroori baat, har zaroori insaan tak.” `sandeshvani.in` is selected/intended only; do not claim registration or legal clearance. CivicReach is historical codename only.

## Approved architecture — do not change without approval
- Modular monolith + separate Celery workers.
- React + JavaScript + Vite + Tailwind CSS + DaisyUI. JavaScript is intentional; no TypeScript migration without approval.
- FastAPI/Python; PostgreSQL; SQLAlchemy 2.x + Alembic; Celery + Redis; Docker Compose.
- REST JSON under `/api/v1`; OpenAPI is the API contract source.
- Multi-tenancy: organization_id on tenant-owned rows; tenant-scoped repository/service queries; PostgreSQL RLS with transaction-local tenant context; composite tenant-safe foreign keys.
- Application DB role must not own tenant tables and must not have BYPASSRLS.
- PostgreSQL is authoritative for transactional outbox; Redis/Celery is transport/execution infrastructure.
- Approved campaign versions are immutable; approval binds to a specific version/hash.
- Consent is channel- and purpose-specific; missing consent is not permission.
- Jobs/webhooks are idempotent; bounded backoff; unknown outcomes explicitly represented.

## MVP scope lock
Release 1: identity, organizations, memberships, multi-role RBAC, tenant isolation, audiences/imports/segments/consent, templates/campaign versioning, English/Hindi variants, approvals/audit, four mock channels and basic analytics.
MVP channels are `mock_all`: mock Email, SMS, WhatsApp and Push only. No provider SDKs, credentials or real dispatch paths.
MVP languages are English (`en`) and Hindi (`hi`), with extensible registry. Do not imply all Indic languages have complete MVP support.
Membership roles are multiple via `membership_roles`; do not collapse to a single membership role.
Release 2 (not MVP): AI content/translation assistance, human translation review, quality checks, personalization.
Release 3 (not MVP): real providers, scheduling, feedback, engagement and advanced analytics.
Do not introduce Kafka, Kubernetes, microservices, advanced ML targeting or AI-based approval/dispatch in MVP.

## Security and correctness
- Never bypass tenant-aware repository/service patterns or RLS.
- Enforce authorization server-side; frontend visibility is not authorization.
- Test RLS with the actual non-owner application DB role; runtime role must not own tables or have BYPASSRLS.
- Use composite tenant-safe FKs where needed.
- Missing consent is not opt-in.
- Never mutate approved campaign versions; create a new version and require approval again.
- Bind approval to immutable version identity/hash.
- Use durable idempotency/deduplication for jobs and webhook-like inputs.
- Never commit secrets, tokens, personal data or production data.
- Do not weaken controls to make tests pass.
- No real dispatch adapter or live send path in MVP.

## Engineering conventions
- Keep route handlers thin; business logic in domain/services.
- Use Pydantic at API boundaries and SQLAlchemy 2.x for persistence.
- Use Alembic; never edit an already-applied migration to rewrite history.
- Use explicit transaction boundaries and UTC persisted timestamps.
- Validate inputs and return consistent errors.
- Test success, invalid, unauthorized, cross-tenant, retry and idempotency cases as applicable.
- Avoid unrelated rewrites and unnecessary dependencies.
- Update OpenAPI/contracts and docs when API behaviour changes.
- Use environment variables; commit placeholders only in `.env.example`.

## Agent operating rules
- Work only on assigned issue and branch/worktree.
- Inspect code first; report assumptions, dependencies and planned files before edits.
- Do not invent product decisions. Stop on blocking ambiguity.
- Do not modify architecture, ADRs, security invariants or MVP scope without explicit human approval.
- Do not merge, force-push, delete branches, change repository settings, deploy or access production unless specifically authorised.
- Never run destructive DB commands against shared/production environments.
- Do not overwrite another agent's work; use isolated branches/worktrees.
- Never claim tests passed unless executed; report exact commands/results.
- Open a PR or provide a patch; do not self-approve or merge.

## Definition of Done
1. Acceptance criteria met.
2. Diff limited to task scope.
3. Relevant tests added/updated.
4. Checks run and exact results reported; unrun checks disclosed.
5. Contracts/docs updated where applicable.
6. Security and tenant implications described.
7. Limitations/follow-up recorded.
8. PR ready for human review.

## Required final report
Summary; files changed; decisions/assumptions; exact tests and outcomes; security/tenant considerations; migration impact; limitations; branch/PR reference.
# SandeshVani — Agent Instructions

## Project
SandeshVani is a multi-tenant communication platform. Follow the current five-day Milestone 1 plan in `MILESTONE.md`.

## Stack
- Frontend: React, JavaScript, Vite, Tailwind CSS, DaisyUI
- Backend: FastAPI, SQLAlchemy async, Pydantic Settings
- Database: PostgreSQL, Alembic
- Tests/lint: pytest, Ruff

## Rules
1. Inspect existing code before implementing anything. Reuse working code and free tools; do not rebuild standard functionality unnecessarily.
2. Work on one milestone task at a time.
3. Preserve the existing architecture and UI unless a change is necessary.
4. Preserve tenant isolation, RBAC, PostgreSQL RLS and database integrity.
5. Never expose secrets or copy credentials into documentation.
6. Never drop/reset the development database.
7. Never stage, commit, reset or stash Git changes unless explicitly authorized.
8. Never rewrite existing migrations 0001 or 0002. Create a new migration for subsequent schema changes.
9. Do not overwrite or discard existing uncommitted changes.
10. Do not claim completion without test evidence.
11. Use exact repository paths and existing project commands.
12. After each task, update `HANDOFF.md` with verified results and the next action.

## Workflow
Read `HANDOFF.md` and `MILESTONE.md`, inspect `git status --short`, then inspect only the files relevant to the task. Make the smallest safe change, run targeted tests, and report files changed, commands, results and remaining issues.
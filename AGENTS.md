# SandeshVani — Repository Agent Instructions

**Status:** Authoritative repository-wide instructions  
**Baseline reviewed:** 2026-11-13, `main` at `c88e270add18c6b0a4259fa5dbb310afa69534e7`  
**Product owner:** Human owner; agents do not infer approval from these instructions.

## 1. Mandatory reading order

At the start of every task, read these in order:

1. `AGENTS.md` — repository-wide rules (this file).
2. `docs/README.md` — documentation authority, navigation and deprecation policy.
3. `docs/PROJECT_STATUS.md` — verified implementation snapshot and current priorities.
4. `docs/decision-register.md` — decisions and their implementation status.
5. Only then read the specific requirement, architecture, API, security, workflow or design documents relevant to the task.
6. Inspect the actual source code and tests that own the requested behaviour before editing.

Do not start by reading every document or recursively scanning the repository. Use the index and task scope to keep inspection targeted.

## 2. Source-of-truth and conflict resolution

Use this precedence:

1. Explicit, current instruction from the human owner for the task.
2. This root `AGENTS.md` for repository-wide operating and safety rules.
3. `docs/README.md` and `docs/PROJECT_STATUS.md` for documentation authority and the dated implementation snapshot.
4. Approved decisions in `docs/decision-register.md` and explicitly approved ADRs, where present.
5. Product requirements and current implementation/acceptance documents.
6. Actual source code, migrations, generated OpenAPI, tests and CI evidence for claims about what is implemented and works.
7. Historical handoffs, milestones, prompt packs and execution ledgers only as archival evidence.

**Important:** A planning document is not proof of implementation. A source file is not proof that its behaviour is tested. A passing test recorded in an old ledger is not proof that the current branch still passes. When sources disagree, do not guess, silently reconcile, or invent an endpoint/model. Record the discrepancy and ask the human owner when a product/security decision is required.

## 3. Current product and MVP boundary

SandeshVani (संदेशवाणी) is a multi-tenant institutional/public-awareness communication platform. The selected working domain is `sandeshvani.in`; registration, trademark and legal clearance are not asserted. CivicReach is a historical codename only.

The intended MVP is a governed workflow: identity and organization access; audience management; consent/suppression; segmentation; campaign and template versioning; human approval; mock-only distribution; auditability and basic analytics.

The current implementation is materially earlier than that complete MVP. See `docs/PROJECT_STATUS.md`. Do not build later-stage capabilities merely because the PRD, UI specification or architecture diagram describes them.

**Hard MVP safety boundaries:**
- No real Email/SMS/WhatsApp/Push dispatch, production provider credentials, SDKs or outbound provider endpoints.
- No AI approval, AI dispatch, autonomous targeting or autonomous sending.
- No Kafka, Kubernetes, microservices, multi-region active-active or advanced data warehouse without an approved change decision.
- No campaign, approval, consent, segment, delivery or analytics endpoint may be invented by the frontend or an agent.

## 4. Technology baseline

### Implemented in the reviewed repository snapshot
- Frontend: React + JavaScript + Vite.
- Styling: Tailwind CSS 3 + DaisyUI 4.
- API client: Axios.
- Visual identity: Gunmetal Blue / Warm Concrete / Saffron Gold; Mukta font (Latin and Devanagari).
- Three.js is present only for a decorative sign-in background scene; keep it isolated and nonessential to authentication.
- Backend: Python + FastAPI + Pydantic.
- Persistence: PostgreSQL + SQLAlchemy 2.x + Alembic.
- Authentication/tenant foundations and audience CRUD/upload code are present on `main`.

### Selected target architecture, not yet fully integrated
- Celery + Redis for bounded background processing.
- PostgreSQL transactional outbox as source of truth for future asynchronous jobs.
- Docker Compose as the intended local multi-service environment; a root Compose file is not present in the reviewed tree.

Do not describe Celery/Redis workers, outbox processing or Compose orchestration as implemented on `main` unless current code and tests demonstrate it. Do not add React Router, Recharts, React Hook Form, Zod, shadcn/ui, Flowbite or another library based on old proposal lists; check the current package manifests and obtain approval before adding dependencies.

JavaScript is intentional. Do not migrate to TypeScript or upgrade major framework/toolchain versions without explicit approval.

## 5. Architecture and security invariants

- Preserve the modular-monolith boundary; modules are not independent deployable services.
- Resolve tenant context from authenticated membership and active organization. A client-supplied organization identifier is a selector, never authorization evidence.
- Keep tenant-owned reads/writes explicitly scoped and preserve PostgreSQL RLS and transaction-local tenant context.
- Runtime DB role must not own tenant tables and must not have `BYPASSRLS`.
- Preserve tenant-safe composite foreign keys and test cross-tenant relationships.
- Authorization is server-side. Frontend visibility/route guards are not security controls.
- Keep auth cookies, CSRF/origin checks, key/secret validation, token rotation and revocation semantics intact.
- Do not weaken or skip security tests to make a change pass.
- Missing/unknown consent is not permission where consent is required.
- Approved campaign versions must be immutable; approval binds to the exact version/hash.
- Future workers must establish and validate tenant context, re-check current state and be idempotent.
- No real-provider dispatch path in MVP.

## 6. Engineering workflow

1. Inspect current branch, worktree, recent commits and the relevant source/tests/docs. Preserve existing user changes.
2. State a concise plan for substantial tasks. Identify exact files, dependencies and acceptance criteria.
3. Prefer the smallest complete vertical slice. Reuse existing patterns and avoid speculative abstraction or unnecessary dependencies.
4. Stabilise API, schema, event and permission contracts before parallel frontend/backend work.
5. Add/update focused tests. Include invalid, unauthorized, cross-tenant and failure/retry cases where relevant.
6. Run exact, relevant checks. Report passed, failed, skipped, timed out and not run separately. Never claim unobserved test results.
7. Update affected docs and status records in the same change. Do not mark tasks complete without implementation and verification evidence.
8. Inspect the complete diff for regressions, secrets, PII, generated files and unrelated changes. Run `git diff --check`.

## 7. Git, migration and approval boundaries

- Work on an assigned issue and isolated branch/worktree. Do not overwrite another agent's changes.
- Never run destructive database commands against shared or production data. Use a dedicated disposable PostgreSQL database for migration/RLS tests.
- Never rewrite an applied migration. Add a new migration and verify upgrade/downgrade where safe.
- Do not stage, commit, push, create/update a PR, merge, force-push, delete branches, change repository settings, deploy or mutate external services without explicit authorization for that action.
- Architecture changes, new major dependencies, auth/RLS/RBAC/consent/approval changes, sensitive migrations and real-provider boundaries require human review.
- Preserve evidence and history. Deprecate old docs with a notice; do not silently delete useful historical records.

## 8. Completion report

Report the objective, exact files changed, decisions and assumptions, tests/commands and outcomes, security/tenant implications, migration impact, residual risks, and Git/branch/PR state. Clearly identify any work that remains only proposed or unverified.

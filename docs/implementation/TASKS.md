# SandeshVani — implementation task tracker

**Status date:** 2026-11-13  
**Baseline:** reviewed `main` at `c88e270add18c6b0a4259fa5dbb310afa69534e7`.

This tracker replaces the older all-unchecked list. Status is based on merged code/PRs and execution ledgers observed in the reviewed snapshot. It is not a substitute for GitHub issue tracking. A task is complete only when implementation and relevant verification evidence exist.

Legend: **DONE** = present/merged with recorded evidence; **PARTIAL** = implemented slice only; **NEXT** = immediate priority; **OPEN** = not implemented or decision pending; **DEFERRED** = later release.

## Foundations

| ID | Task | Status | Evidence / note |
|---|---|---|---|
| INF-01 | Repository structure, PR templates and GitHub workflows | DONE | Root tree contains repository, templates and CI/security workflows. |
| INF-02 | React + JavaScript + Vite bootstrap | DONE | Frontend package and source present. |
| INF-03 | Tailwind + DaisyUI baseline | DONE | Tailwind 3 / DaisyUI 4 on main. |
| INF-04 | FastAPI app and health route | DONE | Backend entry point and health router present. |
| INF-05 | PostgreSQL, SQLAlchemy and Alembic | DONE | Migrations 0001–0005 present. |
| INF-06 | Docker Compose multi-service environment | OPEN | Root Compose file absent from reviewed main. |
| INF-07 | Environment examples and secret boundaries | DONE | Root/backend/frontend examples present; verify environment-specific configuration before deployment. |
| INF-08 | CI, frontend/backend checks and secret scan | DONE | GitHub Actions workflows present; check latest run for current status. |

## Identity, organization and tenant security

| ID | Task | Status | Evidence / note |
|---|---|---|---|
| AUTH-01 | Registration, verification, login | DONE | Auth route/service/tests present. |
| AUTH-02 | Refresh rotation, logout and revocation | DONE | P0.4 ledger and migration 0003. |
| AUTH-03 | Recovery/reset and abuse controls | DONE | Auth routes and P0.1/P0.2 records; preserve documented residual timing/process-local limiter risks. |
| ORG-01 | Organization creation/list/detail/current context | DONE | Organization routes/services present. Invitation/onboarding policy remains open. |
| ORG-02 | Membership and organization switching | DONE | Auth select-org and organization/member routes present. |
| RBAC-01 | Roles/permissions and multiple roles per membership | DONE | Membership role association and role APIs present. |
| RBAC-02 | Tenant context, RLS and tenant-safe relationships | DONE | Migrations 0001/0002 and P0.3 ledger. Extend with every new tenant table. |
| RBAC-03 | Refresh/session lifecycle and production security config | DONE | P0.2/P0.4 ledgers. Production secrets/origins still require deployment provisioning. |

## Audience and consent

| ID | Task | Status | Evidence / note |
|---|---|---|---|
| AUD-01 | Tenant-scoped audience CRUD | DONE | Merged PR #16. |
| AUD-02 | CSV file validation and private storage | DONE | Merged PR #17; upload only, not contact processing. |
| AUD-03 | Durable async CSV import jobs, worker and error/progress APIs | NEXT | Competing drafts #18/#19. Select one canonical design; review migration/RLS/ownership, leases/idempotency/outbox and configured runtime tests before merge. |
| AUD-04 | Duplicate identity policy and conflict handling | OPEN | Define matching keys, normalization, ambiguous records and re-import semantics first. |
| CONS-01 | Consent history by channel/purpose | OPEN | Define source/evidence, notice version, withdrawal and legal basis. |
| CONS-02 | Suppression model and execution-time checks | OPEN | Fail closed where consent is required; do not treat missing consent as opt-in. |
| AUD-05 | Allowlisted segments and eligibility preview | OPEN | Typed filter grammar only; never raw SQL. |
| AUD-06 | Permissioned, formula-safe exports | OPEN | Requires permission/audit/retention design. |
| QA-02 | Audience/import/consent security and recovery tests | OPEN | Add tests with AUD-03 and later consent/segment slices. |

## Campaign and localization

| ID | Task | Status | Evidence / note |
|---|---|---|---|
| CMP-01 | Campaign CRUD and backend state machine | OPEN | No campaign routes/models on reviewed main. |
| CMP-02 | Immutable campaign versions and content hash | OPEN | Must precede approval. |
| CMP-03 | Segment association and eligibility preview | OPEN | Depends on AUD-05 and CONS rules. |
| TMP-01 | Template and immutable template versions | OPEN | Not implemented. |
| TMP-02 | Placeholder validation and channel constraints | OPEN | Not implemented. |
| LOC-01 | Language registry for English/Hindi | OPEN | Audience field accepts en/hi; campaign-language registry not implemented. |
| LOC-02 | Versioned channel/language content variants | OPEN | Not implemented. |
| LOC-03 | Four-channel preview and payload validation | OPEN | Not implemented. |

## Approval and audit

| ID | Task | Status | Evidence / note |
|---|---|---|---|
| APR-01 | Approval bound to immutable version/hash | OPEN | Not implemented. |
| APR-02 | Review queue and authorization | OPEN | Dashboard queue is sample-only; no approval API exists. |
| APR-03 | Separation-of-duties policy | OPEN | Human product/security decision required. |
| APR-04 | Rejection rationale and immutable decision history | OPEN | Not implemented. |
| AUDIT-01 | Append-oriented audit event model | OPEN | Not implemented as a dedicated audit stream. |
| AUDIT-02 | Role/campaign/approval audit coverage | OPEN | Not implemented. |

## Mock distribution

| ID | Task | Status | Evidence / note |
|---|---|---|---|
| DIST-01 | Provider-independent adapter contract | OPEN | No distribution module on main. |
| DIST-02 | Mock Email adapter | OPEN | No adapter on main. |
| DIST-03 | Mock SMS adapter | OPEN | No adapter on main. |
| DIST-04 | Mock WhatsApp adapter | OPEN | No adapter on main. |
| DIST-05 | Mock Push adapter | OPEN | No adapter on main. |
| DIST-06 | Execution and recipient snapshot model | OPEN | Not implemented. |
| DIST-07 | Channel delivery and attempt records | OPEN | Not implemented. |
| DIST-08 | PostgreSQL transactional outbox | OPEN | Appears only in AUD-03 proposals, not merged. |
| DIST-09 | Celery/Redis bounded workers | OPEN | Selected target; not installed/integrated on main. |
| DIST-10 | Idempotency, retries, exhausted work and unknown outcome | OPEN | Not implemented. |
| DIST-11 | Pause/cancel and current-state checks | OPEN | Not implemented. |

## Analytics, reliability and deferred releases

| ID | Task | Status | Evidence / note |
|---|---|---|---|
| AN-01 | Define campaign/channel metric semantics | OPEN | No live analytics API/data. |
| AN-02 | Tenant-scoped analytics dashboard | OPEN | Current Overview is demonstration data. |
| OBS-01 | Structured logs, request IDs and error monitoring | PARTIAL | Logging/request-ID foundations exist; monitoring choice/integration needs review. |
| OPS-01 | Backup/restore exercise and RPO/RTO | OPEN | Targets and runbook not evidenced. |
| PERF-01 | 100k import workload test | OPEN | No import worker on main. |
| PERF-02 | 100k recipient snapshot test | OPEN | No snapshot module. |
| PERF-03 | 100k mock-delivery throughput/recovery test | OPEN | No distribution module. |
| DOC-01 | Keep docs aligned with verified implementation | IN PROGRESS | This documentation baseline migration; continue updating with each feature. |
| DEMO-01 | Reproducible mock-only end-to-end demonstration | OPEN | Depends on stages above. |
| AI-01–05 | AI drafting/translation evaluation and assistance | DEFERRED | Release 2; no AI provider decision or implementation. |
| LIVE-01–06 | Real providers, webhooks, scheduling and engagement | DEFERRED | Release 3; separate legal/security/operational gate required. |

## Definition of done

A task is complete only when acceptance criteria are met, migration and tenant constraints are correct, authorization and state transitions are enforced, relevant tests pass, API/OpenAPI and docs are updated, logs exclude secrets/PII, and residual risks are recorded. "UI present", "endpoint listed in docs" and "draft PR exists" are not completion evidence.

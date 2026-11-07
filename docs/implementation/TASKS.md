# SandeshVani — Ordered Implementation Task Breakdown v2

**Priority:** P0 = critical path/security; P1 = high; P2 = later.  
**Tracking:** move tasks into GitHub Issues/Projects only after Stage 0 design review. All boxes are intentionally unchecked; none imply implementation progress.

## Stage 0 — Specification and foundations

- [ ] SPEC-01 Review PRD and RTM; assign owners to open decisions (P0)
- [ ] SPEC-02 Finalize ERD, composite constraints and migration plan (P0)
- [ ] SPEC-03 Finalize permission catalog and role grant policy (P0)
- [ ] SPEC-04 Finalize campaign/delivery state machines (P0)
- [ ] SPEC-05 Define channel payload and language variant schemas (P0)
- [ ] SPEC-06 Define 100k workload profile and measurable targets (P1)
- [ ] INF-01 Create repository and pull-request workflow (P0)
- [ ] INF-02 Create Vite React JavaScript app (P0)
- [ ] INF-03 Configure Tailwind + DaisyUI (P0)
- [ ] INF-04 Create FastAPI package and configuration (P0)
- [ ] INF-05 Configure PostgreSQL, SQLAlchemy and Alembic (P0)
- [ ] INF-06 Configure Docker Compose and health checks (P1)
- [ ] INF-07 Add `.env.example` and secret-handling rules (P0)
- [ ] INF-08 Add CI lint/test baseline (P1)

## Stage 1 — Identity, organizations and RBAC

- [ ] AUTH-01 User model/password hashing/login (P0)
- [ ] AUTH-02 Secure session creation/rotation/revocation (P0)
- [ ] AUTH-03 Recovery and rate-limit design/implementation (P0)
- [ ] ORG-01 Organization and onboarding policy (P0)
- [ ] ORG-02 Membership and organization switching (P0)
- [ ] RBAC-01 Roles/permissions schema (P0)
- [ ] RBAC-02 `membership_roles` association and constraints (P0)
- [ ] RBAC-03 Permission aggregation and grant-authority checks (P0)
- [ ] RBAC-04 Tenant-scoped repositories and RLS (P0)
- [ ] RBAC-05 Transaction-local tenant context and worker checks (P0)
- [ ] QA-01 Cross-tenant and multi-role negative tests (P0)

## Stage 2 — Audience and consent

- [ ] AUD-01 Audience/contact model and CRUD APIs (P0)
- [ ] AUD-02 CSV upload validation and controlled storage (P0)
- [ ] AUD-03 Import job, chunked worker and row errors (P0)
- [ ] AUD-04 Duplicate identity policy and tests (P0)
- [ ] AUD-05 Allowlisted segment grammar and preview (P0)
- [ ] CONS-01 Consent history by channel/purpose (P0)
- [ ] CONS-02 Suppression model and execution-time checks (P0)
- [ ] AUD-06 Permissioned safe export (P1)
- [ ] QA-02 Import/segment/consent/security tests (P0)

## Stage 3 — Campaigns, templates and localization

- [ ] CMP-01 Campaign model/API and state machine (P0)
- [ ] CMP-02 Immutable campaign versions and content hash (P0)
- [ ] CMP-03 Segment association and eligibility preview (P0)
- [ ] TMP-01 Template and immutable template version models (P0)
- [ ] TMP-02 Placeholder validation (P0)
- [ ] LOC-01 Language registry seeded with English/Hindi (P0)
- [ ] LOC-02 Versioned language/channel content variants (P0)
- [ ] LOC-03 Four-channel content preview and payload validation (P0)
- [ ] QA-03 Campaign/version/localization tests (P0)

## Stage 4 — Approval and audit

- [ ] APR-01 Approval model/API bound to version/hash (P0)
- [ ] APR-02 Review queue and authorization (P0)
- [ ] APR-03 Separation-of-duties policy enforcement (P0)
- [ ] APR-04 Reject rationale and immutable decision record (P0)
- [ ] AUDIT-01 Append-oriented application audit events (P0)
- [ ] AUDIT-02 Role/campaign/approval audit coverage (P0)
- [ ] QA-04 Approval tampering and unauthorized review tests (P0)

## Stage 5 — Mock-all distribution

- [ ] DIST-01 Provider-independent adapter contract (P0)
- [ ] DIST-02 Mock Email adapter (P0)
- [ ] DIST-03 Mock SMS adapter (P0)
- [ ] DIST-04 Mock WhatsApp adapter (P0)
- [ ] DIST-05 Mock Push adapter (P0)
- [ ] DIST-06 Execution and recipient snapshot model (P0)
- [ ] DIST-07 Channel delivery and attempt models/unique keys (P0)
- [ ] DIST-08 Transactional outbox publisher (P0)
- [ ] DIST-09 Celery/Redis bounded workers (P0)
- [ ] DIST-10 Retry/backoff/exhausted-work/unknown outcome (P0)
- [ ] DIST-11 Pause/cancel and current-state checks (P1)
- [ ] QA-05 Duplicate task, worker crash and mock-only boundary tests (P0)

## Stage 6 — Analytics, reliability and performance

- [ ] AN-01 Campaign and channel metric definitions (P0)
- [ ] AN-02 Tenant-scoped dashboard and delivery detail (P1)
- [ ] OBS-01 Structured logs, request IDs and error monitoring (P1)
- [ ] OPS-01 Backup and restore exercise (P0)
- [ ] SEC-01 Upload/export/auth/dependency security tests (P0)
- [ ] PERF-01 100k audience import test (P1)
- [ ] PERF-02 100k recipient snapshot test (P1)
- [ ] PERF-03 100k delivery throughput and worker failure test (P1)
- [ ] DOC-01 Update docs from verified implementation (P0)
- [ ] DEMO-01 Reproducible mock-only demonstration (P1)

## Stage 7 — AI and localization intelligence (R2)

- [ ] AI-01 Evaluate provider privacy, terms, language quality, cost and latency (P1)
- [ ] AI-02 Create permissioned evaluation datasets (P1)
- [ ] AI-03 Draft assistance behind provider adapter (P2)
- [ ] AI-04 Translation suggestions and human review (P2)
- [ ] AI-05 Quality checks and evaluation report (P2)

## Stage 8 — Live providers and engagement (R3)

- [ ] LIVE-01 Define legal/consent and production dispatch policy (P0 for R3)
- [ ] LIVE-02 Provider-specific adapters and secret management (P0 for R3)
- [ ] LIVE-03 Signed webhook verification/replay protection (P0 for R3)
- [ ] LIVE-04 Scheduling/rate limits/operational runbooks (P1)
- [ ] LIVE-05 Feedback and engagement events (P1)
- [ ] LIVE-06 Advanced analytics and sentiment evaluation (P2)

## Definition of Done

Migration where applicable; validation; tenant/resource authorization; state transition checks; idempotency where applicable; tests; API docs/Postman updated; UI integrated; logs redact secrets/PII; documentation updated; no real provider access in R1.

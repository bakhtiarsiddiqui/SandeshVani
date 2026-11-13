# SandeshVani — implementation roadmap

**Status:** Current dependency-aware plan, reconciled against reviewed `main` on 2026-11-13.  
**Baseline:** `c88e270add18c6b0a4259fa5dbb310afa69534e7`.  
**Principle:** finish the governed data workflow before expanding into campaign execution, integrations or AI.

## Stage 0 — Engineering and security foundations

**Status: substantially implemented.**

Current repository includes React/Vite and FastAPI bootstraps, PostgreSQL configuration, Alembic migrations `0001`–`0005`, CI workflows, backend/frontend test suites, auth/token lifecycle, organization/membership/RBAC foundations and forced-RLS policies. P0.2/P0.3/P0.4 ledgers record completion. Remaining setup and operational gaps are tracked below; do not re-open completed foundations without a defect or new requirement.

## Stage 1 — Audience foundation

**Status: partially implemented; current workstream.**

Merged:
- AUD-01 audience contact CRUD (PR #16).
- AUD-02 CSV file-level validation and private storage (PR #17).

Next:
1. AUD-03 choose and complete one asynchronous import implementation; #18 and #19 are competing drafts, not additive.
2. Verify RLS, schema ownership/grants, outbox state, task idempotency, crash recovery, progress counters, row errors and production worker/Redis/Beat wiring using disposable PostgreSQL and configured Redis.
3. AUD-04 define duplicate identity rules and conflict resolution.
4. Define channel/purpose consent, evidence, withdrawal, suppression, retention and legal review.
5. Implement allowlisted segments and eligibility preview; re-check eligibility at execution.
6. Add permissioned, formula-safe exports only after authorization/audit design.

**Exit gate:** large upload is safely processed in bounded chunks; failures are recoverable; duplicates are governed; consent/suppression fail closed; tenant boundaries and row errors are tested.

## Stage 2 — Campaign and content foundation

**Status: not implemented on reviewed main.**

- Campaign CRUD and state machine.
- Immutable campaign versions and stable content hashes.
- Template and template-version models.
- English/Hindi channel content variants and preview validation.
- Segment-to-campaign association and eligibility preview.

**Exit gate:** validated content snapshot is immutable after submission; template edits cannot mutate existing campaign versions; channel/language completeness is explicit.

## Stage 3 — Approval and audit

**Status: not implemented on reviewed main.**

- Reviewer queue and version/hash-bound approve/reject APIs.
- Permission and separation-of-duties policy.
- Recorded rationale and immutable decision history.
- Append-oriented audit events and tenant-scoped audit views.

**Exit gate:** only authorized reviewers can decide; prohibited self-approval is blocked by a human-approved policy; every sensitive transition is auditable.

## Stage 4 — Mock-only distribution

**Status: not implemented on reviewed main.**

- Provider-independent mock adapter interface for Email, SMS, WhatsApp and Push.
- Approved-version execution and execution-time consent/suppression checks.
- Recipient snapshots, logical channel-delivery intents and attempt history.
- PostgreSQL transactional outbox; Celery/Redis workers once AUD-03 worker foundations are accepted.
- Bounded concurrency/batches, idempotent consumers, retry/backoff, pause/cancel and explicit unknown outcomes.

**Exit gate:** all four mock adapters conform; duplicate tasks do not duplicate logical deliveries; worker interruption and replay are tested; no live provider path exists.

## Stage 5 — Analytics, reliability and performance

**Status: not implemented as product analytics; operational foundations partial.**

- Define metric semantics before chart implementation.
- Tenant-scoped campaign/channel aggregates and drill-down.
- Structured logs, request IDs and error monitoring.
- Backup/restore exercise, security regression gates and operational runbooks.
- Representative 100,000-recipient import/snapshot/distribution workload tests.

**Exit gate:** report measured throughput, completion time, resource use, failures, recovery and explicit workload assumptions. No performance claim before evidence.

## Stage 6 — Release 2 intelligence

Deferred: opt-in AI drafting and translation suggestions, human review, quality evaluation per language, provider/privacy/cost/latency assessment. AI cannot approve, target autonomously or dispatch.

## Stage 7 — Release 3 real distribution and engagement

Deferred: provider-specific adapters, secret management, signed webhooks/replay protection, live scheduling/rate controls, feedback and engagement. Requires separate legal, consent, security, provider, operational and rollback gates.

## Working rules

- Do not start a later stage while its data, permission, API or state-machine dependency is undecided.
- Stabilise contracts before frontend/backend parallelism.
- Estimates are not commitments. Re-estimate after acceptance criteria and workload are defined.
- Synchronize this roadmap with `TASKS.md`, `PROJECT_STATUS.md`, API docs and actual GitHub issue/PR state.

# Agent — QA / Security Engineer

**Mission:** independently verify acceptance criteria and adversarial security cases.

## Required context
Read root `AGENTS.md`, docs index/status/decision register, then the relevant threat model, RBAC matrix, security review gates, API contract and acceptance criteria.

## Test areas
- Authentication, CSRF/origin, token rotation/replay, session revocation and rate limiting.
- Multi-role RBAC, grant authority, organization boundaries and post-revocation access.
- RLS reads/writes/deletes, missing tenant context, cross-tenant references and runtime DB privileges.
- Audience CSV size/type/header/row validation, private file handling, checksum and PII minimization.
- Import job idempotency, duplicate task delivery, chunk commit/recovery, worker interruption, outbox retries/dead letters and row errors when AUD-03 is integrated.
- Consent by channel/purpose, missing consent fail-closed, suppression and execution-time re-checks when implemented.
- Campaign immutability, approval binding, separation of duties and audit when implemented.
- Mock-only boundary; no real external provider path in MVP.
- Sensitive-data leakage in logs, errors, exports and test fixtures.

## Must not
- Weaken, skip or rewrite tests to force a pass.
- Use production data or privileged credentials to bypass controls.
- Treat historical execution-ledger results as a current test run.
- Claim untested Redis/Celery runtime behaviour from direct worker-function tests alone.

## Deliver
Test matrix, automated tests, reproducible findings and severity, exact commands/results, skipped/not-run checks and residual risks.

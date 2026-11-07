# QA and security verification

Read root `AGENTS.md` and `agents/qa-security.md`.

Feature/PR [link]; requirements [paths]; environment [local/test].

Create a test matrix before tests. Include success, invalid input, unauthorized, cross-tenant, duplicate/retry and invalid state transitions. For tenancy, test reads/writes/deletes, cross-tenant relationships and missing context. Run RLS tests under actual non-owner runtime role; verify no table ownership or BYPASSRLS. For consent, missing consent must fail closed and purpose/channel specificity must hold. For approval, approval must bind to immutable version/hash. For background jobs, test duplicate delivery and unknown outcomes.

Never use production data or weaken controls. Deliver tests, exact commands/results, reproducible defects/severity and residual risks.

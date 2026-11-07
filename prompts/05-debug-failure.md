# Diagnose and fix a failure

Read root `AGENTS.md` and relevant specialist instructions.

Evidence: redacted logs/command [paste]; expected [x]; actual [y]; branch/commit [ref]; reproduction [steps].

Reproduce before editing where feasible. Trace root cause and distinguish symptoms. Check contract drift, race, tenant-context loss, transaction boundary, idempotency and environment/configuration. Propose smallest safe fix. Add a regression test that fails before and passes after. Run relevant checks. Do not suppress errors, loosen authorization, skip tests or alter unrelated behaviour.

Report root cause, fix, files, regression test, exact commands/results and remaining uncertainty.

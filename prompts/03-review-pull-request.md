# Independent PR review

Read root `AGENTS.md` and `agents/integration-reviewer.md`.

PR [link]; issue [link]; design/contracts [paths].

Read issue and full diff. Check scope, architecture, dependencies, server-side authorization, tenant scoping, migrations/constraints/indexes, consent, campaign immutability, approval binding, audit, idempotency, test quality, frontend/backend contract consistency and absence of real dispatch paths.

Report findings first. Each finding: severity (Critical/High/Medium/Low), file/line, impact, reproduction/rationale and correction. Separate blockers from suggestions. State exactly what was verified and not verified. Do not approve or merge.

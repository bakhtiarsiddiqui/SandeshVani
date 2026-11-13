# SandeshVani — agent operating model

## Mandatory context

Every agent reads root `AGENTS.md`, then `docs/README.md`, `docs/PROJECT_STATUS.md` and `docs/decision-register.md`. Read only task-relevant specifications after that. The `prompts/` pack is archival, not an active source of instructions.

## Tool/role allocation

Tools can change; product names are not role authority. Use the tool selected by the human owner and repository permissions available:
- Architect/planner: dependencies, contracts, data boundaries, ADR/change proposals.
- Backend: FastAPI/domain logic, schemas, persistence, migrations and OpenAPI.
- Frontend: React/JS UI using approved API contracts.
- Data/infrastructure: PostgreSQL, Alembic, RLS, worker and local infrastructure foundations.
- QA/security: independent functional, adversarial, tenant and failure testing.
- Integration reviewer: cross-layer contract and end-to-end verification.
- Human owner: product scope, unresolved business/security policy, architecture approvals, provider/live-dispatch gates and GitHub merge/release decisions.

## Lifecycle

1. Human selects an approved requirement and acceptance criteria.
2. Architect identifies dependencies, affected modules, data/API/event contracts and risks.
3. Resolve contracts before parallel frontend/backend implementation.
4. Implement bounded vertical slices on isolated branches/worktrees.
5. Run focused tests first; QA independently tests acceptance and security boundaries.
6. Integration reviewer checks API/schema drift, migration ordering and end-to-end behaviour.
7. Human reviews security-sensitive design, scope, migrations and acceptance.
8. Merge to protected `main` only through the repository's approved PR process.

## Coordination rules

- Use `feature/<name>`, `fix/<name>` and `docs/<name>` branches.
- Do not have concurrent agents edit the same worktree or migration.
- Every implementation PR links an issue, lists exact tests and states untested behaviour.
- Do not split frontend/backend work until route names, Pydantic schemas, error states, permissions and domain state transitions are agreed.
- One migration revision must have one canonical owner and a unique revision ID. Competing AUD-03 drafts #18/#19 are alternatives and must not be merged independently.
- Agents do not approve/merge their own PRs. Human approval is required for push/PR creation when specified by repository policy, and for merge/release.
- Never use privileged DB credentials to make a tenant test pass. Test RLS with a restricted runtime role.

## Human approval required

Architecture changes; new major dependencies/frameworks; authentication/session/token changes; tenant context/RLS/DB roles; RBAC/grant policy; consent/retention; approval/versioning; audit controls; outbox/idempotency; sensitive migrations; provider integrations, live dispatch and production operations.

## Agent handoff format

State objective, assumptions, exact files/contracts, dependencies, acceptance tests, security/tenant implications, verification commands/results, unresolved decisions and Git branch/PR state. Distinguish verified facts from previous-agent reports and proposed design.

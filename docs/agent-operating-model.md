# Agent operating model

## Tool allocation
- Cursor: primary interactive IDE and main implementation workspace.
- OpenAI Codex: bounded repository tasks, complex fixes, test generation and independent review.
- Google Antigravity: task decomposition/orchestration and browser verification.
- GitHub: source of truth for issues, branches, PRs, checks and releases.
- Figma: design system and screen specifications.
- Docker Compose: reproducible local services.

## Lifecycle
1. Human selects approved requirement.
2. Architect decomposes it into bounded tasks and dependencies.
3. API/data/event contracts are agreed before parallel work.
4. Agents implement on separate branches or isolated worktrees.
5. QA tests acceptance criteria and adversarial security cases.
6. Integration reviewer checks contracts and end-to-end behaviour.
7. Human reviews scope, security, migrations and acceptance.
8. Approved PR merges to protected `main`.

Parallelise frontend/backend only after contract stabilisation. Sequence schema changes before dependent code; coordinate auth/tenant context, approvals/dispatch and cross-cutting API changes.

Use `feature/<name>`, `fix/<name>` and `chore/<name>` branches. No concurrent edits in one worktree. Every PR links an issue and lists exact tests. Agents never merge their own PR.

Human approval is mandatory for architecture, RLS/tenant isolation, auth, RBAC, consent, approval/versioning, sensitive migrations, provider/dispatch and production operations.

# Milestone 0 — Engineering Foundation

## Goal
A developer can clone the repository, start the local environment with Docker Compose and verify React frontend, FastAPI backend, PostgreSQL and Redis. CI runs baseline quality checks. No production dispatch or business feature is included.

## Exit criteria
- Monorepo target structure exists.
- Root `AGENTS.md`, specialist instructions and prompt library committed.
- React + JavaScript + Vite + Tailwind + DaisyUI frontend starts.
- FastAPI backend starts and exposes health endpoint.
- PostgreSQL and Redis start with health checks.
- `.env.example` documents placeholders; no secrets committed.
- GitHub Actions validates frontend/backend.
- `main` protected; PR templates work.
- Setup verified from a clean clone.

## Issue 0.1 — Repository and governance
Owner: Human + Architect. Depends: none.
- Create repository and initial commit.
- Add README, AGENTS, specialist instructions, prompts, .gitignore, .editorconfig and .env.example.
- Protect main: PR required, no force push/direct push, required checks after first successful run.
Acceptance: root instructions present; no secrets tracked; PR/issue templates render; main protected.

## Issue 0.2 — Monorepo skeleton
Owner: Architect + Infrastructure. Depends: 0.1.
- Create frontend, backend, infrastructure, contracts, docs and .github directories.
- Add module ownership notes where useful.
Acceptance: target layout matches `docs/repository-layout.md`; remains modular monolith, not deployable microservices.

## Issue 0.3 — Frontend bootstrap
Owner: Frontend. Depends: 0.2.
- Initialise React + JavaScript + Vite.
- Configure compatible Tailwind CSS and DaisyUI versions.
- Add minimal shell, env config, lint/test/build scripts.
Acceptance: clean install; lint, tests and build pass; no TypeScript migration or unnecessary framework.

## Issue 0.4 — Backend bootstrap
Owner: Backend. Depends: 0.2.
- Initialise Python project/dependency management.
- Add FastAPI entry point and `/api/v1/health`.
- Add environment config, lint/format/test setup and health test.
Acceptance: documented startup works; health JSON/status stable; tests pass; no business-domain feature added.

## Issue 0.5 — Local data/worker infrastructure
Owner: Data/Infrastructure. Depends: 0.2 and 0.4.
- Add PostgreSQL and Redis to Docker Compose.
- Add health checks, local persistent volume and safe env wiring.
- Document startup/shutdown/reset.
Acceptance: `docker compose up -d` healthy; backend connects; no production secrets or unsafe public ports. Runtime DB role separation is enforced when DB schema/RLS work is introduced.

## Issue 0.6 — CI workflows
Owner: Infrastructure. Depends: 0.3 and 0.4.
- Add frontend install/lint/test/build job.
- Add backend install/lint/format/test job.
- Add secret scanning and Dependabot configuration.
Acceptance: PR triggers checks; failed required check blocks merge; no production secrets required. Add PostgreSQL/RLS integration job once runtime role and tenant fixtures exist; never run RLS tests as superuser.

## Issue 0.7 — Clean-clone verification
Owner: Integration reviewer. Depends: 0.1–0.6.
- Verify from clean clone/worktree.
- Run Compose, service health, frontend checks, backend checks and health endpoint.
- Fix setup docs.
Acceptance: second developer follows docs without undocumented steps; exact commands/results recorded; human owner accepts exit checklist.

## Suggested sequencing
0.1 → 0.2 → (0.3 and 0.4 in parallel) → 0.5; 0.3 + 0.4 → 0.6; 0.1–0.6 → 0.7.

## Exclusions
No auth implementation, tenant schema/RLS policy, organization management, campaign feature, provider integration, AI feature, production deployment, Kubernetes or Kafka in Milestone 0.

# SandeshVani — shared AI coding handoff

**Updated:** 2026-11-13  
**Purpose:** Compact session handoff. This file is not the authoritative entry point.

## Read first

1. Root \`AGENTS.md\`.
2. \`docs/README.md\`.
3. \`docs/PROJECT_STATUS.md\`.
4. \`docs/decision-register.md\`.
5. Then inspect only task-relevant source, migrations, tests and specifications.

Do not follow older instructions in \`prompts/AGENTS.md\`, \`prompts/HANDOFF.md\` or \`prompts/MILESTONE.md\`; those locations are retained as deprecated redirects.

## Current verified baseline snapshot

Reviewed default branch: \`main\` at \`c88e270add18c6b0a4259fa5dbb310afa69534e7\`.

Merged slices:
- React/JavaScript/Vite frontend and FastAPI backend foundations.
- Auth/session/security foundations and organization/multi-role/RLS foundations.
- Audience CRUD (PR #16).
- Secure CSV upload validation/private storage (PR #17).
- Gunmetal/Saffron visual system and Overview prototype (PR #14).

Important limits:
- The Overview uses hard-coded sample metrics/campaigns/approvals. It is not live analytics.
- CSV upload stores a validated file and metadata; it does not process rows into contacts.
- Campaigns, consent/suppression, segments, approvals, audit stream, mock distribution and real analytics are not implemented on this main snapshot.
- Celery/Redis and a transactional outbox are selected target architecture but not merged on main.

## Immediate workstream: AUD-03

Two competing draft PRs remain open:
- [PR #18](https://github.com/bakhtiarsiddiqui/SandeshVani/pull/18)
- [PR #19](https://github.com/bakhtiarsiddiqui/SandeshVani/pull/19)

They both introduce an Alembic 0006 import-job/outbox migration from 0005, but use different schemas and worker/outbox implementations. They are alternatives, not additive. Review and select one canonical path; do not merge both independently. See \`docs/PROJECT_STATUS.md\` for the preliminary comparison and required review gates.

## Operating constraints

- Preserve existing user work and inspect \`git status --short --branch\` before edits.
- Never invent routes, models, states, permissions or product decisions.
- Never add live provider dispatch, AI approval/dispatch, Kafka, Kubernetes or microservices to MVP.
- Do not run destructive database operations against a shared/production database.
- Do not stage, commit, push, create/update a PR or merge without explicit authorization for that action.
- Report exact checks run and distinguish current verification from historical ledger evidence.

# SandeshVani documentation index

**Status:** Authoritative documentation entry point  
**Baseline:** 2026-11-13; implementation snapshot references `main` at `c88e270add18c6b0a4259fa5dbb310afa69534e7`.

This index replaces the former instruction to treat the `prompts/` v4 pack as the active source of truth. The v4 pack remains available as an archival planning snapshot only.

## Required reading order for agents

1. Root [`AGENTS.md`](../AGENTS.md).
2. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — what is implemented, what is not, and the next work sequence.
3. [`decision-register.md`](decision-register.md) — decisions and maturity labels.
4. The task-specific document(s) listed below.
5. Relevant source code, Alembic migrations, tests, generated OpenAPI and CI evidence.

Agents should not read every file by default.

## Authority rules

- Root `AGENTS.md` is the mandatory repository operating policy.
- This index controls document navigation and deprecation status.
- `PROJECT_STATUS.md` is a dated status snapshot, not a substitute for checking the current branch.
- `decision-register.md` records selected decisions and whether they are implemented.
- PRD/RTM describe requirements; they do not prove implementation.
- Architecture/data-model/workflow/UI documents can describe target behaviour. Read their status banners before treating any detail as current behaviour.
- `docs/api/API_CONTRACT.md` is a planning/contract inventory. Actual endpoints and schemas must be verified in FastAPI source and the generated `/openapi.json` for the current branch.
- Security execution ledgers preserve historical verification evidence. They are not live CI status.
- Code, migrations, tests and CI for the checked-out revision determine what exists and what has been verified.

If documents conflict, report the inconsistency. Do not merge two competing technical designs or invent a decision.

## Authoritative documents

| Document | Purpose | Authority/status |
|---|---|---|
| [Project status](PROJECT_STATUS.md) | Current implementation snapshot and next steps | Authoritative dated snapshot; re-check Git |
| [Decision register](decision-register.md) | Product/architecture decisions and maturity | Current decision record |
| [Agent operating model](agent-operating-model.md) | Collaboration, branch and review workflow | Current process |
| [Technology decisions](architecture/TECH_STACK_DECISIONS.md) | Selected stack vs target/deferred technologies | Current decision record |
| [Implementation roadmap](implementation/ROADMAP.md) | Dependency-aware delivery sequence | Current planned sequence |
| [Implementation tasks](implementation/TASKS.md) | Task-level status and acceptance | Current working tracker; reconcile with GitHub issues |
| [API contract](api/API_CONTRACT.md) | Current endpoints and planned resource contract | Mixed: implementation inventory + future contract; see banner |
| [Root repository instructions](../AGENTS.md) | Agent rules | Mandatory |

## Domain specifications

| Area | Document | Interpretation |
|---|---|---|
| Product | [PRD / project brief](product/PRD_PROJECT_BRIEF.md) | Requirements and scope; not implementation proof |
| Requirements | [Requirements traceability matrix](product/REQUIREMENTS_TRACEABILITY_MATRIX.md) | Acceptance targets; rows require source/test evidence |
| Architecture | [System architecture](architecture/ARCHITECTURE.md) | Target architecture; distinguishes current from proposed |
| Data | [Logical data model](architecture/DATA_MODEL_SCHEMA.md) | Logical target, not current migration DDL |
| Security | [RBAC matrix](security/RBAC_MATRIX.md), [threat model](security/THREAT_MODEL.md), [review gates](security-review-gates.md) | Security requirements and review controls |
| Workflows | [User and system flows](workflows/USER_FLOWS.md) | Target journeys; implemented subset only |
| UI | [UI specification](design/UI_SPEC.md) | Design direction and screen requirements; screens may be unimplemented |
| Brand | [Brand identity](brand/BRAND_IDENTITY.md) | Working brand; registration/legal clearance remain open |

## Historical and superseded materials

These files are retained for context, but are not active instructions:
- `prompts/README.md`: former Project Documentation Pack v4; superseded as the active index.
- `prompts/AGENTS.md`: duplicated/contradictory agent instructions; superseded by root `AGENTS.md`.
- `prompts/HANDOFF.md`: legacy handoff location; use root `SandeshVani_AI_Handoff.md` as a concise redirect/status alias and the current docs above.
- `prompts/MILESTONE.md`: expired five-day milestone plan; superseded by the staged roadmap and task tracker.
- `backlog/milestone-0.md`: historical engineering-foundation plan; its completion state must not be inferred from original acceptance criteria.
- `prompts/CHANGELOG_V4.md`: historical brand-alignment changelog, retained as archival record.
- `docs/security/P0.*_EXECUTION_STATE.md`: historical security execution ledgers; preserve their evidence, but use this index/status for present priorities.

Do not remove archival files without explicit owner approval. If an old file is opened directly, follow its deprecation banner and return to this index.

## Updating documentation

When implementation changes:
1. Update source/API/schema/tests first or in the same coherent change.
2. Update the affected domain specification and API inventory.
3. Update `PROJECT_STATUS.md` and `implementation/TASKS.md` only with verified evidence.
4. Record material decisions in the decision register/ADR.
5. Keep links and status labels accurate.

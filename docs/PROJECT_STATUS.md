# SandeshVani — Project status

**Snapshot date:** 2026-11-13  
**Repository baseline reviewed:** \`main\` at \`c88e270add18c6b0a4259fa5dbb310afa69534e7\`  
**Purpose:** factual implementation snapshot and dependency-aware next-work list.

> This is a dated repository inspection, not a claim that tests were re-run on this date. Re-check the current branch, source, migrations, CI and open PRs before relying on it after the snapshot date.

## Executive status

The repository has established security-conscious identity/tenant foundations and the first audience-management slices. The end-to-end product workflow is still incomplete. The most important near-term work is to resolve the competing asynchronous CSV-import proposals, then finish audience identity/consent/segmentation foundations before starting the campaign/approval/distribution sequence.

Do not describe the dashboard as live analytics or any future workflow as implemented solely because it appears in a UI or planning document.

## Implemented on the reviewed main baseline

| Area | Verified repository evidence | Status |
|---|---|---|
| Frontend bootstrap | React/JavaScript/Vite app, Tailwind/DaisyUI, tests/build scripts | Implemented |
| Visual system | Gunmetal/Saffron DaisyUI theme, Mukta font, shared components and auth styling merged by PR #14 | Implemented |
| Sign-in visual effects | Three.js decorative scene and pointer effects; nonessential to auth | Implemented, decorative only |
| Auth foundation | Registration, verification, login, refresh, logout/logout-all, recovery/reset and session/token handling in \`backend/app/api/v1/auth.py\` and services | Implemented; review tests for current branch |
| Security configuration | P0.2 execution ledger records completion of JWT, cookies, CSRF/origin, CORS and startup validation | Ledger says complete; production deployment configuration still required |
| Tenant/organization security | Organization discovery/switching, membership, multi-role association, tenant context and RLS migrations \`0001\`–\`0003\`; see P0.3/P0.4 records | Implemented foundation; ledgers contain historical verification |
| Audience contact CRUD | Create, list, retrieve and update endpoints; merged by PR #16 | Implemented |
| CSV file-level upload | CSV format/headers/row structure, size and row limits, private storage and tenant-scoped upload metadata; merged by PR #17 | Implemented upload only; does not import contacts |

## Present but demonstrative, not connected to domain APIs

- The Overview dashboard merged by PR #14 includes sample KPI, campaign, dispatch and approval data.
- The dispatch panel is a front-end simulation. No messages leave the system.
- Approval buttons are intentionally disabled unless handlers are supplied.
- The dashboard must remain labelled as sample/demo data until backed by real tenant-scoped APIs and analytics definitions.
- Three.js animation is decorative and must not become a dependency for auth or core product behaviour.

## Not implemented on the reviewed main baseline

No corresponding campaign/approval/distribution domain routers, models or worker modules appear in the reviewed main tree for:
- Asynchronous CSV import jobs, worker processing and row-error APIs.
- Duplicate identity detection/deduplication policy.
- Audience segments and segment preview.
- Consent history, channel/purpose decisioning and suppression management.
- Permissioned audience exports.
- Campaign CRUD, immutable campaign versions and campaign state machine.
- Templates/template versioning and channel/language content variants.
- Approval records, reviewer actions, separation-of-duties enforcement and audit-event stream.
- Mock Email/SMS/WhatsApp/Push provider adapters, recipient snapshots, delivery attempts, retry/unknown-outcome state or execution APIs.
- Real campaign analytics or measured 100,000-recipient performance.

These remain planned requirements, not current capabilities. The PRD and UI specification contain target journeys for them.

## Open implementation proposals: AUD-03

As of this snapshot, two competing draft pull requests remain open:

- [PR #18 — asynchronous CSV import](https://github.com/bakhtiarsiddiqui/SandeshVani/pull/18), branch \`feat/audience-import-processing\`.
- [PR #19 — asynchronous CSV import](https://github.com/bakhtiarsiddiqui/SandeshVani/pull/19), branch \`feat/audience-csv-processing\`.

They both create an Alembic \`0006_audience_import_jobs\` revision from migration \`0005_audience_import_uploads\`, but their worker, schema, outbox and error models differ. They are alternatives, not additive changes. Do not merge both independently or treat either as merged/implemented.

Preliminary review direction (not an approved merge decision):
- PR #18 has a persisted job lease/worker token and a more explicit outbox claim, retry and dead-letter lifecycle.
- PR #19 stores row errors as allowlisted field/error codes and exposes cursor pagination; its description notes that the production wrapper, broker and Beat schedule need runtime validation.
- Before selecting a base, compare migration ownership/role grants, RLS, task payload minimization, concurrency, lease recovery, outbox duplicate publication, worker process lifecycle, same-volume file access and tests with a real disposable PostgreSQL plus configured Redis.
- Select one canonical migration/model/API contract; port only reviewed improvements from the other branch. Keep AUD-04 duplicate policy separate.

## Recommended next sequence

1. **AUD-03 decision and integration:** choose one implementation, resolve schema/API names and statuses, ensure one unique migration revision, review RLS/ownership/grants and test worker/outbox runtime. No main-branch implementation until accepted.
2. **AUD-04 duplicate identity policy:** decide safe matching and conflict handling before importing duplicate contacts.
3. **Consent and suppression:** define channel/purpose model, provenance, withdrawal and retention; enforce fail-closed eligibility.
4. **Segments:** allowlisted filter grammar, preview counts and execution-time re-evaluation.
5. **Campaign and template foundation:** campaign draft/state model, immutable versions, template versions, channel/language variants and preview validation.
6. **Approval and audit:** immutable hash binding, reviewer authority, separation-of-duties decision and append-oriented audit records.
7. **Mock distribution:** provider-independent mock adapters, recipient snapshots, transactional outbox, Celery/Redis, bounded idempotent jobs, retries and explicit unknown outcomes.
8. **Analytics and operations:** metric definitions, backup/restore, observability and representative performance tests.

Do not parallelise dependent frontend/backend work until API, permissions, state and data contracts are agreed.

## Still-open product/operational decisions

Organization onboarding/invitation policy; audience identity uniqueness and deduplication; consent legal basis and retention by jurisdiction/channel/purpose; separation-of-duties rules; audit retention/tamper-evidence; supported languages beyond English/Hindi; campaign/delivery state machines; exact 100k workload and completion objective; RPO/RTO; worker recovery and scheduling semantics; provider selection for a future release.

## Evidence and update rules

- PR #14, #16 and #17 are merged and explain the current UI, audience CRUD and upload slices.
- P0.2/P0.3/P0.4 execution ledgers preserve past verification results; they are not a current test run.
- The current main tree contains migrations \`0001\` through \`0005\`. No migration 0006 is merged in this snapshot.
- Update this file only when implementation/PR state changes and link the evidence. Do not use unchecked task boxes or design mockups as completion evidence.

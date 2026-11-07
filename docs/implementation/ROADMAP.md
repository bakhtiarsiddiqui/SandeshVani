# SandeshVani — Staged Project Roadmap

**Status:** Proposed sequence; estimates are not commitments.  
**Principle:** Resolve architecture and security dependencies before feature implementation.

## Stage 0 — Specification and technical foundation

**Goal:** Make the system implementable.  
**Deliverables:** approved PRD/RTM; ERD and constraints; permission catalog; API schemas; threat model; repository skeleton; Docker Compose; CI/test baseline.  
**Exit gate:** critical relationships and tenant boundaries defined; mock-only boundary testable; unresolved decisions assigned owners.

## Stage 1 — Identity, organizations and tenant security

**Deliverables:** authentication/session handling; organizations; memberships; `membership_roles`; roles/permissions; active organization context; RLS; audit.  
**Exit gate:** multi-org/multi-role tests pass; cross-tenant tests pass; role revocation takes effect; org admin cannot grant platform role.

## Stage 2 — Audience and consent

**Deliverables:** audience CRUD; CSV validation/import jobs; duplicate policy; segment builder/preview; consent history; suppression.  
**Exit gate:** row-level errors and recovery; safe file handling; allowlisted segment grammar; consent/suppression tested at execution.

## Stage 3 — Campaign and localization foundation

**Deliverables:** campaigns; templates/template versions; immutable campaign versions; English/Hindi content variants; extensible language registry; four-channel previews; validation.  
**Exit gate:** selected channel/language variants are complete or explicitly incomplete; version hash stable; material edits create new version.

## Stage 4 — Approval and audit

**Deliverables:** reviewer queue; approve/reject; version/hash binding; separation-of-duties rules; audit views.  
**Exit gate:** only authorized reviewers act; rationale captured; creator self-approval policy enforced; approved version immutable.

## Stage 5 — Mock-all distribution

**Deliverables:** execution model; recipient snapshots; channel delivery intents; outbox; Celery/Redis; mock Email/SMS/WhatsApp/Push adapters; attempts; retry/backoff; pause/cancel.  
**Exit gate:** all four adapters conform; duplicate tasks do not duplicate logical deliveries; worker failure recovery tested; no real provider path exists.

## Stage 6 — Analytics, reliability and performance

**Deliverables:** campaign/channel metrics; structured logs/request IDs; operational metrics; backup/restore; security regression suite; representative 100k load tests.  
**Exit gate:** documented workload test reports completion time, throughput, resource use and errors; recovery exercised; metric definitions agreed; known limitations recorded.

## Stage 7 — AI and localization intelligence (Release 2)

**Deliverables:** provider evaluation; opt-in drafting/translation suggestions; human translation review; quality checks; language-specific evaluation; AI cost/latency monitoring.  
**Exit gate:** privacy/provider approval; factual and language quality evidence; AI cannot approve or dispatch; human review enforced.

## Stage 8 — Real distribution and engagement (Release 3)

**Deliverables:** provider-specific Email/SMS/WhatsApp/Push adapters; credentials/secrets; signed webhooks; scheduling/rate controls; feedback/engagement; advanced analytics.  
**Exit gate:** legal/consent review; provider integration and failure tests; webhook replay protection; operational runbooks; rollback plan; explicit production authorization.

## Schedule note

The original v1 pack proposed Sprint 0 plus six weeks. The v2 sequence preserves the same broad work order but adds explicit localization, multi-role RBAC and release gates. Do not promise a six-week completion date until scope, team capacity, acceptance profile and estimates are reviewed. Stages may be split into sprints; dependencies should not be skipped for schedule reasons.

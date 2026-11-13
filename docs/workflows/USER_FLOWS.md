> **DOCUMENT STATUS — TARGET WORKFLOWS:** This document describes end-to-end product journeys, including workflows not yet implemented. The reviewed main branch does not yet provide campaign, consent, segment, approval, distribution or analytics workflows. Treat these as future acceptance targets; see [PROJECT_STATUS.md](../PROJECT_STATUS.md).

---

# SandeshVani — User and System Flows v2

## 1. Sign-in and organization selection

1. User submits credentials.
2. Backend authenticates and establishes secure session.
3. Backend returns user memberships and organization-scoped role summaries.
4. User selects an organization if multiple memberships exist.
5. Backend verifies membership and activates organization context.
6. UI loads effective permissions for that context.
7. Every API request checks active membership, resource tenant, permission and workflow state. Removed membership/revoked session is denied.

## 2. Multiple-role assignment

1. Authorized organization administrator opens member details.
2. Backend returns roles assignable by that administrator.
3. Administrator assigns or revokes one or more roles.
4. Backend validates membership/role organization match and grant authority.
5. `membership_roles` is updated and action audited.
6. Effective permissions are recalculated on subsequent requests; no stale client-side grant is trusted.

## 3. Audience import

1. Authorized user opens Audience and uploads CSV.
2. UI explains required columns, file limits and mapping.
3. API validates upload and creates import job (202).
4. Worker processes bounded chunks: encoding, headers, formats, normalization, duplicates and allowed attributes.
5. UI shows progress, processed/rejected counts and safe row errors.
6. Records are stored under active organization. Oversized files are rejected; failed jobs remain visible/recoverable under policy.

## 4. Segment creation

1. User selects approved fields/operators in visual builder.
2. API validates filter grammar and value types.
3. Preview returns count and eligibility caveats.
4. User saves segment.
5. Queries always apply tenant scope and status/eligibility constraints. Raw SQL is never accepted.

## 5. Campaign creation and localization

1. Campaign Manager creates draft and enters objective/type.
2. Selects one or more channels from Email, SMS, WhatsApp and Push.
3. Selects template and exact template version.
4. Adds English and/or Hindi content variants; other registered Indic languages may be enabled when product policy permits.
5. Selects audience segments and verifies channel contact requirements.
6. Validates placeholders, payload constraints and required language variants.
7. Previews rendered content for every selected channel/language combination.
8. Previews estimated audience, eligible, suppressed and missing-consent counts.
9. Creates immutable campaign version and content hash.
10. Material changes create a new version.

## 6. Approval

1. Manager submits exact version.
2. Backend checks permission, required fields, version integrity and separation-of-duties policy.
3. Item enters approval queue.
4. Reviewer inspects exact snapshot/hash, content variants, channels, audience and schedule if applicable.
5. Reviewer approves/rejects with rationale.
6. Backend stores reviewer, timestamp, decision and version hash.
7. Approved version remains immutable; changes require new version and approval.

## 7. Mock-all execution

1. Authorized user requests execution for approved version.
2. Backend enforces fixed mock mode and selects only mock adapters.
3. Eligibility rechecks consent, suppression, channel address and campaign rules.
4. System creates one recipient snapshot per eligible audience identity per execution (proposed rule; see RTM DEC-005).
5. Separate channel delivery intents and outbox rows are committed in the same transaction.
6. Outbox publisher queues bounded tasks.
7. Celery workers validate task, tenant and current execution state.
8. Appropriate mock Email/SMS/WhatsApp/Push adapter returns simulated outcome.
9. Attempts and delivery states persist idempotently.
10. UI shows progress, channel, status and explicit SANDBOX/MOCK labeling. Pause/cancel is backend-enforced. No real provider is permitted in R1.

## 8. Analytics

Authorized users see tenant-scoped campaign and channel totals. Distinguish pending/processing, accepted, delivered, failed, retrying and unknown. Metric definitions must specify denominator, time window and treatment of retries. Exports are separately permissioned and audited.

## 9. State rules

Draft is editable; submitted is locked for review; approved version is immutable; rejected version cannot execute; scheduled waits for time (scheduling semantics remain open); processing is active; paused blocks new work subject to in-flight policy; completed is terminal; cancelled blocks new work and reconciles in-flight results; failed requires review/recovery. Backend owns state transitions.

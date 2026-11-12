# SandeshVani — Logical Data Model and Schema v2

**Database:** PostgreSQL  
**ORM/migrations:** SQLAlchemy 2.x / Alembic  
**Status:** Logical model for review; not final migration DDL

## 1. Modeling rules

- UUID primary keys; `TIMESTAMPTZ`; explicit foreign keys and check constraints.
- Tenant-owned rows carry `organization_id` and use tenant-safe relationships.
- Use composite unique/FK constraints where needed to ensure related rows belong to the same tenant.
- RLS enabled for tenant-owned tables; application DB role is not owner and has no `BYPASSRLS`.
- Tenant context set transaction-locally before tenant queries.
- JSONB only for validated flexible structures, not arbitrary query execution.
- Migrations only through Alembic.
- Sensitive contact data encrypted; keys managed outside the database; keyed hashes used for lookup where appropriate.

## 2. Identity and access entities

### `organizations`
`id`, `name`, `slug` (unique), `status`, `created_at`, `updated_at`.

### `users`
`id`, `email`, `normalized_email` (unique), `password_hash`, `full_name`, `status`, `email_verified_at`, timestamps.

### `memberships`
`id`, `organization_id`, `user_id`, `status`, `joined_at`, timestamps. Unique `(organization_id, user_id)`. **Do not store a single `role_id` here.**

### `roles`
`id`, nullable `organization_id` for controlled platform roles, `name`, `description`, `scope`, `is_system_role`, timestamps. Role naming/immutability policy remains to be finalized.

### `permissions`
`id`, `code` (unique), `description`.

### `membership_roles`
`id`, `organization_id`, `membership_id`, `role_id`, `assigned_by`, `assigned_at`. Unique `(membership_id, role_id)`. Enforce that membership and role are valid for the same organization. If platform roles are supported, model their assignment separately and explicitly rather than allowing tenant admins to grant them.

### `role_permissions`
`role_id`, `permission_id`; composite primary key.

### `sessions`
`id`, `user_id`, `token_hash`, `created_at`, `expires_at`, `revoked_at`. Store token hashes, not raw secrets.

### `organization_invitations`
Proposed: `id`, `organization_id`, normalized invitee identifier, token hash, invited role assignment policy, status, expiry, inviter, accepted membership and timestamps. Final invitation semantics require API/security review.

## 3. Audience and eligibility entities

### `audience_members`
`id`, `organization_id`, `external_reference`, `full_name`, encrypted email/phone or channel contact points, keyed lookup hashes, `preferred_language`, district/state, validated attributes JSONB, status, timestamps.

### `consent_records`
`id`, `organization_id`, `audience_member_id`, `channel`, `purpose`, `status`, `source`, `notice_version`, `recorded_at`, `withdrawn_at`, `evidence_reference`. Preserve history; define legal basis and retention policy before production use.

### `suppression_entries`
`id`, `organization_id`, `audience_member_id` or appropriately protected contact lookup, `channel`, `reason`, `created_at`, `expires_at`.

### `segments`
`id`, `organization_id`, `name`, `filter_definition` JSONB, `created_by`, timestamps. Grammar is allowlisted and type-checked; never compile user JSON into arbitrary SQL.

### `audience_import_jobs` / `audience_import_job_errors`
An import job references one same-tenant upload and stores creator, status, total/processed/imported/rejected row counts, safe failure code and lifecycle timestamps. Error rows store source row number, allowlisted field name and stable error code only; never store rejected cell values or raw validation messages.

The generic `outbox_events` table stores tenant, aggregate identity, event type, validated JSON payload, status, dispatch attempts and retry timestamps. The import outbox event is inserted in the same transaction as the job. PostgreSQL remains authoritative; Redis/Celery is transport and execution infrastructure.

## 4. Campaign and localization entities

### `campaigns`
`id`, `organization_id`, `name`, `campaign_type`, `status`, `created_by`, optional schedule fields, timestamps.

### `campaign_versions`
`id`, `organization_id`, `campaign_id`, `version_number`, immutable `content_snapshot` JSONB, `content_hash`, `created_by`, `created_at`; unique `(campaign_id, version_number)`.

### `campaign_segments`
`organization_id`, `campaign_id`, `segment_id`; tenant-safe composite FKs.

### `templates` / `template_versions`
Tenant-owned template and immutable numbered template versions. Template versions must be referenced by the campaign version snapshot so future template edits cannot alter an approved campaign.

### `languages`
`code` (language tag), `display_name`, `native_name`, `is_active`, `is_rtl`, optional script metadata. Seed English `en` and Hindi `hi`; additional Indic languages are configurable. Exact language launch set is OPEN.

### `campaign_content_variants`
`id`, `organization_id`, `campaign_version_id`, `language_code`, `channel`, optional subject/title, body/content payload, source language, review status, created metadata. Uniqueness must prevent duplicate variant keys within a version. The precise channel-specific payload schema is an API/schema design task.

### `translation_reviews`
Proposed: variant ID, reviewer, status, notes, reviewed timestamp and version/hash reference. R1 may use a simpler content review status; AI-assisted translation is R2.

## 5. Governance entities

### `campaign_approvals`
`id`, `organization_id`, `campaign_version_id`, `reviewer_id`, `decision`, `rationale`, `decided_at`, reviewed content hash. Approval references exact immutable version/hash. Define quorum and self-approval restrictions before implementation.

### `audit_logs`
`id`, nullable `organization_id` for controlled platform events, `actor_id`, `action`, `resource_type`, `resource_id`, before/after state JSONB with PII minimization, `ip_address`, `request_id`, `created_at`. Database append-only permissions alone do not make logs tamper-proof; protect export/retention separately.

## 6. Execution and delivery entities

### `campaign_executions`
`id`, `organization_id`, `campaign_id`, `campaign_version_id`, execution status, mode (R1 fixed to mock), requested_by, idempotency key, started/completed timestamps. One campaign may have multiple executions; re-execution semantics are OPEN.

### `campaign_recipients`
`id`, `organization_id`, `campaign_execution_id`, `audience_member_id`, eligibility result/reason, snapshot timestamp and minimal recipient snapshot fields required for reproducibility. Proposed uniqueness `(campaign_execution_id, audience_member_id)`; do not assume uniqueness across all executions.

### `message_deliveries`
`id`, `organization_id`, `campaign_recipient_id`, `channel`, language/content variant reference or immutable rendered snapshot, status, provider/adapter name, provider message ID (nullable in mock), idempotency key, accepted/delivered/failed timestamps. Unique logical delivery key should include recipient execution and channel (and any other dimension required by product semantics).

### `delivery_attempts`
`id`, `organization_id`, `message_delivery_id`, `attempt_number`, request/response metadata, outcome, error category, attempted timestamp. Unique `(message_delivery_id, attempt_number)`.

### `outbox_events`
`id`, `organization_id`, aggregate type/ID, event type, validated payload, status, created/published timestamps, attempt/lease metadata. Outbox insert must be in same transaction as logical delivery intent.

### `webhook_events`
Reserved for later provider integration. `organization_id` may not be known at receipt time; define trusted provider-account-to-tenant mapping and nullable/global intake model before R3. Unique provider/event identity; verify signature and replay controls before processing.

## 7. Relationships

- Organization 1:N memberships, audience, segments, campaigns, templates, executions and tenant audit records.
- User 1:N memberships and authored/reviewed records.
- Membership M:N roles through `membership_roles`.
- Role M:N permissions through `role_permissions`.
- Audience member 1:N consent, suppression and execution recipient snapshots.
- Campaign 1:N versions and executions.
- Campaign version 1:N content variants and approvals.
- Execution 1:N recipient snapshots.
- Recipient snapshot 1:N channel deliveries.
- Delivery 1:N attempts.
- Outbox events publish work for aggregates; PostgreSQL remains authoritative.

## 8. Index candidates

- `memberships(organization_id, user_id)` UNIQUE.
- `membership_roles(membership_id, role_id)` UNIQUE; index by organization and role.
- Audience `(organization_id, status)`, `(organization_id, district)`, `(organization_id, preferred_language)`.
- Campaign `(organization_id, status, created_at DESC)`.
- Versions `(campaign_id, version_number)` UNIQUE.
- Execution recipients `(campaign_execution_id, eligibility_status)` and unique execution/member.
- Deliveries `(organization_id, status, created_at)` and unique logical idempotency key.
- Outbox `(status, created_at)` plus lease/claim index.
- Audit `(organization_id, created_at DESC)`.

Validate indexes with representative query plans and write volume. Do not index every JSONB path without evidence.

## 9. Integrity and security rules

- Composite tenant-safe FKs prevent cross-organization associations.
- RLS and tenant-scoped repositories both apply; neither substitutes for the other.
- Worker tasks carry organization and aggregate identifiers but revalidate current state and tenant context.
- Approved versions and referenced template/content snapshots are immutable.
- Consent/suppression rechecked immediately before delivery intent/dispatch.
- Logical delivery idempotency is enforced with database uniqueness, not only task code.
- Define retention, deletion, legal hold and PII minimization before production data.

## 10. Schema decisions still open

Organization hierarchy; platform/system role representation; role inheritance/customization; invitation semantics; exact channel contact-point normalization; recipient snapshot PII content; execution re-run semantics; unique delivery key dimensions; campaign scheduling/rescheduling; approval quorum/self-approval; webhook tenant attribution; retention/deletion/legal hold. Produce an ERD and migration-level DDL only after these are resolved or explicitly accepted as provisional.

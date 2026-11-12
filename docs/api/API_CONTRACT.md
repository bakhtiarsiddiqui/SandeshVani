# SandeshVani — API Contract v2

**Base path:** `/api/v1`  
**Format:** JSON over HTTPS  
**Contract source of truth:** FastAPI-generated OpenAPI plus reviewed schemas

This is a resource/endpoint inventory, not final Pydantic schemas. Request/response fields, idempotency semantics and error codes must be finalized before frontend integration.

## 1. Conventions

- UUID resource IDs; UTC ISO-8601 timestamps.
- Cursor pagination with bounded `limit` and allowlisted filters/sorting.
- Pydantic request/response schemas and consistent error envelope.
- Tenant resolved from authenticated membership and active organization; client org ID is never authorization evidence.
- Request ID in responses/errors and structured logs.
- Idempotency keys for asynchronous/state-changing operations where appropriate.
- Resource-level authorization and state-machine validation on every request.
- Cookie-authenticated mutations require CSRF protection; cookies HttpOnly, Secure over HTTPS and appropriate SameSite.

## 2. Authentication and organization context

- `POST /auth/login`
- `POST /auth/logout`
- `POST /auth/refresh` (if refresh rotation is implemented)
- `GET /auth/me` — user and memberships; expose role summaries per organization without leaking other tenant data.
- `POST /auth/active-organization` — server verifies membership before switching context.
- `POST /auth/password-recovery` and recovery completion endpoints — required design work; exact contract to be finalized.

## 3. Organizations, memberships and roles

- `GET /organizations`
- `GET /organizations/current`
- `POST /organizations` (subject to onboarding policy)
- `GET /organizations/{organization_id}`
- `PATCH /organizations/{organization_id}`
- `GET /organizations/{organization_id}/members`
- `POST /organizations/{organization_id}/invitations`
- `PATCH /organizations/{organization_id}/members/{membership_id}`
- `GET /organizations/{organization_id}/roles`
- `POST /organizations/{organization_id}/roles`
- `GET /organizations/{organization_id}/permissions`
- `PUT /organizations/{organization_id}/roles/{role_id}/permissions`
- `POST /organizations/{organization_id}/members/{membership_id}/roles`
- `DELETE /organizations/{organization_id}/members/{membership_id}/roles/{role_id}`

Role assignment must validate same-organization membership/role scope and grant authority. Platform roles must not be assignable by tenant administrators.

## 4. Audience, imports, segments and consent

- `GET /audiences?cursor=&limit=&search=&status=&district=&language=`
- `POST /audiences`
- `GET /audiences/{audience_id}`
- `PATCH /audiences/{audience_id}`
- `POST /audiences/imports` (multipart CSV; 202)
- `GET /audiences/imports/{import_id}`
- `GET /audiences/imports/{import_id}/errors`
- `GET /segments`, `POST /segments`, `GET /segments/{segment_id}`
- `POST /segments/{segment_id}/preview`
- `POST /audiences/exports` (controlled permissioned export)
- `GET /audiences/{audience_id}/consent`
- `POST /audiences/{audience_id}/consent`
- `GET /suppression-entries`, `POST /suppression-entries`

### AUD-01 — Audience contact CRUD

The first implementation slice exposes organization-scoped audience contact records:

- `POST /audiences` — create one contact (201).
- `GET /audiences` — list contacts using a bounded cursor (limit 1–100; default 25), with optional `search`, `status`, `district`, and `language` filters.
- `GET /audiences/{audience_id}` — retrieve one contact in the verified active organization.
- `PATCH /audiences/{audience_id}` — update supplied fields; use `status: "inactive"` to deactivate. Hard deletion is not exposed.

Create/update requests require the existing organization-scoped `audiences:create` / `audiences:update` permission, CSRF token and trusted Origin/Referer validation. Reads require `audiences:read`. The tenant is derived from authenticated membership and active organization context; an organization header is not authorization evidence.

Fields in this CRUD slice: `full_name` (required), `email` (optional), `phone` (optional, E.164), `preferred_language` (`en` or `hi` in the current MVP registry), `district` (optional), and `status` (`active` or `inactive`). At least one contact point (email or phone) is required. Email is normalized to lowercase.

Duplicate identity matching is intentionally not enforced yet: the product's duplicate policy is still open and must be resolved before CSV import/deduplication. This CRUD slice does not implement CSV imports, segments, consent, suppression, exports or audit-event history. The record stores creator/last-updater references, which are metadata rather than an append-only audit log.

Collection response:

```json
{
  "data": [],
  "pagination": {
    "next_cursor": null,
    "has_more": false,
    "limit": 25
  }
}
```

Example audience:

```json
{
  "full_name": "Example Person",
  "email": "person@example.org",
  "phone": "+911234567890",
  "preferred_language": "hi",
  "district": "Meerut"
}
```

### AUD-02 — CSV upload validation and controlled storage

- `POST /audiences/imports` accepts one multipart file in the `file` field and returns HTTP 202 after file-level validation and durable private storage.
- The filename must have a `.csv` extension. The content is parsed as UTF-8 (an optional UTF-8 BOM is accepted); a declared media type, when present, must be CSV-compatible.
- Headers are case-insensitive after trimming and must be unique and drawn from `full_name`, `email`, `phone`, `preferred_language`, and `district`. `full_name` is required, and at least one of `email` or `phone` must be present.
- CSV quoting and row structure are checked. Blank rows are ignored. Each nonblank row must have the same number of fields as the header.
- Default limits are 25 MiB and 100,000 nonblank data rows; both are configurable with `AUDIENCE_IMPORT_MAX_BYTES` and `AUDIENCE_IMPORT_MAX_ROWS`.
- The backend stores files outside the frontend static tree, under `AUDIENCE_IMPORT_STORAGE_DIR`. It generates the stored filename from a UUID, creates private directories/files (0700/0600), and does not persist or return the supplied filename or a filesystem path.
- Upload metadata (tenant, uploader, byte size, row count, SHA-256 and creation time) is stored in a tenant-owned database table protected by PostgreSQL RLS.
- The endpoint requires authenticated organization membership, `audiences:create`, and the existing CSRF and trusted-origin checks.

The 202 response contains the upload UUID, organization UUID, byte size, row count, SHA-256 and creation time. This stage validates and retains the upload only: it does not create audience contacts, queue a worker, report per-row semantic validation errors, or apply duplicate matching. Those are AUD-03/AUD-04 scope.

Segment filters use an allowlisted, type-checked grammar. Never accept raw SQL.

## 5. Campaigns, templates and localization

- `GET /campaigns`, `POST /campaigns`
- `GET /campaigns/{campaign_id}`, `PATCH /campaigns/{campaign_id}` (draft-only)
- `POST /campaigns/{campaign_id}/versions`
- `GET /campaigns/{campaign_id}/versions`
- `GET /campaigns/{campaign_id}/versions/{version_id}`
- `POST /campaigns/{campaign_id}/preview`
- `POST /campaigns/{campaign_id}/submit`
- `POST /campaigns/{campaign_id}/cancel`
- `GET /languages`
- `GET /campaigns/{campaign_id}/versions/{version_id}/content`
- `PUT /campaigns/{campaign_id}/versions/{version_id}/content/{language_code}`
- `GET /templates`, `POST /templates`, `GET /templates/{template_id}`
- `POST /templates/{template_id}/versions`, `GET /templates/{template_id}/versions`

R1 language registry includes English and Hindi and supports adding further Indic language metadata. Content variant completeness and review status must be visible. Submitted version content cannot be edited in place.

## 6. Approvals

- `GET /approvals`
- `GET /approvals/{approval_id}`
- `POST /approvals/{approval_id}/approve`
- `POST /approvals/{approval_id}/reject`

Decision payload example: `{"rationale":"Reviewed the exact submitted version."}`. Backend verifies reviewer permissions, separation-of-duties policy, organization, immutable version and content hash.

## 7. Mock execution and delivery

- `POST /campaigns/{campaign_id}/executions` — creates mock execution only in R1.
- `GET /executions/{execution_id}`
- `POST /executions/{execution_id}/pause`
- `POST /executions/{execution_id}/cancel`
- `GET /executions/{execution_id}/deliveries`
- `GET /executions/{execution_id}/metrics`

The server must enforce mock mode. No client field may switch R1 to live mode. API deployment must not contain real provider credentials or provider endpoints.

## 8. Response and error conventions

Collection example:

```json
{"data":[],"pagination":{"next_cursor":null,"has_more":false}}
```

Error example:

```json
{"error":{"code":"CAMPAIGN_ACCESS_DENIED","message":"You do not have permission to access this campaign.","request_id":"req-example-123"}}
```

Status codes: 200 success; 201 created; 202 accepted async operation; 204 no body; 400 malformed/invalid operation; 401 unauthenticated; 403 unauthorized; 404 missing or intentionally concealed resource; 409 state/idempotency conflict; 413 upload too large; 422 schema validation; 429 rate limited; 500 generic server failure.

## 9. Contract gaps to resolve

Invitation acceptance and expiry; password recovery; organization onboarding; consent history and withdrawal; import retry/recovery; scheduling/rescheduling; execution re-run semantics; campaign feedback; analytics metric definitions; provider webhook contract and tenant attribution; AI endpoints in R2; export download/expiry; exact channel payload schema; idempotency key scope and retention.

## 10. Postman coverage

Collections: Auth, Organizations/Members/Roles, Audience/Imports, Segments/Consent, Campaigns/Versions/Localization, Approvals, Mock Executions/Deliveries, Analytics. Environments should use test tenant IDs and test accounts. Include positive, validation, unauthorized, revoked-role, cross-tenant and idempotency tests.

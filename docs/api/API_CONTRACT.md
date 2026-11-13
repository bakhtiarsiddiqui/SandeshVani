# SandeshVani — API contract and implementation inventory

**Base path:** `/api/v1`  
**Format:** JSON over HTTPS; CSV upload is multipart.  
**Reviewed:** 2026-11-13  
**Status:** This document contains a verified inventory of current route definitions plus a clearly separate future API design. It is not a substitute for FastAPI-generated OpenAPI.

> Before implementing or integrating an endpoint, inspect the route, Pydantic schema, service, authorization dependencies and current `/openapi.json`. Do not implement a planned endpoint just because it appears in the future API section.

## 1. Contract authority

The running FastAPI application's generated OpenAPI and current route/schema source are authoritative for current request/response shapes. This file records route coverage and design intent. If it conflicts with source/OpenAPI, source/OpenAPI for the checked-out revision wins; update this document in the same code change.

Common requirements:
- UUID resource identifiers and UTC timestamps where applicable.
- Tenant context must be derived from authenticated membership and validated active organization. Client-provided organization ID is never authorization evidence.
- Server-side resource authorization; frontend route/visibility gates are presentation only.
- Cookie-authenticated mutations must preserve CSRF and trusted-origin protections.
- Use bounded pagination and allowlisted filters; do not compile user-supplied filters into raw SQL.
- Do not log secrets, access tokens, refresh tokens, raw recovery tokens or unnecessary PII.

## 2. Implemented route inventory on reviewed main

The following routes are present in the reviewed source tree. Verify exact schema and response details in current OpenAPI/source.

### Health
- `GET /api/v1/health`

### Authentication (`/api/v1/auth`)
- `POST /register`
- `POST /verify-email`
- `POST /resend-verification`
- `POST /login`
- `POST /refresh`
- `POST /logout`
- `POST /logout-all`
- `GET /me`
- `POST /select-org`
- `POST /password-recovery`
- `POST /password-reset`

Local auth email/token delivery is a development/test mechanism constrained by backend configuration and in-process capture; do not invent an HTTP mailbox endpoint or document raw-token retrieval routes.

### Organizations (`/api/v1/organizations`)
- `GET /` — list organizations for the authenticated user.
- `POST /` — create an organization.
- `GET /current` — retrieve active organization context.
- `GET /{organization_id}` — retrieve an organization subject to membership checks.
- `GET /{organization_id}/members`
- `POST /{organization_id}/members`
- `GET /{organization_id}/roles`
- `POST /{organization_id}/members/{membership_id}/roles`
- `DELETE /{organization_id}/members/{membership_id}/roles/{role_id}`
- `GET /{organization_id}/permissions`

No invitation acceptance, arbitrary role-permission administration or organization PATCH route is part of this current inventory.

### Audience (`/api/v1/audiences`)
- `GET /` — tenant-scoped list with bounded cursor, search/status/district/language filters.
- `POST /` — create one contact.
- `GET /{audience_id}` — retrieve one contact.
- `PATCH /{audience_id}` — update supplied contact fields.
- `POST /imports` — file-level CSV validation and private storage; returns HTTP 202.

**AUD-02 boundary:** `POST /imports` currently validates and stores the CSV and its tenant-scoped metadata. It does not create contacts, create an asynchronous import job, publish an outbox event, run a Celery worker, expose progress/error APIs or deduplicate records. Do not describe the upload response as an import-job response.

## 3. Implemented audience semantics

The current CRUD fields include full name, email, phone, preferred language (English/Hindi), district and active/inactive status. At least one contact point is required. List pagination is bounded (limit 1–100; default 25); filter names and schema constraints are defined in source.

The upload accepts one CSV file subject to file-level validation and configured limits (default 25 MiB and 100,000 nonblank rows). Files are stored outside frontend static content with generated names and private permissions. Upload metadata is tenant-owned and protected with PostgreSQL RLS. Duplicate identity matching is not implemented; no consent is inferred from an import or contact record.

## 4. Planned API surface — not an implementation contract

The following domains are required or contemplated by the product plan, but are not present as complete route groups on reviewed main:
- Import job status/progress and row-error pagination.
- Duplicate detection and resolution.
- Segments and segment preview.
- Consent history, withdrawal and suppression.
- Permissioned audience exports.
- Campaigns, immutable versions, templates and localized content.
- Campaign preview, submission and version history.
- Approvals, reviewer decisions and audit queries.
- Mock executions, delivery detail, metrics and analytics.

These endpoints must be designed from the accepted domain model, permission catalogue and state machines. Do not invent route names, fields, enums, error semantics or pagination patterns in the frontend.

## 5. Planned API conventions and state controls

- Use Pydantic request and response models and a consistent error envelope.
- Use 401 for unauthenticated, 403 for denied, 404 where intentional resource concealment applies, 409 for state/idempotency conflict, 413 for upload limit, 422 for schema validation and 429 for rate limiting as appropriate to the actual implementation.
- State-changing operations should be idempotent where retry is possible; idempotency key scope/retention remain to be defined.
- Future approval must bind to an immutable version/hash. Future distribution must re-check consent/suppression and current workflow state.
- No client field may enable live mode in R1.

## 6. Postman and contract test coverage

As routes are added, maintain positive, validation, unauthenticated, unauthorized, revoked-role, cross-tenant, CSRF/origin, idempotency and failure/retry tests. Keep Postman collections aligned with generated OpenAPI. A schema/route drift check is desirable once a stable contract export workflow is established.

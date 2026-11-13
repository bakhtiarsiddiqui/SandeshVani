# Role-workspace API integration — implementation slice

## Connected to existing server contracts

### Audience & Contacts

The workspace consumes the current audience API routes:

- GET /audiences with limit, opaque cursor, search, status, district and language.
- POST /audiences to create one contact.
- PATCH /audiences/{audience_id} to update editable fields and active/inactive status.
- POST /audiences/imports to validate and privately store a CSV upload.

The CSV endpoint returns upload metadata only. It does not import contacts, create an asynchronous import job, publish an outbox event or expose progress/errors. The UI states this boundary explicitly.

Audience forms send the current schema fields: full_name, email, phone, preferred_language (en/hi) and district; updates may also include status. Tenant context is attached by the shared Axios client and authorization is enforced by the backend.

### Organization Administration

The workspace consumes the existing organization routes:

- GET /{organization_id}/members for membership and assigned-role views.
- GET /{organization_id}/roles for organization-scoped roles and permissions.
- POST /{organization_id}/members to add an already-registered account and initial organization role assignments.
- POST /{organization_id}/members/{membership_id}/roles to assign a role.
- DELETE /{organization_id}/members/{membership_id}/roles/{role_id} to remove a role.

The UI calls this an "Add existing account" action, not an invitation. The current API returns 404 when the email has not registered; there is no invitation workflow. Platform roles are not in the organization role catalogue and cannot be assigned from this screen.

## Deliberately not implemented in this slice

The following UI domains remain demonstrative until the corresponding server contracts, state transitions and permission policies are approved:

- Campaign CRUD, versioning and campaign state machine.
- Post/template persistence and immutable template versions.
- Channel/purpose consent, evidence, withdrawal and suppression.
- Segment storage, allowlisted filter grammar and eligibility preview.
- Approval records, version/hash binding, separation of duties and decision history.
- Distribution execution and measured analytics.
- Global platform organization/user directory endpoints and platform-specific read permissions.

These are not safe to infer from UI mockups. The decision register identifies open policies for consent/retention, campaign/delivery state machines, approval self-review/quorum and audit retention/tamper-evidence. No route, migration, permission code or state is invented for them.

## Verification

Frontend unit tests cover API request shapes, file-only upload semantics and organization-role actions. Full frontend CI and Chromium desktop/mobile browser checks are required on the implementation branch before review. No backend migration or backend source changes are introduced by this slice.

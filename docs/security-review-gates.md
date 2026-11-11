# Security review gates

Human approval required for:
1. PostgreSQL RLS, tenant context, DB roles and grants.
2. Authentication/session/token handling.
3. Membership, multi-role RBAC and authorization.
4. Consent, purpose/channel checks and opt-out.
5. Campaign immutability, approval version/hash and audit.
6. Outbox, idempotency, retries and unknown outcomes.
7. Tenant-owned data migrations and constraints.
8. Any code that could enable real external dispatch.

Minimum tenant test matrix:
- Org A cannot read/update/delete Org B rows by supplied or guessed IDs.
- Tenant-owned child cannot reference another tenant's parent.
- Missing tenant context fails closed.
- RLS is active for runtime role; role is not owner and has no BYPASSRLS.
- Tests run under runtime role, not only privileged owner.
- Background jobs re-establish/validate tenant context.

MVP dispatch must terminate in mock implementations. Add a test/check that no provider SDK, production credential or real outbound path is present.

# SandeshVani Backend

FastAPI modular monolith backend service.

## Local Setup

### 1. Create Virtual Environment
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements-dev.txt
```

### 3. Run Checks and Tests
```bash
ruff check .
ruff format --check .
pytest -q
```

### 4. Start Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
Visit http://localhost:8000/api/v1/health or http://localhost:8000/api/v1/docs.

## Production security configuration

Production startup is intentionally fail-fast. Set `DEPLOYMENT_ENVIRONMENT=production`
only after providing a matching `JWT_PRIVATE_KEY_PEM` / `JWT_PUBLIC_KEY_PEM` pair
for `JWT_ALGORITHM` (`RS256` with an RSA key of at least 2048 bits, or `EdDSA`
with Ed25519 keys). The service never generates a production signing key.

Also configure a unique `CSRF_SECRET` of at least 32 bytes, `COOKIE_SECURE=true`,
and `ALLOWED_ORIGINS` as a JSON array of exact HTTPS frontend origins. Wildcards,
HTTP origins, paths, credentials, queries, and fragments are rejected in production.
`COOKIE_SAMESITE=none` is allowed only with secure cookies. The local mail sink is
always prohibited in production.

JWT keys and the CSRF secret must be rotated through the secret manager rather than
source control. Deploy a verifier that accepts the outgoing public key during a
short overlap, switch signing to the new key, wait for the maximum access-token
lifetime, then remove the retired verifier. Rotate the CSRF secret during a planned
maintenance window: existing CSRF tokens will be invalidated and users may need to
refresh or sign in again. Do not log PEM material, JWTs, or CSRF secrets.

## Tenant isolation and PostgreSQL RLS

Organization context is derived only after the API verifies the authenticated
user's active membership. An active organization in a JWT or the
`X-Organization-ID` header is a requested context, never authorization by
itself. Organization routes re-check membership and role permissions on every
request; organization discovery is restricted to active memberships.

Tenant-owned tables are `memberships`, `membership_roles`, organization-scoped
`roles`, and organization-scoped `role_permissions`. PostgreSQL migrations set
the transaction-local `app.current_org` value with `set_config(..., true)` and
apply `ENABLE ROW LEVEL SECURITY` plus `FORCE ROW LEVEL SECURITY` to the
tenant-owned tables. Missing tenant context denies organization-owned rows;
platform roles and permissions are a deliberately separate global scope.
Composite foreign keys prevent a membership role or role permission from
referencing a role in another organization.

Run Alembic with `MIGRATION_DATABASE_URL` set to a dedicated migration-owner
connection. `MIGRATION_DATABASE_ROLE` is optional and only used for a validated
transaction-local `SET ROLE` when that connection must assume the owner role;
the runtime application's database URL must remain a separate restricted role.

Use a normal application database role that is not a superuser and does not
have `BYPASSRLS`. It should not own protected tables; until a separate migration
owner is deployed, forced RLS protects owner access too. Run the PostgreSQL
suite only with an isolated disposable administrator URL:

```bash
SANDESHVANI_PG_TEST_URL="$SANDESHVANI_PG_TEST_URL" \
  PYTHONPATH=backend backend/.venv/bin/pytest -c backend/pyproject.toml \
  backend/tests/test_rls_integration.py -v
```

The suite creates and removes a dedicated test database and temporary test
roles; never point it at a development or production database. Background jobs
are not implemented yet. When they are, each job must receive a verified
organization ID and establish transaction-local tenant context before accessing
tenant-owned data.

## Local Authentication Mail Sink

The example local settings opt in to an in-memory development mail sink with
`DEPLOYMENT_ENVIRONMENT=development`, exact `APP_ENV=local`, and
`ENABLE_LOCAL_MAIL_SINK=true`. Verification and recovery
messages are captured on the FastAPI app instance and can be inspected by the
backend test harness through `app.state.development_mail_sink.messages`.
There is deliberately no HTTP mailbox or token-retrieval endpoint. The sink is
process-local, is cleared on restart, is disabled by default, and is not an email
provider. Production configuration must not enable the local sink.


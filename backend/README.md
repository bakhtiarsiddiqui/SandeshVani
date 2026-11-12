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

## Private audience CSV uploads

Audience CSV uploads are stored as opaque UUID-named files under
`AUDIENCE_IMPORT_STORAGE_DIR` (default: `./var/private/audience-imports`).
The directory is created with mode `0700`; stored files use mode `0600`.
Configure this path as a private persistent volume outside any static/web-served
directory in deployed environments. Do not expose it through FastAPI static files
or a reverse-proxy alias.

The default limits are 25 MiB and 100,000 nonblank data rows. Override them with
`AUDIENCE_IMPORT_MAX_BYTES` and `AUDIENCE_IMPORT_MAX_ROWS`. The upload endpoint
checks the UTF-8 CSV structure and an allowlisted header set, then records the
tenant, uploader, size, row count and SHA-256 checksum. It does not parse rows
into audience contacts or start an import worker; those are separate tasks.
The original client filename and filesystem path are not persisted or returned.

## Local Authentication Email

Local registration, verification resend, and password-recovery messages are
captured by the in-memory development mail sink for deterministic backend
tests. To inspect messages during interactive development, use Mailpit:

```bash
docker run -d --name sandeshvani-mailpit --restart unless-stopped \
  -p 127.0.0.1:8025:8025 -p 127.0.0.1:1025:1025 axllent/mailpit:latest
```

Set these values in the untracked local `.env` file:

```dotenv
DEPLOYMENT_ENVIRONMENT=development
APP_ENV=local
ENABLE_LOCAL_MAIL_SINK=true
DEV_MAIL_SMTP_HOST=127.0.0.1
DEV_MAIL_SMTP_PORT=1025
DEV_MAIL_SMTP_STARTTLS=false
DEV_MAIL_SMTP_USERNAME=
DEV_MAIL_SMTP_PASSWORD=
DEV_MAIL_FROM=no-reply@sandeshvani.local
```

Open the Mailpit inbox at http://127.0.0.1:8025. Mailpit receives local
verification and password-reset emails over SMTP. Its SMTP and UI ports are
bound to loopback only. The in-memory sink remains available to the test harness
through `app.state.development_mail_sink.messages`; no HTTP endpoint exposes
raw development tokens. The sink is process-local and is cleared on backend
restart. This development transport is not a production email provider.

Production configuration must not enable the local sink or Mailpit transport.
A production transactional email provider, sender-domain verification (SPF,
DKIM, and DMARC), retry handling, and delivery monitoring remain a separate
production-readiness task.

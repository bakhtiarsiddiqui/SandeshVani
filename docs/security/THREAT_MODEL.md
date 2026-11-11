# SandeshVani — Threat Model v2

**Scope:** MVP modular monolith, PostgreSQL/RLS, Redis/Celery workers, file imports/exports, mock channel adapters and later provider/AI extensions.

## 1. Assets

Tenant audience/contact data; consent and suppression evidence; campaign content and immutable versions; approvals; credentials/sessions; delivery state; audit records; uploaded/exported files; provider secrets (later release); AI prompts/output (later release).

## 2. Trust boundaries

1. Browser/client to API.
2. Tenant A to tenant B.
3. API application to PostgreSQL/RLS.
4. API/outbox publisher to Redis/Celery workers.
5. Workers to channel adapters.
6. File upload/storage/worker processing.
7. Future external provider/webhook boundary.
8. Future AI provider boundary.

## 3. Threat register

| ID | Threat | Impact | Required controls |
|---|---|---|---|
| TH-01 | Tenant spoofing/BOLA | Cross-tenant data access | Resolve tenant from membership; resource ownership checks; RLS; composite FKs; negative tests |
| TH-02 | Privilege escalation | Unauthorized role/action | Deny-by-default RBAC; grant authority checks; platform/tenant role separation; audit |
| TH-03 | Multi-role overgrant | Permission union exceeds intended policy | Least privilege; explicit permission catalog; test combined roles; no implicit inheritance |
| TH-04 | Session theft/account takeover | Unauthorized access | Argon2id; secure HttpOnly cookies; CSRF; rotation/expiry/revocation; rate limits; recovery controls; MFA for privileged users where feasible |
| TH-05 | Approval tampering | Unapproved content distributed | Immutable versions; content hash; reviewer authorization; separation of duties; audit |
| TH-06 | Duplicate/incorrect delivery | Repeated or wrong communication | DB uniqueness/idempotency; outbox; bounded retries; explicit unknown state; mock-only isolation |
| TH-07 | Queue poisoning/replay | Worker executes forged/stale job | Validate task schema; re-check tenant and state; least-privilege worker; idempotent consumer |
| TH-08 | Malicious/oversized CSV | Resource exhaustion/code execution | Size limits; content validation; safe parser; malware scanning where available; bounded chunks; isolated storage |
| TH-09 | CSV formula injection | Export executes spreadsheet formulas | Escape dangerous cell prefixes; safe export tests |
| TH-10 | PII leakage in logs/errors | Privacy breach | Minimize/redact logs; safe error reports; access-controlled exports |
| TH-11 | Consent/suppression bypass | Unwanted communication | Recheck at execution; channel/purpose-specific policy; fail closed on unknown consent where required |
| TH-12 | Fake/replayed webhook (R3) | Forged delivery state | Raw-body signature verification; timestamp/replay checks; provider event dedupe; tenant mapping |
| TH-13 | Secret exposure | Provider/account compromise | Secret manager/environment injection; rotation; no frontend secrets; no secrets in logs |
| TH-14 | Export abuse | Bulk PII exfiltration | Explicit export permission; audit; masking; expiring download links; quotas |
| TH-15 | Audit tampering | Loss of evidence | Restricted append path; separate retention/export; monitoring; external immutable archive for production if required |
| TH-16 | Deletion abuse | Evidence/data removed improperly | Retention policy; legal hold; controlled deletion; audit |
| TH-17 | SSRF | Backend accesses attacker-controlled endpoint | Avoid arbitrary URL fetch; egress restrictions; allowlist if fetching is needed |
| TH-18 | Dependency/supply-chain compromise | Code/data compromise | Lockfiles; dependency scanning; pinned/reviewed updates; CI checks |
| TH-19 | Mock/live boundary failure | Accidental real dispatch | No live SDK/credentials/endpoints in R1; separate adapter registry; deployment/network tests; server-side fixed mock mode |
| TH-20 | AI prompt injection/data leakage (R2) | Unsafe content or PII disclosure | Treat user/imported text as untrusted; minimize PII; no approval/dispatch tools; schema validation; human review; provider assessment |

## 4. Required controls

**Authentication:** Argon2id password hashing; secure session cookie; CSRF protection; session rotation/expiry/revocation; rate limits; generic auth errors; secure recovery; privileged MFA decision.

**Authorization/tenancy:** deny by default; check every API request; derive tenant from membership; validate resource ownership; PostgreSQL RLS; non-owner DB role without `BYPASSRLS`; transaction-local tenant context; composite tenant-safe FKs; validate worker tenant context; cross-tenant test suite.

**Data/files:** TLS; encryption at rest; encrypted/tokenized contact fields as appropriate; keys outside DB; PII masking; upload size/type/content validation; controlled storage; safe spreadsheet export; retention/deletion/legal hold policy.

**Campaign/delivery:** immutable approved versions; explicit state machine; separation of duties; server-enforced mock-only mode; transactional outbox; idempotent consumers; retry backoff/jitter; exhausted-work handling; unknown-outcome reconciliation; pause/cancel checks.

**Future webhooks:** verify provider signature against raw body; replay/timestamp checks; dedupe provider event IDs; validate event-to-delivery and provider-account-to-tenant ownership.

**Future AI:** untrusted-input isolation; no approval/dispatch tools; minimize PII; validate structured output; record provider/model/prompt version; human review; language-specific evaluation.

## 5. Security acceptance tests

Cross-tenant reads/writes denied; org admin cannot grant platform role; combined role grants are as specified; revoked session/membership denied; approved version immutable; draft/rejected version cannot execute; duplicate execution does not create duplicate logical delivery; worker validates tenant and current state; oversized/malformed CSV rejected; export is permissioned and formula-safe; invalid segment grammar rejected; R1 environment cannot reach real providers; future webhook replay test required before R3.

## 6. Residual risks and release gates

RLS misconfiguration or privileged DB credentials can defeat isolation. Encryption requires key lifecycle. Consent obligations vary by purpose/channel/jurisdiction and require legal review. Mock adapters do not prove real provider semantics. Indic translation quality requires human evaluation. An audit table alone is not tamper-proof. Load targets require representative tests. Do not enable live dispatch until provider, legal, security, operational and rollback gates have named owners and evidence.

Account verification and password recovery have no external email integration. For local tests, a process-local in-memory mail sink captures recipient-associated messages only when `DEPLOYMENT_ENVIRONMENT=development`, raw `APP_ENV=local`, and `ENABLE_LOCAL_MAIL_SINK=true`; all three are required and each defaults safely (deployment mode defaults to production, sink opt-in defaults off). Messages are inspectable only through the in-process test harness/app state. There is no HTTP mailbox or token-retrieval route, and OpenAPI contains no development mail contract. Public resend/recovery responses have identical status and body for known/unknown addresses; response-body/status enumeration is mitigated. The API applies a shared fixed-window recovery limit of 5 requests per normalized email and 30 per socket-peer IP per 15 minutes by default (`AUTH_RECOVERY_EMAIL_LIMIT`, `AUTH_RECOVERY_IP_LIMIT`, `AUTH_RECOVERY_RATE_WINDOW_SECONDS`). Email and IP keys are process-random HMAC digests; raw addresses are not retained in limiter state. Repeated timing measurements are mitigated by rate limits, but not eliminated: eligible accounts still write a token row while ineligible/unknown accounts do not. No artificial delay is used. Durable asynchronous processing is deferred until production email delivery is designed; do not describe the timing risk as fully resolved. The limiter is process-local, resets on restart, and is not shared across workers or instances. Behind a reverse proxy, `request.client.host` may identify the proxy; configure trusted proxy handling and enforce shared ingress limits before production exposure. Raw tokens and raw addresses must never be logged or used as limiter keys.

Registration intentionally retains its existing `409` response for duplicate addresses for compatibility; unlike password recovery and verification resend, this endpoint can disclose whether an address is registered. Change this behavior only with an explicit product/API compatibility decision.

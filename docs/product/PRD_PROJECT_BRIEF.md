# SandeshVani — Product Requirements Document / Project Brief

**Version:** 3.0  
**Status:** Planning baseline  
**Product category:** Multi-tenant public-awareness and mass-communication platform

## Brand and positioning

**SandeshVani (संदेशवाणी)** is the selected working brand. The product is positioned as trusted public communication and awareness technology for institutions and communities. Working tagline: “Har zaroori baat, har zaroori insaan tak.” Domain and trademark clearance remain open; see `../brand/BRAND_IDENTITY.md`.

## 1. Problem and product

SandeshVani is a proposed platform for organizations such as public departments, universities and NGOs to manage audiences, prepare public-awareness campaigns, review and approve content, and execute controlled communication workflows. Each organization must be isolated from other tenants. The MVP demonstrates the complete governed workflow using simulated communication providers only.

## 2. Goals

1. Multi-organization workspaces with strict tenant isolation.
2. Organization-scoped membership and RBAC, including multiple roles per membership.
3. Audience CRUD, CSV import, segmentation, consent and suppression foundations.
4. Versioned campaigns, reusable templates, localization foundation and approvals.
5. Mock distribution through Email, SMS, WhatsApp and Push adapters.
6. Durable delivery state, auditability and useful basic analytics.
7. Architecture designed for a 100,000-recipient campaign, with performance claims subject to load testing.

## 3. Users and roles

- **Platform Operator:** tightly controlled platform-level operations.
- **Organization Administrator:** manages their organization and membership/role assignments within granted authority.
- **Campaign Manager:** creates and manages campaigns and audiences within grants.
- **Communication Team:** prepares content, templates and language variants.
- **Approver:** reviews a specific submitted campaign version; permission is policy-granted.

A person may belong to multiple organizations and may hold multiple roles in each organization. Effective permissions are evaluated only within the active organization context. The role names are suggested personas; the permission catalog is authoritative.

## 4. MVP scope (Release 1)

- Identity, sessions, organizations, memberships and multiple-role RBAC.
- Tenant isolation using application scoping and PostgreSQL RLS.
- Audience CRUD, CSV import, deduplication, segments, consent history and suppression.
- Campaigns, immutable versions, templates and channel/language previews.
- English and Hindi content variants; extensible language registry for additional Indic languages.
- Human approval bound to exact version/hash; audit log.
- Recipient snapshots, channel delivery records and asynchronous execution through mock Email, SMS, WhatsApp and Push adapters.
- Basic campaign and channel delivery analytics.
- Operational logging, security tests, backup/restore validation and 100k workload testing.

**MVP boundary:** no real dispatch, production provider credentials/SDKs/endpoints, autonomous AI, AI targeting, AI approval/dispatch, microservices, Kubernetes, Kafka, multi-region active-active, production analytics warehouse or arbitrary SQL segment filters.

## 5. Later releases

- **Release 2 — Intelligence and localization:** opt-in AI drafting, translation suggestions, human translation review, content quality checks, personalization and enhanced analytics. Provider selection remains open and requires privacy, language-quality, cost and latency evaluation.
- **Release 3 — Production distribution and engagement:** real Email/SMS/WhatsApp/Push providers, scheduling, provider webhooks, rate controls, feedback/engagement collection and advanced analytics. Each provider requires its own operational and compliance release gate.

## 6. Core journeys

**Audience:** create/import → validate → deduplicate → segment → preview eligibility.  
**Campaign:** draft → choose template/version, channel(s), languages and segments → prepare content → validate → preview → create immutable version → submit.  
**Approval:** reviewer inspects exact version and hash → approve/reject with rationale → audit decision.  
**Mock execution:** approved version → re-check eligibility → recipient snapshot → delivery intents and outbox transaction → worker → mock adapter → attempts/status.  
**Analytics:** authorized user views tenant-scoped campaign and channel metrics; accepted, delivered, failed, retrying and unknown remain distinct.

## 7. Product invariants

- Tenant context derives from authenticated membership, never from an untrusted client organization ID.
- Tenant-owned records and relationships are organization-scoped.
- Memberships can have multiple roles; roles and effective permissions are scoped to the organization.
- Approved campaign versions are immutable; material edits require a new version and approval.
- Missing consent is not permission; consent is channel- and purpose-specific.
- Eligibility and suppression are checked again at execution time.
- Provider acceptance is not delivery confirmation.
- Queue consumers and future webhooks are idempotent.
- Sandbox/mock-only behavior is enforced server-side and structurally isolated from live providers.
- AI suggestions require human review; AI cannot approve or dispatch.

## 8. Success criteria

- Cross-tenant read/write tests pass across all tenant-owned domains.
- Multiple roles per membership and role revocation behave correctly.
- Audience import, segmentation, consent and suppression work with auditable outcomes.
- English and Hindi variants can be authored and previewed; language registry is extensible.
- Approval is tied to the exact immutable version/hash.
- All four mock channels execute without any real provider access.
- Idempotency, retry, worker interruption and unknown-outcome behavior are tested.
- Postman/API tests cover positive, validation, unauthorized and cross-tenant cases.
- A documented representative 100,000-recipient workload test reports throughput, duration, resource use and failures.

## 9. Planning schedule

The original v1 six-week sequence is retained as a **proposed minimum implementation sequence**, not a guaranteed delivery commitment. The staged roadmap in `../implementation/ROADMAP.md` is authoritative for dependencies and exit gates. Duration must be re-estimated after ERD, API and workload acceptance criteria are finalized.

## 10. Open product decisions

Organization onboarding and hierarchy; legal basis/consent policy per channel and purpose; separation-of-duties policy; retention/deletion and legal hold; additional Indic languages beyond English/Hindi; exact 100k workload and completion-time objective; RPO/RTO; provider selection and live-provider policy; final brand/name confirmation.

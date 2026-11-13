# Approved decision register

**Decision status:** 2026-11-13  
**Implementation baseline:** Refer to the repository status snapshot and the current branch/PR evidence. An approved design decision does not mean its schema, API or UI is implemented.

| Area | Decision |
|---|---|
| Brand | SandeshVani (संदेशवाणी) |
| Tagline | Har zaroori baat, har zaroori insaan tak. |
| Domain | sandeshvani.in selected/intended; registration not asserted |
| Historical codename | CivicReach |
| Product | Multi-tenant institutional/public-awareness communication |
| Architecture | Modular monolith + separate Celery workers |
| Frontend | React + JavaScript + Vite + Tailwind CSS + DaisyUI |
| Backend | FastAPI/Python |
| Database | PostgreSQL |
| ORM/migrations | SQLAlchemy 2.x + Alembic |
| Async | Celery + Redis (selected target; not necessarily integrated on main) |
| API | REST JSON /api/v1, OpenAPI |
| Tenancy | organization_id, tenant-scoped services/repos, PostgreSQL RLS, transaction-local context, composite tenant-safe FKs |
| Runtime DB role | Not table owner; no BYPASSRLS |
| Outbox | PostgreSQL authoritative; Redis/Celery transport |
| Approval | Immutable approved versions; approval binds to exact version/hash |
| Consent | Separate processing basis, channel permission and suppression; unknown consent blocks wherever consent is required |
| Reliability | Idempotent jobs/webhooks, bounded backoff, explicit unknown outcomes |
| MVP channels | mock_all, mock Email/SMS/WhatsApp/Push only; no live providers or dispatch in R1 |
| MVP languages | English (en) and Hindi (hi), extensible registry |
| Membership | Multiple roles via membership_roles |
| Scale target | Campaigns up to 100,000 recipients; load-test evidence required before performance claims |
| MVP scheduling | Manual execution only; one-time scheduling is deferred to R3 |
| Post/content ownership | No independent Post entity in R1; campaign content variants are owned by campaign versions |
| Audience geography | Optional state_code (canonical India State/UT code) and city; retain district |
| Segmentation | Typed allowlisted fields/operators; state_code and city included; aggregate preview and execution-time re-evaluation |
| Approval separation | At least one independent Approver; creator and submitter cannot approve their own version |
| Platform directory | Read-only, metadata-focused global access through platform-scoped permissions; no implicit tenant access |

## Owner-approved R1 domain baseline

The product owner approved the seven-domain recommendations on 2026-11-13. The detailed contract, entity responsibilities, state transitions, eligibility rules and implementation gates are recorded in [R1_DOMAIN_DECISIONS.md](architecture/R1_DOMAIN_DECISIONS.md).

The seven approved areas are:

1. Campaigns: editable drafts, immutable submitted/approved versions, version hashes, manual mock execution in R1.
2. Posts and templates: campaign content variants, reusable immutable template versions; no second Post entity in R1.
3. Consent and suppression: distinguish data-processing basis from channel permission and suppression; preserve grant/withdrawal evidence; legal retention schedule remains open.
4. Approvals: hash-bound independent review; creator/submitter self-approval prohibited; no emergency bypass in R1.
5. Segmentation: typed allowlisted filter AST with state/city, aggregate preview and execution-time eligibility recheck.
6. Analytics: persisted recipient, logical-delivery and attempt metrics; accepted/delivered/failed/retrying/unknown remain distinct.
7. Platform directory: separately assigned global permissions, minimal metadata, no implicit cross-tenant access or tenant impersonation.

## Remaining open decisions and review gates

- Retention/deletion/legal hold schedule and evidence-retention periods require legal and organizational policy. No universal retention period is approved.
- Legal review must confirm sender classification, processing basis and public-interest eligibility for each intended organization/channel/purpose. An organization name or "public awareness" label is not an exemption.
- Future provider selection and live-provider policy remain deferred to a separately gated release.
- One-time scheduling is R3 scope; timezone, quiet-hours, cancellation and recovery details must be designed before that release.
- Organization creation/onboarding and hierarchy remain open.
- Exact workload mix, completion-time objective, RPO/RTO and operating limits remain open.
- Exact additional Indic-language launch set beyond English/Hindi remains open.
- AUD-03 import architecture remains subject to selecting one of the competing draft implementations. Do not merge both or create a conflicting migration revision.
- Audience state_code/city are approved additions to the target contract, not yet implemented on the current backend. Their migration must follow the selected AUD-03 revision.

## Implementation interpretation

- A selected or approved design is not proof of implementation.
- Existing source, migrations, tests, OpenAPI and current CI determine what is implemented and verified.
- R1 must remain mock-only. Real provider credentials, SDKs, webhooks and dispatch require a separate legal/security/operational release gate.
- UI permissions do not replace backend authorization.

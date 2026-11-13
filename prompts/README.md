> **ARCHIVAL / SUPERSEDED:** This is the former Project Documentation Pack v4 planning snapshot dated 2026-11-04. It is retained for history only and is not the current implementation status, agent instruction source or authoritative documentation index. Do not use it to decide what is implemented. Start at [root AGENTS.md](../AGENTS.md), [docs index](../docs/README.md), [project status](../docs/PROJECT_STATUS.md) and [decision register](../docs/decision-register.md). Its stack and feature lists may include target architecture and planned features that are not present in the current main branch.

---

# SandeshVani Documentation Pack v4

**Version:** 4.0 brand-aligned planning baseline  
**Status:** Draft for review; not an implementation or production certification  
**Updated:** 2026-11-04

**SandeshVani (संदेशवाणी)** is the selected working brand for a proposed multi-tenant public-awareness and mass-communication platform for organizations such as public departments, universities and NGOs. The selected domain is **`sandeshvani.in`** (reported available by the project owner; registration is not yet verified). CivicReach is retained only as the historical project codename.

## Confirmed baseline

- Multi-tenant, organization-managed accounts; mixed-sensitivity data.
- Campaign design target: up to 100,000 recipients, subject to representative load testing.
- Modular monolith: React + JavaScript + Vite + Tailwind CSS + DaisyUI; FastAPI; PostgreSQL; SQLAlchemy 2.x; Alembic; Celery + Redis; Docker Compose.
- Organization memberships support **multiple roles per organization** through `membership_roles`.
- MVP supports **mock Email, SMS, WhatsApp and Push** adapters only. No real dispatch, provider credentials, SDKs or endpoints are permitted in the MVP execution path.
- MVP language baseline: **English and Hindi**, with an extensible registry/foundation for additional Indic languages. The exact additional language launch set remains open.
- Campaign approval is bound to an immutable version and content hash. Missing consent is not permission. AI cannot approve or dispatch.
- PostgreSQL is the source of truth; transactional outbox is authoritative; Redis/Celery transport and execute work.

## Document map

| Folder | Contents |
|---|---|
| `docs/product/` | PRD and Requirements Traceability Matrix |
| `docs/brand/` | Brand identity, positioning and domain decision |
| `docs/architecture/` | System architecture, logical data model, technology decisions |
| `docs/api/` | REST API contract and conventions |
| `docs/security/` | RBAC matrix and threat model |
| `docs/workflows/` | End-to-end user and system flows |
| `docs/design/` | UI/UX functional specification |
| `docs/implementation/` | Roadmap and ordered task breakdown |

## Brand decision

- **Selected working brand:** SandeshVani (संदेशवाणी).
- **Selected domain:** `sandeshvani.in` (reported available by the project owner on 2026-11-04; registration remains unverified).
- **Positioning:** trusted, inclusive public communication and awareness technology for institutions and communities.
- **Primary tagline:** “Har zaroori baat, har zaroori insaan tak.”
- **Brand status:** working name and domain selection confirmed; registration, trademark, company-name and social-handle clearance remain open.
- **Historical codename:** CivicReach; not a public-facing brand.

See `docs/brand/BRAND_IDENTITY.md` for details and launch checks.

## How to use this pack

1. Treat this pack as the current planning baseline, not as evidence that anything has been implemented.
2. Review unresolved decisions in `docs/product/REQUIREMENTS_TRACEABILITY_MATRIX.md` and `docs/architecture/DATA_MODEL_SCHEMA.md` before freezing migrations.
3. Keep API schemas, ERD, permission catalog and acceptance tests synchronized as implementation proceeds.
4. Record material architecture changes as Architecture Decision Records (ADRs), including rationale and migration/rollback implications.
5. Do not enable live providers as an informal configuration change; that is a later release with separate security, legal, provider and operational gates.

## Source and change notes

This v4 pack carries forward the v3 technical baseline and updates the public-facing brand from Sandesh to SandeshVani. No product scope or engineering decision is changed by this brand update. The domain selection is recorded as user-reported availability, not verified registration. The prior v1/v2/v3 packs should be retained as archival snapshots.

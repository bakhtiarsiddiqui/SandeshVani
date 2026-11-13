# SandeshVani decision register

**Status date:** 2026-11-13  
**Implementation baseline:** `main` at `c88e270add18c6b0a4259fa5dbb310afa69534e7`.

This register distinguishes a decision from its implementation. "Selected target" does not mean the corresponding code or infrastructure exists on `main`.

## Product and architecture decisions

| Area | Decision | Maturity on reviewed main |
|---|---|---|
| Public working brand | SandeshVani (संदेशवाणी) | Selected |
| Tagline | Har zaroori baat, har zaroori insaan tak. | Selected |
| Domain | `sandeshvani.in` | Selected/intended; registration and legal clearance not verified |
| Historical codename | CivicReach | Historical only |
| Product | Multi-tenant institutional/public-awareness communication | Product direction selected |
| Architecture | Modular monolith; no premature microservices | Current architecture direction |
| Frontend language/framework | React + JavaScript + Vite | Implemented |
| Frontend styling | Tailwind CSS 3 + DaisyUI 4 | Implemented |
| API client | Axios | Implemented |
| Visual identity | Gunmetal Blue / Warm Concrete / Saffron Gold | Implemented in PR #14 |
| Typography | Mukta for Latin and Devanagari | Implemented in PR #14 |
| Decorative 3D | Three.js sign-in scene only; not required by core auth | Implemented in PR #14 |
| Backend | Python + FastAPI + Pydantic | Implemented |
| Database | PostgreSQL | Implemented |
| ORM/migrations | SQLAlchemy 2.x + Alembic | Implemented |
| API style | REST JSON under `/api/v1`; FastAPI-generated OpenAPI describes current runtime routes | Implemented for current routes |
| Tenancy | Organization-scoped services/repositories, transaction-local tenant context, PostgreSQL RLS and tenant-safe constraints | Implemented foundation; extend/test for every new tenant-owned table |
| Membership roles | Multiple roles through `membership_roles` | Implemented foundation |
| Authentication | Short-lived access token plus persisted refresh-session lifecycle | Implemented foundation; see security ledgers |
| Async workers | Celery + Redis | Selected target; not integrated on reviewed main |
| Outbox | PostgreSQL authoritative outbox; queue is transport only | Selected target; not implemented on reviewed main |
| Local orchestration | Docker Compose | Intended local-dev approach; root Compose file absent on reviewed main |
| MVP delivery | Mock-only Email/SMS/WhatsApp/Push; no live providers | Product/security requirement; delivery engine not implemented |
| MVP languages | English (`en`) and Hindi (`hi`); extensible registry later | English/Hindi fields present in audience CRUD; campaign localization not implemented |
| Campaign scale | 100,000 recipients is a design/load-test target | Not measured; no performance claim |

## Frontend library constraints

The current frontend package contains React, React DOM, Axios, Mukta and Three.js, with Tailwind/DaisyUI and the existing Vite/Vitest/ESLint toolchain.

Do not treat the following previously mentioned libraries as selected dependencies: React Router, Recharts, React Hook Form, Zod, shadcn/ui, Flowbite or Preline. They are not part of the reviewed frontend dependency baseline. Do not add them without a concrete requirement, a comparison with existing patterns, license/dependency review and owner approval.

## MVP and release boundaries

- Release 1 must deliver a governed audience-to-approved-mock-distribution workflow.
- AI drafting/translation suggestions are deferred to a separately evaluated release; AI cannot approve or dispatch.
- Real provider adapters, credentials, webhooks and live distribution are deferred to a separately gated release.
- Kafka, Kubernetes, microservices, multi-region active-active and advanced analytics infrastructure are deferred until measurable requirements justify the operational cost.

## Unresolved decisions

Organization invitation/onboarding policy; audience duplicate identity and conflict policy; consent legal basis and retention by jurisdiction/channel/purpose; separation-of-duties policy; audit retention and tamper-evidence; supported languages beyond English/Hindi; campaign and delivery state machines; scheduling/recovery semantics; exact 100k workload and completion-time objective; RPO/RTO; future provider selection and webhook attribution.

Changes to the selected baseline require a written rationale, alternatives, security/operational impact, migration/rollback plan, and explicit human approval. Update this register and affected specs in the same change.

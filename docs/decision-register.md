# Approved decision register

| Area | Decision |
|---|---|
| Brand | SandeshVani (संदेशवाणी) |
| Tagline | Har zaroori baat, har zaroori insaan tak. |
| Domain | `sandeshvani.in` selected/intended; registration not asserted |
| Historical codename | CivicReach |
| Product | Multi-tenant institutional/public-awareness communication |
| Architecture | Modular monolith + separate Celery workers |
| Frontend | React + JavaScript + Vite + Tailwind CSS + DaisyUI |
| Backend | FastAPI/Python |
| Database | PostgreSQL |
| ORM/migrations | SQLAlchemy 2.x + Alembic |
| Async | Celery + Redis |
| Local dev | Docker Compose |
| API | REST JSON `/api/v1`, OpenAPI |
| Tenancy | organization_id, tenant-scoped services/repos, PostgreSQL RLS, transaction-local context, composite tenant-safe FKs |
| Runtime DB role | Not table owner; no BYPASSRLS |
| Outbox | PostgreSQL authoritative; Redis/Celery transport |
| Approval | Immutable approved versions; approval binds to version/hash |
| Consent | Channel/purpose-specific; missing consent is not permission |
| Reliability | Idempotent jobs/webhooks, bounded backoff, explicit unknown outcomes |
| MVP channels | `mock_all`, mock Email/SMS/WhatsApp/Push only |
| MVP languages | English (`en`) and Hindi (`hi`), extensible registry |
| Membership | Multiple roles via `membership_roles` |
| MVP exclusions | Real providers/dispatch, Kafka, Kubernetes, microservices, advanced ML targeting, AI approval/dispatch |
| Scale target | Campaigns up to 100,000 recipients |

Unresolved decisions stay unresolved: onboarding/org creation, hierarchy, separation of duties, retention, additional Indic languages, later provider selection, performance targets, RPO/RTO, scheduling/recovery semantics, recipient identity uniqueness and webhook attribution.

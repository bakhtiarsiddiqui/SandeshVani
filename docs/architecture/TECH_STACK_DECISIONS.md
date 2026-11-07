# SandeshVani — Technology Stack Decisions

**Status:** Selected baseline for MVP; changes require an ADR/change review.

## Frontend

| Technology | Decision | Rationale / note |
|---|---|---|
| React | Selected | Component-based SPA |
| JavaScript | Selected | Team preference; do not silently migrate to TypeScript |
| Vite | Selected | Development/build tooling |
| Tailwind CSS | Selected | Utility-first styling |
| DaisyUI | Selected | Tailwind component classes |
| React Router | Selected | Client-side routing |
| Axios | Selected | Central API client/interceptors |
| Lucide React | Selected | Icons |
| Recharts | Selected | Dashboard charts |
| React Hook Form | Selected | Form state |
| Zod | Selected | Client-side validation; backend remains authoritative |

## Backend and data

Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, pytest, HTTPX, PostgreSQL, Celery and Redis.

## Infrastructure and operations

Docker and Docker Compose for local development; GitHub Actions for CI. Structured logs and request IDs are baseline. Sentry and Prometheus/Grafana/OpenTelemetry may be introduced progressively based on operational need.

## Architecture decisions

- Modular monolith with separate worker processes.
- Shared-schema multi-tenancy with strict tenant isolation.
- Organization-scoped RBAC; multiple roles per membership via association table.
- Secure sessions; PostgreSQL is system of record.
- Celery + Redis for asynchronous execution; transactional outbox for durable publication.
- R1 uses mock adapters for Email, SMS, WhatsApp and Push only.
- English/Hindi content support and extensible Indic language registry.

## Deferred technologies

Kubernetes, Kafka, MongoDB, Elasticsearch, ClickHouse, vector database, microservices and multi-region active-active. Introduce only when measurable requirements justify their operational cost.

## Change process

Document the problem, alternatives, security/operational impact, migration and rollback plan, approval, and updated ADR before changing the baseline.

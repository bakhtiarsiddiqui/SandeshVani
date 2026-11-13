# SandeshVani — technology stack decisions

**Status:** Current decision register for the technology baseline  
**Reviewed:** 2026-11-13  
**Rule:** Selected target technologies are not necessarily integrated. See maturity column.

## Frontend

| Technology | Decision | Maturity / constraints |
|---|---|---|
| React + JavaScript | Selected | Implemented. JavaScript is intentional; no TypeScript migration without approval. |
| Vite | Selected | Implemented build/dev tooling. |
| Tailwind CSS 3 | Selected | Implemented. Preserve current compatible toolchain. |
| DaisyUI 4 | Selected | Implemented component/theme layer. |
| Axios | Selected | Implemented central API client. |
| Mukta | Selected | Implemented via Fontsource for Latin/Devanagari. |
| Three.js | Narrow use only | Implemented for decorative sign-in animation; lazy/failure-safe and nonessential. |
| React Router | Not selected | Not in current dependency baseline; inspect current routing pattern before proposing. |
| Recharts | Not selected | Not in current dependency baseline; do not add before real analytics data/contracts exist. |
| React Hook Form / Zod | Not selected | Not in current dependency baseline; do not add without a concrete form-validation need. |
| shadcn/ui / Flowbite / Preline | Not selected | Alternatives previously discussed; not dependencies. |

Current visual palette:
- Gunmetal Blue: `#1B2029`, `#222833`, `#2B3240`, `#3A4352`.
- Warm Concrete: `#B9B3A8`.
- Saffron Gold: `#FFB800` with lighter accent `#FFD166`.
- Main text: `#E8E4DC`.
- Typeface: Mukta; verify contrast and visible keyboard focus for every component.

## Backend and persistence

| Technology | Decision | Maturity / constraints |
|---|---|---|
| Python + FastAPI | Selected | Implemented. |
| Pydantic | Selected | Implemented for API schemas/settings. |
| SQLAlchemy 2.x | Selected | Implemented. |
| Alembic | Selected | Implemented; migrations `0001`–`0005` on reviewed main. Never rewrite applied migrations. |
| PostgreSQL | Selected | Implemented persistence and RLS foundation. |
| Async SQLAlchemy driver | Selected | Implemented for API persistence. |
| pytest / Ruff | Selected | Implemented backend test/lint toolchain. |

## Background processing and infrastructure

| Technology | Decision | Maturity / constraints |
|---|---|---|
| Celery + Redis | Selected target | Not integrated on reviewed main; appears in two competing AUD-03 draft PRs. |
| PostgreSQL transactional outbox | Selected target | No outbox model/table/worker merged on reviewed main. |
| Docker Compose | Intended local orchestration | Root Compose file absent on reviewed main; do not claim services start via Compose. |
| GitHub Actions | Selected | Workflows exist for CI, browser checks and secret scanning. |
| Sentry / Prometheus / Grafana / OpenTelemetry | Deferred candidates | No current commitment; add only for an identified operational need. |

## Architecture rules

- Keep the application a modular monolith.
- PostgreSQL remains the source of truth; Redis/Celery is transport/execution only if/when integrated.
- Tenant context, forced RLS, non-owner runtime role and composite tenant-safe constraints are mandatory.
- No live provider path or provider secrets in MVP.
- No Kafka, Kubernetes, MongoDB, Elasticsearch, Clickhouse, vector database, microservices or multi-region active-active without an approved ADR/change review.

## Change process

Before adding a framework, runtime service or dependency, state the problem, compare the current stack and at least one alternative, inspect license/maintenance/security posture, assess bundle/operational cost, define migration and rollback, and obtain human approval. Update this file, `docs/decision-register.md`, relevant agent instructions and setup docs together.

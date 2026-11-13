# SandeshVani

SandeshVani (संदेशवाणी) is a multi-tenant institutional/public-awareness communication platform.

**Working tagline:** Har zaroori baat, har zaroori insaan tak.  
**Working domain:** `sandeshvani.in` (selected/intended; domain registration and legal clearance are not verified).  
**Historical codename:** CivicReach.

## Development status

The repository currently contains working foundations for authentication, organization membership and role management, PostgreSQL tenant isolation, audience contact CRUD, secure CSV upload validation/storage, and the initial frontend shell/theme/dashboard prototype.

It is **not yet a complete campaign or communication platform**. Campaigns, consent/suppression, segmentation, approvals, audit workflows, mock delivery execution and real analytics are not implemented on the reviewed `main` baseline. The dashboard uses demonstration data.

See [current project status](docs/PROJECT_STATUS.md) before planning or claiming feature work.

## Technology

- Frontend: React, JavaScript, Vite, Tailwind CSS 3, DaisyUI 4, Axios.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic.
- Database: PostgreSQL.
- Selected future worker architecture: Celery + Redis with PostgreSQL transactional outbox; not yet integrated on the reviewed `main` baseline.

## Start here

1. Read [repository agent instructions](AGENTS.md).
2. Read the [documentation index](docs/README.md).
3. Read [project status and next priorities](docs/PROJECT_STATUS.md).
4. Read [technology and product decisions](docs/decision-register.md).

Setup details are maintained in [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md). Verify environment requirements and commands against those files before running them.

## MVP safety boundary

The MVP must remain mock-only for Email, SMS, WhatsApp and Push. Do not add provider SDKs, credentials or live-send endpoints. AI may not approve or dispatch. Do not add microservices, Kafka or Kubernetes without a reviewed decision and explicit owner approval.

## Contribution and AI-agent workflow

All agents must follow the root [AGENTS.md](AGENTS.md). The docs index defines authoritative versus historical materials. Source code, migrations and tests establish actual behaviour; planning documents do not.

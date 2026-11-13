# SandeshVani — system architecture

**Document type:** Target architecture with current implementation annotations  
**Reviewed:** 2026-11-13  
**Important:** The diagrams and future flows in this document describe the intended MVP architecture, not proof that those modules are implemented.

## 1. Current implementation snapshot

The reviewed \`main\` baseline is a React/JavaScript/Vite frontend and a FastAPI/Python backend using PostgreSQL, SQLAlchemy 2.x and Alembic. The implemented backend domains are authentication, organization/membership/role management and audience contact CRUD plus secure CSV upload validation/storage.

The main tree does not yet contain campaign, consent, segment, template, approval, audit-event, delivery, analytics or Celery worker domains. The Overview dashboard contains hard-coded sample data. The async worker/outbox architecture described below is a selected target and is under competing draft PR review.

## 2. Target architectural decision

Use a **modular monolith**: one FastAPI application with clear domain modules. When background processing is integrated, run worker processes separately while retaining one shared PostgreSQL database and Redis as the Celery broker/transport. Do not turn module boundaries into independently deployed microservices for the MVP.

## 3. Target goals

- Multi-organization workspaces and organization-scoped multiple-role RBAC.
- Secure audience management, channel/purpose-specific consent and suppression.
- Segments using an allowlisted filter grammar.
- Versioned campaigns and templates with English/Hindi content variants.
- Human approval bound to an immutable version and content hash.
- Mock-only Email, SMS, WhatsApp and Push delivery.
- Durable audit, delivery state, basic analytics and explicit operational recovery.
- A design target of up to 100,000 recipients per campaign, subject to representative load testing.

## 4. Target logical architecture

\`\`\`mermaid
flowchart TB
  USER[Organization Users] --> WEB[React SPA]
  WEB --> API[FastAPI REST API]
  subgraph APP[Modular Monolith]
    AUTH[Identity and Organizations]
    RBAC[Permissions and Tenant Context]
    AUD[Audience, Consent and Segments]
    CAMP[Campaigns and Templates]
    LOC[Localization]
    APR[Approvals and Audit]
    DIST[Distribution Orchestration]
    ANALYTICS[Analytics]
  end
  API --> AUTH
  API --> RBAC
  API --> AUD
  API --> CAMP
  API --> LOC
  API --> APR
  API --> DIST
  APP --> DB[(PostgreSQL)]
  DIST --> OUTBOX[Transactional Outbox]
  OUTBOX --> PUB[Outbox Publisher]
  PUB --> REDIS[(Redis)]
  REDIS --> WORKER[Celery Workers]
  WORKER --> MOCK[Mock Channel Adapter Registry]
  MOCK --> EMAIL[Mock Email]
  MOCK --> SMS[Mock SMS]
  MOCK --> WA[Mock WhatsApp]
  MOCK --> PUSH[Mock Push]
  WORKER --> DB
  ANALYTICS --> DB
\`\`\`

**Implementation caveat:** only identity/organization/RBAC and audience CRUD/upload portions currently exist on main. Redis, Celery, outbox and the product modules shown in the diagram are future work.

## 5. Current and target technology

- Implemented frontend: React, JavaScript, Vite, Tailwind CSS 3, DaisyUI 4, Axios, Mukta; Three.js only for decorative sign-in animation.
- Implemented backend/data: Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PostgreSQL.
- Selected target background processing: Celery + Redis and a PostgreSQL transactional outbox; not merged into main in the reviewed snapshot.
- Intended local orchestration: Docker Compose; root Compose file not present in the reviewed tree.

Do not describe React Router, Recharts, React Hook Form, Zod or other previously proposed UI libraries as selected dependencies. See \`TECH_STACK_DECISIONS.md\`.

## 6. Backend module boundaries

Target module areas:
- \`identity\`: users, authentication, sessions and recovery.
- \`organizations\`: organizations, memberships and role assignments.
- \`audiences\`: contacts and controlled CSV upload/import.
- \`consent\`: consent evidence and suppression.
- \`segments\`: allowlisted filter definitions and preview.
- \`campaigns\`: drafts, state transitions and immutable versions.
- \`templates\` / \`localization\`: versioned reusable content and language variants.
- \`approvals\` / \`audit\`: reviewer decisions and append-oriented events.
- \`distribution\`: recipient snapshots, mock adapters, delivery state and retry.
- \`analytics\`: tenant-scoped aggregates.
- \`ai_engine\`: deferred, human-reviewed suggestions only.

Only identity/organizations and audiences currently have implemented API modules. The module list above is a target boundary, not a claim that these packages exist.

## 7. Request and tenant flow

Target: Browser → FastAPI → authenticate session → resolve requested/active organization through verified membership → aggregate roles/permissions in that organization → authorize resource and workflow state → tenant-scoped service/repository → PostgreSQL with transaction-local RLS context.

A client-supplied organization ID is a selector, not proof of access. Every tenant-owned operation must verify membership and resource ownership. The runtime DB role must not own tenant tables and must not have \`BYPASSRLS\`.

## 8. Target major data flows

**CSV import:** validated private upload → tenant-scoped durable import job + outbox → bounded worker chunks → imported contacts and PII-minimized row errors → progress/status UI. The current merged AUD-02 slice stops after file validation and private storage; async import is AUD-03 and is not on main.

**Campaign approval:** draft → immutable version/hash → submit → reviewer inspects exact snapshot → authorized decision with rationale → audit. Not implemented on main.

**Mock execution:** approved version → execution-time eligibility recheck → recipient snapshot → channel delivery intents and outbox → worker → mock adapter → attempt/status persistence → analytics. Not implemented on main.

## 9. Distribution reliability requirements

When introduced, use a provider-independent mock adapter contract. PostgreSQL stores logical state and outbox events atomically; Redis/Celery may deliver duplicate tasks, so consumers must be idempotent. Use bounded batches, bounded retries/backoff, exhausted-work handling, worker recovery, pause/cancel checks and explicit unknown outcomes.

No live provider SDKs, credentials, endpoints or configuration flag capable of enabling live dispatch may be present in the MVP execution path.

## 10. 100k recipient target

Do not enqueue an entire audience as one unbounded task or execute recipient fan-out inside an API request. Plan bounded recipient snapshots and worker batches, indexed tenant/campaign/status access patterns and realistic resource limits. The required workload profile and completion-time objective remain open. No 100k throughput or completion claim may be made until measured and reported.

## 11. Open design decisions

Campaign and delivery state machines; consent legal basis and retention; organization invitation/onboarding; separation of duties; audit retention/tamper-evidence; scheduling and recovery semantics; recipient identity/deduplication; 100k workload profile; RPO/RTO; future provider/webhook and AI provider selection.

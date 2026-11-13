# SandeshVani — repository layout

**Status:** Current layout snapshot on 2026-11-13, plus explicit target notes. Actual files may change; inspect \`git ls-files\` before creating new folders.

## Current top-level structure

\`\`\`text
SandeshVani/
├── .github/
│   ├── agents/
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
├── agents/                  # Specialist agent role guides
├── backend/
│   ├── alembic/versions/    # Migrations 0001–0005 on reviewed main
│   ├── app/
│   │   ├── api/v1/          # health, auth, organizations, audiences
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
├── backlog/                 # Historical milestone planning
├── docs/
│   ├── api/
│   ├── architecture/
│   ├── brand/
│   ├── design/
│   ├── implementation/
│   ├── product/
│   ├── security/
│   └── workflows/
├── frontend/
│   └── src/
├── prompts/                 # Archived prompt/docs pack; not active instructions
├── AGENTS.md                # Repository-wide agent instructions (added in docs migration)
├── README.md                # Project overview (added in docs migration)
└── SandeshVani_AI_Handoff.md
\`\`\`

## Implementation boundary

The \`backend/app/api/v1\` routes on the reviewed main baseline cover health, auth, organizations and audiences. Campaign, consent, segment, template, approval, audit, distribution and analytics packages/routes are future work even though target docs mention them.

Celery/Redis worker and transactional outbox code are not present on reviewed main; they appear in competing AUD-03 pull requests only.

## Target layout guidance

Keep frontend feature boundaries and backend domain/service/repository boundaries explicit as they grow. New folders are created when code exists, not as empty scaffolding. Module boundaries are not deployable microservices. A root Compose file, separate infrastructure tree and OpenAPI export directory are target possibilities, not current directories.


# Target repository layout

```text
sandeshvani/
├── frontend/src/{app,components,features,hooks,services}/
├── frontend/tests/
├── backend/app/{api,core,models,schemas,services,repositories,workers}/
├── backend/migrations/
├── backend/tests/
├── infrastructure/{docker,scripts}/
├── contracts/{openapi,events}/
├── docs/{architecture,decisions,development}/
├── .github/{ISSUE_TEMPLATE,workflows}/
├── AGENTS.md
├── docker-compose.yml
└── README.md
```

This is a target layout, not a claim all application code exists. Folders are modular-monolith boundaries, not deployable microservices.

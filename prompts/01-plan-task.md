# Plan a SandeshVani task

Act as Architect/Planner. Read root `AGENTS.md` and `agents/architect.md`.

Inputs: GitHub issue [link/ID]; requirement source [path/section]; contracts [paths]; milestone [name].

1. Inspect repository and source requirements.
2. Restate requested outcome, scope and exclusions.
3. Identify dependencies, API/data/event contracts and affected modules.
4. Identify tenant, RBAC, consent, audit, immutability, idempotency and mock-dispatch implications.
5. Split into small tasks with owners, dependencies, acceptance criteria and tests.
6. Mark safe parallel work versus sequential work.
7. List likely files, but do not edit.
8. List unresolved decisions; do not invent answers.

Output: interpretation; scope/exclusions; dependencies/contracts; task breakdown; parallelisation; risks/security; acceptance criteria; human decisions. Do not implement until blocking decisions are approved.

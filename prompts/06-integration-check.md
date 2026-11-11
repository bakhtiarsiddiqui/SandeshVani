# Integration verification

Read root `AGENTS.md` and `agents/integration-reviewer.md`.

Frontend PR [ref]; backend PR [ref]; OpenAPI contract [path/version]; environment [local/test].

Verify request/response shapes, auth and organization context, validation/errors, pagination/filtering, forbidden states, end-to-end acceptance criteria and mock-only dispatch. Run available integration/browser tests. Report mismatches with files and reproduction steps. Do not redefine contracts silently; route changes through Architect and human owner.

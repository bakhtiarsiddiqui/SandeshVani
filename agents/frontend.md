# Agent — Frontend Engineer

**Mission:** build accessible, responsive features using the existing React + JavaScript + Vite + Tailwind CSS + DaisyUI baseline.

## Required context
Read root `AGENTS.md`, docs index/status/decision register, then the relevant UI and API documents. Inspect current package manifests, routes, shared components and API client before editing.

## Responsibilities
- Use current implemented or explicitly approved OpenAPI contracts; do not infer endpoints from UI specs.
- Reuse existing design tokens/components and the Gunmetal/Saffron/Mukta system.
- Clearly label sample/demo data. Never present hard-coded dashboard values as live operational metrics.
- Build loading, empty, validation, error, forbidden and success states.
- Keep organization context explicit; frontend visibility is not authorization.
- Add component/interaction tests and check keyboard, responsive and reduced-motion behaviour.
- Keep API requests tenant-aware and use the central API client.

## Must not
- Invent endpoint paths, fields, enum values, permission codes or backend capabilities.
- Enable approval actions without real backend handlers and server-side authorization.
- Convert sandbox simulation into actual dispatch or add a live-send control.
- Add React Router, Recharts, React Hook Form, Zod or another UI library without review and approval.
- Migrate JavaScript to TypeScript without approval.
- Put secrets or long-lived credentials in the browser.

## Deliver
Working UI, focused tests, screenshots/browser evidence where appropriate, API assumptions, accessibility notes and exact check results.

# Role-based MVP workspaces

This milestone introduces separate landing workspaces for the five established SandeshVani roles while preserving the existing Gunmetal Blue / Warm Concrete / Saffron Gold visual system, Mukta typography, Tailwind CSS 3 and DaisyUI 4.

## What is included

- Permission-driven navigation and role-appropriate default landing pages.
- Overview, audience, segmentation, consent/suppression, campaigns, content/templates, approvals, mock distribution, analytics, organization administration, organization settings, audit and platform administration screens.
- Platform role context endpoint GET /api/v1/platform/me, which returns only global role assignments belonging to the authenticated user.
- Frontend unit coverage for the five role permission profiles and multiple-role combinations.

## What remains demonstrative

Campaign, post, template, segment, consent, approval, distribution, analytics, audit and platform-directory data are samples until the corresponding domain APIs are delivered. Sample interactions stay in local React state and reset on refresh. The existing audience APIs remain available but are not yet wired to the new contact workspace.

No new frontend packages, real communication providers, or migrations are introduced.

## Verification required before merge

Run backend Ruff lint/format and the full pytest suite; run frontend lint, Vitest and Vite production build; then run desktop/mobile Chromium smoke tests with users assigned each of the five established role profiles. The Platform Operator user must have an actual PlatformRoleAssignment; organization membership alone must never expose Platform Administration.

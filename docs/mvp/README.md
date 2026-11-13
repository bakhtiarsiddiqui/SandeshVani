# Role-based MVP workspaces

This milestone provides separate landing workspaces for the five established SandeshVani roles while preserving the existing Gunmetal Blue / Warm Concrete / Saffron Gold visual system, Mukta typography, Tailwind CSS 3 and DaisyUI 4.

## Implemented

- Permission-driven navigation and role-appropriate landing pages.
- Separate screens for audience, segments, consent/suppression, campaigns, posts/templates, approvals, mock distribution, analytics, organization administration, organization settings, audit and platform administration.
- Authenticated platform-role context endpoint at GET /api/v1/platform/me, returning only global role assignments belonging to the authenticated user.
- Audience & Contacts connects to existing list, create, update and CSV file-upload endpoints.
- Organization Administration connects to existing member and organization-role endpoints, including adding registered accounts and assigning/removing organization roles.
- Frontend unit coverage for role navigation and connected audience/organization API request shapes.

## Demonstration-only domains

Campaign, post, template, segment, consent, approval, distribution, analytics, audit and platform-directory data remain sample data until their domain APIs and policies are approved and implemented. The current CSV upload validates and stores a file only; it does not process contact rows. Organization membership addition requires an already-registered user; there is no invitation endpoint.

No new frontend packages, real communication providers or database migrations are introduced by the audience/organization integration slice.

## Verification

Review WORKSPACE_API_INTEGRATION.md for endpoint contracts, explicit non-goals and tests. Full frontend CI and Chromium desktop/mobile browser checks are required before merge. The Platform Operator must have a real PlatformRoleAssignment; organization membership alone must never expose Platform Administration.

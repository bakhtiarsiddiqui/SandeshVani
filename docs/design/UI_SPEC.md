# SandeshVani — UI/UX functional specification

**Stack:** React + JavaScript + Vite + Tailwind CSS 3 + DaisyUI 4.  
**Design status:** Initial design system and Overview prototype merged; most domain screens remain requirements, not implemented pages.  
**Reviewed:** 2026-11-13.

> This file describes both current design foundations and planned product screens. Do not claim that every listed screen or component exists. The current Overview uses hard-coded demonstration data and has no campaign/delivery API integration.

## 1. Current design foundation

The merged visual direction is Gunmetal Blue / Warm Concrete / Saffron Gold, with Mukta for Latin and Devanagari text.

Current tokens:
- Gunmetal Blue: `#1B2029`, `#222833`, `#2B3240`, `#3A4352`.
- Warm Concrete: `#B9B3A8`.
- Saffron Gold: `#FFB800`; lighter accent `#FFD166`.
- Foreground: `#E8E4DC`.
- DaisyUI theme: `sandeshvani`.
- Typography: Mukta via Fontsource; retain readable fallback stacks.

The dashboard Overview, shared shell/components, auth pages, organization-selection styling and decorative sign-in scene were merged by PR #14. Three.js is decorative, not a product workflow requirement. Preserve reduced-motion handling, error fallback, keyboard focus, responsive behaviour and accessible labels.

## 2. Design direction

Professional institutional SaaS with clear hierarchy, readable content surfaces, semantic status cues, keyboard focus and predictable forms. Never use colour alone to encode status. Confirm destructive/consequential actions. Validate actual contrast rather than relying on palette names.

## 3. Application shell

Target shell: organization switcher; responsive sidebar; profile/session menu; breadcrumbs; notifications/activity; content area. Active organization must remain visible wherever tenant context affects an action.

Current navigation is a shell/prototype; do not assume every destination is routed to a working feature.

## 4. Planned screen inventory

These are planned screens unless the current source proves otherwise:

1. Sign in / recovery / session expired.
2. Organization selection and switcher.
3. Overview dashboard.
4. Audience list/detail/create/edit.
5. CSV upload and import progress/error report.
6. Segment list, builder and preview.
7. Consent/suppression detail and history.
8. Campaign list/detail/wizard.
9. Channel selection and channel-specific content editor.
10. English/Hindi variant editor and later language registry.
11. Template selector/editor/version history.
12. Campaign preview by channel and language.
13. Campaign version history.
14. Approval queue/review/approve/reject.
15. Mock execution monitor and delivery detail.
16. Analytics dashboard and channel filters.
17. Member management and multiple-role assignment.
18. Roles/permissions administration.
19. Audit log.

## 5. Dashboard and prototype safeguards

The current Overview displays sample KPI, campaign, dispatch and approval records. It must:
- Display a persistent sample/demo label while the data is static.
- Never represent sample delivery counts as actual messages, revenue, reach or delivery confirmation.
- Never imply an approval was recorded; approve/reject controls remain disabled unless real authorized handlers are wired.
- Keep sandbox simulation visibly separate from any future API-backed execution.
- Replace sample values only when backend contracts and tenant-scoped data are implemented and verified.
- Preserve loading, empty, error, retry and forbidden states when APIs are connected.

## 6. Planned domain UI requirements

**Audience:** search/filter/pagination, permission-based PII masking, import progress and safe row errors, consent/suppression state and permissioned export.

**Member/role management:** show membership and all assigned roles. Add/remove role actions only for authorized admins and within the active organization.

**Campaign wizard:** Basics → Channels → Template → Content/languages → Audience → Preview/eligibility → Review/submit. Prevent submission until validation and required content pass.

**Localization:** show source/target language, variant status and reviewer state. R1 content is human-authored; any later AI-suggested text must be distinguishable and human-reviewed.

**Approval:** show exact version/hash, snapshot, audience/channel/language summary and rationale. No silent editing.

**Mock execution:** persistent SANDBOX/MOCK MODE label, explicit mock adapter identity, bounded progress/status counts and no live-send control.

## 7. Accessibility and frontend rules

Target WCAG AA contrast. Maintain keyboard navigation, visible focus, labels/error associations, status announcements, responsive layouts and reduced-motion support. Central API client; no secrets in browser; no long-lived credentials in localStorage. Backend remains authoritative. Mask PII by default. Handle authentication, forbidden, conflict, validation and rate-limit responses explicitly.

## 8. Component and dependency policy

Reuse existing shared components in `frontend/src/components`. Do not add another component library or form/chart framework unless a real requirement cannot be served with current patterns and the change is approved. Third-party branding/assets require license review.

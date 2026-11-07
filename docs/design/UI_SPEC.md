# SandeshVani — UI/UX Functional Specification v2

**Stack:** React + JavaScript + Vite + Tailwind CSS + DaisyUI  
**Design status:** Functional brief; no Figma link supplied

## 1. Design direction

Professional, trustworthy administrative SaaS. Neutral slate/gray shell, white content surfaces, restrained primary color, semantic status colors, readable typography, clear hierarchy, accessible contrast and keyboard focus. Never use color alone for status. Confirm destructive/consequential actions.

## 2. Application shell

Organization switcher; responsive sidebar; profile/session menu; breadcrumbs; notifications/activity; content area. Active organization must remain visible in the shell and context-sensitive forms.

Navigation: Overview, Audience, Segments, Campaigns, Approvals, Templates, Analytics, Users & Roles, Organization Settings, Audit Log (restricted).

## 3. Screen inventory

1. Sign in / recovery / session expired.
2. Organization selection and switcher.
3. Dashboard.
4. Audience list/detail/create/edit.
5. CSV import wizard, progress and row-error report.
6. Segment list, builder and preview.
7. Consent/suppression detail and history.
8. Campaign list/detail/wizard.
9. Channel selection and channel-specific content editor.
10. Language variant editor (English/Hindi; registered languages as enabled).
11. Template selector/editor/version history.
12. Campaign preview by channel and language.
13. Campaign version history.
14. Approval queue/review/approve/reject.
15. Mock execution monitor and delivery detail.
16. Analytics dashboard and channel filters.
17. Member management and multiple-role assignment.
18. Roles/permissions administration.
19. Audit log.

## 4. Key screen requirements

**Dashboard:** active campaigns, audience size, pending approvals, mock deliveries, campaign status chart and recent campaigns. Label simulated data clearly.

**Audience:** search/filter/pagination, permission-based PII masking, import action by permission, consent/suppression state and empty/loading/error states.

**Member/role management:** show organization membership and all assigned roles; add/remove role actions only for authorized admins; explain effective permissions without implying roles cross organizations.

**Campaign wizard:** Basics → Channels → Template → Content/languages → Audience → Preview/eligibility → Review/submit. Prevent submission until required content and validation pass.

**Localization:** show source language, target language, variant status and reviewer state. Do not mark AI-suggested text as approved. In R1 content is human-authored; AI assistance is later.

**Preview:** render each selected channel/language combination; show channel constraints and placeholder validation. Do not imply mock preview is identical to every future provider rendering.

**Approval:** exact version/hash, content snapshot, audience/channel/language summary and reviewer decision/rationale; no silent editing.

**Mock execution:** persistent SANDBOX/MOCK MODE label, explicit mock adapter identity, progress/status counts, pause/cancel actions; no live-send control.

## 5. Component inventory

AppShell, SidebarNavigation, OrganizationSwitcher, PageHeader, Breadcrumbs, StatCard, DataTable, FilterBar, SearchInput, StatusBadge, EmptyState, LoadingSkeleton, ErrorState, ConfirmDialog, FormField, FileUpload, ImportProgress, CampaignStepper, ChannelSelector, LanguageVariantTabs, ContentPreview, VersionHistory, ApprovalDecisionPanel, DeliveryStatusSummary, PermissionGate (presentation only).

## 6. Accessibility and frontend rules

Target WCAG AA contrast; keyboard navigation and visible focus; labels and error associations; accessible status announcements. Central API client; no secrets in browser; avoid long-lived credentials in localStorage; handle 401/403/409/422/429; backend remains authoritative; mask PII by default. Use responsive layouts and clear empty/loading/error states.

## 7. Initial visual tokens

System sans or licensed/hosted Inter; radius 6/10/14px; spacing 4/8/12/16/24/32; desktop sidebar approx. 248px; content max width approx. 1440px. Use DaisyUI theme tokens and verify contrast.

## 8. Reference systems to evaluate

DaisyUI; shadcn/ui (alternative component-source approach, not DaisyUI dependency); Flowbite and Preline (verify license/free-paid boundaries); Tailwind UI (paid patterns); Material Design 3 guidance; Untitled UI (check asset license). Do not copy third-party branding/assets without permission.

# SandeshVani — R1 domain decision baseline

**Status:** Product-owner approved baseline  
**Approval recorded:** 2026-11-13  
**Scope:** R1 product, domain and API design for campaigns, content/templates, consent/suppression, approvals, segmentation, analytics and platform directory.  
**Implementation status:** Decisions are approved; domain models, migrations and APIs described here are not thereby implemented.

This baseline resolves the seven domain recommendations approved by the product owner. It also records the requested audience state and city dimensions. Legal interpretation, sender eligibility and retention schedules remain subject to review by qualified counsel and channel providers.

## 1. System-wide workflow and invariants

R1 is a governed, mock-only communication workflow:

1. Maintain an organization-scoped audience.
2. Record the purpose and applicable processing/communication authority.
3. Define a saved segment with an allowlisted filter.
4. Preview audience matches and channel-specific eligibility.
5. Prepare content variants and immutable template references.
6. Submit an immutable campaign version for independent human review.
7. Execute only an approved version through mock adapters.
8. Persist recipient snapshots, logical delivery outcomes and separate attempts.
9. Derive tenant-scoped analytics from persisted execution records.

Hard invariants:

- A tenant's data and relationships are organization-scoped and protected by server-side authorization and PostgreSQL RLS.
- Organization context is derived from authenticated membership. Client-supplied organization IDs are selectors, not proof of access.
- UI navigation and client permission checks are not security boundaries.
- No real Email, SMS, WhatsApp or Push provider, production provider credential or outbound dispatch path is included in R1.
- No AI approval, autonomous targeting or autonomous dispatch.
- Unknown consent is not permission whenever consent is required.
- Eligibility is checked at preview and re-evaluated when execution is requested.
- An approval is valid only for the exact immutable campaign version and content hash reviewed.
- All sensitive workflow transitions are auditable. Audit retention and legal hold are separate policy decisions.

## 2. Audience profile and location dimensions

The audience record retains the existing fields:

- full_name
- email
- phone
- preferred_language
- district
- status

The R1 audience contract is extended with two optional fields:

| API/storage field | UI label | Contract |
|---|---|---|
| state_code | State / UT | Optional canonical India subdivision code using ISO 3166-2 form, e.g. IN-UP; validated against a controlled State/UT registry |
| city | City | Optional normalized city/locality display value; trim whitespace and normalize Unicode; matching is case-insensitive |

district remains a separate optional field. Do not derive city, district or state from a phone number or other contact identifier. No geocoding, GPS collection or automatic location inference is introduced by this decision.

The State/UT registry supplies display names and accepted codes. City remains a normalized text attribute in R1; do not introduce a nationwide city master-data dependency before there is an authoritative source and an identified maintenance owner. A city filter must be scoped by state where appropriate because city names can repeat across states.

The list API and segment grammar will support state_code and city. CSV import processing will accept these fields after the audience schema and import contract are upgraded. The current AUD-02 upload validator and current audience CRUD API do not yet accept these additional fields.

Implementation dependency: AUD-03 has two competing draft implementations that both claim migration revision 0006. Do not create or merge a competing migration. After one import implementation is selected, add the audience location migration as the next unique Alembic revision, then update SQLAlchemy, Pydantic, list filters, CSV validation/processing, frontend forms and tests together.

## 3. Consent, processing basis and suppression

### 3.1 Keep three questions separate

The platform must not collapse these into a single consent=true field:

1. Personal-data processing basis: why the organization may collect, store, use or share personal data for the stated purpose.
2. Channel/communication permission: whether a particular message may be sent to this recipient through this channel for this purpose under the applicable law and channel policy.
3. Suppression: whether a recipient, contact point, channel or purpose has been blocked or opted out.

The applicable basis can differ by sender, organization type, purpose, recipient relationship, channel and jurisdiction. A government-public-interest basis must never be inferred merely because an organization is named a department, university, NGO or public institution.

### 3.2 Proposed evidence model

Use an append-oriented event history for consent and withdrawal. A grant must not be overwritten when a later withdrawal arrives.

A consent event should preserve, as applicable:

- organization and audience member;
- protected contact-point reference;
- channel and specific communication purpose/category;
- event type (grant, withdrawal, expiry or correction);
- collection source and capture method;
- notice and consent-template version;
- event timestamp and actor/system source;
- evidence reference or verification metadata;
- jurisdiction/policy reference where applicable.

Suppression entries are separate from consent history. They should support audience member or protected contact-point scope, channel, optional purpose scope, reason/source, creation/effective/expiry time and the actor or originating system. Withdrawal and opt-out must be reflected promptly in the effective suppression state while preserving the underlying event.

A separate, reviewed communication-authority record is required for exceptions or non-consent bases. It must identify the sender, purpose, jurisdiction, channel, applicable rule/policy, evidence, validity interval and reviewer. It must not be a free-form Boolean override.

### 3.3 Eligibility decision

For every recipient/channel/purpose tuple, evaluate:

1. Active tenant and audience-record state.
2. Documented lawful processing basis for the data use.
3. Applicable channel-specific consent, registered preference, sender registration, template or exception requirements.
4. Current suppression and withdrawal state.
5. Valid channel address/contact point.
6. Any campaign-specific age, geography or policy restrictions.

If consent is required and the state is missing, unknown, expired or unproven, exclude the recipient. A valid exception is accepted only after the sender's eligibility and supporting evidence have been verified for that specific use. An exception for one channel must not authorize another channel.

### 3.4 India-specific compliance design inputs

This section is an engineering design input, not a legal opinion.

- The Digital Personal Data Protection Act, 2023 distinguishes consent-based processing from the defined legitimate uses in section 7. Section 7 includes specific scenarios such as data voluntarily provided for a specified purpose, defined State functions, public-health emergencies and disaster response; it is not a general permission for all public-awareness or promotional campaigns. Official text: https://www.indiacode.nic.in/bitstream/123456789/22037/1/a2023-22.pdf
- The commencement notification dated 13 November 2025 schedules the principal provisions in sections 3–17 for commencement eighteen months later (13 May 2027); some other provisions commenced earlier. Official Gazette: https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf
- TRAI's TCCCPR framework remains a separate and currently relevant control for bulk SMS. TRAI's sender guidance requires Principal Entity registration, assigned headers, content templates and associated delivery metadata for bulk messaging; consent is required where applicable. Promotional commercial communications require the relevant recipient consent and must respect registered preferences. Official guidance: https://www.trai.gov.in/advice-to-senders and https://www.trai.gov.in/what-spam-or-ucc
- TRAI describes a limited public-interest treatment for communications sent on the directions of the Central Government, State Government or bodies established under the Constitution. It is not a general NGO/university/private-company exemption. Even government entities are instructed to complete sender, header and content-template registration for bulk SMS. Government-entity guidance: https://www.trai.gov.in/government-entities
- TRAI's Fourth Amendment, dated 4 November 2026, brought itself into force on publication but deferred Regulation 35A (inserted by the Third Amendment) until a further Gazette notification. Official amendment: https://trai.gov.in/sites/default/files/2026-11/Regulation_TCCCPR_04112026.pdf
- WhatsApp Business Messaging Policy (last updated 23 September 2026) requires the business to have the recipient's number/username and opt-in permission before contacting that person, and requires requests to block/discontinue/opt out to be respected. Platform policy remains an independent requirement even where a sender may have a different statutory basis. Official policy: https://whatsappbusiness.com/policy/

Accordingly, the product must classify and evidence each sender/channel/purpose combination. Do not promise that a message is exempt because it is labelled "public service", "government", "emergency" or "awareness".

### 3.5 Retention and erasure

No universal retention duration is approved. Do not hard-code one.

Provide configurable policy support for data category, purpose, jurisdiction, start/trigger, retention period, legal hold, deletion/anonymization action and evidence of completion. A legal owner must approve the retention schedule, statutory exceptions and legal-hold process before production personal data is used. Consent evidence should be minimized but sufficient to establish the relevant event and authorization.

## 4. Segmentation and eligibility preview

R1 uses a typed, versioned, allowlisted filter definition. The backend validates types and operators; raw SQL, arbitrary expressions, unapproved JSON paths and user-supplied code are never accepted.

Allowed fields:

| Field | Type | Initial operators |
|---|---|---|
| status | enum: active/inactive | equals, in |
| district | string | equals, in |
| state_code | registered State/UT code | equals, in |
| city | normalized string | equals, in |
| preferred_language | registered language code (en, hi initially) | equals, in |
| has_email | boolean derived from contact-point presence | equals |
| has_phone | boolean derived from contact-point presence | equals |

Boolean groups use AND / OR, with server-enforced limits on nesting, predicate count and payload size. Operators, fields and limits are server-controlled.

Segment preview returns aggregate information only by default:

- matching records;
- active/inactive counts;
- channel-address availability;
- excluded counts by eligibility category (where disclosure is appropriate);
- eligible counts per selected channel and purpose.

It must not return names, phone numbers, emails or other recipient-level PII by default. Preview counts are estimates, not frozen execution membership. At execution time, re-evaluate the definition and current audience, consent, suppression and contact state. Record the resulting recipient snapshot and reason-coded eligibility outcomes.

## 5. Campaign and content versioning

### 5.1 Campaign aggregate

A campaign is the organizational container for campaign metadata and versions. It is not itself an executable authorization. A separate execution record represents each mock run.

A campaign version snapshot contains the material execution inputs: selected channels, purposes, segment definitions/versions, exact template-version references, content variants, language configuration and relevant execution options. The snapshot is canonicalized and hashed with SHA-256.

### 5.2 Version lifecycle

- DRAFT: editable; authors may prepare a candidate version.
- SUBMITTED: exact version snapshot and hash are locked for review.
- APPROVED: immutable and eligible for R1 mock execution.
- CHANGES_REQUESTED: not executable; revisions require a new version.
- SUPERSEDED: retained for history and not executable where a later version replaces it.

Submission locks the version. No mutation of a submitted or approved version is allowed. Material change creates a new version and hash; earlier versions and decisions remain available for audit. The campaign container may continue to evolve through later versions.

### 5.3 Scheduling

R1 supports manual execution requests for approved versions only. No scheduled, recurring or automatically triggered campaign execution is included in R1.

R3 may add one-time scheduling only after timezone, quiet hours, cancellation, rescheduling, consent re-check, recovery and operational controls have been separately designed and approved.

## 6. Posts, templates and localization

Do not create an independent Post entity for R1. A post/announcement is represented as campaign content. This avoids two competing owners for content, versions, approval and audit.

Use:

- Campaign for the communication activity;
- CampaignVersion for immutable targeting and content snapshot;
- CampaignContentVariant for one channel/language combination;
- Template for a reusable content structure;
- TemplateVersion for an immutable template revision.

A campaign version references exact template versions and also preserves its rendered content snapshot. A later template edit cannot change a previously submitted or approved version.

English (en) and Hindi (hi) are the initial supported language set. Variants must be explicit per selected channel/language. No silent language fallback, automatic translation or unreviewed content is permitted in R1.

Role boundary:

- Campaign Manager owns campaign objective, channels, audience targeting, draft lifecycle and submission.
- Communication Team prepares content variants, language content and templates through explicit content/localization/template permissions.
- Communication Team does not approve or execute campaigns by default.
- Approver reviews the submitted immutable snapshot and cannot modify it.

The current seeded grants give Communication Team broad campaigns:create / campaigns:update permissions. The permission catalogue and default grants must be refined before the connected screens are treated as production workflows.

## 7. Approval and separation of duties

Approval binds to exact campaign_version_id and its SHA-256 content hash.

R1 requires at least one independent Approver decision. The user who created the version or submitted it cannot approve that same version. Organization Administrator status does not automatically confer approval permission. Platform Operator status does not confer tenant approval authority.

Approval records preserve reviewer, decision, timestamp, rationale and reviewed hash. Decisions are approve or request changes. Requesting changes requires a rationale and makes the submitted version non-executable; the author must create a new version for review. No emergency bypass, quorum expansion or self-approval override is included in R1.

## 8. Audit

Sensitive actions must generate server-side append-oriented audit events, including:

- changes to members and role grants;
- audience create/update/import and location changes;
- consent grant/withdrawal and suppression changes;
- segment create/update and preview;
- campaign/version creation, submission and replacement;
- approval decisions and content-hash mismatches;
- execution requests, recipient eligibility and mock-delivery transitions;
- platform directory access and exceptional administrative actions.

Audit records should minimize PII. Ordinary organization users cannot edit or delete audit events. Tamper-evidence, external archival, legal retention and hold durations remain separate operational/legal design gates.

## 9. Analytics definitions

Analytics are derived from persisted campaign execution, recipient and logical delivery records. They are not hard-coded sample values.

Keep three units separate: unique recipients, logical recipient/channel deliveries and delivery attempts.

- Target recipients: unique audience identities matched by the segment evaluation.
- Eligible recipients: unique identities passing all required checks for the relevant channel/purpose.
- Excluded recipients: identities excluded by eligibility, with aggregate reason categories.
- Delivery intents: logical recipient/channel deliveries persisted for an execution.
- Accepted: unique logical deliveries accepted by the mock adapter.
- Delivered: unique logical deliveries with a simulated confirmed-delivery outcome.
- Failed: unique logical deliveries in a terminal failure state.
- Retrying: unique logical deliveries with retry work pending.
- Unknown: unique logical deliveries without a definitive outcome.

Attempts are reported separately and do not increase logical-delivery counts. A mock acceptance/delivery must always be labelled as simulated. The confirmed-delivery rate uses terminal outcomes (delivered / (delivered + terminal_failed)) and displays its denominator; pending, retrying and unknown are separately visible and excluded from that terminal-outcome denominator. No engagement, conversion, read-receipt or money-saved metric is claimed without a defined data source and methodology.

All tenant analytics require tenant scope and analytics:read. Platform aggregates use separately assigned platform permissions and must not expose tenant recipient-level data.

## 10. Platform directory and global access

Platform directory access is independent of organization RBAC and must use a separately assigned platform role. Organization administrators cannot assign platform roles or grant platform permissions.

Proposed platform read permissions:

- platform:organizations:read — organization metadata and status;
- platform:users:read — minimal global user directory;
- platform:operations:read — platform health and aggregate operational summaries;
- platform:audit:read — platform-level audit records.

Platform directory defaults:

- organization metadata and aggregate counts only;
- global user directory with minimum identity fields and email masked by default;
- no audience contact details, consent evidence, campaign message content, recipient lists, credentials or session secrets;
- no implicit tenant impersonation or "view as tenant" support.

Exceptional support access to tenant data is deferred. Any future support-access feature requires separate explicit permission, reason code, narrow scope and duration, approval where appropriate, tenant visibility and immutable audit.

## 11. Permission catalogue changes required before workflow implementation

The current permission seed is incomplete relative to the approved workflow. The implementation proposal must add and seed explicit tenant permissions for:

- campaign content read/update;
- template update (and publish only if a publish workflow is approved);
- localization read/update;
- consent read/update;
- suppression read/update;
- segment read/create/update/preview;
- approval read/approve/request-changes;
- distribution mock execution and operational pause/cancel where supported;
- analytics and audit read.

The Communication Team default grant should be content/template/localization-focused, not campaign targeting/submission/approval/execution. Campaign Manager owns campaign metadata and targeting. Approver gets review permissions only. Organization Administrator receives only the reviewed organization policy grants. Platform permissions remain in platform-scoped role assignments.

Do not add permission codes to production seeds or grant them to roles until the RBAC implementation is reviewed and tested for least privilege, revocation and cross-tenant denial.

## 12. Implementation dependencies and open gates

Approved design does not close the following legal/operational gates:

- legal review of sender categories, public-interest eligibility, statutory processing basis and channel-purpose mapping;
- retention, deletion, legal hold and consent-evidence schedules;
- channel/provider rule changes and organization sender verification;
- exact campaign channel payload schemas and template placeholder rules;
- operational RPO/RTO, audit tamper-evidence and worker recovery;
- performance profile and 100,000-recipient acceptance thresholds.

AUD-03 PRs #18 and #19 are competing implementations with conflicting migration ownership. Select one canonical import implementation before adding a migration for state_code and city. Do not merge both or reuse migration revision 0006.

## 13. Official regulatory references checked on 2026-11-13

- DPDP Act, 2023 (India Code): https://www.indiacode.nic.in/bitstream/123456789/22037/1/a2023-22.pdf
- DPDP Act commencement notification, 13 November 2025: https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf
- TRAI Advice to Senders: https://www.trai.gov.in/advice-to-senders
- TRAI What is Spam/UCC: https://www.trai.gov.in/what-spam-or-ucc
- TRAI Government Entities: https://www.trai.gov.in/government-entities
- TRAI Fourth Amendment, 4 November 2026: https://trai.gov.in/sites/default/files/2026-11/Regulation_TCCCPR_04112026.pdf
- WhatsApp Business Messaging Policy, last updated 23 September 2026: https://whatsappbusiness.com/policy/

Re-check current official sources before enabling any real provider or changing the compliance model. This document is a product/engineering baseline, not legal advice.

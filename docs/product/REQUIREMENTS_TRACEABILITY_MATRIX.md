# SandeshVani — Requirements Traceability Matrix (RTM)

**Version:** 2.0  
**Status:** Planning baseline; requirements require product-owner review  
**Release labels:** R1 = MVP, R2 = intelligence/localization, R3 = production distribution/engagement

## 1. Confirmed decisions

| ID | Decision | Confirmed value | Consequence |
|---|---|---|---|
| DEC-001 | Roles per organization | Multiple | `memberships` has no single `role_id`; use `membership_roles` and aggregate permissions within active organization. |
| DEC-004 | MVP channels | `mock_all` | Mock Email, SMS, WhatsApp and Push adapters; no real provider dispatch or credentials in R1. |
| DEC-006 | MVP languages | `english_hindi_indic` | English (`en`) and Hindi (`hi`) supported initially; extensible Indic language registry. Exact additional launch languages remain open. |

## 2. Functional requirements

| ID | Requirement | Release | Traceability / acceptance evidence |
|---|---|---|---|
| FR-001 | Users authenticate and manage secure sessions. | R1 | Auth/session tests; revocation works. |
| FR-002 | Users can belong to multiple organizations. | R1 | Membership list and organization switching tests. |
| FR-003 | A membership can hold multiple roles. | R1 | `membership_roles`; assignment/revocation tests. |
| FR-004 | Effective permissions are evaluated in active organization context. | R1 | Cross-org permission isolation tests. |
| FR-005 | Authorized organization admins manage memberships and role assignments. | R1 | Grant-authority and audit tests. |
| FR-006 | Platform-level administration is separate from tenant administration. | R1 | Org admin cannot grant platform roles. |
| FR-007 | Tenant-owned resources are organization-scoped. | R1 | RLS and cross-tenant tests. |
| FR-008 | Sensitive membership and permission changes are audited. | R1 | Audit assertions. |
| FR-009 | Authorized users create and manage audience records. | R1 | Audience CRUD tests. |
| FR-010 | Users import audience data by CSV. | R1 | Import job and file validation tests. |
| FR-011 | Imports expose progress and row-level errors. | R1 | Import status/error report tests. |
| FR-012 | Duplicate records are detected by documented identity rules. | R1 | Duplicate policy tests; matching rules remain to be finalized. |
| FR-013 | Users create and manage segments through allowlisted filters. | R1 | Filter grammar validation; no raw SQL. |
| FR-014 | Eligibility is evaluated before execution and rechecked at execution. | R1 | Preview vs execution eligibility tests. |
| FR-015 | Consent is channel- and purpose-specific and historical. | R1 | Consent history tests. |
| FR-016 | Missing/unknown consent is not permission where consent is required. | R1 | Negative eligibility tests. |
| FR-017 | Suppression entries block prohibited channel delivery. | R1 | Suppression tests at execution. |
| FR-018 | Audience exports are permissioned, safe and audited. | R1 | Export authorization/formula-injection tests. |
| FR-019 | Audience records support channel-specific contact points. | R1 | Contact validation and delivery eligibility tests. |
| FR-020 | Audience, consent and suppression changes are auditable. | R1 | Audit coverage tests. |
| FR-021 | Users create and manage campaign drafts. | R1 | Campaign CRUD/state tests. |
| FR-022 | Campaigns target one or more eligible segments. | R1 | Segment association and preview tests. |
| FR-023 | Campaign versions contain language-specific content variants. | R1 | Version/content schema tests. |
| FR-024 | English and Hindi content variants can be authored and previewed. | R1 | Language editor and preview tests. |
| FR-025 | Language registry is extensible for additional Indic languages. | R1 | Language registry/configuration test; full translation coverage not implied. |
| FR-026 | Content can be previewed per selected channel and language. | R1 | Rendered preview tests for all four mock channels. |
| FR-027 | Submitted campaign versions are immutable. | R1 | Mutation rejection tests. |
| FR-028 | Material edits create a new version. | R1 | Version lifecycle tests. |
| FR-029 | Approval binds to exact version and content hash. | R1 | Hash integrity tests. |
| FR-030 | Reviewers approve/reject with recorded rationale. | R1 | Approval authorization and rationale tests. |
| FR-031 | AI cannot approve or dispatch. | R1/R2 | Architecture boundary and negative tests. |
| FR-032 | Users may request AI draft suggestions. | R2 | Human-reviewed AI workflow. |
| FR-033 | Users may request translation suggestions. | R2 | Language-specific evaluation and review. |
| FR-034 | Human reviewers verify translated content. | R2 | Review state and reviewer audit. |
| FR-035 | AI suggestions are distinguishable from approved content. | R2 | UI and persistence tests. |
| FR-036 | Quality checks flag readability, placeholders and unsupported claims. | R2 | Evaluation dataset and review evidence. |
| FR-037 | AI processing follows privacy/minimization policy. | R2 | Provider and data-flow review. |
| FR-038 | AI quality is evaluated per supported language. | R2 | Human evaluation report. |
| FR-039 | AI output cannot bypass approval. | R2 | Workflow authorization tests. |
| FR-040 | Approved campaigns execute through mock adapters. | R1 | Mock execution integration tests. |
| FR-041 | R1 supports mock Email, SMS, WhatsApp and Push. | R1 | Adapter contract/conformance tests for all four. |
| FR-042 | Each execution records a recipient snapshot. | R1 | Snapshot completeness and reproducibility tests. |
| FR-043 | Each recipient may have separate channel delivery records. | R1 | Recipient-to-delivery relationship tests. |
| FR-044 | Delivery attempts are recorded separately from logical deliveries. | R1 | Attempt history tests. |
| FR-045 | Distribution work is asynchronous and bounded. | R1 | Worker and batch-size tests. |
| FR-046 | Distribution processing is idempotent. | R1 | Duplicate task/unique constraint tests. |
| FR-047 | Retryable failures use bounded retry/backoff. | R1 | Retry policy tests. |
| FR-048 | Unknown outcomes are represented explicitly. | R1 | State transition and reconciliation tests. |
| FR-049 | R1 execution cannot call a real provider. | R1 | Network/credential/configuration isolation test. |
| FR-050 | Real provider integrations are introduced only in a separately gated release. | R3 | Provider-specific security and operational approval. |
| FR-051 | Authorized users view campaign execution summaries. | R1 | Tenant-scoped dashboard tests. |
| FR-052 | Metrics distinguish accepted, delivered, failed, retrying and unknown. | R1 | Metric definitions and state aggregation tests. |
| FR-053 | Delivery metrics can be filtered by channel. | R1 | Channel aggregation tests. |
| FR-054 | Engagement events are collected when supported by real providers. | R3 | Provider event contract tests. |
| FR-055 | Campaign feedback can be collected. | R3 | Feedback workflow and consent/privacy review. |
| FR-056 | Feedback can be aggregated by campaign and language. | R3 | Metric definitions and aggregation tests. |
| FR-057 | Advanced sentiment analysis is a later capability. | R3 | Evaluation and privacy gate. |
| FR-058 | Analytics metrics have documented definitions across channels. | R1 | Metric glossary and contract tests. |

## 3. Non-functional requirements

| ID | Requirement | Release | Acceptance evidence |
|---|---|---|---|
| NFR-001 | Tenant isolation at application and database layers. | R1 | RLS, tenant-scoped repository and adversarial tests. |
| NFR-002 | Server-side RBAC and resource-level authorization. | R1 | Negative API tests. |
| NFR-003 | Secure sessions, credential handling and recovery. | R1 | Session, expiry, rotation and recovery tests. |
| NFR-004 | Sensitive data encrypted in transit and at rest. | R1 | Deployment/configuration review. |
| NFR-005 | Security-sensitive actions are audited. | R1 | Audit coverage tests. |
| NFR-006 | Design for up to 100,000 recipients per campaign. | R1 | Representative load test; no throughput promise until measured. |
| NFR-007 | Large imports and distribution are asynchronous and bounded. | R1 | Batch and worker failure tests. |
| NFR-008 | Workers and event consumers are idempotent. | R1 | Duplicate/replay tests. |
| NFR-009 | APIs validate inputs and enforce resource authorization. | R1 | Schema and authorization tests. |
| NFR-010 | Collection endpoints use bounded pagination. | R1 | Contract and query tests. |
| NFR-011 | Interfaces meet agreed accessibility baseline. | R1 | Keyboard and WCAG AA-oriented checks. |
| NFR-012 | Structured logs, request IDs and operational metrics exist. | R1 | Observability checks. |
| NFR-013 | Backup and recovery procedures are tested. | R1 | Restore exercise; RPO/RTO targets remain open. |
| NFR-014 | AI processing follows privacy, safety and human-review controls. | R2 | Provider assessment and evaluation. |
| NFR-015 | Channel adapters implement a provider-independent contract. | R1 | Adapter conformance tests. |

## 4. Requirement-to-module traceability

| Domain | Backend modules | Main data entities | Frontend areas |
|---|---|---|---|
| Identity/tenancy | identity, organizations, permissions | users, organizations, memberships, membership_roles, roles, permissions, role_permissions, sessions | auth, organization switcher, members, roles |
| Audience/consent | audiences, consent | audience_members, import_jobs, import_job_errors, segments, consent_records, suppression_entries | audience, imports, segments, consent |
| Campaign/localization | campaigns, templates, localization | campaigns, campaign_versions, campaign_segments, templates, template_versions, languages, campaign_content_variants | campaigns, editor, templates, language variants |
| Governance | approvals, audit | campaign_approvals, audit_logs | approvals, audit viewer |
| Distribution | distribution, providers | campaign_executions, campaign_recipients, message_deliveries, delivery_attempts, outbox_events | execution monitor, delivery detail |
| Analytics | analytics | delivery/event records, metric snapshots | dashboard, analytics |
| AI (later) | ai_engine | AI request/evaluation records as approved by later design | drafting and translation assistance |

## 5. MVP acceptance checklist

- [ ] Multi-organization membership and multiple roles per membership work.
- [ ] Cross-tenant read/write access is denied and tested.
- [ ] CSV imports validate files and expose row errors.
- [ ] Duplicate policy is documented and tested.
- [ ] Segments use an allowlisted grammar.
- [ ] Consent is channel/purpose-specific; missing consent is not permission.
- [ ] Suppression is rechecked at execution.
- [ ] English and Hindi variants can be created and previewed.
- [ ] Additional Indic languages can be registered without schema redesign.
- [ ] Campaign versions are immutable after submission.
- [ ] Approval binds to version/hash and separation-of-duties policy.
- [ ] Mock Email, SMS, WhatsApp and Push execute through adapters.
- [ ] No real provider can be reached from the MVP environment.
- [ ] Recipient snapshots, channel deliveries and attempts are traceable.
- [ ] Idempotency, retry, unknown outcome and worker recovery are tested.
- [ ] Basic channel analytics distinguish delivery states.
- [ ] Representative 100k load test and backup/restore evidence are documented.

## 6. Open decisions register

| ID | Decision | Current status / recommendation | Owner / due gate |
|---|---|---|---|
| DEC-002 | Organization creation/onboarding | OPEN. Controlled onboarding/platform approval is a proposed starting point. | Product/security before identity implementation |
| DEC-003 | Organization hierarchy | OPEN. Do not implement parent-child hierarchy unless an initial use case requires it. | Product before schema freeze |
| DEC-005 | Recipient uniqueness semantics | Proposed: one recipient snapshot row per audience identity per execution; separate delivery per channel. Confirm re-execution semantics. | Product/architecture before distribution schema |
| DEC-007 | Emergency approval | OPEN. Explicit authorized emergency reviewer policy; no approval bypass. | Governance owner before approvals |
| DEC-008 | Retention/deletion/legal hold | OPEN. Requires legal and organizational policy. | Legal/security before production data |
| DEC-009 | AI provider | OPEN. Evaluate privacy, regional processing, language quality, cost, latency and terms. | Product/security before R2 |
| DEC-010 | Performance targets | OPEN. Define workload mix, concurrency, completion-time objective, error budget and hardware before load test. | Engineering before performance gate |
| DEC-011 | Additional Indic languages | OPEN. English/Hindi are confirmed; exact additional language launch list is not. | Product/language reviewers before R1 language acceptance |
| DEC-012 | Consent/legal basis | OPEN. Define per channel, purpose and jurisdiction; do not infer legal basis. | Legal/product before real dispatch |
| DEC-013 | Approval separation of duties | OPEN. Define creator self-approval and quorum rules. | Governance before approval implementation |
| DEC-014 | RPO/RTO | OPEN. Set backup frequency, recovery objectives and retention. | Operations before deployment gate |
| DEC-015 | Live provider policy | OPEN. R3 only; provider-specific release approval required. | Product/security/operations before R3 |
| DEC-016 | Brand name | CONFIRMED working brand: SandeshVani (संदेशवाणी); selected domain: `sandeshvani.in` (availability reported by owner; registration and trademark clearance remain OPEN). | Before public launch |

## 7. Interpretation notes

- `mock_all` means four simulated adapters, not real provider readiness.
- `english_hindi_indic` means English and Hindi initial content support plus an extensible Indic language registry; it does not imply every Indic language is fully translated, evaluated or launch-ready.
- Requirement IDs are planning identifiers. Changes should be versioned and mapped to tests/issues as implementation begins.

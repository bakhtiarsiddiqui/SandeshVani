> **DOCUMENT STATUS — POLICY TARGET:** This matrix describes intended permission boundaries. Verify currently implemented permission codes and route dependencies in the backend source and generated OpenAPI. Do not invent or expose permissions because a future workflow requires them. Use [PROJECT_STATUS.md](../PROJECT_STATUS.md) for implemented domains.

---

# SandeshVani — RBAC Matrix v2

**Model:** Organization-scoped RBAC with multiple roles per membership and resource/workflow-level authorization.

Permission is necessary but not sufficient: tenant ownership, assignment, consent and workflow state also apply. Deny by default.

## 1. Roles (suggested baseline)

- **Platform Operator:** tightly controlled platform-level operations; never grantable by an organization administrator.
- **Organization Administrator:** manages own organization, members and permitted role assignments.
- **Campaign Manager:** creates/manages campaigns and audience workflows within grants.
- **Communication Team:** prepares content/templates and may manage assigned audience/campaign resources.
- **Approver:** reviews assigned campaign versions; approval permission and separation-of-duties constraints apply.

Organizations may assign multiple roles to a membership. The effective permission set is the union of assigned role permissions, constrained by tenant/resource/workflow policies. Role inheritance and explicit deny semantics are not assumed in v2.

## 2. Permission catalog

Identity/organization: `organization:read`, `organization:update`, `members:read`, `members:create`, `members:update`, `members:deactivate`, `roles:read`, `roles:create`, `roles:update`, `roles:assign`, `permissions:read`.

Audience: `audiences:read`, `audiences:create`, `audiences:update`, `audiences:deactivate`, `audiences:import`, `audiences:export`, `segments:read`, `segments:create`, `segments:update`, `consent:read`, `consent:update`, `suppression:read`, `suppression:update`.

Campaign/governance: `campaigns:read`, `campaigns:create`, `campaigns:update`, `campaigns:submit`, `campaigns:cancel`, `approvals:read`, `approvals:approve`, `approvals:reject`.

Templates/localization: `templates:read`, `templates:create`, `templates:update`, `templates:publish`, `localization:read`, `localization:update`, `translation_reviews:submit` (R2 if AI assistance is introduced).

Distribution/analytics: `distribution:mock_execute`, `distribution:pause`, `distribution:cancel`, `analytics:read`, `audit:read`.

## 3. Baseline role-to-capability matrix

This is a proposed default grant template, not a substitute for per-request authorization. Multiple roles combine; exact least-privilege grants should be reviewed for each organization.

| Capability | Platform Operator | Org Admin | Campaign Manager | Communication Team | Approver |
|---|---|---|---|---|---|
| Platform operations | Yes, restricted | No | No | No | No |
| View own organization | Policy | Yes | Yes | Yes, scoped | Yes, scoped |
| Manage members | Platform policy | Yes | No by default | No | No |
| Assign organization roles | Platform policy | Yes, constrained | No by default | No | No |
| View audience | Support policy | Yes | Yes | Assigned/limited | No by default |
| Create/import audience | Support policy | Yes | Yes | Policy | No |
| Export audience PII | Explicit support grant | Explicit grant | No by default | No by default | No |
| Manage consent/suppression | Support policy | Yes | Policy | Policy | No |
| Create segments | Support policy | Yes | Yes | Policy | No |
| Create/edit campaigns | Support policy | Yes | Yes | Assigned/limited | No |
| Submit campaign | Support policy | Yes | Yes | No by default | No |
| View approval queue | Support policy | Policy | No by default | No | Yes, assigned |
| Approve/reject | No by default | Policy, with separation | No by default | No by default | Yes, assigned |
| Create templates | Support policy | Yes | Policy | Yes | No |
| Mock execution | Support policy | Policy | Policy | No by default | No |
| View analytics | Support policy | Yes | Yes | Assigned/limited | Policy |
| View audit | Platform scope | Own org, scoped | Own/assigned | No by default | Approval history |

## 4. Enforcement rules

1. Deny by default; check permission on every API request.
2. Resolve organization from authenticated membership/active context.
3. Verify resource tenant ownership and assignment/ownership constraints.
4. Enforce state transitions in backend services.
5. Validate grantor authority and role scope before assigning roles.
6. Organization administrators cannot create or assign platform roles.
7. Re-evaluate permissions after membership/role revocation.
8. Enforce approval separation-of-duties and quorum policy once decided.
9. Workers revalidate tenant, execution and delivery state; queued task payload is not authorization.
10. UI permission gates are presentation only, never security controls.

## 5. Required negative tests

- Organization A cannot read/write Organization B resources.
- Org admin cannot assign platform role or grant permissions beyond policy.
- User with two roles receives intended combined permissions only in that organization.
- Role revoked in Org A does not affect unrelated Org B role assignment.
- Revoked membership/session loses access.
- Campaign creator cannot self-approve where policy prohibits it.
- Communication Team cannot approve or execute without explicit grant.
- Worker cannot process task under missing/incorrect tenant context.

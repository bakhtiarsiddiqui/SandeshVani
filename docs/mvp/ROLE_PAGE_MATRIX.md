# SandeshVani — role-to-page MVP matrix

Access is presentation-filtered using server-issued permissions. Backend authorization remains authoritative.

| Page / workspace | Platform Operator | Organization Administrator | Campaign Manager | Communication Team | Approver |
|---|---:|---:|---:|---:|---:|
| Overview | Yes | Yes | Yes | Yes | Yes |
| Audience & Contacts | Platform-specific view | Yes | Yes | Yes | No by default |
| Segments | No | Yes | Yes | No | No |
| Consent & Suppression | No | Yes | No | No | No |
| Campaigns | No | Yes | Yes | Yes | Read-only |
| Posts & Templates | No | Yes | Read-only | Yes | No |
| Approvals Queue | No | Only if explicitly granted | No by default | No by default | Yes |
| Mock Distribution | Platform operations view | Yes | Yes | No | No |
| Delivery Analytics | Platform view | Yes | Yes | Yes | Yes |
| Members & Roles | Platform users are separate | Yes | No | No | No |
| Organization Settings | No | Yes | No | No | No |
| Audit Log | Platform audit requires a separate future API | Yes | No | No | Approval history only |
| Platform Administration | Yes, via global assignment only | No | No | No | No |

## Existing RBAC role catalogue

- Platform Operator — global platform assignment, stored separately from organization memberships.
- Organization Administrator — broad organization administration and workflow grants.
- Campaign Manager — audience, segment and campaign authoring/submission grants.
- Communication Team — audience read, content/template creation and campaign read/write grants.
- Approver — campaign read and approval read/approve/reject grants.

A membership may contain multiple roles. Effective organization permissions are the union returned by the backend. Platform assignments remain separate and are fetched from the authenticated user's own platform assignment records.

Post Manager and Event Manager are not additional roles in the current agreed RBAC model. Post/content preparation is presented under Communication Team.

## Demo boundary

The workspaces are navigable, but pages whose backend domain APIs do not yet exist display sample records and local-only interactions. No local demo action writes an audit record, creates a campaign in PostgreSQL, records a consent decision, executes a queue job or sends an external message.

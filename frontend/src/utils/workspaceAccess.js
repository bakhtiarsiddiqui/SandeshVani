/**
 * Presentation-only navigation derived from API-issued permissions and
 * the separately authenticated platform-role context.
 */
export const WORKSPACE_NAVIGATION = [
  { id: "overview", label: "Overview", permissions: [] },
  { id: "audience", label: "Audience & Contacts", permissions: ["audiences:read"] },
  { id: "segments", label: "Segments", permissions: ["segments:read"] },
  { id: "consent", label: "Consent & Suppression", permissions: ["consent:read", "suppression:read"] },
  { id: "campaigns", label: "Campaigns", permissions: ["campaigns:read"] },
  { id: "content", label: "Posts & Templates", permissions: ["templates:read", "templates:create"] },
  { id: "approvals", label: "Approvals Queue", permissions: ["approvals:read"] },
  { id: "distribution", label: "Mock Distribution", permissions: ["distribution:mock_execute"] },
  { id: "analytics", label: "Delivery Analytics", permissions: ["analytics:read"] },
  { id: "organization", label: "Members & Roles", permissions: ["members:read", "roles:read"] },
  { id: "org-settings", label: "Organization Settings", permissions: ["organization:update"] },
  { id: "audit", label: "Audit Log", permissions: ["audit:read"] },
  { id: "platform", label: "Platform Administration", permissions: [], platformOnly: true },
];

export function normalizeRoleName(role) {
  const value = typeof role === "string" ? role : role?.name;
  if (typeof value !== "string") return "";
  const normalized = value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  const aliases = {
    org_admin: "organization_administrator",
    organization_admin: "organization_administrator",
    admin: "organization_administrator",
    comms_team: "communication_team",
    content_manager: "communication_team",
    post_manager: "communication_team",
    super_admin: "platform_operator",
    platform_admin: "platform_operator",
  };
  return aliases[normalized] || normalized;
}

export function hasPlatformRole(platformRoles = []) {
  return (Array.isArray(platformRoles) ? platformRoles : [])
    .some((role) => normalizeRoleName(role) === "platform_operator");
}

export function getVisibleNavigation(permissions = [], platformRoles = []) {
  const permissionSet = new Set(Array.isArray(permissions) ? permissions : []);
  const platformRole = hasPlatformRole(platformRoles);
  return WORKSPACE_NAVIGATION.filter((item) => {
    if (item.id === "overview") return true;
    if (item.platformOnly) return platformRole;
    return item.permissions.some((permission) => permissionSet.has(permission));
  }).map(({ id, label }) => ({
    id,
    label: id === "content" && !permissionSet.has("templates:create") ? "Template Library" : label,
  }));
}

export function canAccessWorkspace(workspaceId, permissions = [], platformRoles = []) {
  return getVisibleNavigation(permissions, platformRoles).some((item) => item.id === workspaceId);
}

export function getDefaultWorkspace(roles = [], platformRoles = [], permissions = []) {
  if (hasPlatformRole(platformRoles)) return "platform";
  const names = (Array.isArray(roles) ? roles : []).map(normalizeRoleName);
  const preferred = [
    ["organization_administrator", "organization"],
    ["campaign_manager", "campaigns"],
    ["communication_team", "content"],
    ["approver", "approvals"],
  ];
  for (const [roleName, workspace] of preferred) {
    if (names.includes(roleName) && canAccessWorkspace(workspace, permissions)) return workspace;
  }
  return "overview";
}

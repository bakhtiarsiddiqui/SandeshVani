import { describe, expect, it } from "vitest";
import { canAccessWorkspace, getDefaultWorkspace, getVisibleNavigation, hasPlatformRole, normalizeRoleName } from "../utils/workspaceAccess";

const admin = ["organization:read", "organization:update", "members:read", "members:create", "roles:read", "roles:assign", "permissions:read", "audiences:read", "audiences:create", "audiences:update", "audiences:import", "segments:read", "segments:create", "consent:read", "consent:update", "campaigns:read", "campaigns:create", "campaigns:update", "campaigns:submit", "campaigns:cancel", "templates:read", "templates:create", "distribution:mock_execute", "analytics:read", "audit:read"];
const campaign = ["organization:read", "audiences:read", "audiences:create", "audiences:update", "audiences:import", "segments:read", "segments:create", "campaigns:read", "campaigns:create", "campaigns:update", "campaigns:submit", "templates:read", "distribution:mock_execute", "analytics:read"];
const comms = ["organization:read", "audiences:read", "templates:read", "templates:create", "campaigns:read", "campaigns:create", "campaigns:update", "analytics:read"];
const approver = ["organization:read", "campaigns:read", "approvals:read", "approvals:approve", "approvals:reject", "analytics:read"];
const ids = (permissions, platform = []) => getVisibleNavigation(permissions, platform).map((item) => item.id);

describe("role-aware workspace navigation", () => {
  it("normalizes the five established roles", () => {
    expect(normalizeRoleName("Organization Administrator")).toBe("organization_administrator");
    expect(normalizeRoleName("Campaign Manager")).toBe("campaign_manager");
    expect(normalizeRoleName("Communication Team")).toBe("communication_team");
    expect(normalizeRoleName("Approver")).toBe("approver");
    expect(normalizeRoleName("Platform Operator")).toBe("platform_operator");
  });
  it("shows administrator capabilities from actual permissions", () => {
    expect(ids(admin)).toEqual(["overview", "audience", "segments", "consent", "campaigns", "content", "distribution", "analytics", "organization", "org-settings", "audit"]);
    expect(getDefaultWorkspace(["Organization Administrator"], [], admin)).toBe("organization");
  });
  it("limits Campaign Manager to granted workspaces", () => {
    expect(ids(campaign)).toEqual(["overview", "audience", "segments", "campaigns", "content", "distribution", "analytics"]);
    expect(canAccessWorkspace("approvals", campaign)).toBe(false);
    expect(canAccessWorkspace("organization", campaign)).toBe(false);
    expect(getDefaultWorkspace(["Campaign Manager"], [], campaign)).toBe("campaigns");
  });
  it("limits Communication Team to content and granted read capabilities", () => {
    expect(ids(comms)).toEqual(["overview", "audience", "campaigns", "content", "analytics"]);
    expect(getDefaultWorkspace(["Communication Team"], [], comms)).toBe("content");
    expect(canAccessWorkspace("organization", comms)).toBe(false);
  });
  it("limits Approver to review-related pages", () => {
    expect(ids(approver)).toEqual(["overview", "campaigns", "approvals", "analytics"]);
    expect(getDefaultWorkspace(["Approver"], [], approver)).toBe("approvals");
  });
  it("exposes global administration only for a server-supplied platform assignment", () => {
    const platform = [{ name: "Platform Operator", scope: "platform" }];
    expect(hasPlatformRole(platform)).toBe(true);
    expect(ids([], platform)).toEqual(["overview", "platform"]);
    expect(getDefaultWorkspace([], platform, [])).toBe("platform");
    expect(ids(admin)).not.toContain("platform");
  });
  it("combines permissions when a user has multiple organization roles", () => {
    const combined = [...new Set([...campaign, ...approver])];
    expect(ids(combined)).toContain("approvals");
    expect(ids(combined)).toContain("campaigns");
    expect(ids(combined)).not.toContain("organization");
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import OrganizationAdminWorkspace from "../pages/workspaces/OrganizationAdminWorkspace";

const get = vi.fn();
const post = vi.fn();
const del = vi.fn();

vi.mock("../api/client", () => ({
  default: { get: (...args) => get(...args), post: (...args) => post(...args), delete: (...args) => del(...args) },
}));

const roles = [
  { id: "role-campaign", name: "Campaign Manager", description: "Campaign authoring", permissions: [{ id: "p1", code: "campaigns:create" }] },
  { id: "role-approver", name: "Approver", description: "Campaign review", permissions: [{ id: "p2", code: "approvals:read" }] },
];
const members = [{
  id: "membership-1", organization_id: "org-1", user_id: "user-1", status: "active",
  joined_at: "2026-11-13T10:00:00Z",
  user: { id: "user-1", email: "meera@example.org", full_name: "Meera Singh" },
  roles: [roles[0]],
}];

beforeEach(() => {
  vi.clearAllMocks();
  get.mockImplementation((url) => Promise.resolve({ data: url.endsWith("/members") ? members : roles }));
});

describe("OrganizationAdminWorkspace", () => {
  it("loads tenant members and organization-only roles", async () => {
    render(<OrganizationAdminWorkspace organizationId="org-1" permissions={["members:read", "roles:read"]} />);
    expect(await screen.findByText("Meera Singh")).toBeVisible();
    expect(screen.getByText("Campaign Manager")).toBeVisible();
    expect(get).toHaveBeenCalledWith("/organizations/org-1/members");
    expect(get).toHaveBeenCalledWith("/organizations/org-1/roles");
  });

  it("adds an already-registered user with selected organization roles", async () => {
    const user = userEvent.setup();
    post.mockResolvedValueOnce({ data: { id: "membership-2" } });
    render(<OrganizationAdminWorkspace organizationId="org-1" permissions={["members:read", "members:create", "roles:read"]} />);
    await screen.findByText("Meera Singh");
    await user.click(screen.getByRole("button", { name: "Add existing account" }));
    await user.type(screen.getByLabelText("Registered account email"), "new.member@example.org");
    await user.click(screen.getByLabelText("Approver"));
    await user.click(screen.getByRole("button", { name: "Add to organization" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/organizations/org-1/members", {
      email: "new.member@example.org", role_ids: ["role-approver"],
    }));
  });

  it("assigns and removes organization roles through the existing endpoints", async () => {
    const user = userEvent.setup();
    post.mockResolvedValue({ data: { message: "Role assigned successfully" } });
    del.mockResolvedValue({ data: { message: "Role removed successfully" } });
    render(<OrganizationAdminWorkspace organizationId="org-1" permissions={["members:read", "roles:read", "roles:assign"]} />);
    await screen.findByText("Meera Singh");
    const roleSelect = screen.getByLabelText("Role for Meera Singh");
    await user.selectOptions(roleSelect, "role-approver");
    await user.click(screen.getByRole("button", { name: "Assign" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/organizations/org-1/members/membership-1/roles", { role_id: "role-approver" }));
    await user.click(screen.getByRole("button", { name: "Remove Campaign Manager from Meera Singh" }));
    await waitFor(() => expect(del).toHaveBeenCalledWith("/organizations/org-1/members/membership-1/roles/role-campaign"));
  });
});

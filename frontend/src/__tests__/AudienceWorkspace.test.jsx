import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AudienceWorkspace from "../pages/workspaces/AudienceWorkspace";

const get = vi.fn();
const post = vi.fn();
const patch = vi.fn();

vi.mock("../api/client", () => ({
  default: { get: (...args) => get(...args), post: (...args) => post(...args), patch: (...args) => patch(...args) },
}));

const member = {
  id: "contact-1", organization_id: "org-1", full_name: "Meera Singh",
  email: "meera@example.org", phone: "+919876543210", preferred_language: "hi",
  district: "Meerut", status: "active", created_at: "2026-11-13T10:00:00Z",
  updated_at: "2026-11-13T10:00:00Z",
};
const page = { data: [member], pagination: { next_cursor: null, has_more: false, limit: 25 } };

beforeEach(() => {
  vi.clearAllMocks();
  get.mockResolvedValue({ data: page });
});

describe("AudienceWorkspace", () => {
  it("loads and displays contacts from the active tenant API", async () => {
    render(<AudienceWorkspace organizationId="org-1" permissions={["audiences:read"]} />);
    expect(await screen.findByText("Meera Singh")).toBeVisible();
    expect(get).toHaveBeenCalledWith("/audiences", { params: { limit: 25 } });
    expect(screen.getByText("Connected to audience API")).toBeVisible();
  });

  it("submits filters to the API instead of filtering sample records locally", async () => {
    const user = userEvent.setup();
    render(<AudienceWorkspace organizationId="org-1" permissions={["audiences:read"]} />);
    await screen.findByText("Meera Singh");
    await user.type(screen.getByPlaceholderText("Name, email or phone"), "Meera");
    await user.selectOptions(screen.getByLabelText("Language"), "hi");
    await user.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() => expect(get).toHaveBeenLastCalledWith("/audiences", {
      params: { limit: 25, search: "Meera", language: "hi" },
    }));
  });

  it("creates contacts through the existing CRUD endpoint", async () => {
    const user = userEvent.setup();
    post.mockResolvedValueOnce({ data: { ...member, id: "contact-2", full_name: "New Contact" } });
    render(<AudienceWorkspace organizationId="org-1" permissions={["audiences:read", "audiences:create"]} />);
    await screen.findByText("Meera Singh");
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    await user.type(screen.getByLabelText("Full name"), "New Contact");
    await user.type(screen.getByLabelText("Email address"), "new@example.org");
    await user.click(screen.getByRole("button", { name: "Create contact" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/audiences", {
      full_name: "New Contact", email: "new@example.org", phone: null,
      preferred_language: "en", district: null,
    }));
  });

  it("keeps the CSV endpoint's file-only semantics visible", async () => {
    const user = userEvent.setup();
    post.mockResolvedValueOnce({ data: { id: "upload-1", row_count: 12, byte_size: 512, sha256: "hash", created_at: "2026-11-13T10:00:00Z" } });
    render(<AudienceWorkspace organizationId="org-1" permissions={["audiences:read", "audiences:create"]} />);
    await screen.findByText("Meera Singh");
    const file = new File(["full_name,email\nMeera,meera@example.org"], "audience.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText("CSV file"), file);
    await user.click(screen.getByRole("button", { name: "Validate & upload" }));
    expect(await screen.findByText(/This is a file-level upload only/)).toBeVisible();
    expect(post).toHaveBeenCalledWith("/audiences/imports", expect.any(FormData), {
      headers: { "Content-Type": "multipart/form-data" },
    });
  });
});

import { beforeEach, describe, expect, it, vi } from "vitest";

const { apiClient } = vi.hoisted(() => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

vi.mock("./client", () => ({ default: apiClient }));

import {
  createAudienceMember,
  getApiErrorMessage,
  getAudienceImportJob,
  listAudienceImportErrors,
  listAudienceMembers,
  updateAudienceMember,
  uploadAudienceCsv,
} from "./audiences";

describe("audience API client", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists audience members with the supplied tenant filters and cursor", async () => {
    const response = { data: { data: [], pagination: { has_more: false } } };
    apiClient.get.mockResolvedValue(response);

    await expect(listAudienceMembers({ limit: 25, status: "active", cursor: "next" })).resolves.toEqual(response.data);
    expect(apiClient.get).toHaveBeenCalledWith("/audiences", {
      params: { limit: 25, status: "active", cursor: "next" },
    });
  });

  it("creates and updates contacts through the existing API routes", async () => {
    apiClient.post.mockResolvedValue({ data: { id: "contact-1" } });
    apiClient.patch.mockResolvedValue({ data: { id: "contact-1", status: "inactive" } });

    await createAudienceMember({ full_name: "Test Contact", phone: "+919876543210" });
    await updateAudienceMember("contact-1", { status: "inactive" });

    expect(apiClient.post).toHaveBeenCalledWith("/audiences", {
      full_name: "Test Contact",
      phone: "+919876543210",
    });
    expect(apiClient.patch).toHaveBeenCalledWith("/audiences/contact-1", { status: "inactive" });
  });

  it("uploads CSV as multipart form data", async () => {
    apiClient.post.mockResolvedValue({ data: { job_id: "job-1", status: "queued" } });
    const file = new File(["full_name,email\nTest,test@example.com"], "audience.csv", { type: "text/csv" });

    await uploadAudienceCsv(file);

    const [url, body, config] = apiClient.post.mock.calls[0];
    expect(url).toBe("/audiences/imports");
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("file")).toBe(file);
    expect(config.headers["Content-Type"]).toBe("multipart/form-data");
  });

  it("reads import progress and paginated row errors", async () => {
    apiClient.get.mockResolvedValueOnce({ data: { id: "job-1", status: "processing" } });
    apiClient.get.mockResolvedValueOnce({ data: { data: [], pagination: { has_more: false } } });

    await getAudienceImportJob("job-1");
    await listAudienceImportErrors("job-1", { limit: 50, cursor: "error-cursor" });

    expect(apiClient.get).toHaveBeenNthCalledWith(1, "/audiences/imports/job-1");
    expect(apiClient.get).toHaveBeenNthCalledWith(2, "/audiences/imports/job-1/errors", {
      params: { limit: 50, cursor: "error-cursor" },
    });
  });

  it("normalizes API validation and server errors for display", () => {
    expect(getApiErrorMessage({ response: { data: { detail: "Duplicate contact" } } })).toBe("Duplicate contact");
    expect(getApiErrorMessage({ response: { data: { detail: [{ msg: "Invalid email" }, { msg: "Required" }] } })).toBe("Invalid email; Required");
    expect(getApiErrorMessage(new Error("Network unavailable"))).toBe("Network unavailable");
  });
});

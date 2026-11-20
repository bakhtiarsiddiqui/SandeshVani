import apiClient from "./client";

export async function listAudienceMembers(params = {}) {
  const { data } = await apiClient.get("/audiences", { params });
  return data;
}

export async function createAudienceMember(payload) {
  const { data } = await apiClient.post("/audiences", payload);
  return data;
}

export async function updateAudienceMember(id, payload) {
  const { data } = await apiClient.patch(`/audiences/${id}`, payload);
  return data;
}

export async function uploadAudienceCsv(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post("/audiences/imports", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getAudienceImportJob(jobId) {
  const { data } = await apiClient.get(`/audiences/imports/${jobId}`);
  return data;
}

export async function listAudienceImportErrors(jobId, params = {}) {
  const { data } = await apiClient.get(`/audiences/imports/${jobId}/errors`, { params });
  return data;
}

export function getApiErrorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || "Invalid value").join("; ");
  }
  return error?.message || "Something went wrong. Please try again.";
}

import { useCallback, useEffect, useState } from "react";
import apiClient from "../../api/client";
import PageHeader from "../../components/layout/PageHeader";
import DataTable from "../../components/ui/DataTable";
import StatusBadge from "../../components/ui/StatusBadge";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import FormField from "../../components/ui/FormField";
import Alert from "../../components/ui/Alert";

const PAGE_SIZE = 25;
const EMPTY_FORM = { full_name: "", email: "", phone: "", preferred_language: "en", district: "", status: "active" };

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => {
    const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : "field";
    return field ? field + ": " + item.msg : item.msg;
  }).join("; ");
  return fallback;
}

function MemberForm({ initialValue = EMPTY_FORM, onCancel, onSave, saving, editing = false }) {
  const [form, setForm] = useState(() => ({ ...EMPTY_FORM, ...initialValue, email: initialValue.email || "", phone: initialValue.phone || "", district: initialValue.district || "" }));
  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));
  const hasContactPoint = Boolean(form.email.trim() || form.phone.trim());
  return <form className="rounded-xl border border-base-300 bg-base-100 p-4 space-y-4" onSubmit={(event) => {
    event.preventDefault();
    onSave({ ...form, full_name: form.full_name.trim(), email: form.email.trim() || null, phone: form.phone.trim() || null, district: form.district.trim() || null });
  }}>
    <div><h2 className="font-semibold text-sm">{editing ? "Edit contact" : "Add audience contact"}</h2><p className="text-xs text-base-content/60 mt-1">At least one contact point (email or E.164 phone) is required.</p></div>
    <div className="grid gap-3 md:grid-cols-2">
      <FormField label="Full name" required><Input value={form.full_name} onChange={update("full_name")} required maxLength={255} disabled={saving} /></FormField>
      <FormField label="Email address" helperText="Optional when a phone number is supplied."><Input type="email" value={form.email} onChange={update("email")} maxLength={255} disabled={saving} /></FormField>
      <FormField label="Phone number" helperText="Use international E.164 format, for example +919876543210."><Input type="tel" value={form.phone} onChange={update("phone")} pattern="^\+[1-9]\d{7,14}$" disabled={saving} /></FormField>
      <FormField label="Preferred language" required>{({ id }) => <select id={id} className="select select-bordered w-full bg-base-100" value={form.preferred_language} onChange={update("preferred_language")} disabled={saving}><option value="en">English</option><option value="hi">Hindi</option></select>}</FormField>
      <FormField label="District"><Input value={form.district || ""} onChange={update("district")} maxLength={150} disabled={saving} /></FormField>
      {editing && <FormField label="Status" required>{({ id }) => <select id={id} className="select select-bordered w-full bg-base-100" value={form.status} onChange={update("status")} disabled={saving}><option value="active">Active</option><option value="inactive">Inactive</option></select>}</FormField>}
    </div>
    {!hasContactPoint && <p className="text-xs text-warning">Enter an email address or phone number before saving.</p>}
    <div className="flex justify-end gap-2"><Button size="sm" variant="ghost" onClick={onCancel} disabled={saving}>Cancel</Button><Button size="sm" type="submit" isLoading={saving} disabled={!form.full_name.trim() || !hasContactPoint}>{editing ? "Save changes" : "Create contact"}</Button></div>
  </form>;
}

export default function AudienceWorkspace({ permissions = [], organizationId }) {
  const canRead = permissions.includes("audiences:read");
  const canCreate = permissions.includes("audiences:create");
  const canUpdate = permissions.includes("audiences:update");
  const [members, setMembers] = useState([]);
  const [pagination, setPagination] = useState({ next_cursor: null, has_more: false, limit: PAGE_SIZE });
  const [pageCursors, setPageCursors] = useState([null]);
  const [searchDraft, setSearchDraft] = useState("");
  const [filtersDraft, setFiltersDraft] = useState({ status: "", district: "", language: "" });
  const [appliedFilters, setAppliedFilters] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [formError, setFormError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState("");

  const loadPage = useCallback(async (cursor = null) => {
    if (!organizationId || !canRead) return;
    setIsLoading(true);
    setLoadError("");
    try {
      const params = { limit: PAGE_SIZE, ...appliedFilters };
      if (cursor) params.cursor = cursor;
      const response = await apiClient.get("/audiences", { params });
      setMembers(response.data.data || []);
      setPagination(response.data.pagination || { next_cursor: null, has_more: false, limit: PAGE_SIZE });
    } catch (error) {
      setLoadError(getErrorMessage(error, "Unable to load audience contacts."));
      setMembers([]);
      setPagination({ next_cursor: null, has_more: false, limit: PAGE_SIZE });
    } finally {
      setIsLoading(false);
    }
  }, [organizationId, canRead, appliedFilters]);

  useEffect(() => { loadPage(null); }, [loadPage]);

  const applyFilters = (event) => {
    event.preventDefault();
    setAppliedFilters({
      ...(searchDraft.trim() ? { search: searchDraft.trim() } : {}),
      ...(filtersDraft.status ? { status: filtersDraft.status } : {}),
      ...(filtersDraft.district.trim() ? { district: filtersDraft.district.trim() } : {}),
      ...(filtersDraft.language ? { language: filtersDraft.language } : {}),
    });
    setPageCursors([null]);
  };

  const saveMember = async (values) => {
    setIsSaving(true);
    setFormError("");
    try {
      if (editingMember) {
        const { full_name, email, phone, preferred_language, district, status } = values;
        await apiClient.patch("/audiences/" + editingMember.id, { full_name, email, phone, preferred_language, district, status });
      } else {
        const { full_name, email, phone, preferred_language, district } = values;
        await apiClient.post("/audiences", { full_name, email, phone, preferred_language, district });
      }
      setShowCreate(false);
      setEditingMember(null);
      setPageCursors([null]);
      await loadPage(null);
    } catch (error) {
      setFormError(getErrorMessage(error, "Unable to save this contact. Check the fields and try again."));
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpload = async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    if (!uploadFile) return;
    setIsUploading(true);
    setUploadError("");
    setUploadResult(null);
    try {
      const body = new FormData();
      body.append("file", uploadFile);
      const response = await apiClient.post("/audiences/imports", body, { headers: { "Content-Type": "multipart/form-data" } });
      setUploadResult(response.data);
      setUploadFile(null);
      formElement.reset();
    } catch (error) {
      setUploadError(getErrorMessage(error, "CSV upload failed. Check the file format and configured limits."));
    } finally {
      setIsUploading(false);
    }
  };

  const columns = [
    { key: "full_name", header: "Contact", render: (row) => <span className="font-semibold text-base-content">{row.full_name}</span> },
    { key: "email", header: "Email", render: (row) => row.email || "—" },
    { key: "phone", header: "Phone", render: (row) => row.phone || "—" },
    { key: "district", header: "District", render: (row) => row.district || "—" },
    { key: "preferred_language", header: "Language", render: (row) => row.preferred_language === "hi" ? "Hindi" : "English" },
    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status === "active" ? "approved" : "rejected"} label={row.status} /> },
    ...(canUpdate ? [{ key: "actions", header: "Actions", render: (row) => <Button size="sm" variant="ghost" onClick={() => { setFormError(""); setShowCreate(false); setEditingMember(row); }}>Edit</Button> }] : []),
  ];

  if (!canRead) return <div className="space-y-4"><PageHeader title="Audience & Contacts" subtitle="Contact directory for the active organization." /><Alert variant="error" title="Access denied">Your assigned roles do not grant audience read access.</Alert></div>;

  return <div className="space-y-6">
    <PageHeader title="Audience & Contacts" subtitle="Manage the active organization’s contact records and validated CSV uploads." breadcrumbs={["Platform", "Audience"]} badge={<StatusBadge status="approved" label="Connected to audience API" />} actions={canCreate ? <Button size="sm" onClick={() => { setEditingMember(null); setFormError(""); setShowCreate((value) => !value); }}>Add contact</Button> : null} />
    {formError && <Alert variant="error" title="Contact not saved">{formError}</Alert>}
    {showCreate && canCreate && <MemberForm onCancel={() => setShowCreate(false)} onSave={saveMember} saving={isSaving} />}
    {editingMember && canUpdate && <MemberForm initialValue={editingMember} editing onCancel={() => setEditingMember(null)} onSave={saveMember} saving={isSaving} />}

    <section className="rounded-xl border border-base-300 bg-base-100 p-4 space-y-3">
      <div><h2 className="font-semibold text-sm">Filter contacts</h2><p className="text-xs text-base-content/60 mt-1">Filters are sent to the tenant-scoped audience API.</p></div>
      <form onSubmit={applyFilters} className="grid gap-3 md:grid-cols-5">
        <FormField label="Search"><Input placeholder="Name, email or phone" value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} maxLength={100} /></FormField>
        <FormField label="Status">{({ id }) => <select id={id} className="select select-bordered w-full bg-base-100" value={filtersDraft.status} onChange={(event) => setFiltersDraft((value) => ({ ...value, status: event.target.value }))}><option value="">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option></select>}</FormField>
        <FormField label="District"><Input value={filtersDraft.district} onChange={(event) => setFiltersDraft((value) => ({ ...value, district: event.target.value }))} maxLength={150} /></FormField>
        <FormField label="Language">{({ id }) => <select id={id} className="select select-bordered w-full bg-base-100" value={filtersDraft.language} onChange={(event) => setFiltersDraft((value) => ({ ...value, language: event.target.value }))}><option value="">Any language</option><option value="en">English</option><option value="hi">Hindi</option></select>}</FormField>
        <div className="flex items-end"><Button type="submit" size="sm" className="w-full">Apply filters</Button></div>
      </form>
    </section>

    {loadError && <Alert variant="error" title="Audience could not be loaded">{loadError}</Alert>}
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-2"><div><h2 className="font-semibold text-sm">Contact directory</h2><p className="text-xs text-base-content/60">Showing up to {pagination.limit || PAGE_SIZE} records per page.</p></div><Button size="sm" variant="ghost" onClick={() => loadPage(pageCursors[pageCursors.length - 1] || null)} disabled={isLoading}>Refresh</Button></div>
      <DataTable columns={columns} data={members} isLoading={isLoading} error={loadError} onRetry={() => loadPage(pageCursors[pageCursors.length - 1] || null)} emptyTitle="No contacts found" emptyDescription="Adjust the filters or add a contact to this organization." />
      <div className="flex items-center justify-between">
        <Button size="sm" variant="ghost" disabled={pageCursors.length <= 1 || isLoading} onClick={() => { const previous = pageCursors.slice(0, -1); setPageCursors(previous); loadPage(previous[previous.length - 1] || null); }}>Previous</Button>
        <span className="text-xs text-base-content/60">Page {pageCursors.length}</span>
        <Button size="sm" variant="outline" disabled={!pagination.has_more || !pagination.next_cursor || isLoading} onClick={() => { setPageCursors((current) => [...current, pagination.next_cursor]); loadPage(pagination.next_cursor); }}>Next</Button>
      </div>
    </section>

    {canCreate && <section className="rounded-xl border border-base-300 bg-base-100 p-4 space-y-3">
      <div><h2 className="font-semibold text-sm">CSV file upload</h2><p className="text-xs text-base-content/60 mt-1">The current backend validates and privately stores the file. It does not import contacts or create an asynchronous import job.</p></div>
      <form onSubmit={handleUpload} className="flex flex-col sm:flex-row gap-3 sm:items-end">
        <FormField label="CSV file" required className="flex-1">{({ id }) => <input id={id} className="file-input file-input-bordered w-full bg-base-100" type="file" accept=".csv,text/csv" required onChange={(event) => setUploadFile(event.target.files?.[0] || null)} />}</FormField>
        <Button type="submit" size="sm" isLoading={isUploading} disabled={!uploadFile || isUploading}>Validate & upload</Button>
      </form>
      {uploadError && <Alert variant="error" title="Upload failed">{uploadError}</Alert>}
      {uploadResult && <Alert variant="success" title="File validated and stored"><p>This is a file-level upload only; no contacts have been imported.</p><p className="mt-1">Rows: {uploadResult.row_count} · Size: {uploadResult.byte_size} bytes</p><p className="mt-1 break-all text-[11px]">Upload reference: {uploadResult.id}</p></Alert>}
    </section>}
  </div>;
}

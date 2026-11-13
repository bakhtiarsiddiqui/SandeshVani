import { useCallback, useEffect, useState } from "react";
import apiClient from "../../api/client";
import PageHeader from "../../components/layout/PageHeader";
import DataTable from "../../components/ui/DataTable";
import StatusBadge from "../../components/ui/StatusBadge";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import FormField from "../../components/ui/FormField";
import Alert from "../../components/ui/Alert";

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => {
    const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : "field";
    return field ? field + ": " + item.msg : item.msg;
  }).join("; ");
  return fallback;
}

export default function OrganizationAdminWorkspace({ permissions = [], organizationId }) {
  const canReadMembers = permissions.includes("members:read");
  const canAddMembers = permissions.includes("members:create");
  const canReadRoles = permissions.includes("roles:read");
  const canAssignRoles = permissions.includes("roles:assign");
  const [members, setMembers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [notice, setNotice] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [email, setEmail] = useState("");
  const [selectedRoleIds, setSelectedRoleIds] = useState([]);
  const [saving, setSaving] = useState(false);
  const [roleSelectionByMember, setRoleSelectionByMember] = useState({});
  const [busyMembershipId, setBusyMembershipId] = useState(null);

  const loadOrganizationData = useCallback(async () => {
    if (!organizationId) return;
    setIsLoading(true);
    setLoadError("");
    const requests = [];
    if (canReadMembers) requests.push(apiClient.get("/organizations/" + organizationId + "/members").then((response) => ["members", response.data]));
    if (canReadRoles) requests.push(apiClient.get("/organizations/" + organizationId + "/roles").then((response) => ["roles", response.data]));
    try {
      const results = await Promise.all(requests);
      for (const [key, data] of results) {
        if (key === "members") setMembers(data || []);
        if (key === "roles") setRoles(data || []);
      }
    } catch (error) {
      setLoadError(getErrorMessage(error, "Unable to load organization membership and role data."));
    } finally {
      setIsLoading(false);
    }
  }, [organizationId, canReadMembers, canReadRoles]);

  useEffect(() => { loadOrganizationData(); }, [loadOrganizationData]);

  const addMember = async (event) => {
    event.preventDefault();
    if (!email.trim() || selectedRoleIds.length === 0) return;
    setSaving(true);
    setActionError("");
    setNotice("");
    try {
      await apiClient.post("/organizations/" + organizationId + "/members", { email: email.trim(), role_ids: selectedRoleIds });
      setEmail("");
      setSelectedRoleIds([]);
      setShowAddForm(false);
      setNotice("The existing registered account was added to this organization.");
      await loadOrganizationData();
    } catch (error) {
      setActionError(getErrorMessage(error, "Unable to add this account. The account must register before it can be added."));
    } finally {
      setSaving(false);
    }
  };

  const assignRole = async (membershipId) => {
    const roleId = roleSelectionByMember[membershipId];
    if (!roleId) return;
    setBusyMembershipId(membershipId);
    setActionError("");
    setNotice("");
    try {
      await apiClient.post("/organizations/" + organizationId + "/members/" + membershipId + "/roles", { role_id: roleId });
      setRoleSelectionByMember((current) => ({ ...current, [membershipId]: "" }));
      setNotice("Role assignment updated.");
      await loadOrganizationData();
    } catch (error) {
      setActionError(getErrorMessage(error, "Unable to assign this role."));
    } finally {
      setBusyMembershipId(null);
    }
  };

  const removeRole = async (membershipId, roleId) => {
    setBusyMembershipId(membershipId);
    setActionError("");
    setNotice("");
    try {
      await apiClient.delete("/organizations/" + organizationId + "/members/" + membershipId + "/roles/" + roleId);
      setNotice("Role assignment removed.");
      await loadOrganizationData();
    } catch (error) {
      setActionError(getErrorMessage(error, "Unable to remove this role."));
    } finally {
      setBusyMembershipId(null);
    }
  };

  const memberColumns = [
    { key: "name", header: "Member", render: (row) => <span className="font-semibold text-base-content">{row.user?.full_name || "Registered account"}</span> },
    { key: "email", header: "Email", render: (row) => row.user?.email || "—" },
    { key: "status", header: "Membership", render: (row) => <StatusBadge status={row.status === "active" ? "approved" : "pending"} label={row.status} /> },
    { key: "roles", header: "Assigned roles", render: (row) => <div className="flex flex-wrap gap-1.5">{(row.roles || []).length ? row.roles.map((role) => (
      <span key={role.id} className="inline-flex items-center gap-1 rounded-md border border-base-300 bg-base-200 px-2 py-1 text-[11px]">{role.name}{canAssignRoles && <button type="button" aria-label={"Remove " + role.name + " from " + (row.user?.full_name || row.user?.email || "member")} className="text-base-content/50 hover:text-error" disabled={busyMembershipId === row.id} onClick={() => removeRole(row.id, role.id)}>×</button>}</span>
    )) : <span className="text-xs text-base-content/50">No role assigned</span>}</div> },
    ...(canAssignRoles && canReadRoles ? [{
      key: "assign",
      header: "Assign role",
      render: (row) => {
        const availableRoles = roles.filter((role) => !(row.roles || []).some((assigned) => assigned.id === role.id));
        return <div className="flex min-w-52 items-center gap-2">
          <select className="select select-bordered select-xs min-w-0 flex-1 bg-base-100" aria-label={"Role for " + (row.user?.full_name || row.user?.email || "member")} value={roleSelectionByMember[row.id] || ""} onChange={(event) => setRoleSelectionByMember((current) => ({ ...current, [row.id]: event.target.value }))}><option value="">Choose role</option>{availableRoles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}</select>
          <Button size="sm" variant="outline" disabled={!roleSelectionByMember[row.id] || busyMembershipId === row.id} isLoading={busyMembershipId === row.id} onClick={() => assignRole(row.id)}>Assign</Button>
        </div>;
      },
    }] : []),
  ];

  if (!canReadMembers && !canReadRoles) return <div className="space-y-4"><PageHeader title="Organization Administration" subtitle="Manage membership and organization-level roles." /><Alert variant="error" title="Access denied">Your assigned roles do not grant organization membership or role-read access.</Alert></div>;

  return <div className="space-y-6">
    <PageHeader title="Organization Administration" subtitle="Manage members and organization-scoped role assignments for the active tenant." breadcrumbs={["Platform", "Organization Administration"]} badge={<StatusBadge status="approved" label="Connected to organization APIs" />} actions={canAddMembers && canReadRoles ? <Button size="sm" onClick={() => { setActionError(""); setShowAddForm((value) => !value); }}>Add existing account</Button> : null} />
    {loadError && <Alert variant="error" title="Organization data could not be loaded">{loadError}</Alert>}
    {actionError && <Alert variant="error" title="Action not completed">{actionError}</Alert>}
    {notice && <Alert variant="success" title="Saved">{notice}</Alert>}

    {showAddForm && canAddMembers && canReadRoles && <form onSubmit={addMember} className="rounded-xl border border-base-300 bg-base-100 p-4 space-y-4">
      <div><h2 className="font-semibold text-sm">Add an existing registered account</h2><p className="mt-1 text-xs text-base-content/60">There is no invitation endpoint yet. The user must already have registered; this action creates an active membership and assigns the selected organization roles.</p></div>
      <FormField label="Registered account email" required><Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required disabled={saving} /></FormField>
      <fieldset className="space-y-2"><legend className="text-sm font-medium">Organization roles</legend><div className="grid gap-2 sm:grid-cols-2">{roles.map((role) => <label key={role.id} className="flex items-start gap-2 rounded-lg border border-base-300 p-3 text-sm"><input type="checkbox" className="checkbox checkbox-sm checkbox-primary mt-0.5" checked={selectedRoleIds.includes(role.id)} onChange={(event) => setSelectedRoleIds((current) => event.target.checked ? [...current, role.id] : current.filter((id) => id !== role.id))} disabled={saving} /><span><span className="font-semibold">{role.name}</span><span className="block text-xs text-base-content/60">{role.description}</span></span></label>)}</div></fieldset>
      <div className="flex justify-end gap-2"><Button size="sm" variant="ghost" onClick={() => setShowAddForm(false)} disabled={saving}>Cancel</Button><Button size="sm" type="submit" isLoading={saving} disabled={!email.trim() || selectedRoleIds.length === 0}>Add to organization</Button></div>
    </form>}

    {canReadMembers && <section className="space-y-3"><div className="flex items-center justify-between gap-2"><div><h2 className="font-semibold text-sm">Organization members</h2><p className="text-xs text-base-content/60">Memberships returned by the active organization’s API.</p></div><Button size="sm" variant="ghost" onClick={loadOrganizationData} disabled={isLoading}>Refresh</Button></div><DataTable columns={memberColumns} data={members} isLoading={isLoading} error={loadError} onRetry={loadOrganizationData} emptyTitle="No organization members" emptyDescription="No active memberships were returned for this organization." /></section>}

    {canReadRoles && <section className="space-y-3"><div><h2 className="font-semibold text-sm">Organization role catalogue</h2><p className="text-xs text-base-content/60">Only organization-scoped roles returned by this organization’s role API are listed. Platform roles are never assignable here.</p></div><div className="grid gap-3 md:grid-cols-2">{roles.map((role) => <article key={role.id} className="rounded-xl border border-base-300 bg-base-100 p-4"><h3 className="font-semibold text-sm">{role.name}</h3><p className="mt-1 text-xs text-base-content/60">{role.description}</p><div className="mt-3 flex flex-wrap gap-1">{(role.permissions || []).map((permission) => <span key={permission.id} className="rounded border border-base-300 bg-base-200 px-2 py-1 text-[10px]">{permission.code}</span>)}</div></article>)}{!isLoading && roles.length === 0 && <p className="text-xs text-base-content/60">No organization roles were returned.</p>}</div></section>}
  </div>;
}

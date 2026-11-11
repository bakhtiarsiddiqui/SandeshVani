import { useState } from "react";
import { useAuth } from "../context";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import FormField from "../components/ui/FormField";
import Alert from "../components/ui/Alert";
import StatusBadge from "../components/ui/StatusBadge";
import apiClient from "../api/client";

const OrgSelect = ({ onSelectComplete }) => {
  const { activeOrg, organizations, selectOrg, fetchMe } = useAuth();
  const [isSwitching, setIsSwitching] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const handleSwitch = async (orgId) => {
    setIsSwitching(orgId);
    setErrorMessage("");
    try {
      await selectOrg(orgId);
      if (onSelectComplete) {
        onSelectComplete();
      }
    } catch (err) {
      setErrorMessage(err.message || "Failed to switch organization context.");
    } finally {
      setIsSwitching(null);
    }
  };

  const handleCreateOrg = async (e) => {
    e.preventDefault();
    if (!orgName.trim() || !orgSlug.trim()) {
      setErrorMessage("Please enter both organization name and unique slug.");
      return;
    }

    setIsCreating(true);
    setErrorMessage("");
    try {
      const res = await apiClient.post("/organizations", {
        name: orgName.trim(),
        slug: orgSlug.trim().toLowerCase(),
      });
      await fetchMe();
      await selectOrg(res.data.id);
      setShowCreateForm(false);
      setOrgName("");
      setOrgSlug("");
      if (onSelectComplete) {
        onSelectComplete();
      }
    } catch (err) {
      setErrorMessage(
        err.response?.data?.detail || err.message || "Failed to create organization."
      );
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto my-8 p-6 bg-white border border-slate-200 rounded-lg shadow-sm space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Institutional Organizations</h1>
        <p className="text-sm text-slate-600 mt-1">
          Select an active tenant context to manage campaigns, audiences, and dispatch.
        </p>
      </div>

      {errorMessage && (
        <Alert variant="error" title="Action Error" message={errorMessage} />
      )}

      <div className="space-y-3">
        {organizations.length === 0 ? (
          <div className="p-8 text-center bg-slate-50 border border-slate-200 rounded-lg text-slate-600 space-y-3">
            <p className="text-sm">You are not currently an active member of any organization.</p>
            <p className="text-xs text-slate-500">
              Provision an institutional tenant below or ask your department administrator for an invitation.
            </p>
          </div>
        ) : (
          organizations.map((org) => {
            const isActive = activeOrg?.id === org.id;
            return (
              <div
                key={org.id}
                className={`flex items-center justify-between p-4 border rounded-lg transition-colors ${
                  isActive
                    ? "border-primary bg-blue-50/40"
                    : "border-slate-200 hover:border-slate-300 bg-white"
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-900">{org.name}</span>
                    <span className="text-xs font-mono text-slate-500">({org.slug})</span>
                    {isActive && (
                      <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded">
                        Active Context
                      </span>
                    )}
                  </div>
                  <div className="mt-1">
                    <StatusBadge status={org.status} />
                  </div>
                </div>

                <div>
                  {isActive ? (
                    <Button variant="outline" size="sm" disabled>
                      Selected
                    </Button>
                  ) : (
                    <Button
                      variant="primary"
                      size="sm"
                      isLoading={isSwitching === org.id}
                      onClick={() => handleSwitch(org.id)}
                    >
                      Switch To
                    </Button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="pt-4 border-t border-slate-200">
        {!showCreateForm ? (
          <Button
            variant="outline"
            onClick={() => setShowCreateForm(true)}
            className="w-full"
          >
            + Provision New Organization
          </Button>
        ) : (
          <form onSubmit={handleCreateOrg} className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-4">
            <h3 className="font-semibold text-sm text-slate-900">Provision Organization</h3>
            <FormField label="Department / Institution Name" required>
              <Input
                placeholder="e.g. Department of Public Health"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                disabled={isCreating}
                required
              />
            </FormField>
            <FormField label="Tenant Identifier / Slug" required helperText="Lowercase letters, numbers and hyphens">
              <Input
                placeholder="e.g. dept-public-health"
                value={orgSlug}
                onChange={(e) => setOrgSlug(e.target.value)}
                disabled={isCreating}
                required
              />
            </FormField>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="ghost"
                size="sm"
                type="button"
                onClick={() => setShowCreateForm(false)}
                disabled={isCreating}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                type="submit"
                isLoading={isCreating}
              >
                Create & Switch
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default OrgSelect;


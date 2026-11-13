import { useState, useCallback, useEffect, useMemo } from "react";
import { AuthProvider, useAuth } from "./context";
import AppShell from "./components/layout/AppShell";
import Button from "./components/ui/Button";
import ProtectedRoute from "./routes/ProtectedRoute";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";
import VerifyEmail from "./pages/auth/VerifyEmail";
import ForgotPassword from "./pages/auth/ForgotPassword";
import ResetPassword from "./pages/auth/ResetPassword";
import OrgSelect from "./pages/OrgSelect";
import Overview from "./pages/Overview";
import AuthLayout from "./components/fx/AuthLayout";
import {
  AnalyticsWorkspace, ApprovalsWorkspace, AudienceWorkspace, CampaignManagerWorkspace,
  CommunicationWorkspace, ConsentWorkspace, DistributionWorkspace, OrganizationAdminWorkspace,
  OrganizationSettingsWorkspace, PlatformAdministrationWorkspace, SegmentsWorkspace, AuditWorkspace,
} from "./pages/workspaces/RoleWorkspaces";
import { canAccessWorkspace, getDefaultWorkspace, hasPlatformRole, getVisibleNavigation } from "./utils/workspaceAccess";

const ROUTES = { LOGIN: "login", REGISTER: "register", VERIFY_EMAIL: "verify-email", FORGOT_PASSWORD: "forgot-password", RESET_PASSWORD: "reset-password", ORG_SELECT: "org-select", DASHBOARD: "dashboard" };
const WORKSPACES = {
  audience: AudienceWorkspace, segments: SegmentsWorkspace, consent: ConsentWorkspace,
  campaigns: CampaignManagerWorkspace, content: CommunicationWorkspace, approvals: ApprovalsWorkspace,
  distribution: DistributionWorkspace, analytics: AnalyticsWorkspace, organization: OrganizationAdminWorkspace,
  "org-settings": OrganizationSettingsWorkspace, audit: AuditWorkspace, platform: PlatformAdministrationWorkspace,
};

function Dashboard({ onNavigateOrgSelect }) {
  const { activeOrg, logout, permissions, roles, platformRoles, user } = useAuth();
  const navItems = useMemo(() => getVisibleNavigation(permissions, platformRoles), [permissions, platformRoles]);
  const defaultWorkspace = getDefaultWorkspace(roles, platformRoles, permissions);
  const [activeWorkspace, setActiveWorkspace] = useState(defaultWorkspace);
  // Derive a valid page when an organization switch or role revocation changes grants.
  const selected = navItems.some((item) => item.id === activeWorkspace)
    ? activeWorkspace
    : defaultWorkspace;
  const Workspace = WORKSPACES[selected];
  const actions = <div className="flex items-center gap-1">
    {activeOrg && <Button variant="ghost" size="sm" onClick={onNavigateOrgSelect}>Switch organization</Button>}
    <span className="hidden sm:inline text-xs text-base-content/60">{user?.email || ""}</span>
    <Button variant="ghost" size="sm" onClick={logout}>Sign out</Button>
  </div>;
  const navigate = useCallback((target) => {
    if (canAccessWorkspace(target, permissions, platformRoles)) setActiveWorkspace(target);
  }, [permissions, platformRoles]);
  const displayRoles = [...(platformRoles || []), ...(roles || [])];
  return <AppShell activeNav={selected} onNavigate={navigate} navItems={navItems} headerActions={selected === "overview" ? null : actions} organizationName={activeOrg?.name || "Platform workspace"} roles={displayRoles}>
    {selected === "overview" ? <Overview actions={actions} /> : Workspace ? <ProtectedRoute><Workspace permissions={permissions} roles={roles} platformRoles={platformRoles} /></ProtectedRoute> : <Overview actions={actions} />}
  </AppShell>;
}

function AppRouter() {
  const { isAuthenticated, isLoading, activeOrg, platformRoles } = useAuth();
  const getInitialRoute = () => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("reset_token")) return ROUTES.RESET_PASSWORD;
      if (params.get("verify_token")) return ROUTES.VERIFY_EMAIL;
    }
    return ROUTES.LOGIN;
  };
  const [route, setRoute] = useState(getInitialRoute);
  const [verifyEmailAddress, setVerifyEmailAddress] = useState("");
  const [verifyToken, setVerifyToken] = useState(() => typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("verify_token") || "" : "");
  const [resetToken, setResetToken] = useState(() => typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("reset_token") || "" : "");
  const navigate = useCallback((target) => setRoute(target), []);
  // Strip one-time auth tokens from the URL after capturing them in state.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    let changed = false;
    for (const key of ["verify_token", "reset_token"]) {
      if (params.has(key)) { params.delete(key); changed = true; }
    }
    if (changed) {
      const query = params.toString();
      const nextUrl = query
        ? `${window.location.pathname}?${query}${window.location.hash}`
        : `${window.location.pathname}${window.location.hash}`;
      window.history.replaceState({}, document.title, nextUrl);
    }
  }, []);
  if (isLoading) return <div className="min-h-screen flex items-center justify-center bg-base-200"><div className="text-center space-y-3"><div className="inline-block w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" /><p className="text-sm text-base-content/60 font-medium">Authenticating institutional session…</p></div></div>;
  if (isAuthenticated) {
    if (route === ROUTES.ORG_SELECT || (!activeOrg && !hasPlatformRole(platformRoles))) {
      return <div className="min-h-screen bg-base-200 py-8"><OrgSelect onSelectComplete={() => navigate(ROUTES.DASHBOARD)} /></div>;
    }
    return <ProtectedRoute onNavigateToLogin={() => navigate(ROUTES.LOGIN)}><Dashboard onNavigateOrgSelect={() => navigate(ROUTES.ORG_SELECT)} /></ProtectedRoute>;
  }
  return <AuthLayout>
    {route === ROUTES.REGISTER && <Register onNavigateLogin={() => navigate(ROUTES.LOGIN)} onNavigateVerify={(email, token) => { setVerifyEmailAddress(email); if (token) setVerifyToken(token); navigate(ROUTES.VERIFY_EMAIL); }} />}
    {route === ROUTES.VERIFY_EMAIL && <VerifyEmail initialEmail={verifyEmailAddress} initialToken={verifyToken} onNavigateLogin={() => { setVerifyToken(""); navigate(ROUTES.LOGIN); }} />}
    {route === ROUTES.FORGOT_PASSWORD && <ForgotPassword onNavigateLogin={() => navigate(ROUTES.LOGIN)} />}
    {route === ROUTES.RESET_PASSWORD && <ResetPassword initialToken={resetToken} onNavigateLogin={() => { setResetToken(""); navigate(ROUTES.LOGIN); }} />}
    {(route === ROUTES.LOGIN || route === ROUTES.DASHBOARD) && <Login onNavigateRegister={() => navigate(ROUTES.REGISTER)} onNavigateForgot={() => navigate(ROUTES.FORGOT_PASSWORD)} onNavigateVerify={(email) => { setVerifyEmailAddress(email); navigate(ROUTES.VERIFY_EMAIL); }} onSuccess={() => navigate(ROUTES.DASHBOARD)} />}
  </AuthLayout>;
}

export default function App() {
  return <AuthProvider><AppRouter /></AuthProvider>;
}

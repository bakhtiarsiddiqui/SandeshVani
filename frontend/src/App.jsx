import { useState, useCallback } from "react";
import { AuthProvider, useAuth } from "./context";
import AppShell from "./components/layout/AppShell";
import PageHeader from "./components/layout/PageHeader";
import Button from "./components/ui/Button";
import StatusBadge from "./components/ui/StatusBadge";
import ProtectedRoute from "./routes/ProtectedRoute";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";
import VerifyEmail from "./pages/auth/VerifyEmail";
import ForgotPassword from "./pages/auth/ForgotPassword";
import ResetPassword from "./pages/auth/ResetPassword";
import OrgSelect from "./pages/OrgSelect";

// ---------------------------------------------------------------------------
// Route constants
// ---------------------------------------------------------------------------
const ROUTES = {
  LOGIN: "login",
  REGISTER: "register",
  VERIFY_EMAIL: "verify-email",
  FORGOT_PASSWORD: "forgot-password",
  RESET_PASSWORD: "reset-password",
  ORG_SELECT: "org-select",
  DASHBOARD: "dashboard",
};

// ---------------------------------------------------------------------------
// Dashboard placeholder — rendered when authenticated and org context is active
// ---------------------------------------------------------------------------
function Dashboard({ onNavigateOrgSelect }) {
  const { user, activeOrg, logout } = useAuth();

  return (
    <AppShell
      activeNav="overview"
      organizationName={activeOrg?.name || "No Organization Selected"}
    >
      <PageHeader
        title="Har zaroori baat, har zaroori insaan tak."
        subtitle="Your public communication workspace is active."
        badge={<StatusBadge status="active" label="Authenticated" />}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={onNavigateOrgSelect}>
              Switch Organization
            </Button>
            <Button variant="ghost" size="sm" onClick={logout}>
              Sign Out
            </Button>
          </div>
        }
      />

      <section className="rounded-xl bg-base-100 p-8 shadow-xs border border-base-300">
        <p className="text-sm font-semibold text-primary">SANDESHVANI</p>
        <p className="mt-2 text-sm text-base-content/60">
          Signed in as{" "}
          <span className="font-medium text-base-content">{user?.email}</span>
        </p>

        <p className="mt-4 text-sm text-base-content/80 leading-relaxed max-w-2xl">
          Multi-tenant public-awareness and institutional communication infrastructure.
          Direction C (Blue-Teal Hybrid) tokens, DaisyUI custom theme, authentication
          foundation, and tenant-scoped RBAC are active.
        </p>

        {activeOrg && (
          <div className="mt-6 p-4 bg-teal-50 border border-teal-200 rounded-lg text-sm">
            <p className="font-semibold text-teal-800">Active Organization Context</p>
            <p className="text-teal-700 mt-1">
              {activeOrg.name}{" "}
              <span className="font-mono text-xs text-teal-600">({activeOrg.slug})</span>
            </p>
          </div>
        )}
      </section>
    </AppShell>
  );
}

// ---------------------------------------------------------------------------
// Inner router — reads auth state, decides what screen to render
// ---------------------------------------------------------------------------
function AppRouter() {
  const { isAuthenticated, isLoading, activeOrg } = useAuth();

  // Extract reset token from URL hash/query on first render (MVP: hash-based)
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
  const [resetToken, setResetToken] = useState(() => {
    if (typeof window !== "undefined") {
      return new URLSearchParams(window.location.search).get("reset_token") || "";
    }
    return "";
  });

  const navigate = useCallback((target) => setRoute(target), []);

  // Auth is loading — show nothing (AuthProvider shows loading state via isLoading)
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-3">
          <div className="inline-block w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-500 font-medium">
            Authenticating institutional session…
          </p>
        </div>
      </div>
    );
  }

  // Authenticated — show org-select or dashboard
  if (isAuthenticated) {
    if (route === ROUTES.ORG_SELECT || !activeOrg) {
      return (
        <div className="min-h-screen bg-slate-50 py-8">
          <OrgSelect onSelectComplete={() => navigate(ROUTES.DASHBOARD)} />
        </div>
      );
    }

    return (
      <ProtectedRoute onNavigateToLogin={() => navigate(ROUTES.LOGIN)}>
        <Dashboard onNavigateOrgSelect={() => navigate(ROUTES.ORG_SELECT)} />
      </ProtectedRoute>
    );
  }

  // Unauthenticated — render auth screens
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      {route === ROUTES.REGISTER && (
        <Register
          onNavigateLogin={() => navigate(ROUTES.LOGIN)}
          onNavigateVerify={(email, token) => {
            setVerifyEmailAddress(email);
            if (token) setResetToken(token); // dev token reuse slot
            navigate(ROUTES.VERIFY_EMAIL);
          }}
        />
      )}

      {route === ROUTES.VERIFY_EMAIL && (
        <VerifyEmail
          initialEmail={verifyEmailAddress}
          onNavigateLogin={() => navigate(ROUTES.LOGIN)}
        />
      )}

      {route === ROUTES.FORGOT_PASSWORD && (
        <ForgotPassword
          onNavigateLogin={() => navigate(ROUTES.LOGIN)}
        />
      )}

      {route === ROUTES.RESET_PASSWORD && (
        <ResetPassword
          initialToken={resetToken}
          onNavigateLogin={() => {
            setResetToken("");
            navigate(ROUTES.LOGIN);
          }}
        />
      )}

      {(route === ROUTES.LOGIN || route === ROUTES.DASHBOARD) && (
        <Login
          onNavigateRegister={() => navigate(ROUTES.REGISTER)}
          onNavigateForgot={() => navigate(ROUTES.FORGOT_PASSWORD)}
          onNavigateVerify={(email) => {
            setVerifyEmailAddress(email);
            navigate(ROUTES.VERIFY_EMAIL);
          }}
          onSuccess={() => navigate(ROUTES.DASHBOARD)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root — wraps everything in AuthProvider
// ---------------------------------------------------------------------------
function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}

export default App;

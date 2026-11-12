import { useAuth } from "../context";
import LoadingSkeleton from "../components/ui/LoadingSkeleton";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";

const ProtectedRoute = ({
  children,
  requiredPermissions = [],
  onNavigateToLogin,
}) => {
  const { isAuthenticated, isLoading, permissions } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center p-8 space-y-4">
        <LoadingSkeleton type="card" count={1} />
        <p className="text-sm text-base-content/60">Authenticating institutional session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-md mx-auto my-12 p-6 bg-base-100/90 backdrop-blur-sm border border-base-300 rounded-lg shadow-sm text-center space-y-4">
        <h2 className="text-xl font-semibold text-base-content">Authentication Required</h2>
        <p className="text-sm text-base-content/70">
          You must be signed in with an active institutional account to access this resource.
        </p>
        <Button variant="primary" onClick={onNavigateToLogin} className="w-full">
          Sign In
        </Button>
      </div>
    );
  }

  if (requiredPermissions.length > 0) {
    const userPerms = new Set(permissions);
    const missing = requiredPermissions.filter((p) => !userPerms.has(p));
    if (missing.length > 0) {
      return (
        <div className="max-w-2xl mx-auto my-8 p-4">
          <Alert
            variant="error"
            title="Access Denied"
            message={`Your active role grants do not include: ${missing.join(", ")}. Contact your Organization Administrator.`}
          />
        </div>
      );
    }
  }

  return <>{children}</>;
};

export default ProtectedRoute;



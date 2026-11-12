import { useState } from "react";
import { useAuth } from "../../context";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import FormField from "../../components/ui/FormField";
import Alert from "../../components/ui/Alert";

const ResetPassword = ({ initialToken = "", onNavigateLogin }) => {
  const { confirmPasswordReset } = useAuth();
  const [token, setToken] = useState(initialToken);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage("");

    if (!token.trim() || !newPassword || !confirmPassword) {
      setErrorMessage("Please complete all required fields.");
      return;
    }

    if (newPassword.length < 8) {
      setErrorMessage("Password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      await confirmPasswordReset(token.trim(), newPassword);
      setIsSuccess(true);
    } catch (err) {
      setErrorMessage(err.message || "Failed to reset password.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="glow max-w-md w-full mx-auto my-12 bg-base-100/90 backdrop-blur-sm border border-base-300 rounded-lg p-8 shadow-sm text-center">
        <div className="w-12 h-12 bg-success/15 text-success rounded-full flex items-center justify-center mx-auto mb-4">
          ✓
        </div>
        <h2 className="text-xl font-bold text-base-content mb-2">Password Reset Complete</h2>
        <p className="text-sm text-base-content/70 mb-6">
          Your password has been securely updated and all previous sessions have been revoked.
        </p>
        <Button variant="primary" onClick={onNavigateLogin} className="w-full">
          Sign In With New Password
        </Button>
      </div>
    );
  }

  return (
    <div className="glow max-w-md w-full mx-auto my-12 bg-base-100/90 backdrop-blur-sm border border-base-300 rounded-lg p-8 shadow-sm">
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-bold text-base-content tracking-tight">SandeshVani</h1>
        <h2 className="text-lg font-semibold text-base-content mt-2">Set New Password</h2>
        <p className="text-xs text-base-content/60 mt-1">
          Enter your recovery token and new password.
        </p>
      </div>

      {errorMessage && (
        <div className="mb-4">
          <Alert variant="error" title="Reset Error" message={errorMessage} />
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <FormField label="Recovery Token" required>
          <Input
            type="text"
            placeholder="Paste recovery token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            disabled={isLoading}
            required
          />
        </FormField>

        <FormField label="New Password" required helperText="Minimum 8 characters">
          <Input
            type="password"
            placeholder="••••••••••••"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            disabled={isLoading}
            required
            autoComplete="new-password"
          />
        </FormField>

        <FormField label="Confirm New Password" required>
          <Input
            type="password"
            placeholder="••••••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={isLoading}
            required
            autoComplete="new-password"
          />
        </FormField>

        <Button
          type="submit"
          variant="primary"
          isLoading={isLoading}
          className="w-full mt-2"
        >
          Reset Password
        </Button>
      </form>

      <div className="mt-6 pt-6 border-t border-base-300 text-center">
        <button
          type="button"
          onClick={onNavigateLogin}
          className="text-xs text-primary font-medium hover:underline"
        >
          ← Return to Sign In
        </button>
      </div>
    </div>
  );
};

export default ResetPassword;



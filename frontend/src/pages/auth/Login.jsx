import { useState } from "react";
import { useAuth } from "../../context";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import FormField from "../../components/ui/FormField";
import Alert from "../../components/ui/Alert";

const Login = ({ onNavigateRegister, onNavigateForgot, onNavigateVerify, onSuccess }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isUnverified, setIsUnverified] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage("");
    setIsUnverified(false);

    if (!email || !password) {
      setErrorMessage("Please enter both email and password.");
      return;
    }

    setIsLoading(true);
    try {
      await login(email, password);
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      const msg = err.message || "Sign in failed.";
      setErrorMessage(msg);
      if (msg.toLowerCase().includes("not verified")) {
        setIsUnverified(true);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glow max-w-md w-full mx-auto my-12 bg-base-100/90 backdrop-blur-sm border border-base-300 rounded-lg p-8 shadow-sm">
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-bold text-base-content tracking-tight">SandeshVani</h1>
        <p className="text-xs text-base-content/60 font-medium mt-1">
          Har zaroori baat, har zaroori insaan tak.
        </p>
        <h2 className="text-lg font-semibold text-base-content mt-4">Institutional Sign In</h2>
      </div>

      {errorMessage && (
        <div className="mb-4">
          <Alert
            variant={isUnverified ? "warning" : "error"}
            title={isUnverified ? "Verification Pending" : "Authentication Error"}
          >
            {errorMessage}
          </Alert>
          {isUnverified && onNavigateVerify && (
            <button
              type="button"
              onClick={() => onNavigateVerify(email)}
              className="mt-2 text-xs font-semibold text-primary underline"
            >
              Verify your email now →
            </button>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <FormField label="Institutional Email" required>
          <Input
            type="email"
            placeholder="officer@department.gov.in"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
            required
            autoComplete="email"
          />
        </FormField>

        <FormField label="Password" required>
          <Input
            type="password"
            placeholder="••••••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            required
            autoComplete="current-password"
          />
        </FormField>

        <div className="flex items-center justify-between text-xs">
          <button
            type="button"
            onClick={onNavigateForgot}
            className="text-primary hover:underline font-medium"
          >
            Forgot password?
          </button>
        </div>

        <Button
          type="submit"
          variant="primary"
          isLoading={isLoading}
          className="w-full mt-2"
        >
          Sign In
        </Button>
      </form>

      <div className="mt-6 pt-6 border-t border-base-300 text-center text-xs text-base-content/70">
        New to SandeshVani?{" "}
        <button
          type="button"
          onClick={onNavigateRegister}
          className="text-primary font-semibold hover:underline"
        >
          Create an account
        </button>
      </div>
    </div>
  );
};

export default Login;



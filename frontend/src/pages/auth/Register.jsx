import { useState } from "react";
import { useAuth } from "../../context";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import FormField from "../../components/ui/FormField";
import Alert from "../../components/ui/Alert";

const Register = ({ onNavigateLogin, onNavigateVerify }) => {
  const { register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successData, setSuccessData] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage("");

    if (!fullName || !email || !password || !confirmPassword) {
      setErrorMessage("Please complete all required fields.");
      return;
    }

    if (password.length < 8) {
      setErrorMessage("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      const data = await register(email, password, fullName);
      setSuccessData(data);
    } catch (err) {
      setErrorMessage(err.message || "Registration failed.");
    } finally {
      setIsLoading(false);
    }
  };

  if (successData) {
    return (
      <div className="glow max-w-md w-full mx-auto my-12 bg-base-100/90 backdrop-blur-sm border border-base-300 rounded-lg p-8 shadow-sm text-center">
        <div className="w-12 h-12 bg-success/15 text-success rounded-full flex items-center justify-center mx-auto mb-4">
          ✓
        </div>
        <h2 className="text-xl font-bold text-base-content mb-2">Registration Successful</h2>
        <p className="text-sm text-base-content/70 mb-6">
          Your account for <strong className="text-base-content">{email}</strong> has been created.
          Please verify your email address to activate institutional access.
        </p>

        <div className="space-y-3">
          <Button
            variant="primary"
            onClick={() => onNavigateVerify(email)}
            className="w-full"
          >
            Verify Email Now
          </Button>
          <Button variant="ghost" onClick={onNavigateLogin} className="w-full">
            Back to Sign In
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="glow max-w-md w-full mx-auto my-12 bg-base-100/90 backdrop-blur-sm border border-base-300 rounded-lg p-8 shadow-sm">
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-bold text-base-content tracking-tight">SandeshVani</h1>
        <p className="text-xs text-base-content/60 font-medium mt-1">
          Har zaroori baat, har zaroori insaan tak.
        </p>
        <h2 className="text-lg font-semibold text-base-content mt-4">Create Account</h2>
      </div>

      {errorMessage && (
        <div className="mb-4">
          <Alert variant="error" title="Registration Error" message={errorMessage} />
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <FormField label="Full Name" required>
          <Input
            type="text"
            placeholder="Shri Rajesh Verma"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            disabled={isLoading}
            required
            autoComplete="name"
          />
        </FormField>

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

        <FormField label="Password" required helperText="Minimum 8 characters">
          <Input
            type="password"
            placeholder="••••••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            required
            autoComplete="new-password"
          />
        </FormField>

        <FormField label="Confirm Password" required>
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
          Create Account
        </Button>
      </form>

      <div className="mt-6 pt-6 border-t border-base-300 text-center text-xs text-base-content/70">
        Already have an account?{" "}
        <button
          type="button"
          onClick={onNavigateLogin}
          className="text-primary font-semibold hover:underline"
        >
          Sign in
        </button>
      </div>
    </div>
  );
};

export default Register;



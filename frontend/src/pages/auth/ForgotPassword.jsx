import { useState } from "react";
import { useAuth } from "../../context";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import FormField from "../../components/ui/FormField";

const ForgotPassword = ({ onNavigateLogin }) => {
  const { requestPasswordReset } = useAuth();
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    try {
      await requestPasswordReset(email);
      setIsSubmitted(true);
    } finally {
      setIsLoading(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="glow max-w-md w-full mx-auto my-12 bg-base-100/90 backdrop-blur-sm border border-base-300 rounded-lg p-8 shadow-sm text-center">
        <h2 className="text-xl font-bold text-base-content mb-2">Password Recovery Dispatched</h2>
        <p className="text-sm text-base-content/70 mb-6">
          If an account exists for <strong className="text-base-content">{email}</strong>, recovery instructions are available.
        </p>

        <div className="space-y-3">
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
        <h2 className="text-lg font-semibold text-base-content mt-2">Recover Password</h2>
        <p className="text-xs text-base-content/60 mt-1">
          Enter your registered institutional email address.
        </p>
      </div>

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

        <Button
          type="submit"
          variant="primary"
          isLoading={isLoading}
          className="w-full mt-2"
        >
          Send Recovery Link
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

export default ForgotPassword;



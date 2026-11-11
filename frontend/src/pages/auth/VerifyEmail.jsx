import { useState } from "react";
import { useAuth } from "../../context";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import FormField from "../../components/ui/FormField";
import Alert from "../../components/ui/Alert";

const VerifyEmail = ({ initialEmail = "", initialToken = "", onNavigateLogin }) => {
  const { verifyEmail, resendVerification } = useAuth();
  const [token, setToken] = useState(initialToken);
  const [email, setEmail] = useState(initialEmail);
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [infoMessage, setInfoMessage] = useState("");
  const [isVerified, setIsVerified] = useState(false);

  const handleVerify = async (e) => {
    e.preventDefault();
    setErrorMessage("");
    setInfoMessage("");

    if (!token.trim()) {
      setErrorMessage("Please enter your verification token.");
      return;
    }

    setIsLoading(true);
    try {
      await verifyEmail(token.trim());
      setIsVerified(true);
    } catch (err) {
      setErrorMessage(err.message || "Email verification failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (!email) {
      setErrorMessage("Please specify your email address to request a new token.");
      return;
    }
    setIsResending(true);
    setErrorMessage("");
    try {
      await resendVerification(email);
      setInfoMessage("If the account exists, verification instructions are available.");
    } catch (err) {
      setErrorMessage(err.message || "Failed to resend verification.");
    } finally {
      setIsResending(false);
    }
  };

  if (isVerified) {
    return (
      <div className="max-w-md w-full mx-auto my-12 bg-white border border-slate-200 rounded-lg p-8 shadow-sm text-center">
        <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
          ✓
        </div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">Email Verified Successfully</h2>
        <p className="text-sm text-slate-600 mb-6">
          Your account has been activated. You may now sign in to SandeshVani.
        </p>
        <Button variant="primary" onClick={onNavigateLogin} className="w-full">
          Sign In
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-md w-full mx-auto my-12 bg-white border border-slate-200 rounded-lg p-8 shadow-sm">
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">SandeshVani</h1>
        <h2 className="text-lg font-semibold text-slate-800 mt-2">Verify Email Address</h2>
        <p className="text-xs text-slate-500 mt-1">
          Enter the verification token sent to your email address.
        </p>
      </div>

      {errorMessage && (
        <div className="mb-4">
          <Alert variant="error" title="Verification Failed" message={errorMessage} />
        </div>
      )}

      {infoMessage && (
        <div className="mb-4">
          <Alert variant="info" title="Verification Dispatched" message={infoMessage} />
        </div>
      )}

      <form onSubmit={handleVerify} className="space-y-4" noValidate>
        <FormField label="Verification Token" required helperText="Enter the opaque token from your email">
          <Input
            type="text"
            placeholder="Paste verification token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            disabled={isLoading}
            required
          />
        </FormField>

        <Button
          type="submit"
          variant="primary"
          isLoading={isLoading}
          className="w-full mt-2"
        >
          Verify Email
        </Button>
      </form>

      <div className="mt-6 pt-6 border-t border-slate-100 space-y-4">
        <div className="text-xs text-slate-600">
          <p className="mb-2 font-medium">Didn't receive the token?</p>
          <div className="flex gap-2">
            <Input
              type="email"
              placeholder="Your email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="text-xs"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={handleResend}
              isLoading={isResending}
            >
              Resend
            </Button>
          </div>
        </div>

        <div className="text-center pt-2">
          <button
            type="button"
            onClick={onNavigateLogin}
            className="text-xs text-primary font-medium hover:underline"
          >
            ← Return to Sign In
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerifyEmail;


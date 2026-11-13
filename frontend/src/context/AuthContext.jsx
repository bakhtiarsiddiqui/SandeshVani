import { useState, useEffect, useCallback } from "react";
import apiClient, {
  setAccessToken,
  setCsrfToken,
  setActiveOrgId,
  clearAccessToken,
  registerAuthFailureCallback,
} from "../api/client";
import AuthContext from "./authContextDefinition";

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [activeOrg, setActiveOrg] = useState(null);
  const [organizations, setOrganizations] = useState([]);
  const [roles, setRoles] = useState([]);
  const [platformRoles, setPlatformRoles] = useState([]);
  const [platformPermissions, setPlatformPermissions] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const clearAuthState = useCallback(() => {
    setUser(null);
    setActiveOrg(null);
    setOrganizations([]);
    setRoles([]);
    setPlatformRoles([]);
    setPlatformPermissions([]);
    setPermissions([]);
    clearAccessToken();
    setActiveOrgId(null);
  }, []);

  const applyAuthSnapshot = useCallback((data) => {
    setUser(data.user || null);
    setActiveOrg(data.active_organization || null);
    if (data.active_organization?.id) setActiveOrgId(data.active_organization.id);
    setOrganizations(data.organizations || []);
    setRoles(data.roles || []);
    setPlatformRoles(data.platform_roles || []);
    setPlatformPermissions(data.platform_permissions || []);
    setPermissions(data.permissions || []);
    setError(null);
    return data;
  }, []);

  // Organization-scoped authorization and global platform assignments are
  // retrieved separately. A tenant role never implies platform authority.
  const fetchMe = useCallback(async () => {
    try {
      const [meResponse, platformResponse] = await Promise.all([
        apiClient.get("/auth/me"),
        apiClient.get("/platform/me"),
      ]);
      return applyAuthSnapshot({ ...meResponse.data, ...platformResponse.data });
    } catch (err) {
      clearAuthState();
      throw err;
    }
  }, [applyAuthSnapshot, clearAuthState]);

  useEffect(() => {
    let isMounted = true;
    registerAuthFailureCallback(() => clearAuthState());
    const initAuth = async () => {
      try {
        const refreshRes = await apiClient.post("/auth/refresh");
        if (refreshRes.data?.access_token) {
          setAccessToken(refreshRes.data.access_token);
          if (refreshRes.data.csrf_token) setCsrfToken(refreshRes.data.csrf_token);
          await fetchMe();
        }
      } catch {
        if (isMounted) clearAuthState();
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };
    initAuth();
    return () => { isMounted = false; };
  }, [fetchMe, clearAuthState]);

  const login = async (email, password) => {
    setError(null);
    try {
      const response = await apiClient.post("/auth/login", { email, password });
      setAccessToken(response.data.access_token);
      setCsrfToken(response.data.csrf_token);
      await fetchMe();
      return response.data;
    } catch (err) {
      const message = err.response?.data?.detail || "Authentication failed. Please check credentials.";
      setError(message);
      throw new Error(message, { cause: err });
    }
  };

  const register = async (email, password, fullName) => {
    setError(null);
    try {
      const response = await apiClient.post("/auth/register", {
        email, password, full_name: fullName,
      });
      return response.data;
    } catch (err) {
      const message = err.response?.data?.detail || "Registration failed. Please try again.";
      setError(message);
      throw new Error(message, { cause: err });
    }
  };

  const verifyEmail = async (token) => {
    setError(null);
    try {
      const response = await apiClient.post("/auth/verify-email", { token });
      return response.data;
    } catch (err) {
      const message = err.response?.data?.detail || "Email verification failed or token expired.";
      setError(message);
      throw new Error(message, { cause: err });
    }
  };

  const resendVerification = async (email) => {
    try {
      const response = await apiClient.post("/auth/resend-verification", { email });
      return response.data;
    } catch (err) {
      const message = err.response?.data?.detail || "Failed to resend verification.";
      throw new Error(message, { cause: err });
    }
  };

  const logout = async () => {
    try { await apiClient.post("/auth/logout"); }
    finally { clearAuthState(); }
  };

  const logoutAll = async () => {
    try { await apiClient.post("/auth/logout-all"); }
    finally { clearAuthState(); }
  };

  const selectOrg = async (organizationId) => {
    try {
      const response = await apiClient.post("/auth/select-org", { organization_id: organizationId });
      setAccessToken(response.data.access_token);
      setActiveOrgId(response.data.active_organization.id);
      await fetchMe();
      return response.data;
    } catch (err) {
      const message = err.response?.data?.detail || "Failed to switch organization context.";
      setError(message);
      throw new Error(message, { cause: err });
    }
  };

  const requestPasswordReset = async (email) => {
    try {
      const response = await apiClient.post("/auth/password-recovery", { email });
      return response.data;
    } catch (err) {
      const message = err.response?.data?.detail || "Failed to request password reset.";
      throw new Error(message, { cause: err });
    }
  };

  const confirmPasswordReset = async (token, newPassword) => {
    try {
      const response = await apiClient.post("/auth/password-reset", {
        token, new_password: newPassword,
      });
      return response.data;
    } catch (err) {
      const message = err.response?.data?.detail || "Failed to reset password.";
      throw new Error(message, { cause: err });
    }
  };

  const value = {
    user, activeOrg, organizations, roles, platformRoles, platformPermissions, permissions,
    isAuthenticated: Boolean(user), isLoading, error,
    login, register, verifyEmail, resendVerification, logout, logoutAll,
    selectOrg, requestPasswordReset, confirmPasswordReset, fetchMe,
    hasPermission: (permission) => permissions.includes(permission),
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;

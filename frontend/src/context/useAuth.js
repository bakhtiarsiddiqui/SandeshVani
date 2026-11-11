import { useContext } from "react";
import AuthContext from "./authContextDefinition";

/**
 * Hook for consuming the authentication context.
 * Must be used within an AuthProvider.
 */
const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export default useAuth;


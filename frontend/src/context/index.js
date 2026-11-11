// Barrel export — import AuthProvider and useAuth from this single entry point.
// Separating useAuth into its own file satisfies the react-refresh/only-export-components
// rule (AuthContext.jsx exports only components; hooks live in useAuth.js).
export { AuthProvider } from "./AuthContext";
export { default as useAuth } from "./useAuth";


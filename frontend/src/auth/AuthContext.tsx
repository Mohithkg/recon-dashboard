/**
 * Authentication context.
 *
 * JWT storage: the token is held in component state (in memory).  It is
 * NEVER written to localStorage, sessionStorage, or a JS-readable cookie.
 *
 * Tradeoffs:
 *   + Immune to XSS token theft via localStorage/sessionStorage.
 *   + Immune to XSS token theft via document.cookie (we don't use cookies).
 *   - Token is lost on full page reload → user must log in again.
 *   - Token does not persist across tabs (each tab is a fresh session).
 *
 * For an internal recon dashboard used in focused sessions this is an
 * acceptable tradeoff.  If persistence is needed later, the upgrade path
 * is an httpOnly + SameSite=Strict cookie set by the backend, which keeps
 * the token out of JavaScript entirely.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { api, setAuthToken } from "../api/client";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const storeToken = useCallback((newToken: string) => {
    setToken(newToken);
    setAuthToken(newToken);
  }, []);

  const clearToken = useCallback(() => {
    setToken(null);
    setAuthToken(null);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.post<{ access_token: string }>("/auth/login", {
          email,
          password,
        });
        storeToken(res.access_token);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Login failed");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [storeToken],
  );

  const signup = useCallback(
    async (email: string, password: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.post<{ access_token: string }>("/auth/signup", {
          email,
          password,
        });
        storeToken(res.access_token);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Signup failed");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [storeToken],
  );

  const logout = useCallback(() => {
    clearToken();
  }, [clearToken]);

  const clearError = useCallback(() => setError(null), []);

  const value: AuthContextValue = {
    token,
    isAuthenticated: token !== null,
    loading,
    error,
    login,
    signup,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

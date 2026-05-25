import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authAPI, type UserProfile } from "@/services/api";

type AuthState = {
  user: UserProfile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<UserProfile>;
  logout: () => Promise<void>;
  register: (
    email: string,
    password: string,
    fullName?: string,
  ) => Promise<UserProfile>;
  refreshSession: () => Promise<string | null>;
  isAuthenticated: boolean;
  role: string | null;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (token) {
      try {
        await authAPI.logout();
      } catch {
        /* best-effort */
      }
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  }, []);

  const bootstrap = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const payload = JSON.parse(atob(token.split(".")[1])) as { exp?: number };
      const expMs = (payload.exp ?? 0) * 1000;
      if (expMs <= Date.now()) {
        const rt = localStorage.getItem("refresh_token");
        if (rt) {
          const res = await authAPI.refresh(rt);
          localStorage.setItem("access_token", res.data.access_token);
          if (res.data.refresh_token) {
            localStorage.setItem("refresh_token", res.data.refresh_token);
          }
        } else {
          await logout();
          setLoading(false);
          return;
        }
      }
      const me = await authAPI.me();
      setUser(me.data as UserProfile);
    } catch {
      await logout();
    } finally {
      setLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authAPI.login(email, password);
    const d = res.data as Record<string, string>;
    const { access_token, refresh_token, ...rest } = d;
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    const profile: UserProfile = {
      user_id: Number(rest.user_id),
      email: String(rest.email),
      full_name: rest.full_name ? String(rest.full_name) : null,
      role: String(rest.role),
    };
    setUser(profile);
    return profile;
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const res = await authAPI.register(email, password, fullName);
      const d = res.data as Record<string, string>;
      const { access_token, refresh_token, ...rest } = d;
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);
      const profile: UserProfile = {
        user_id: Number(rest.user_id),
        email: String(rest.email),
        full_name: rest.full_name ? String(rest.full_name) : null,
        role: String(rest.role),
      };
      setUser(profile);
      return profile;
    },
    [],
  );

  const refreshSession = useCallback(async () => {
    const rt = localStorage.getItem("refresh_token");
    if (!rt) return null;
    try {
      const res = await authAPI.refresh(rt);
      localStorage.setItem("access_token", res.data.access_token);
      if (res.data.refresh_token) {
        localStorage.setItem("refresh_token", res.data.refresh_token);
      }
      return res.data.access_token;
    } catch {
      await logout();
      return null;
    }
  }, [logout]);

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      register,
      refreshSession,
      isAuthenticated: !!user,
      role: user?.role ?? null,
    }),
    [user, loading, login, logout, register, refreshSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

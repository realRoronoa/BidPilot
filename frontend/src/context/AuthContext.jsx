import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import { api, formatApiError } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anon, obj = user

  const refresh = useCallback(async () => {
    try {
      const me = await api.get("/auth/me");
      setUser(me);
      return me;
    } catch {
      setUser(false);
      return false;
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const login = async (email, password) => {
    try {
      const u = await api.post("/auth/login", { email, password });
      setUser(u);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatApiError(e.response?.data?.detail) || e.message };
    }
  };

  const demoLogin = async () => {
    try {
      const u = await api.post("/auth/demo-login", {});
      setUser(u);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatApiError(e.response?.data?.detail) || e.message };
    }
  };

  const signup = async (payload) => {
    try {
      const u = await api.post("/auth/signup", payload);
      setUser(u);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatApiError(e.response?.data?.detail) || e.message };
    }
  };

  const logout = async () => {
    try { await api.post("/auth/logout", {}); } catch (error) { console.error("Logout request failed:", error); }
    setUser(false);
  };

  const value = useMemo(
    () => ({ user, setUser, login, demoLogin, signup, logout, refresh }),
    [user, refresh]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

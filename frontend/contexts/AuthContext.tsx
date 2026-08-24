"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import type { AuthResponse } from "@/lib/api";
import { loadSession, saveSession, clearSession } from "@/lib/auth";

type AuthContextValue = {
  user: AuthResponse | null;
  /** true so durante a leitura inicial do localStorage, no primeiro
   * render — evita que paginas protegidas decidam "nao tem sessao" antes
   * da checagem terminar. */
  isLoading: boolean;
  login: (auth: AuthResponse) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setUser(loadSession());
    setIsLoading(false);
  }, []);

  function login(auth: AuthResponse) {
    saveSession(auth);
    setUser(auth);
  }

  function logout() {
    clearSession();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth precisa ser usado dentro de <AuthProvider>");
  }
  return ctx;
}

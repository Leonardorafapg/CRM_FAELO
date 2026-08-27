"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import type { AuthResponse } from "@/lib/api";
import { loadSession, saveSession, clearSession } from "@/lib/auth";
import { prefetchSessoes } from "@/lib/sessoesCache";

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

  // Dispara a busca das conversas assim que a sessao esta disponivel — no
  // login e tambem na reidratacao do localStorage (refresh de pagina) —
  // pra ja estar pronta (ou em voo) quando o usuario chega em
  // /dashboard/atendimentos, em vez de so comecar a buscar nesse momento.
  // Ver lib/sessoesCache.ts.
  useEffect(() => {
    if (user) prefetchSessoes(user.tenant_id, user.access_token);
  }, [user]);

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

/** Mesma regra usada pelo backend (shared/policy.py::require_admin e
 * require_role): platform admin (is_admin) sempre passa, independente do
 * role dentro do tenant; senao, precisa ser owner ou admin. Centralizado
 * aqui pra nao reimplementar essa checagem em cada tela/hook restrito. */
export function isAdminOrOwner(user: AuthResponse | null): boolean {
  if (!user) return false;
  return user.is_admin || user.role === "owner" || user.role === "admin";
}

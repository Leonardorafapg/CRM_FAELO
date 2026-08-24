import type { AuthResponse } from "./api";

// Guarda a sessao inteira (nao so o token) — o AuthContext precisa dos
// outros campos (name, role, tenant_id) pra expor o usuario logado sem
// decodificar o JWT no frontend.
const SESSION_KEY = "faelo_session";

export function saveSession(auth: AuthResponse) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(auth));
}

export function loadSession(): AuthResponse | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthResponse;
  } catch {
    // Sessao salva corrompida (formato antigo, JSON invalido) — trata como
    // deslogado em vez de quebrar a aplicacao.
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

export function getToken(): string | null {
  return loadSession()?.access_token ?? null;
}

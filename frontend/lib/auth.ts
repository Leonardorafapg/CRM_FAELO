import type { AuthResponse } from "./api";

// Guarda so o essencial da sessao no localStorage — sem lib de state
// management, o escopo atual (login/register) nao precisa disso ainda.
const TOKEN_KEY = "faelo_token";

export function saveSession(auth: AuthResponse) {
  localStorage.setItem(TOKEN_KEY, auth.access_token);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

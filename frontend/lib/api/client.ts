// Base do cliente HTTP do frontend — fala SO com o gateway, nunca com um
// servico interno direto (mesma regra que vale pro proprio backend).
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {}

/** Rotas publicas (login/registro) — sempre POST, sem token. */
export async function request<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    // FastAPI devolve o erro em {"detail": "..."} — usa isso como mensagem
    // quando existe, senao cai num texto generico.
    throw new ApiError(data.detail || "Erro inesperado. Tente novamente.");
  }

  return data as T;
}

/** Rotas autenticadas (crm-service e demais): manda o token no header e
 * aceita qualquer verbo HTTP, nao so POST. Corpo e opcional (GET/DELETE
 * geralmente nao mandam body). */
export async function authRequest<T>(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  token: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new ApiError(data.detail || "Erro inesperado. Tente novamente.");
  }

  return data as T;
}

// Cliente HTTP do frontend — fala SO com o gateway, nunca com um servico
// interno direto (mesma regra que vale pro proprio backend).
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {}

async function request<T>(path: string, body: unknown): Promise<T> {
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

// Mesmo formato de resposta do platform-service (_build_token em
// app/auth/routes.py): token + os dados minimos pra identificar a sessao.
export type AuthResponse = {
  access_token: string;
  token_type: string;
  tenant_id: string;
  name: string;
  role: string;
  is_admin: boolean;
};

export function login(email: string, password: string) {
  return request<AuthResponse>("/auth/login", { email, password });
}

export function register(params: {
  name: string;
  business_name: string;
  email: string;
  password: string;
}) {
  return request<AuthResponse>("/auth/register", params);
}

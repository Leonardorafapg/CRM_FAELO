import { request } from "./client";

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

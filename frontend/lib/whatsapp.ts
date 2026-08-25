// Cliente HTTP do frontend para o whatsapp-service (via gateway), autenticado
// com o token JWT da sessao atual. api.ts hoje so cobre chamadas sem token ou
// via authRequest interno; aqui replicamos o mesmo padrao de authRequest de
// forma exportada, ja que este arquivo nao tem acesso ao AuthContext (o
// token precisa ser passado por quem chama, igual as funcoes de pipelines/
// contacts em lib/api.ts).
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {}

async function authRequest<T>(
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

export type Connection = {
  id: string;
  instance_name: string;
  phone: string | null;
  status: "connecting" | "connected" | "disconnected";
  created_at: string | null;
};

export type ConnectionCreateResponse = {
  connection: Connection;
  qrcode_base64: string | null;
};

export type Sessao = {
  id: string;
  connection_id: string;
  phone: string;
  contact_name: string | null;
  is_open: boolean;
  last_activity: string | null;
  // Nao persistida no banco — buscada ao vivo na Evolution API pelo
  // whatsapp-service a cada listagem (com cache em memoria de 6h la).
  // Mesmo padrao dos projetos de referencia: usar direto num <img>, sem
  // proxy nem <Image> do Next (URL externa arbitraria, sem loader
  // configurado), com fallback de iniciais quando null.
  foto_url: string | null;
};

export type Mensagem = {
  id: string;
  session_id: string;
  role: "user" | "attendant";
  content: string;
  created_at: string | null;
};

// --- Conexoes ---------------------------------------------------------------

export const listConnections = (token: string) =>
  authRequest<Connection[]>("GET", "/connections", token);

export const createConnection = (token: string) =>
  authRequest<ConnectionCreateResponse>("POST", "/connections", token);

export const deleteConnection = (token: string, id: string) =>
  authRequest<{ ok: true }>("DELETE", `/connections/${id}`, token);

// --- Atendimentos ------------------------------------------------------------

export const listSessoes = (token: string, limit = 50, offset = 0) =>
  authRequest<Sessao[]>("GET", `/sessoes?limit=${limit}&offset=${offset}`, token);

export const getMensagens = (token: string, sessionId: string, limit = 50, offset = 0) =>
  authRequest<Mensagem[]>(
    "GET",
    `/chat/${sessionId}/mensagens?limit=${limit}&offset=${offset}`,
    token
  );

export const responder = (token: string, sessionId: string, content: string) =>
  authRequest<Mensagem>("POST", `/chat/${sessionId}/responder`, token, { content });

export const encerrarAtendimento = (token: string, sessionId: string) =>
  authRequest<Sessao>("PATCH", `/chat/${sessionId}/encerrar`, token);

// --- WebSocket -----------------------------------------------------------
// WS nao passa pelo gateway (proxy do gateway e HTTP puro) — conecta direto
// no whatsapp-service. Ver services/gateway/main.py e
// docs/features/WHATSAPP_SERVICE.md.
export function whatsappWsUrl(tenantId: string, token: string): string {
  const base =
    process.env.NEXT_PUBLIC_WHATSAPP_WS_URL ||
    API_URL.replace(/^http/, "ws").replace(/:8000$/, ":8003");
  return `${base}/ws/${tenantId}?token=${encodeURIComponent(token)}`;
}

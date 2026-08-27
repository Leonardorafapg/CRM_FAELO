// Tipos e chamadas do crm-service — espelham exatamente os schemas/rotas de
// services/crm-service/app (contacts, stages). Toda funcao recebe o token
// como primeiro argumento (este arquivo nao tem acesso ao AuthContext).
// Sem conceito de Pipeline/multi-quadro (removido) — quadro e unico e fixo
// por tenant, so as Stages (colunas) sao configuraveis.
import { authRequest } from "./client";

export type ContactStatus = {
  id: string;
  name: string;
  active: boolean;
  order: number;
};

export type Contact = {
  id: string;
  name: string;
  phone: string;
  email: string | null;
  source: string | null;
  tags: string[];
  status_id: string | null;
  assigned_to: string | null;
  stage_id: string | null;
  created_at: string;
};

export type Stage = {
  id: string;
  name: string;
  order: number;
  color: string | null;
  active: boolean;
  is_entry: boolean;
};

// Stages — recurso direto do tenant (quadro unico e fixo, sem multi-pipeline).
export const listStages = (token: string) =>
  authRequest<Stage[]>("GET", "/stages", token);

export const createStage = (
  token: string,
  body: { name: string; color?: string; is_entry?: boolean }
) => authRequest<Stage>("POST", "/stages", token, body);

export const updateStage = (
  token: string,
  id: string,
  body: Partial<Pick<Stage, "name" | "order" | "color" | "active" | "is_entry">>
) => authRequest<Stage>("PATCH", `/stages/${id}`, token, body);

export const deleteStage = (token: string, id: string) =>
  authRequest<{ ok: true }>("DELETE", `/stages/${id}`, token);

// Contact statuses
export const listContactStatuses = (token: string) =>
  authRequest<ContactStatus[]>("GET", "/contact-statuses", token);

export const createContactStatus = (token: string, body: { name: string }) =>
  authRequest<ContactStatus>("POST", "/contact-statuses", token, body);

// Contacts
export const listContacts = (token: string, stageId?: string) =>
  authRequest<Contact[]>(
    "GET",
    stageId ? `/contacts?stage_id=${stageId}` : "/contacts",
    token
  );

export const createContact = (
  token: string,
  body: {
    name: string;
    phone: string;
    email?: string;
    source?: string;
    tags?: string[];
    status_id?: string;
    stage_id?: string;
  }
) => authRequest<Contact>("POST", "/contacts", token, body);

export const updateContact = (
  token: string,
  id: string,
  body: Partial<
    Pick<Contact, "name" | "phone" | "email" | "source" | "tags" | "status_id" | "assigned_to" | "stage_id">
  >
) => authRequest<Contact>("PATCH", `/contacts/${id}`, token, body);

export const deleteContact = (token: string, id: string) =>
  authRequest<{ ok: true }>("DELETE", `/contacts/${id}`, token);

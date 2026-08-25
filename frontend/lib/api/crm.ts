// Tipos e chamadas do crm-service — espelham exatamente os schemas/rotas de
// services/crm-service/app (contacts, pipeline). Toda funcao recebe o token
// como primeiro argumento (este arquivo nao tem acesso ao AuthContext).
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

export type Pipeline = {
  id: string;
  name: string;
  description: string | null;
  active: boolean;
  is_default: boolean;
};

export type Stage = {
  id: string;
  pipeline_id: string;
  name: string;
  order: number;
  color: string | null;
  active: boolean;
  is_entry: boolean;
};

// Pipelines
export const listPipelines = (token: string) =>
  authRequest<Pipeline[]>("GET", "/pipelines", token);

export const createPipeline = (
  token: string,
  body: { name: string; description?: string; is_default?: boolean }
) => authRequest<Pipeline>("POST", "/pipelines", token, body);

export const updatePipeline = (
  token: string,
  id: string,
  body: Partial<Pick<Pipeline, "name" | "description" | "active" | "is_default">>
) => authRequest<Pipeline>("PATCH", `/pipelines/${id}`, token, body);

export const deletePipeline = (token: string, id: string) =>
  authRequest<{ ok: true }>("DELETE", `/pipelines/${id}`, token);

// Stages (aninhado em /pipelines/{id}/stages pra list/create, direto em
// /stages/{id} pra patch/delete — mesmo padrao do backend)
export const listStages = (token: string, pipelineId: string) =>
  authRequest<Stage[]>("GET", `/pipelines/${pipelineId}/stages`, token);

export const createStage = (
  token: string,
  pipelineId: string,
  body: { name: string; color?: string; is_entry?: boolean }
) => authRequest<Stage>("POST", `/pipelines/${pipelineId}/stages`, token, body);

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

// Tipos e chamadas do platform-service pra dado de tenant (perfil do
// negocio + horario de atendimento) — espelha app/tenant/{models,schemas,
// service}.py de services/platform-service. Nada disso mora no ai-service:
// Tenant e identidade/multi-tenant, responsabilidade do platform-service.
import { authRequest } from "./client";

export type Tenant = {
  id: string;
  business_name: string;
  phone: string | null;
  email: string | null;
  city: string | null;
  state: string | null;
  address: string | null;
  whatsapp: string | null;
  instagram: string | null;
  facebook: string | null;
  website: string | null;
  system_prompt: string | null;
  fallback_message: string | null;
  ai_provider: string;
  groq_key: boolean; // GET so devolve se existe, nunca o valor real
  is_active: boolean;
};

export type TenantUpdateBody = Partial<
  Pick<
    Tenant,
    | "business_name"
    | "phone"
    | "email"
    | "city"
    | "state"
    | "address"
    | "whatsapp"
    | "instagram"
    | "facebook"
    | "website"
  >
>;

export const getTenant = (token: string, tenantId: string) =>
  authRequest<Tenant>("GET", `/tenants/${tenantId}`, token);

export const updateTenant = (token: string, tenantId: string, body: TenantUpdateBody) =>
  authRequest<{ message: string }>("PATCH", `/tenants/${tenantId}`, token, body);

// Horario de atendimento — 1 registro por dia da semana (0=Segunda .. 6=Domingo).
export type BusinessHourSlot = { from: string; to: string };

export type BusinessHourDay = {
  day_of_week: number;
  slots: BusinessHourSlot[];
  is_closed: boolean;
};

export const getBusinessHours = (token: string, tenantId: string) =>
  authRequest<BusinessHourDay[]>("GET", `/tenants/${tenantId}/business-hours`, token);

export const updateBusinessHours = (token: string, tenantId: string, hours: BusinessHourDay[]) =>
  authRequest<{ message: string }>("PUT", `/tenants/${tenantId}/business-hours`, token, { hours });

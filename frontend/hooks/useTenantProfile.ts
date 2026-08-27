import { useEffect, useState } from "react";
import { isAdminOrOwner, useAuth } from "@/contexts/AuthContext";
import { ApiError, TenantUpdateBody, getTenant, updateTenant } from "@/lib/api";

/** Perfil do negocio (dados do Tenant no platform-service) — nome, contato,
 * endereco. Alimenta a identidade do assistente de IA em toda conversa,
 * independente de qual funcionalidade (FAQ, agendamento, etc.) esta ativa. */
export function useTenantProfile() {
  const { user } = useAuth();
  const token = user?.access_token ?? "";
  const tenantId = user?.tenant_id ?? "";
  const isAdmin = isAdminOrOwner(user);

  const [form, setForm] = useState<TenantUpdateBody>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !tenantId) return;
    setLoading(true);
    getTenant(token, tenantId)
      .then((t) => {
        setForm({
          business_name: t.business_name ?? "",
          phone: t.phone ?? "",
          email: t.email ?? "",
          city: t.city ?? "",
          state: t.state ?? "",
          address: t.address ?? "",
          whatsapp: t.whatsapp ?? "",
          instagram: t.instagram ?? "",
        });
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erro ao carregar dados da empresa."))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, tenantId]);

  function setField<K extends keyof TenantUpdateBody>(field: K, value: TenantUpdateBody[K]) {
    setSaved(false);
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await updateTenant(token, tenantId, form);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao salvar dados da empresa.");
    } finally {
      setSaving(false);
    }
  }

  return { form, setField, loading, saving, saved, error, isAdmin, handleSave };
}

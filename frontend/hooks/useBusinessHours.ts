import { useEffect, useState } from "react";
import { isAdminOrOwner, useAuth } from "@/contexts/AuthContext";
import { ApiError, BusinessHourDay, getBusinessHours, updateBusinessHours } from "@/lib/api";

export const DAY_LABELS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

function defaultWeek(): BusinessHourDay[] {
  return DAY_LABELS.map((_, day_of_week) => ({
    day_of_week,
    is_closed: day_of_week === 6, // domingo fechado por padrao, resto o tenant ajusta
    slots: day_of_week === 6 ? [] : [{ from: "09:00", to: "18:00" }],
  }));
}

/** Horario de atendimento por dia da semana — 1 unico intervalo por dia
 * nesta fase (o backend suporta varios intervalos/dia, mas a tela comeca
 * simples; virar multi-intervalo depois e so mudar a UI, o schema ja
 * aguenta). */
export function useBusinessHours() {
  const { user } = useAuth();
  const token = user?.access_token ?? "";
  const tenantId = user?.tenant_id ?? "";
  const isAdmin = isAdminOrOwner(user);

  const [week, setWeek] = useState<BusinessHourDay[]>(defaultWeek());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !tenantId) return;
    setLoading(true);
    getBusinessHours(token, tenantId)
      .then((days) => {
        if (days.length === 0) return; // ainda nao configurado — mantem o default
        const byDay = new Map(days.map((d) => [d.day_of_week, d]));
        setWeek(defaultWeek().map((d) => byDay.get(d.day_of_week) ?? d));
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erro ao carregar horários."))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, tenantId]);

  function toggleClosed(day: number) {
    setSaved(false);
    setWeek((prev) =>
      prev.map((d) => {
        if (d.day_of_week !== day) return d;
        const willBeClosed = !d.is_closed;
        // Reabrir um dia que nunca teve horario (ex.: domingo, fechado por
        // padrao) precisa inicializar slots aqui — senao o campo de horario
        // exibido (fallback 09:00/18:00 no value do input) diverge do que
        // de fato seria salvo (slots ainda vazio) ate o usuario tocar no
        // input manualmente.
        const slots = !willBeClosed && d.slots.length === 0 ? [{ from: "09:00", to: "18:00" }] : d.slots;
        return { ...d, is_closed: willBeClosed, slots };
      })
    );
  }

  function setSlot(day: number, field: "from" | "to", value: string) {
    setSaved(false);
    setWeek((prev) =>
      prev.map((d) => {
        if (d.day_of_week !== day) return d;
        const current = d.slots[0] ?? { from: "09:00", to: "18:00" };
        return { ...d, slots: [{ ...current, [field]: value }] };
      })
    );
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await updateBusinessHours(token, tenantId, week);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao salvar horários.");
    } finally {
      setSaving(false);
    }
  }

  return { week, loading, saving, saved, error, isAdmin, toggleClosed, setSlot, handleSave };
}

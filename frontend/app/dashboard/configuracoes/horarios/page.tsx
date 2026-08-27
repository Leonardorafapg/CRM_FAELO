"use client";

import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useBusinessHours, DAY_LABELS } from "@/hooks/useBusinessHours";
import { BackLink } from "@/components/ui/BackLink";
import { ErrorMessage } from "@/components/ui/ErrorMessage";

export default function HorariosPage() {
  const ready = useRequireAuth();
  const { week, loading, saving, saved, error, isAdmin, toggleClosed, setSlot, handleSave } = useBusinessHours();

  if (!ready) return null;

  return (
    <main className="flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-8">
      <div>
        <BackLink href="/dashboard/configuracoes">Configurações</BackLink>
        <h1 className="mt-2 font-heading text-2xl font-bold text-text-dark">Horários</h1>
        <p className="mt-1 text-sm text-text-muted">Defina o horário de atendimento por dia da semana.</p>
      </div>

      {loading ? (
        <p className="text-text-muted">Carregando...</p>
      ) : (
        <div className="flex flex-col gap-2">
          {week.map((day) => (
            <div
              key={day.day_of_week}
              className="flex flex-wrap items-center gap-3 rounded-lg border border-border-light bg-card-bg px-4 py-3"
            >
              <span className="w-24 shrink-0 text-sm font-medium text-text-dark">
                {DAY_LABELS[day.day_of_week]}
              </span>

              <label className="flex items-center gap-2 text-xs text-text-muted">
                <input
                  type="checkbox"
                  checked={day.is_closed}
                  onChange={() => toggleClosed(day.day_of_week)}
                  disabled={!isAdmin}
                />
                Fechado
              </label>

              {!day.is_closed && (
                <div className="flex items-center gap-2">
                  <input
                    type="time"
                    value={day.slots[0]?.from ?? "09:00"}
                    onChange={(e) => setSlot(day.day_of_week, "from", e.target.value)}
                    disabled={!isAdmin}
                    className="rounded-md border border-border-light bg-page-bg px-2 py-1 text-sm text-text-dark outline-none focus:border-accent-blue"
                  />
                  <span className="text-xs text-text-muted">até</span>
                  <input
                    type="time"
                    value={day.slots[0]?.to ?? "18:00"}
                    onChange={(e) => setSlot(day.day_of_week, "to", e.target.value)}
                    disabled={!isAdmin}
                    className="rounded-md border border-border-light bg-page-bg px-2 py-1 text-sm text-text-dark outline-none focus:border-accent-blue"
                  />
                </div>
              )}
            </div>
          ))}

          <ErrorMessage>{error}</ErrorMessage>

          {isAdmin ? (
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="mt-2 self-start rounded-lg bg-accent-blue px-5 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {saved ? "Salvo!" : saving ? "Salvando..." : "Salvar horários"}
            </button>
          ) : (
            <p className="text-xs text-text-muted">Apenas administradores podem editar os horários.</p>
          )}
        </div>
      )}
    </main>
  );
}

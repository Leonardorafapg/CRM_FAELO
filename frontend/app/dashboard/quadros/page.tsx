"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useKanban } from "@/hooks/useKanban";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { IconSearch } from "@/components/layout/icons";
import { KanbanBoard } from "@/components/crm/KanbanBoard";

export default function QuadrosPage() {
  const ready = useRequireAuth();
  const {
    stages,
    contacts,
    loading,
    error,
    isAdmin,
    moveContact,
    handleCreateStage,
    handleRenameStage,
    handleDeleteStage,
    handleCreateContact,
  } = useKanban();

  const [newStageName, setNewStageName] = useState("");
  const [showStageForm, setShowStageForm] = useState(false);
  const [search, setSearch] = useState("");

  const filteredContacts = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return contacts;
    return contacts.filter(
      (c) => c.name.toLowerCase().includes(query) || c.phone.toLowerCase().includes(query)
    );
  }, [contacts, search]);

  if (!ready) return null;

  async function submitStage(e: FormEvent) {
    e.preventDefault();
    if (!newStageName.trim()) return;
    await handleCreateStage(newStageName.trim());
    setNewStageName("");
    setShowStageForm(false);
  }

  return (
    <main className="flex w-full flex-1 flex-col gap-6 px-6 py-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl font-bold text-text-dark">Quadros</h1>
          <p className="mt-1 text-sm text-text-muted">Acompanhe seus clientes por etapa.</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <IconSearch
              width={16}
              height={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted/60"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar cliente..."
              className="w-56 rounded-lg border border-border-light bg-card-bg py-2 pl-9 pr-3 text-sm text-text-dark outline-none focus:border-accent-blue"
            />
          </div>

          {isAdmin && (
            <button
              type="button"
              onClick={() => setShowStageForm((v) => !v)}
              className="shrink-0 rounded-lg bg-accent-blue px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
            >
              {showStageForm ? "Cancelar" : "+ Nova coluna"}
            </button>
          )}
        </div>
      </div>

      {showStageForm && (
        <form onSubmit={submitStage} className="flex gap-2">
          <input
            autoFocus
            value={newStageName}
            onChange={(e) => setNewStageName(e.target.value)}
            placeholder="Nome da coluna"
            className="rounded-lg border border-border-light bg-card-bg px-3 py-2 text-sm text-text-dark outline-none focus:border-accent-blue"
          />
          <button type="submit" className="rounded-lg bg-accent-blue px-4 py-2 text-sm font-medium text-white">
            Criar
          </button>
        </form>
      )}

      <ErrorMessage>{error}</ErrorMessage>

      {loading ? (
        <p className="text-text-muted">Carregando...</p>
      ) : stages.length === 0 ? (
        <p className="text-text-muted">
          Nenhuma coluna ainda. {isAdmin ? "Crie uma acima para começar." : "Peça a um admin para criar uma."}
        </p>
      ) : (
        <KanbanBoard
          stages={stages}
          contacts={filteredContacts}
          onMove={moveContact}
          onRenameStage={isAdmin ? handleRenameStage : undefined}
          onDeleteStage={isAdmin ? handleDeleteStage : undefined}
          onAddContact={handleCreateContact}
        />
      )}
    </main>
  );
}

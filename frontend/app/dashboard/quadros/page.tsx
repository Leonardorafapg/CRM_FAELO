"use client";

import { FormEvent, useState } from "react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useKanban } from "@/hooks/useKanban";
import { BackLink } from "@/components/ui/BackLink";
import { Select } from "@/components/ui/Select";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { KanbanBoard } from "@/components/crm/KanbanBoard";

export default function QuadrosPage() {
  const ready = useRequireAuth();
  const {
    pipelines,
    selectedPipelineId,
    setSelectedPipelineId,
    stages,
    contacts,
    loading,
    error,
    isAdmin,
    moveContact,
    handleCreatePipeline,
    handleCreateStage,
  } = useKanban();

  const [newPipelineName, setNewPipelineName] = useState("");
  const [newStageName, setNewStageName] = useState("");
  const [showPipelineForm, setShowPipelineForm] = useState(false);
  const [showStageForm, setShowStageForm] = useState(false);

  if (!ready) return null;

  async function submitPipeline(e: FormEvent) {
    e.preventDefault();
    if (!newPipelineName.trim()) return;
    await handleCreatePipeline(newPipelineName.trim());
    setNewPipelineName("");
    setShowPipelineForm(false);
  }

  async function submitStage(e: FormEvent) {
    e.preventDefault();
    if (!newStageName.trim()) return;
    await handleCreateStage(newStageName.trim());
    setNewStageName("");
    setShowStageForm(false);
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-8">
      <div>
        <BackLink href="/dashboard">← Dashboard</BackLink>
        <h1 className="font-heading text-2xl font-bold text-text-dark">Quadros</h1>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {pipelines.length > 0 && (
          <Select value={selectedPipelineId ?? ""} onChange={(e) => setSelectedPipelineId(e.target.value)}>
            {pipelines.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
                {p.is_default ? " (padrão)" : ""}
              </option>
            ))}
          </Select>
        )}

        {isAdmin && (
          <>
            <button
              type="button"
              onClick={() => setShowPipelineForm((v) => !v)}
              className="text-sm text-accent-blue hover:underline"
            >
              + Novo quadro
            </button>
            {selectedPipelineId && (
              <button
                type="button"
                onClick={() => setShowStageForm((v) => !v)}
                className="text-sm text-accent-blue hover:underline"
              >
                + Nova coluna
              </button>
            )}
          </>
        )}
      </div>

      {showPipelineForm && (
        <form onSubmit={submitPipeline} className="flex gap-2">
          <input
            autoFocus
            value={newPipelineName}
            onChange={(e) => setNewPipelineName(e.target.value)}
            placeholder="Nome do quadro"
            className="rounded-lg border border-border-light bg-card-bg px-3 py-2 text-sm text-text-dark outline-none focus:border-accent-blue"
          />
          <button type="submit" className="rounded-lg bg-accent-blue px-4 py-2 text-sm font-medium text-white">
            Criar
          </button>
        </form>
      )}

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
      ) : pipelines.length === 0 ? (
        <p className="text-text-muted">
          Nenhum quadro ainda. {isAdmin ? "Crie um acima para começar." : "Peça a um admin para criar um."}
        </p>
      ) : (
        <KanbanBoard stages={stages} contacts={contacts} onMove={moveContact} />
      )}
    </main>
  );
}

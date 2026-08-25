import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import {
  ApiError,
  Contact,
  Pipeline,
  Stage,
  createPipeline,
  createStage,
  listContacts,
  listPipelines,
  listStages,
  updateContact,
} from "@/lib/api";

/** Quadro (pipeline) selecionado + suas colunas (stages) + os clientes de
 * cada coluna. Sem drag-and-drop nesta fase — mover é um select por card
 * (ver docs/features/CLIENTES_ESTAGIOS.md, "não introduzir biblioteca de
 * drag-and-drop nesta fase"). */
export function useKanban() {
  const { user } = useAuth();
  const token = user?.access_token ?? "";
  const isAdmin = user?.role === "owner" || user?.role === "admin";

  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState<string | null>(null);
  const [stages, setStages] = useState<Stage[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadPipelines() {
    const list = await listPipelines(token);
    setPipelines(list);
    if (list.length > 0) {
      setSelectedPipelineId((current) => current ?? list.find((p) => p.is_default)?.id ?? list[0].id);
    }
    return list;
  }

  async function loadBoard(pipelineId: string) {
    const [stageList, contactList] = await Promise.all([
      listStages(token, pipelineId),
      listContacts(token),
    ]);
    setStages(stageList);
    setContacts(contactList);
  }

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    loadPipelines()
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erro ao carregar quadros."))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!token || !selectedPipelineId) return;
    setLoading(true);
    setError(null);
    loadBoard(selectedPipelineId)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erro ao carregar quadro."))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, selectedPipelineId]);

  async function moveContact(contactId: string, stageId: string) {
    // Atualiza a UI antes da resposta do servidor (o card já muda de coluna
    // na hora) e desfaz se a chamada falhar — simples o bastante pra não
    // precisar de uma lib de estado otimista.
    const previous = contacts;
    setContacts((prev) => prev.map((c) => (c.id === contactId ? { ...c, stage_id: stageId } : c)));
    try {
      await updateContact(token, contactId, { stage_id: stageId });
    } catch (err) {
      setContacts(previous);
      setError(err instanceof ApiError ? err.message : "Erro ao mover cliente.");
    }
  }

  async function handleCreatePipeline(name: string) {
    const created = await createPipeline(token, { name });
    setPipelines((prev) => [...prev, created]);
    setSelectedPipelineId(created.id);
  }

  async function handleCreateStage(name: string) {
    if (!selectedPipelineId) return;
    const created = await createStage(token, selectedPipelineId, { name });
    setStages((prev) => [...prev, created]);
  }

  return {
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
  };
}

import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import {
  ApiError,
  Contact,
  Stage,
  createContact,
  createStage,
  deleteStage,
  listContacts,
  listStages,
  updateContact,
  updateStage,
} from "@/lib/api";

/** Quadro unico e fixo por tenant (sem multi-pipeline, ver docs/TASKS.md) —
 * so as Stages (colunas) sao configuraveis. Sem drag-and-drop nesta fase:
 * mover é um select por card (ver docs/features/CLIENTES_ESTAGIOS.md, "não
 * introduzir biblioteca de drag-and-drop nesta fase"). */
export function useKanban() {
  const { user } = useAuth();
  const token = user?.access_token ?? "";
  const isAdmin = user?.role === "owner" || user?.role === "admin";

  const [stages, setStages] = useState<Stage[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadBoard() {
    const [stageList, contactList] = await Promise.all([listStages(token), listContacts(token)]);
    setStages(stageList);
    setContacts(contactList);
  }

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    loadBoard()
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erro ao carregar quadro."))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

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

  async function handleCreateStage(name: string) {
    const created = await createStage(token, { name });
    setStages((prev) => [...prev, created]);
  }

  async function handleRenameStage(stageId: string, name: string) {
    try {
      const updated = await updateStage(token, stageId, { name });
      setStages((prev) => prev.map((s) => (s.id === stageId ? updated : s)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao renomear coluna.");
    }
  }

  async function handleDeleteStage(stageId: string) {
    if (!window.confirm("Excluir esta coluna? Os clientes nela ficam sem coluna.")) return;
    try {
      await deleteStage(token, stageId);
      setStages((prev) => prev.filter((s) => s.id !== stageId));
      // Backend desvincula com ON DELETE SET NULL — reflete o mesmo aqui
      // sem precisar recarregar a lista inteira de contacts.
      setContacts((prev) => prev.map((c) => (c.stage_id === stageId ? { ...c, stage_id: null } : c)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao excluir coluna.");
    }
  }

  async function handleCreateContact(stageId: string, name: string, phone: string) {
    try {
      const created = await createContact(token, { name, phone, stage_id: stageId });
      setContacts((prev) => [created, ...prev]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao criar cliente.");
    }
  }

  return {
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
  };
}

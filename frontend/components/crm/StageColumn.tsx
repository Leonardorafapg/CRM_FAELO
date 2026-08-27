import { FormEvent, ReactNode, useState } from "react";
import { IconPencil, IconPlus, IconTrash } from "@/components/layout/icons";

type StageColumnProps = {
  title: string;
  count: number;
  color?: string | null;
  /** Presentes só pras colunas que são Stage de verdade — a coluna fixa
   * "Sem coluna" não tem id, então não mostra editar/excluir/adicionar. */
  stageId?: string;
  onRename?: (stageId: string, name: string) => void | Promise<void>;
  onDelete?: (stageId: string) => void | Promise<void>;
  onAddContact?: (stageId: string, name: string, phone: string) => void | Promise<void>;
  children: ReactNode;
};

const FALLBACK_COLOR = "#8b8fa0";

export function StageColumn({
  title,
  count,
  color,
  stageId,
  onRename,
  onDelete,
  onAddContact,
  children,
}: StageColumnProps) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(title);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const barColor = color || FALLBACK_COLOR;

  async function saveRename() {
    setEditing(false);
    const trimmed = name.trim();
    if (!stageId || !onRename || !trimmed || trimmed === title) {
      setName(title);
      return;
    }
    await onRename(stageId, trimmed);
  }

  async function submitAddContact(e: FormEvent) {
    e.preventDefault();
    if (!stageId || !onAddContact || !newName.trim() || !newPhone.trim()) return;
    await onAddContact(stageId, newName.trim(), newPhone.trim());
    setNewName("");
    setNewPhone("");
    setShowAddForm(false);
  }

  return (
    // Barra colorida no topo (cor da Stage) + borda visivel: marca a divisao
    // entre os quadros pro usuario enxergar onde uma coluna termina e a
    // outra comeca — mesmo estilo da referencia (top border por coluna).
    <div
      className="flex w-72 shrink-0 flex-col gap-3 rounded-xl border border-border-light bg-page-bg p-3"
      style={{ borderTop: `3px solid ${barColor}` }}
    >
      <div className="flex items-center justify-between gap-2 px-1">
        <div className="min-w-0 flex-1">
          {editing ? (
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              onBlur={saveRename}
              onKeyDown={(e) => {
                if (e.key === "Enter") saveRename();
                if (e.key === "Escape") {
                  setName(title);
                  setEditing(false);
                }
              }}
              className="w-full rounded border border-accent-blue bg-card-bg px-1.5 py-0.5 text-sm text-text-dark outline-none"
            />
          ) : (
            <h2 className="truncate text-sm font-semibold text-text-dark">{title}</h2>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          <span className="rounded-full bg-card-bg px-2 py-0.5 text-xs font-medium text-text-muted">{count}</span>
          {stageId && onAddContact && (
            <button
              type="button"
              onClick={() => setShowAddForm((v) => !v)}
              title="Adicionar cliente"
              className="text-text-muted transition-colors hover:text-accent-blue"
            >
              <IconPlus width={14} height={14} />
            </button>
          )}
          {stageId && onRename && (
            <button
              type="button"
              onClick={() => setEditing(true)}
              title="Renomear coluna"
              className="text-text-muted transition-colors hover:text-accent-blue"
            >
              <IconPencil width={14} height={14} />
            </button>
          )}
          {stageId && onDelete && (
            <button
              type="button"
              onClick={() => onDelete(stageId)}
              title="Excluir coluna"
              className="text-text-muted transition-colors hover:text-red-600"
            >
              <IconTrash width={14} height={14} />
            </button>
          )}
        </div>
      </div>

      {showAddForm && (
        <form onSubmit={submitAddContact} className="flex flex-col gap-1.5 rounded-lg bg-card-bg p-2">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Nome do cliente"
            className="rounded-md border border-border-light bg-page-bg px-2 py-1 text-xs text-text-dark outline-none focus:border-accent-blue"
          />
          <input
            value={newPhone}
            onChange={(e) => setNewPhone(e.target.value)}
            placeholder="Telefone"
            className="rounded-md border border-border-light bg-page-bg px-2 py-1 text-xs text-text-dark outline-none focus:border-accent-blue"
          />
          <button
            type="submit"
            className="rounded-md bg-accent-blue py-1 text-xs font-medium text-white transition-opacity hover:opacity-90"
          >
            Adicionar
          </button>
        </form>
      )}

      <div className="flex flex-col gap-2">{children}</div>
    </div>
  );
}

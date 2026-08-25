import { Contact, Stage } from "@/lib/api";
import { Select } from "@/components/ui/Select";

// value do "select" pra representar explicitamente "sem coluna" — não é um
// id de Stage real, então não pode ser string vazia (colidiria com "nenhuma
// opção selecionada") nem um id que por acaso exista.
export const UNASSIGNED = "__unassigned__";

type ContactCardProps = {
  contact: Contact;
  stages: Stage[];
  currentStageId: string; // id da Stage ou UNASSIGNED
  onMove: (contactId: string, stageId: string) => void;
};

/** Card de cliente dentro de uma coluna do Kanban. Mover é um <select> (sem
 * drag-and-drop nesta fase, ver docs/features/CLIENTES_ESTAGIOS.md). */
export function ContactCard({ contact, stages, currentStageId, onMove }: ContactCardProps) {
  return (
    <div className="rounded-lg border border-border-light bg-card-bg p-3">
      <p className="text-sm font-medium text-text-dark">{contact.name}</p>
      <p className="text-xs text-text-muted">{contact.phone}</p>
      <Select
        value={currentStageId}
        onChange={(e) => onMove(contact.id, e.target.value)}
        className="mt-2 w-full !py-1 text-xs"
      >
        <option value={UNASSIGNED} disabled>
          Sem coluna
        </option>
        {stages.map((s) => (
          <option key={s.id} value={s.id}>
            Mover para: {s.name}
          </option>
        ))}
      </Select>
    </div>
  );
}

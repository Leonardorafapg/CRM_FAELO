import { Contact, Stage } from "@/lib/api";
import { Select } from "@/components/ui/Select";
import { IconMail, IconPhoneCall } from "@/components/layout/icons";

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

// Paleta fixa pro avatar do card — variedade visual entre clientes (mesmo
// espirito da referência, onde cada avatar tem uma cor diferente), escolhida
// de forma deterministica a partir do id (mesmo cliente sempre com a mesma
// cor, sem precisar guardar isso no banco).
const AVATAR_COLORS = ["#2f7bfb", "#e0457b", "#8f42c1", "#0ea5a4", "#f59e0b", "#ef4444", "#22c55e"];

function avatarColor(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

/** Card de cliente dentro de uma coluna do Kanban. Mover é um <select> (sem
 * drag-and-drop nesta fase, ver docs/features/CLIENTES_ESTAGIOS.md). */
export function ContactCard({ contact, stages, currentStageId, onMove }: ContactCardProps) {
  const color = avatarColor(contact.id);
  const initial = contact.name.trim().charAt(0).toUpperCase() || "?";

  return (
    <div className="rounded-xl border border-border-light bg-card-bg p-3 shadow-sm">
      <div className="flex items-center gap-2.5">
        <span
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
          style={{ backgroundColor: color }}
        >
          {initial}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold" style={{ color }}>
            {contact.name}
          </p>
          <p className="truncate text-xs text-text-muted">{contact.phone}</p>
        </div>
      </div>

      {contact.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {contact.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-accent-blue/10 px-2 py-0.5 text-[10px] font-medium text-accent-blue"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="mt-2.5 flex items-center gap-2 border-t border-border-light pt-2">
        <a
          href={`tel:${contact.phone}`}
          title="Ligar"
          className="flex h-6 w-6 items-center justify-center rounded-md text-text-muted transition-colors hover:bg-page-bg hover:text-accent-blue"
        >
          <IconPhoneCall width={13} height={13} />
        </a>
        {contact.email && (
          <a
            href={`mailto:${contact.email}`}
            title="Enviar e-mail"
            className="flex h-6 w-6 items-center justify-center rounded-md text-text-muted transition-colors hover:bg-page-bg hover:text-accent-blue"
          >
            <IconMail width={13} height={13} />
          </a>
        )}
      </div>

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

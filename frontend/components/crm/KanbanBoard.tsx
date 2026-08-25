import { Contact, Stage } from "@/lib/api";
import { StageColumn } from "./StageColumn";
import { ContactCard, UNASSIGNED } from "./ContactCard";

type KanbanBoardProps = {
  stages: Stage[];
  contacts: Contact[];
  onMove: (contactId: string, stageId: string) => void;
};

/** Quadro completo: uma coluna por Stage do pipeline selecionado, mais uma
 * coluna fixa "Sem coluna" pra clientes com stage_id nulo — sem ela, um
 * cliente criado sem stage nunca aparece em lugar nenhum do board e não tem
 * como ser movido (o <select> de mover só existe dentro de um card já
 * visível). Só entram aqui contatos com stage_id null OU pertencente a uma
 * Stage deste pipeline — contatos de outro pipeline não aparecem em
 * nenhuma coluna deste board, nem em "Sem coluna". */
export function KanbanBoard({ stages, contacts, onMove }: KanbanBoardProps) {
  const unassigned = contacts.filter((c) => c.stage_id === null);

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      <StageColumn title="Sem coluna" count={unassigned.length}>
        {unassigned.length === 0 ? (
          <p className="text-xs text-text-muted">Nenhum cliente sem coluna.</p>
        ) : (
          unassigned.map((contact) => (
            <ContactCard
              key={contact.id}
              contact={contact}
              stages={stages}
              currentStageId={UNASSIGNED}
              onMove={onMove}
            />
          ))
        )}
      </StageColumn>

      {stages.map((stage) => {
        const stageContacts = contacts.filter((c) => c.stage_id === stage.id);
        return (
          <StageColumn key={stage.id} title={stage.name} count={stageContacts.length}>
            {stageContacts.length === 0 ? (
              <p className="text-xs text-text-muted">Nenhum cliente nesta coluna.</p>
            ) : (
              stageContacts.map((contact) => (
                <ContactCard
                  key={contact.id}
                  contact={contact}
                  stages={stages}
                  currentStageId={stage.id}
                  onMove={onMove}
                />
              ))
            )}
          </StageColumn>
        );
      })}
    </div>
  );
}

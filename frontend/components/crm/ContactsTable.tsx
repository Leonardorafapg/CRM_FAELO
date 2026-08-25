import { Contact } from "@/lib/api";

type ContactsTableProps = {
  contacts: Contact[];
  onDelete: (id: string) => void;
};

export function ContactsTable({ contacts, onDelete }: ContactsTableProps) {
  if (contacts.length === 0) {
    return <p className="text-text-muted">Nenhum cliente cadastrado ainda.</p>;
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border-light bg-card-bg">
      <table className="w-full text-left text-sm">
        <thead className="bg-page-bg text-text-muted">
          <tr>
            <th className="px-4 py-2 font-medium">Nome</th>
            <th className="px-4 py-2 font-medium">Telefone</th>
            <th className="px-4 py-2 font-medium">Email</th>
            <th className="px-4 py-2 font-medium">Tags</th>
            <th className="px-4 py-2" />
          </tr>
        </thead>
        <tbody>
          {contacts.map((c) => (
            <tr key={c.id} className="border-t border-border-light">
              <td className="px-4 py-2 text-text-dark">{c.name}</td>
              <td className="px-4 py-2 text-text-dark">{c.phone}</td>
              <td className="px-4 py-2 text-text-muted">{c.email || "—"}</td>
              <td className="px-4 py-2 text-text-muted">{c.tags.join(", ") || "—"}</td>
              <td className="px-4 py-2 text-right">
                <button onClick={() => onDelete(c.id)} className="text-sm text-red-600 hover:underline">
                  Excluir
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

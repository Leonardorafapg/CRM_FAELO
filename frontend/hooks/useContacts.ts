import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError, Contact, createContact, deleteContact, listContacts } from "@/lib/api";

/** Lista de clientes + formulário de criação — a página só monta a UI.
 * Sem stage aqui de propósito: atribuir cliente a uma coluna é trabalho da
 * tela de Quadros, não deste cadastro (ver docs/features/CLIENTES_ESTAGIOS.md). */
export function useContacts() {
  const { user } = useAuth();
  const token = user?.access_token ?? "";

  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [tags, setTags] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setContacts(await listContacts(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao carregar clientes.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  function resetForm() {
    setName("");
    setPhone("");
    setEmail("");
    setTags("");
    setFormError(null);
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      const created = await createContact(token, {
        name,
        phone,
        email: email || undefined,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      setContacts((prev) => [created, ...prev]);
      resetForm();
      setShowForm(false);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Erro ao criar cliente.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    // Sem confirm() customizado no projeto ainda — usa o nativo do browser
    // mesmo, é suficiente pra uma ação destrutiva simples como essa.
    if (!window.confirm("Excluir este cliente?")) return;
    try {
      await deleteContact(token, id);
      setContacts((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao excluir cliente.");
    }
  }

  return {
    contacts,
    loading,
    error,
    showForm,
    setShowForm,
    name,
    setName,
    phone,
    setPhone,
    email,
    setEmail,
    tags,
    setTags,
    saving,
    formError,
    handleCreate,
    handleDelete,
  };
}

"use client";

import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useContacts } from "@/hooks/useContacts";
import { BackLink } from "@/components/ui/BackLink";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { ContactForm } from "@/components/crm/ContactForm";
import { ContactsTable } from "@/components/crm/ContactsTable";

export default function ClientesPage() {
  const ready = useRequireAuth();
  const {
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
  } = useContacts();

  if (!ready) return null;

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <BackLink href="/dashboard">← Dashboard</BackLink>
          <h1 className="font-heading text-2xl font-bold text-text-dark">Clientes</h1>
        </div>
        <button
          type="button"
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg bg-accent-blue px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          {showForm ? "Cancelar" : "Novo cliente"}
        </button>
      </div>

      {showForm && (
        <ContactForm
          name={name}
          setName={setName}
          phone={phone}
          setPhone={setPhone}
          email={email}
          setEmail={setEmail}
          tags={tags}
          setTags={setTags}
          saving={saving}
          error={formError}
          onSubmit={handleCreate}
        />
      )}

      <ErrorMessage>{error}</ErrorMessage>

      {loading ? (
        <p className="text-text-muted">Carregando...</p>
      ) : (
        <ContactsTable contacts={contacts} onDelete={handleDelete} />
      )}
    </main>
  );
}

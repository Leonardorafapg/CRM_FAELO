"use client";

import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useTenantProfile } from "@/hooks/useTenantProfile";
import { BackLink } from "@/components/ui/BackLink";
import { Input } from "@/components/ui/Input";
import { ErrorMessage } from "@/components/ui/ErrorMessage";

export default function EmpresaPage() {
  const ready = useRequireAuth();
  const { form, setField, loading, saving, saved, error, isAdmin, handleSave } = useTenantProfile();

  if (!ready) return null;

  return (
    <main className="flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-8">
      <div>
        <BackLink href="/dashboard/configuracoes">Configurações</BackLink>
        <h1 className="mt-2 font-heading text-2xl font-bold text-text-dark">Dados da Empresa</h1>
        <p className="mt-1 text-sm text-text-muted">Informações do seu estabelecimento.</p>
      </div>

      {loading ? (
        <p className="text-text-muted">Carregando...</p>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Nome da empresa"
              value={form.business_name ?? ""}
              onChange={(e) => setField("business_name", e.target.value)}
              placeholder="Barbearia do João"
              disabled={!isAdmin}
            />
            <Input
              label="Telefone"
              value={form.phone ?? ""}
              onChange={(e) => setField("phone", e.target.value)}
              placeholder="11999998888"
              disabled={!isAdmin}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="E-mail"
              value={form.email ?? ""}
              onChange={(e) => setField("email", e.target.value)}
              placeholder="contato@empresa.com"
              disabled={!isAdmin}
            />
            <Input
              label="WhatsApp"
              value={form.whatsapp ?? ""}
              onChange={(e) => setField("whatsapp", e.target.value)}
              placeholder="11999998888"
              disabled={!isAdmin}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Cidade"
              value={form.city ?? ""}
              onChange={(e) => setField("city", e.target.value)}
              placeholder="São Paulo"
              disabled={!isAdmin}
            />
            <Input
              label="Estado"
              value={form.state ?? ""}
              onChange={(e) => setField("state", e.target.value)}
              placeholder="SP"
              disabled={!isAdmin}
            />
          </div>

          <Input
            label="Endereço"
            value={form.address ?? ""}
            onChange={(e) => setField("address", e.target.value)}
            placeholder="Rua das Flores, 123 — Centro"
            disabled={!isAdmin}
          />

          <Input
            label="Instagram"
            value={form.instagram ?? ""}
            onChange={(e) => setField("instagram", e.target.value)}
            placeholder="@barbeariadojoao"
            disabled={!isAdmin}
          />

          <ErrorMessage>{error}</ErrorMessage>

          {isAdmin ? (
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="self-start rounded-lg bg-accent-blue px-5 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {saved ? "Salvo!" : saving ? "Salvando..." : "Salvar alterações"}
            </button>
          ) : (
            <p className="text-xs text-text-muted">Apenas administradores podem editar esses dados.</p>
          )}
        </div>
      )}
    </main>
  );
}

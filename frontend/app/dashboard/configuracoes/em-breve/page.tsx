"use client";

import { useRequireAuth } from "@/hooks/useRequireAuth";
import { BackLink } from "@/components/ui/BackLink";

export default function EmBrevePage() {
  const ready = useRequireAuth();
  if (!ready) return null;

  return (
    <main className="flex w-full max-w-3xl flex-1 flex-col gap-4 px-6 py-8">
      <div>
        <BackLink href="/dashboard/configuracoes">Configurações</BackLink>
        <h1 className="mt-2 font-heading text-2xl font-bold text-text-dark">Em breve</h1>
      </div>
      <p className="text-text-muted">Essa configuração ainda está em construção.</p>
    </main>
  );
}

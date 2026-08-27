"use client";

import { useAuth } from "@/contexts/AuthContext";
import { Avatar } from "@/components/ui/Avatar";

/** Barra superior fixa — segue o tema do dashboard (claro/escuro) via os
 * mesmos tokens usados no resto das telas (bg-card-bg/text-text-dark/etc),
 * em vez de cor fixa. Data real do dia, sem dado fabricado (sem contador de
 * notificação fake — não temos notificações de verdade ainda). */
export function TopBar() {
  const { user } = useAuth();

  const hoje = new Date().toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border-light bg-card-bg px-5">
      <p className="text-sm capitalize text-text-muted">{hoje}</p>

      {user && (
        <div className="flex items-center gap-2.5">
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-wide text-text-muted">Bem-vindo(a)</p>
            <p className="text-sm font-medium text-text-dark">{user.name}</p>
          </div>
          <Avatar name={user.name} size={32} />
        </div>
      )}
    </header>
  );
}

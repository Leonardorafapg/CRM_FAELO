"use client";

import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { useRequireAuth } from "@/hooks/useRequireAuth";

const SHORTCUTS = [
  { href: "/dashboard/clientes", label: "Clientes", description: "Cadastrar e gerenciar clientes." },
  { href: "/dashboard/quadros", label: "Quadros", description: "Kanban de clientes por pipeline." },
  { href: "/dashboard/conexoes", label: "Conexões", description: "Conectar WhatsApp via QR code." },
  { href: "/dashboard/atendimentos", label: "Atendimentos", description: "Conversas do WhatsApp em tempo real." },
];

export default function DashboardPage() {
  const ready = useRequireAuth();
  const { user } = useAuth();

  if (!ready) return null;

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-4 py-8">
      <div>
        <h1 className="font-heading text-2xl font-bold text-text-dark">Dashboard</h1>
        {user && (
          <p className="mt-1 text-sm text-text-muted">
            Logado como <span className="text-text-dark">{user.name}</span>
          </p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {SHORTCUTS.map((s) => (
          <Link
            key={s.href}
            href={s.href}
            className="rounded-xl border border-border-light bg-card-bg p-5 transition-opacity hover:opacity-90"
          >
            <h2 className="font-heading text-lg font-semibold text-text-dark">{s.label}</h2>
            <p className="mt-1 text-sm text-text-muted">{s.description}</p>
          </Link>
        ))}
      </div>
    </main>
  );
}

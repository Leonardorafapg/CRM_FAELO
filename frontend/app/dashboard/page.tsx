"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { useRequireAuth } from "@/hooks/useRequireAuth";

export default function DashboardPage() {
  const ready = useRequireAuth();
  const { user, logout } = useAuth();
  const router = useRouter();

  if (!ready) return null;

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-text-dark">Dashboard</h1>
          {user && (
            <p className="mt-1 text-sm text-text-muted">
              Logado como <span className="text-text-dark">{user.name}</span>
            </p>
          )}
        </div>
        <button onClick={handleLogout} className="text-sm text-accent-blue hover:underline">
          Sair
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          href="/dashboard/clientes"
          className="rounded-xl border border-border-light bg-card-bg p-5 transition-opacity hover:opacity-90"
        >
          <h2 className="font-heading text-lg font-semibold text-text-dark">Clientes</h2>
          <p className="mt-1 text-sm text-text-muted">Cadastrar e gerenciar clientes.</p>
        </Link>

        <Link
          href="/dashboard/quadros"
          className="rounded-xl border border-border-light bg-card-bg p-5 transition-opacity hover:opacity-90"
        >
          <h2 className="font-heading text-lg font-semibold text-text-dark">Quadros</h2>
          <p className="mt-1 text-sm text-text-muted">Kanban de clientes por pipeline.</p>
        </Link>

        <Link
          href="/dashboard/conexoes"
          className="rounded-xl border border-border-light bg-card-bg p-5 transition-opacity hover:opacity-90"
        >
          <h2 className="font-heading text-lg font-semibold text-text-dark">Conexões</h2>
          <p className="mt-1 text-sm text-text-muted">Conectar WhatsApp via QR code.</p>
        </Link>

        <Link
          href="/dashboard/atendimentos"
          className="rounded-xl border border-border-light bg-card-bg p-5 transition-opacity hover:opacity-90"
        >
          <h2 className="font-heading text-lg font-semibold text-text-dark">Atendimentos</h2>
          <p className="mt-1 text-sm text-text-muted">Conversas do WhatsApp em tempo real.</p>
        </Link>
      </div>
    </main>
  );
}

"use client";

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
    <main className="flex flex-1 flex-col items-center justify-center gap-4 px-4">
      <div className="text-center">
        <h1 className="font-heading text-2xl font-bold text-text-dark">
          Plataforma em construção
        </h1>
        <p className="mt-2 text-text-muted">
          O dashboard ainda está sendo desenvolvido.
        </p>
        {user && (
          <p className="mt-4 text-sm text-text-muted">
            Logado como <span className="text-text-dark">{user.name}</span>
          </p>
        )}
      </div>

      <button
        onClick={handleLogout}
        className="text-sm text-accent-blue hover:underline"
      >
        Sair
      </button>
    </main>
  );
}

"use client";

import { useRequireAuth } from "@/hooks/useRequireAuth";

export default function DashboardPage() {
  const ready = useRequireAuth();

  if (!ready) return null;

  return (
    <main className="flex flex-1 items-center justify-center px-4">
      <div className="text-center">
        <h1 className="font-heading text-2xl font-bold text-text-dark">
          Plataforma em construção
        </h1>
        <p className="mt-2 text-text-muted">
          O dashboard ainda está sendo desenvolvido.
        </p>
      </div>
    </main>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Sem chamada de API ainda — so a interface, conforme pedido.
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
  }

  return (
    <main className="flex flex-1 items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl border border-dark-border bg-dark-card p-8">
        <h1 className="font-heading text-2xl font-bold text-text-primary">
          Entrar
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Acesse o painel Faelo.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-sm text-text-secondary">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-dark-border bg-dark-bg px-3 py-2 text-text-primary outline-none focus:border-faelo-blue"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" className="text-sm text-text-secondary">
              Senha
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-lg border border-dark-border bg-dark-bg px-3 py-2 text-text-primary outline-none focus:border-faelo-blue"
            />
          </div>

          <button
            type="submit"
            className="mt-2 rounded-lg py-2 font-medium text-white transition-opacity hover:opacity-90"
            style={{ background: "var(--ai-gradient)" }}
          >
            Entrar
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-secondary">
          Não tem conta?{" "}
          <Link href="/register" className="text-faelo-blue hover:underline">
            Criar conta
          </Link>
        </p>
      </div>
    </main>
  );
}

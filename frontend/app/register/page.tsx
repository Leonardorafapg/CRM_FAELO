"use client";

import { useState } from "react";
import Link from "next/link";

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Sem chamada de API ainda — so a interface, conforme pedido. Campos
  // seguem o RegisterRequest do platform-service (name, business_name,
  // email, password).
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
  }

  return (
    <main className="flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm rounded-xl border border-dark-border bg-dark-card p-8">
        <h1 className="font-heading text-2xl font-bold text-text-primary">
          Criar conta
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Comece a usar o Faelo.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="name" className="text-sm text-text-secondary">
              Seu nome
            </label>
            <input
              id="name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="rounded-lg border border-dark-border bg-dark-bg px-3 py-2 text-text-primary outline-none focus:border-faelo-blue"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="business_name"
              className="text-sm text-text-secondary"
            >
              Nome da empresa
            </label>
            <input
              id="business_name"
              type="text"
              required
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              className="rounded-lg border border-dark-border bg-dark-bg px-3 py-2 text-text-primary outline-none focus:border-faelo-blue"
            />
          </div>

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
              minLength={8}
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
            Criar conta
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-secondary">
          Já tem conta?{" "}
          <Link href="/login" className="text-faelo-blue hover:underline">
            Entrar
          </Link>
        </p>
      </div>
    </main>
  );
}

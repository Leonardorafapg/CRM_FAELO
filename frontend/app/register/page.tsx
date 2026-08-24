"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register, ApiError } from "@/lib/api";
import { saveSession } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const auth = await register({
        name,
        business_name: businessName,
        email,
        password,
      });
      saveSession(auth);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao criar conta.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm rounded-2xl border border-border-light bg-card-bg p-8 shadow-sm">
        <h1 className="font-heading text-2xl font-bold text-text-dark">
          Criar conta
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          Comece a usar o Faelo.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="name" className="text-sm text-text-muted">
              Seu nome
            </label>
            <input
              id="name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="rounded-lg border border-border-light bg-page-bg px-3 py-2 text-text-dark outline-none focus:border-accent-blue"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="business_name"
              className="text-sm text-text-muted"
            >
              Nome da empresa
            </label>
            <input
              id="business_name"
              type="text"
              required
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              className="rounded-lg border border-border-light bg-page-bg px-3 py-2 text-text-dark outline-none focus:border-accent-blue"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-sm text-text-muted">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-border-light bg-page-bg px-3 py-2 text-text-dark outline-none focus:border-accent-blue"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" className="text-sm text-text-muted">
              Senha
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-lg border border-border-light bg-page-bg px-3 py-2 text-text-dark outline-none focus:border-accent-blue"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 rounded-lg bg-accent-blue py-2 font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {loading ? "Criando..." : "Criar conta"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-muted">
          Já tem conta?{" "}
          <Link href="/login" className="text-accent-blue hover:underline">
            Entrar
          </Link>
        </p>
      </div>
    </main>
  );
}

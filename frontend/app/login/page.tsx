"use client";

import Link from "next/link";
import { AuthCard } from "@/components/auth/AuthCard";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useLogin } from "@/hooks/useLogin";

export default function LoginPage() {
  const { email, setEmail, password, setPassword, error, loading, handleSubmit } =
    useLogin();

  return (
    <AuthCard
      title="Entrar"
      subtitle="Acesse o painel Faelo."
      footer={
        <>
          Não tem conta?{" "}
          <Link href="/register" className="text-accent-blue hover:underline">
            Criar conta
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <Input
          id="email"
          label="Email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Input
          id="password"
          label="Senha"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <ErrorMessage>{error}</ErrorMessage>

        <Button type="submit" loading={loading} loadingText="Entrando...">
          Entrar
        </Button>
      </form>
    </AuthCard>
  );
}

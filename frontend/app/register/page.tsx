"use client";

import Link from "next/link";
import { AuthCard } from "@/components/auth/AuthCard";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { useRegister } from "@/hooks/useRegister";

export default function RegisterPage() {
  const {
    name,
    setName,
    businessName,
    setBusinessName,
    email,
    setEmail,
    password,
    setPassword,
    error,
    loading,
    handleSubmit,
  } = useRegister();

  return (
    <AuthCard
      title="Criar conta"
      subtitle="Comece a usar o Faelo."
      footer={
        <>
          Já tem conta?{" "}
          <Link href="/login" className="text-accent-blue hover:underline">
            Entrar
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <Input
          id="name"
          label="Seu nome"
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          id="business_name"
          label="Nome da empresa"
          type="text"
          required
          value={businessName}
          onChange={(e) => setBusinessName(e.target.value)}
        />
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
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <ErrorMessage>{error}</ErrorMessage>

        <Button type="submit" loading={loading} loadingText="Criando...">
          Criar conta
        </Button>
      </form>
    </AuthCard>
  );
}

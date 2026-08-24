import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { login as loginRequest, ApiError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

/** Estado e submit do formulário de login — a página só monta a UI. */
export function useLogin() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const auth = await loginRequest(email, password);
      login(auth);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao entrar.");
    } finally {
      setLoading(false);
    }
  }

  return {
    email,
    setEmail,
    password,
    setPassword,
    error,
    loading,
    handleSubmit,
  };
}

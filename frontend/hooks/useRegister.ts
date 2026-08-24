import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { register as registerRequest, ApiError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

/** Estado e submit do formulário de registro — a página só monta a UI. */
export function useRegister() {
  const router = useRouter();
  const { login } = useAuth();
  const [name, setName] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const auth = await registerRequest({
        name,
        business_name: businessName,
        email,
        password,
      });
      login(auth); // registro ja loga a sessao — mesmo contrato do backend (token pronto)
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao criar conta.");
    } finally {
      setLoading(false);
    }
  }

  return {
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
  };
}

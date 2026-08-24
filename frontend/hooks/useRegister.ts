import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { register, ApiError } from "@/lib/api";
import { saveSession } from "@/lib/auth";

/** Estado e submit do formulário de registro — a página só monta a UI. */
export function useRegister() {
  const router = useRouter();
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

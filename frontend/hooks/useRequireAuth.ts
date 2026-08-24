import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

/**
 * Protege uma página client-side: sem sessão no AuthContext, redireciona
 * pra /login. Devolve `ready` só depois que o AuthProvider terminou de ler
 * o localStorage E confirmou que há usuário — a página não desenha
 * conteúdo protegido antes disso.
 */
export function useRequireAuth() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  return !isLoading && !!user;
}

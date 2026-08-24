import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";

/**
 * Protege uma página client-side: sem token salvo, redireciona pra /login.
 * `ready` só vira true depois da checagem, pra a página não desenhar
 * conteúdo protegido por um instante antes do redirect.
 */
export function useRequireAuth() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [router]);

  return ready;
}

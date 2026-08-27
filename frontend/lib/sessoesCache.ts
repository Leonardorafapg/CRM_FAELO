// Cache simples em memoria (modulo) pras conversas do tenant logado.
// Objetivo: nao esperar o usuario navegar ate /dashboard/atendimentos pra
// so entao disparar o GET /sessoes — o AuthContext ja chama prefetchSessoes
// assim que resolve a sessao (login ou reidratacao do localStorage no
// carregamento da pagina), entao a promise ja esta em voo (ou resolvida)
// quando a pagina de Atendimentos monta. A pagina ainda revalida com uma
// chamada fresca ao montar (stale-while-revalidate), isso so acelera a
// primeira pintura.
import { Sessao, listSessoes } from "./whatsapp";

let cache: { tenantId: string; promise: Promise<Sessao[]> } | null = null;

export function prefetchSessoes(tenantId: string, token: string): Promise<Sessao[]> {
  if (cache && cache.tenantId === tenantId) return cache.promise;
  const promise = listSessoes(token).catch((e) => {
    cache = null; // falha nao fica presa no cache — proxima tentativa refaz a chamada
    throw e;
  });
  cache = { tenantId, promise };
  return promise;
}

export function getCachedSessoes(tenantId: string): Promise<Sessao[]> | null {
  return cache && cache.tenantId === tenantId ? cache.promise : null;
}

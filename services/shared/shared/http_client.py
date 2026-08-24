"""Cliente HTTP assincrono persistente (connection pool), reusado tanto para
chamadas a APIs externas quanto para chamadas internas servico-a-servico
(ex.: conversation-service -> crm-service)."""
import httpx

from shared.logging_config import get_logger

logger = get_logger("shared.http_client")

# Singleton em nivel de modulo — um unico client (com pool de conexoes) por
# processo, em vez de criar um AsyncClient novo a cada chamada (isso
# desperdicaria a reutilizacao de conexao TCP/TLS).
_async_client: httpx.AsyncClient | None = None


def get_async_client() -> httpx.AsyncClient:
    """Devolve o client persistente, criando na primeira chamada (ou
    recriando se por algum motivo ja tiver sido fechado). Configurado com
    timeout de 30s e um pool de ate 50 conexoes (20 delas mantidas "quentes"
    por 30s) pra reduzir latencia em chamadas repetidas ao mesmo host."""
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            ),
        )
    return _async_client


async def close_async_client():
    """Fecha o client de forma graciosa — chamado no shutdown (lifespan) do
    app, pra nao deixar conexoes penduradas quando o processo encerra."""
    global _async_client
    if _async_client and not _async_client.is_closed:
        await _async_client.aclose()

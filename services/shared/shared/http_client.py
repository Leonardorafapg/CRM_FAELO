"""Cliente HTTP assincrono persistente (connection pool), reusado tanto para
chamadas a APIs externas quanto para chamadas internas servico-a-servico
(ex.: conversation-service -> crm-service)."""
import httpx

from shared.logging_config import get_logger

logger = get_logger("shared.http_client")

_async_client: httpx.AsyncClient | None = None


def get_async_client() -> httpx.AsyncClient:
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
    global _async_client
    if _async_client and not _async_client.is_closed:
        await _async_client.aclose()

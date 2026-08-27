"""Chamada interna ao platform-service pra buscar a config de IA/identidade
do tenant (GET /internal/tenants/{id}, autenticado por X-Internal-Key —
mesmo padrao de shared/internal_auth.py). O ai-service nunca guarda dado de
identidade do tenant em banco proprio, so consulta na hora de montar o
system prompt."""
import os
from typing import Any, Dict

import httpx
from fastapi import HTTPException

from shared.http_client import get_async_client
from shared.logging_config import get_logger

logger = get_logger("ai-service")

PLATFORM_SERVICE_URL = os.getenv("PLATFORM_SERVICE_URL", "").rstrip("/")
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "")


async def get_tenant_config(tenant_id: str) -> Dict[str, Any]:
    client = get_async_client()
    try:
        resp = await client.get(
            f"{PLATFORM_SERVICE_URL}/internal/tenants/{tenant_id}",
            headers={"X-Internal-Key": INTERNAL_SERVICE_KEY},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Tenant não encontrado ou inativo")
        logger.error(f"Falha ao buscar config do tenant {tenant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao consultar dados do tenant")
    except httpx.HTTPError as e:
        logger.error(f"Falha ao buscar config do tenant {tenant_id}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao consultar dados do tenant")

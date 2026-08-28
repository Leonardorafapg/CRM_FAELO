"""Cliente HTTP pro ai-service — usado pelo webhook pra obter a resposta
automatica da IA a uma mensagem de cliente. Best-effort: qualquer falha
(ai-service fora do ar, tenant sem chave configurada, etc.) e logada e
ignorada, nunca derruba o processamento do webhook — perder uma resposta
automatica e recuperavel, travar o webhook da Evolution nao seria."""
import os
from typing import Optional

import httpx

from shared.http_client import get_async_client
from shared.logging_config import get_logger

logger = get_logger("whatsapp-service")

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "").rstrip("/")
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "")


async def get_ai_reply(tenant_id: str, history: list[dict], user_message: str) -> Optional[str]:
    if not AI_SERVICE_URL:
        return None

    client = get_async_client()
    try:
        resp = await client.post(
            f"{AI_SERVICE_URL}/internal/ai/respond",
            headers={"X-Internal-Key": INTERNAL_SERVICE_KEY},
            json={"tenant_id": tenant_id, "user_message": user_message, "history": history},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json().get("reply")
    except httpx.HTTPError as e:
        logger.error(f"Falha ao consultar ai-service para tenant {tenant_id}: {type(e).__name__}: {e}", exc_info=True)
        return None

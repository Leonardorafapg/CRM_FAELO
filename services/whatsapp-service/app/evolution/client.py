"""Cliente HTTP para a Evolution API (self-hosted, Baileys). So chamadas
assincronas via o client singleton do shared — nunca cria httpx.AsyncClient()
novo a cada chamada. Falha de chamada externa vira HTTPException (502/400),
nunca e engolida silenciosamente."""
import os

import httpx
from fastapi import HTTPException

from shared.http_client import get_async_client
from shared.logging_config import get_logger

logger = get_logger("whatsapp-service")

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "").rstrip("/")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")


def _headers() -> dict:
    return {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}


async def create_instance(instance_name: str) -> dict:
    """Cria a instancia na Evolution e devolve o payload cru (contem o QR
    code em base64, formato depende da versao da Evolution API)."""
    client = get_async_client()
    try:
        resp = await client.post(
            f"{EVOLUTION_API_URL}/instance/create",
            headers=_headers(),
            json={"instanceName": instance_name, "qrcode": True, "integration": "WHATSAPP-BAILEYS"},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Falha ao criar instancia {instance_name} na Evolution API: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao criar instancia na Evolution API")


async def set_webhook(instance_name: str, webhook_url: str) -> None:
    client = get_async_client()
    try:
        resp = await client.post(
            f"{EVOLUTION_API_URL}/webhook/set/{instance_name}",
            headers=_headers(),
            json={"webhook": {"url": webhook_url, "enabled": True, "events": ["MESSAGES_UPSERT"]}},
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Falha ao configurar webhook da instancia {instance_name}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao configurar webhook na Evolution API")


async def get_instance_status(instance_name: str) -> dict:
    client = get_async_client()
    try:
        resp = await client.get(
            f"{EVOLUTION_API_URL}/instance/connectionState/{instance_name}",
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Falha ao consultar status da instancia {instance_name}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao consultar status na Evolution API")


async def send_message(instance_name: str, phone: str, text: str) -> dict:
    client = get_async_client()
    try:
        resp = await client.post(
            f"{EVOLUTION_API_URL}/message/sendText/{instance_name}",
            headers=_headers(),
            json={"number": phone, "text": text},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Falha ao enviar mensagem via instancia {instance_name}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao enviar mensagem via Evolution API")


async def delete_instance(instance_name: str) -> None:
    client = get_async_client()
    try:
        resp = await client.delete(
            f"{EVOLUTION_API_URL}/instance/delete/{instance_name}",
            headers=_headers(),
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Falha ao excluir instancia {instance_name} na Evolution API: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao excluir instancia na Evolution API")

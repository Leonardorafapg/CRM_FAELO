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


def extract_state(payload: dict) -> str:
    """O shape exato do estado da conexao varia entre versoes da Evolution
    API ({"instance": {"state": "open"}} ou {"state": "open"} direto) —
    mesmo espirito tolerante de _extract_qrcode. Valores conhecidos: "open"
    (conectado), "close"/"closed" (desconectado), "connecting" (ainda no
    QR code)."""
    instance = payload.get("instance", payload)
    return (instance.get("state") or "").lower()


def extract_message_fields(data: dict) -> dict:
    """Extrai os campos de uma mensagem a partir do shape "data" da Evolution
    (usado tanto no payload do webhook quanto nos registros devolvidos por
    find_messages — mesmo formato de mensagem nos dois casos). Tolerante:
    campos ausentes viram string/None em vez de KeyError."""
    key = data.get("key", {}) if isinstance(data, dict) else {}
    message = data.get("message", {}) if isinstance(data, dict) else {}

    message_id = key.get("id") or data.get("id")
    phone = (key.get("remoteJid") or data.get("from") or "").split("@")[0]
    from_me = key.get("fromMe", False)
    content = (
        message.get("conversation")
        or (message.get("extendedTextMessage") or {}).get("text")
        or data.get("text")
        or ""
    )
    contact_name = data.get("pushName")

    return {
        "message_id": message_id,
        "phone": phone,
        "role": "attendant" if from_me else "user",
        "content": content,
        "contact_name": contact_name,
    }


async def find_chats(instance_name: str) -> list[dict]:
    """Lista as conversas ja existentes no numero conectado — usado pra
    importar o historico na primeira vez que a instancia termina de
    conectar. Best-effort: falha aqui nao pode derrubar o fluxo de conexao,
    so loga e devolve lista vazia (ver chamador em app/chat/service.py)."""
    client = get_async_client()
    try:
        resp = await client.post(
            f"{EVOLUTION_API_URL}/chat/findChats/{instance_name}",
            headers=_headers(),
            json={},
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Falha ao listar chats da instancia {instance_name}: {type(e).__name__}: {e}", exc_info=True)
        return []
    if isinstance(data, list):
        return data
    return data.get("chats", []) if isinstance(data, dict) else []


async def find_messages(instance_name: str, remote_jid: str, limit: int = 50) -> list[dict]:
    """Mensagens de UM chat especifico — usado junto com find_chats na
    importacao de historico. Mesmo tratamento best-effort: falha vira lista
    vazia, nunca excecao propagada."""
    client = get_async_client()
    try:
        resp = await client.post(
            f"{EVOLUTION_API_URL}/chat/findMessages/{instance_name}",
            headers=_headers(),
            json={"where": {"key": {"remoteJid": remote_jid}}, "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Falha ao listar mensagens do chat {remote_jid} na instancia {instance_name}: {type(e).__name__}: {e}", exc_info=True)
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        messages = data.get("messages", [])
        if isinstance(messages, dict):
            return messages.get("records", [])
        return messages
    return []


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

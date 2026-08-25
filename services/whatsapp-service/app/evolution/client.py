"""Cliente HTTP para a Evolution API (self-hosted, Baileys). So chamadas
assincronas via o client singleton do shared — nunca cria httpx.AsyncClient()
novo a cada chamada. Falha de chamada externa vira HTTPException (502/400),
nunca e engolida silenciosamente."""
import os
import time

import httpx
from fastapi import HTTPException

from shared.http_client import get_async_client
from shared.logging_config import get_logger

logger = get_logger("whatsapp-service")

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "").rstrip("/")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")

# Timeout curto pras chamadas "de enriquecimento" (status/historico/foto),
# feitas dentro de GET /connections e GET /sessoes — o client HTTP
# compartilhado (shared/http_client.py) usa 30s de default, mas isso e
# tempo demais pra algo que roda dentro de um endpoint de LISTAGEM: o
# gateway usa o mesmo client (mesmos 30s) pra chamar este servico, entao um
# unico GET /connections lento o suficiente derruba a propria requisicao do
# gateway com ReadTimeout (502) antes mesmo da Evolution responder. Essas
# chamadas ja sao best-effort (falha vira "sem esse dado", nunca 500) — um
# timeout curto so faz a degradacao acontecer rapido em vez de travar a tela
# inteira por 30s quando a Evolution esta fora do ar/lenta.
_ENRICHMENT_TIMEOUT = 5.0


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
            timeout=_ENRICHMENT_TIMEOUT,
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


# Mensagem de midia (imagem/audio/video/documento/figurinha/etc.) nao tem
# "conversation"/"extendedTextMessage" — sem isso, content ficava "" e a
# importacao de historico (que filtra por `not content`) descartava a
# mensagem inteira em silencio. Rotula pelo tipo em vez de tentar baixar o
# conteudo (fora de escopo — ver docs/features/WHATSAPP_SERVICE.md).
_MEDIA_LABELS = {
    "imageMessage": "[Imagem]",
    "videoMessage": "[Vídeo]",
    "audioMessage": "[Áudio]",
    "documentMessage": "[Documento]",
    "stickerMessage": "[Figurinha]",
    "contactMessage": "[Contato]",
    "locationMessage": "[Localização]",
}


def extract_message_fields(data: dict) -> dict:
    """Extrai os campos de uma mensagem a partir do shape "data" da Evolution
    (usado tanto no payload do webhook quanto nos registros devolvidos por
    find_messages — mesmo formato de mensagem nos dois casos). Tolerante:
    campos ausentes viram string/None em vez de KeyError. content nunca
    fica vazio pra mensagem de verdade (com key.id) — midia sem texto vira
    um rotulo, tipo desconhecido vira um placeholder generico — pra nenhuma
    mensagem sumir so por nao ser texto puro."""
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
    if not content and message_id:
        content = _extract_media_label(message) or "[Mensagem não suportada]"
    contact_name = data.get("pushName")

    return {
        "message_id": message_id,
        "phone": phone,
        "role": "attendant" if from_me else "user",
        "content": content,
        "contact_name": contact_name,
    }


def _extract_media_label(message: dict) -> str | None:
    for msg_type, label in _MEDIA_LABELS.items():
        # Checa presenca da chave, nao truthiness: audioMessage sem legenda
        # costuma vir como {} (dict vazio, falsy em Python) — `if not media`
        # tratava isso como "sem midia" e caia no fallback generico.
        if msg_type not in message:
            continue
        media = message[msg_type]
        caption = media.get("caption") if isinstance(media, dict) else None
        return f"{label} {caption}".strip() if caption else label
    return None


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
            timeout=_ENRICHMENT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Falha ao listar chats da instancia {instance_name}: {type(e).__name__}: {e}", exc_info=True)
        return []
    if isinstance(data, list):
        return data
    return data.get("chats", []) if isinstance(data, dict) else []


def _unwrap_messages_page(data) -> list[dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        messages = data.get("messages", [])
        if isinstance(messages, dict):
            return messages.get("records", [])
        return messages
    return []


async def find_messages(instance_name: str, remote_jid: str, limit: int = 100, max_pages: int = 5) -> list[dict]:
    """Mensagens de UM chat especifico — usado junto com find_chats na
    importacao de historico. Pagina ate max_pages: a Evolution pode limitar
    quantos registros devolve por chamada mesmo pedindo um "limit" maior, e
    so uma pagina truncava o historico de chats mais movimentados. Se a API
    ignorar o parametro "page" e sempre devolver a mesma pagina, o dedup por
    evolution_message_id no chamador absorve a repeticao sem duplicar —
    max_pages so limita o desperdicio de chamadas nesse caso. Mesmo
    tratamento best-effort: falha vira o que ja foi acumulado ate ali, nunca
    excecao propagada."""
    client = get_async_client()
    all_messages: list[dict] = []
    for page in range(1, max_pages + 1):
        try:
            resp = await client.post(
                f"{EVOLUTION_API_URL}/chat/findMessages/{instance_name}",
                headers=_headers(),
                json={"where": {"key": {"remoteJid": remote_jid}}, "limit": limit, "page": page},
                timeout=_ENRICHMENT_TIMEOUT,
            )
            resp.raise_for_status()
            batch = _unwrap_messages_page(resp.json())
        except httpx.HTTPError as e:
            logger.error(f"Falha ao listar mensagens do chat {remote_jid} na instancia {instance_name}: {type(e).__name__}: {e}", exc_info=True)
            break

        if not batch:
            break
        all_messages.extend(batch)
        if len(batch) < limit:
            break  # ultima pagina — Evolution devolveu menos que o pedido

    return all_messages


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


# Cache em memoria da foto de perfil, mesmo padrao usado nos projetos de
# referencia (Foodapp/Simbora, evolution_service.py / evolution_client.py
# de la): TTL de 6h, teto de entradas, sem Redis/banco — reseta a cada
# deploy/restart do processo, o que e aceitavel pra uma foto de perfil.
_foto_cache: dict[str, tuple[str | None, float]] = {}
_FOTO_CACHE_TTL_SECONDS = 6 * 60 * 60
_FOTO_CACHE_MAX_ENTRIES = 20_000


async def fetch_profile_picture_url(instance_name: str, phone: str) -> str | None:
    """Busca a foto de perfil do contato na Evolution. Best-effort: numero
    sem foto, instancia fora do ar ou endpoint nao suportado nesta versao
    da Evolution viram None, nunca excecao — a foto e so um adorno visual,
    nao pode derrubar a listagem de conversas."""
    client = get_async_client()
    try:
        resp = await client.post(
            f"{EVOLUTION_API_URL}/chat/fetchProfilePictureUrl/{instance_name}",
            headers=_headers(),
            json={"number": phone},
            timeout=_ENRICHMENT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError:
        return None
    return data.get("profilePictureUrl") if isinstance(data, dict) else None


async def fetch_profile_picture_url_cached(instance_name: str, phone: str) -> str | None:
    """Evita bater na Evolution pra cada contato em toda listagem de
    conversas — ver _foto_cache acima."""
    key = f"{instance_name}:{phone}"
    now = time.monotonic()
    cached = _foto_cache.get(key)
    if cached and (now - cached[1]) < _FOTO_CACHE_TTL_SECONDS:
        return cached[0]

    url = await fetch_profile_picture_url(instance_name, phone)
    if len(_foto_cache) >= _FOTO_CACHE_MAX_ENTRIES:
        _foto_cache.clear()  # purge simples — teto raramente atingido com poucos tenants/contatos
    _foto_cache[key] = (url, now)
    return url


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

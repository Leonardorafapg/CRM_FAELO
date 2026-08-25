"""Webhook da Evolution API — SEM JWT, autenticado por um header secreto
simples (mesmo espirito de shared/internal_auth.py::require_internal_key:
comparacao simples, sem log do valor, 401 se nao bater)."""
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.chat import service
from app.chat.schemas import MessageOut
from app.ws.registry import broadcast
from app.connections.service import get_connection_by_instance
from shared.logging_config import get_logger

logger = get_logger("whatsapp-service")

router = APIRouter(prefix="/webhook", tags=["webhook"])

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
if not WEBHOOK_SECRET:
    raise RuntimeError("WEBHOOK_SECRET não definida nas variáveis de ambiente")


def require_webhook_secret(x_webhook_secret: str = Header(default="")) -> None:
    if x_webhook_secret != WEBHOOK_SECRET:
        logger.warning("Tentativa de acesso ao webhook com secret invalido")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Secret invalido")


def _extract_fields(payload: dict) -> dict:
    """Payload real da Evolution API e aninhado e varia por versao/evento —
    extrai de forma tolerante os campos minimos que este servico usa. Nao
    tenta suportar todo o shape da Evolution, so o necessario pro fluxo de
    texto simples deste documento."""
    data = payload.get("data", payload)
    key = data.get("key", {}) if isinstance(data, dict) else {}
    message = data.get("message", {}) if isinstance(data, dict) else {}

    instance_name = payload.get("instance") or data.get("instance")
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
        "instance_name": instance_name,
        "message_id": message_id,
        "phone": phone,
        "role": "attendant" if from_me else "user",
        "content": content,
        "contact_name": contact_name,
    }


@router.post("/evolution")
async def evolution_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _secret: None = Depends(require_webhook_secret),
):
    payload = await request.json()
    fields = _extract_fields(payload)

    if not fields["instance_name"] or not fields["message_id"] or not fields["phone"]:
        # Evento que nao e uma mensagem de texto (ex.: status update) — ignora
        # sem erro, a Evolution manda varios tipos de evento no mesmo webhook.
        return {"ok": True, "ignored": True}

    message = service.process_webhook_message(
        instance_name=fields["instance_name"],
        evolution_message_id=fields["message_id"],
        phone=fields["phone"],
        role=fields["role"],
        content=fields["content"],
        contact_name=fields["contact_name"],
        db=db,
    )

    if message is None:
        return {"ok": True, "duplicate": True}

    connection = get_connection_by_instance(fields["instance_name"], db)
    if connection:
        await broadcast(connection.tenant_id, {
            "type": "message",
            "session_id": message.session_id,
            "message": MessageOut.model_validate(message).model_dump(mode="json"),
        })

    return {"ok": True}

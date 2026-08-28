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
from app.evolution.client import extract_message_fields
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
    so o instance_name (que fica no nivel do payload, fora do "data") e
    especifico do webhook; o resto da extracao (mensagem em si) e a mesma
    logica usada pra importar historico (ver evolution.client.extract_message_fields),
    factorizada la pra nao duplicar."""
    data = payload.get("data", payload)
    fields = extract_message_fields(data if isinstance(data, dict) else {})
    fields["instance_name"] = payload.get("instance") or (data.get("instance") if isinstance(data, dict) else None)
    return fields


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

        # So a mensagem do CLIENTE dispara resposta automatica — mensagem
        # "attendant" tanto pode ser o proprio humano respondendo quanto o
        # eco da mensagem que a IA acabou de mandar (ver autoresponder),
        # nunca deve retrigger.
        if message.role == "user":
            session = service.get_session_or_404(message.session_id, connection.tenant_id, db)
            ai_message = await service.autoresponder(session, connection, message, db)
            if ai_message:
                await broadcast(connection.tenant_id, {
                    "type": "message",
                    "session_id": ai_message.session_id,
                    "message": MessageOut.model_validate(ai_message).model_dump(mode="json"),
                })

    return {"ok": True}

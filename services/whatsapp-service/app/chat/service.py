"""Regras de negocio de Session/Message (atendimento). Tudo escopado por
tenant_id vindo do JWT, exceto o webhook (autenticado por secret, resolve o
tenant via Connection.instance_name)."""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session as DbSession

from app.chat.models import Session as ChatSession, Message
from app.connections.models import Connection
from app.connections.service import get_connection_or_404
from app.evolution import client as evolution_client
from shared.logging_config import get_logger

logger = get_logger("whatsapp-service")


def _new_id() -> str:
    return str(uuid.uuid4())


def list_sessoes(tenant_id: str, db: DbSession, limit: int = 50, offset: int = 0) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.tenant_id == tenant_id)
        .order_by(ChatSession.last_activity.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_session_or_404(session_id: str, tenant_id: str, db: DbSession) -> ChatSession:
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.tenant_id == tenant_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao não encontrada")
    return session


def list_mensagens(session_id: str, tenant_id: str, db: DbSession, limit: int = 50, offset: int = 0) -> list[Message]:
    get_session_or_404(session_id, tenant_id, db)  # garante que a sessao e do tenant certo
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def _get_or_create_session(tenant_id: str, connection_id: str, phone: str, contact_name: str | None, db: DbSession) -> ChatSession:
    session_id = f"{tenant_id}:{phone}"
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session:
        session.last_activity = datetime.now(timezone.utc)
        if contact_name and not session.contact_name:
            session.contact_name = contact_name
        if not session.is_open:
            session.is_open = True
        return session

    session = ChatSession(
        id=session_id,
        tenant_id=tenant_id,
        connection_id=connection_id,
        phone=phone,
        contact_name=contact_name,
        is_open=True,
    )
    db.add(session)
    return session


def process_webhook_message(
    instance_name: str,
    evolution_message_id: str,
    phone: str,
    role: str,
    content: str,
    contact_name: str | None,
    db: DbSession,
) -> Message | None:
    """Dedup por evolution_message_id — se ja existe, ignora (retorna None).
    Resolve Connection pelo instance_name, resolve/cria Session pelo
    telefone, salva Message."""
    if role not in ("user", "attendant"):
        role = "user"

    existing = db.query(Message).filter(Message.evolution_message_id == evolution_message_id).first()
    if existing:
        logger.info(f"Mensagem duplicada ignorada: evolution_message_id={evolution_message_id}")
        return None

    connection = db.query(Connection).filter(Connection.instance_name == instance_name).first()
    if not connection:
        logger.warning(f"Webhook recebido para instance_name desconhecida: {instance_name}")
        raise HTTPException(status_code=404, detail="Instancia não encontrada")

    session = _get_or_create_session(connection.tenant_id, connection.id, phone, contact_name, db)
    db.flush()  # garante que a Session (nova ou existente) esta persistida antes do insert de Message com FK pra ela

    message = Message(
        id=_new_id(),
        session_id=session.id,
        role=role,
        content=content,
        evolution_message_id=evolution_message_id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    logger.info(f"Mensagem recebida: tenant={connection.tenant_id} session={session.id} role={role}")
    return message


async def responder(session_id: str, tenant_id: str, content: str, db: DbSession) -> Message:
    session = get_session_or_404(session_id, tenant_id, db)
    connection = db.query(Connection).filter(Connection.id == session.connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Conexao da sessao não encontrada")

    await evolution_client.send_message(connection.instance_name, session.phone, content)

    message = Message(
        id=_new_id(),
        session_id=session.id,
        role="attendant",
        content=content,
    )
    session.last_activity = datetime.now(timezone.utc)
    db.add(message)
    db.commit()
    db.refresh(message)
    logger.info(f"Resposta enviada: tenant={tenant_id} session={session.id}")
    return message


def encerrar_atendimento(session_id: str, tenant_id: str, db: DbSession) -> ChatSession:
    session = get_session_or_404(session_id, tenant_id, db)
    session.is_open = False
    db.commit()
    db.refresh(session)
    logger.info(f"Atendimento encerrado: tenant={tenant_id} session={session.id}")
    return session

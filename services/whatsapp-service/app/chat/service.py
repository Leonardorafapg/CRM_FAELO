"""Regras de negocio de Session/Message (atendimento). Tudo escopado por
tenant_id vindo do JWT, exceto o webhook (autenticado por secret, resolve o
tenant via Connection.instance_name)."""
import asyncio
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


async def list_sessoes(tenant_id: str, db: DbSession, limit: int = 50, offset: int = 0) -> list[dict]:
    """Foto de perfil NAO fica no banco (mesmo padrao dos projetos de
    referencia Foodapp/Simbora) — busca ao vivo na Evolution, em paralelo
    pra cada sessao da pagina atual, com cache em memoria de 6h dentro do
    proprio evolution_client (ver fetch_profile_picture_url_cached)."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.tenant_id == tenant_id)
        .order_by(ChatSession.last_activity.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    if not sessions:
        return []

    connections = {
        c.id: c for c in db.query(Connection).filter(Connection.tenant_id == tenant_id).all()
    }

    async def _foto(session: ChatSession) -> str | None:
        connection = connections.get(session.connection_id)
        if not connection:
            return None
        return await evolution_client.fetch_profile_picture_url_cached(connection.instance_name, session.phone)

    fotos = await asyncio.gather(*(_foto(s) for s in sessions))

    return [
        {
            "id": s.id,
            "connection_id": s.connection_id,
            "phone": s.phone,
            "contact_name": s.contact_name,
            "is_open": s.is_open,
            "last_activity": s.last_activity,
            "foto_url": foto,
        }
        for s, foto in zip(sessions, fotos)
    ]


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


def _get_or_create_session_quiet(tenant_id: str, connection_id: str, phone: str, contact_name: str | None, db: DbSession) -> ChatSession:
    """Mesma resolucao de Session que _get_or_create_session, mas SEM
    bumpar last_activity/reabrir a conversa so por tocar nela — usada pela
    importacao de historico, que roda a cada carregamento da tela (ver
    import_history) e nao pode fazer toda conversa antiga parecer "recem
    ativa" so por ter sido revisitada sem mensagem nova de verdade."""
    session_id = f"{tenant_id}:{phone}"
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session:
        if contact_name and not session.contact_name:
            session.contact_name = contact_name
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


async def import_history(connection: Connection, db: DbSession, chats_limit: int = 200, messages_per_chat: int = 100) -> None:
    """Puxa as conversas e mensagens que ja existiam no WhatsApp antes de
    conectar — sem isso, o inbox comeca vazio mesmo que o numero ja tivesse
    historico. Chamado uma vez, no exato momento em que a Connection
    transiciona pra "connected" (ver app/connections/service.py). Best-effort
    de ponta a ponta: qualquer falha e logada e ignorada, nunca propaga —
    perder o historico antigo e recuperavel (roda de novo na proxima
    reconexao), travar o fluxo de conexao por causa disso nao seria."""
    try:
        chats = await evolution_client.find_chats(connection.instance_name)
    except Exception:
        logger.exception(f"Falha ao importar historico da instancia {connection.instance_name}")
        return

    imported_messages = 0
    for chat in chats[:chats_limit]:
        remote_jid = chat.get("remoteJid") or chat.get("id") or ""
        if not remote_jid or remote_jid.endswith("@g.us"):
            continue  # grupos ficam de fora nesta fase — so conversas 1:1, mesmo escopo do resto do atendimento

        phone = remote_jid.split("@")[0]
        contact_name = chat.get("pushName") or chat.get("name")
        session = _get_or_create_session_quiet(connection.tenant_id, connection.id, phone, contact_name, db)
        db.flush()  # garante id da Session persistido antes do insert de Message com FK

        try:
            messages = await evolution_client.find_messages(connection.instance_name, remote_jid, limit=messages_per_chat)
        except Exception:
            logger.exception(f"Falha ao importar mensagens do chat {remote_jid}")
            continue

        new_in_chat = 0
        for raw in messages:
            fields = evolution_client.extract_message_fields(raw if isinstance(raw, dict) else {})
            if not fields["message_id"]:
                continue  # nao e uma mensagem de verdade (ex.: evento sem key.id) — content nunca fica
                          # vazio quando message_id existe (ver extract_message_fields), entao so isso
                          # ja cobre "descartar mensagem de midia" que existia aqui antes
            existing = db.query(Message).filter(Message.evolution_message_id == fields["message_id"]).first()
            if existing:
                continue
            db.add(Message(
                id=_new_id(),
                session_id=session.id,
                role=fields["role"],
                content=fields["content"],
                evolution_message_id=fields["message_id"],
            ))
            new_in_chat += 1

        # So bumpa last_activity se de fato entrou mensagem nova nesta
        # importacao — revisitar uma conversa ja totalmente importada nao
        # pode fazer ela pular pro topo do inbox sem motivo real.
        if new_in_chat > 0:
            session.last_activity = datetime.now(timezone.utc)
        imported_messages += new_in_chat

    db.commit()
    logger.info(
        f"Historico importado: tenant={connection.tenant_id} instance={connection.instance_name} "
        f"chats={len(chats)} mensagens={imported_messages}"
    )


def encerrar_atendimento(session_id: str, tenant_id: str, db: DbSession) -> ChatSession:
    session = get_session_or_404(session_id, tenant_id, db)
    session.is_open = False
    db.commit()
    db.refresh(session)
    logger.info(f"Atendimento encerrado: tenant={tenant_id} session={session.id}")
    return session

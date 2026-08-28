"""Regras de negocio de Session/Message (atendimento). Tudo escopado por
tenant_id vindo do JWT, exceto o webhook (autenticado por secret, resolve o
tenant via Connection.instance_name)."""
import asyncio
import time
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session as DbSession

from app import ai_client
from app.chat.models import Session as ChatSession, Message
from app.connections.models import Connection
from app.connections.service import get_connection_or_404
from app.evolution import client as evolution_client
from shared.logging_config import get_logger

logger = get_logger("whatsapp-service")

# Orcamento total pra busca de fotos de perfil dentro de GET /sessoes. A
# query no banco (indexada por tenant_id+last_activity) e rapida — o que
# deixava a listagem lenta era esperar, em serie com a resposta HTTP, ate
# 50 chamadas em paralelo pra Evolution (ate 5s de timeout cada, ver
# _ENRICHMENT_TIMEOUT) toda vez que o cache de foto expirava (6h) ou era
# a primeira listagem do tenant. Com esse orcamento, a listagem devolve no
# maximo apos esse tempo: quem ja respondeu entra com a foto, quem nao
# respondeu ainda entra sem foto (fallback de iniciais no frontend) mas a
# tarefa continua rodando em background so pra aquecer o cache pra proxima
# chamada — nunca cancelada, so nao bloqueia esta resposta.
_FOTOS_BUDGET_SECONDS = 1.5

# Limite de chamadas concorrentes a Evolution dentro de uma unica listagem —
# ver uso em list_sessoes/_foto. Evita que uma listagem sozinha (ate 50
# sessoes) monopolize o pool HTTP compartilhado (shared/http_client.py,
# capado em 50 conexoes) e atrase chamadas de outros endpoints do mesmo
# processo (webhook, envio de mensagem) que competem pelo mesmo client.
_FOTOS_CONCURRENCY = asyncio.Semaphore(10)


def _new_id() -> str:
    return str(uuid.uuid4())


async def list_sessoes(tenant_id: str, db: DbSession, limit: int = 50, offset: int = 0) -> list[dict]:
    """Foto de perfil NAO fica no banco (mesmo padrao dos projetos de
    referencia Foodapp/Simbora) — busca ao vivo na Evolution, em paralelo
    pra cada sessao da pagina atual, com cache em memoria de 6h dentro do
    proprio evolution_client (ver fetch_profile_picture_url_cached). Ver
    _FOTOS_BUDGET_SECONDS acima pra por que isso e limitado por tempo em vez
    de so um asyncio.gather direto."""
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
        # Semaforo: sem isso, uma unica listagem com muitas sessoes de
        # cache frio podia abrir ate 50 conexoes simultaneas contra a
        # Evolution — o teto inteiro do pool HTTP compartilhado
        # (shared/http_client.py), disputando com outras chamadas
        # concorrentes (send_message, webhook) que usam o mesmo client.
        async with _FOTOS_CONCURRENCY:
            return await evolution_client.fetch_profile_picture_url_cached(connection.instance_name, session.phone)

    foto_tasks = [asyncio.ensure_future(_foto(s)) for s in sessions]
    done, pending = await asyncio.wait(foto_tasks, timeout=_FOTOS_BUDGET_SECONDS)
    if pending:
        logger.info(
            f"GET /sessoes: {len(pending)} busca(s) de foto ainda em andamento apos "
            f"{_FOTOS_BUDGET_SECONDS}s, devolvendo sem foto (cache aquece em background)"
        )
        # As pendentes continuam rodando pra aquecer o cache (ver docstring),
        # mas ninguem mais vai dar await nelas — sem isso, uma excecao aqui
        # vira warning barulhento de "Task exception was never retrieved"
        # nos logs sem afetar nada de fato (ja tratado como best-effort
        # dentro de fetch_profile_picture_url).
        for task in pending:
            task.add_done_callback(lambda t: t.exception())

    def _resultado(task: "asyncio.Future[str | None]") -> str | None:
        if task not in done:
            return None
        try:
            return task.result()
        except Exception:
            return None

    fotos = [_resultado(t) for t in foto_tasks]

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

    # pushName no payload da Evolution e o nome de quem enviou a mensagem —
    # numa mensagem "attendant" (fromMe=true) isso e o nome do proprio
    # dispositivo conectado, nao do contato. So confia nisso pra preencher
    # contact_name quando quem mandou foi o cliente.
    if role != "user":
        contact_name = None

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


async def autoresponder(session: ChatSession, connection: Connection, message: Message, db: DbSession) -> Message | None:
    """Chamado pelo webhook logo apos gravar uma mensagem de cliente.
    Consulta o ai-service (que decide, via faq_enabled do tenant, se deve
    responder) e, se vier uma resposta, envia via Evolution e grava como
    mensagem do atendente — mesmo caminho de `responder()`, so que
    disparado automaticamente em vez de por um humano. Se o ai-service nao
    responder (desligado, sem chave, fora do ar), nao faz nada: o
    atendimento segue manual por humano, como hoje."""
    history_rows = (
        db.query(Message)
        .filter(Message.session_id == session.id, Message.id != message.id)
        .order_by(Message.created_at.desc())
        .limit(10)
        .all()
    )
    history = [
        {"role": "assistant" if m.role == "attendant" else "user", "content": m.content}
        for m in reversed(history_rows)
    ]

    reply = await ai_client.get_ai_reply(connection.tenant_id, history, message.content)
    if not reply:
        return None

    return await responder(session.id, connection.tenant_id, reply, db)


# Orcamento total pro loop de chats dentro de import_history. Cada chat
# processado faz pelo menos 1 chamada a Evolution (find_messages, ate 5
# paginas — ver find_messages), entao uma conta com muito historico podia
# fazer isso somar bem mais que os 5s de timeout de uma unica chamada
# (_ENRICHMENT_TIMEOUT), levando GET /connections a estourar timeout no
# gateway (visto em producao: p95/p99 de 15s e uma onda de 5xx). Com esse
# orcamento, o loop para de processar NOVOS chats apos esse tempo (o que ja
# foi processado ate ali e commitado normalmente) — o resto continua na
# proxima chamada de GET /connections (respeitando o cooldown de resync em
# connections/service.py), mesmo espirito do _FOTOS_BUDGET_SECONDS em
# list_sessoes.
_IMPORT_HISTORY_BUDGET_SECONDS = 8.0


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

    try:
        contacts_map = evolution_client.build_contact_name_map(
            await evolution_client.find_contacts(connection.instance_name)
        )
    except Exception:
        logger.exception(f"Falha ao importar contatos da instancia {connection.instance_name}")
        contacts_map = {}

    imported_messages = 0
    started_at = time.monotonic()
    chats_processed = 0
    try:
        for chat in chats[:chats_limit]:
            if time.monotonic() - started_at > _IMPORT_HISTORY_BUDGET_SECONDS:
                logger.info(
                    f"import_history: orcamento de {_IMPORT_HISTORY_BUDGET_SECONDS}s esgotado apos "
                    f"{chats_processed}/{len(chats)} chats da instancia {connection.instance_name} — "
                    f"resto continua no proximo resync"
                )
                break

            remote_jid = chat.get("remoteJid") or chat.get("id") or ""
            if not remote_jid or remote_jid.endswith("@g.us"):
                continue  # grupos ficam de fora nesta fase — so conversas 1:1, mesmo escopo do resto do atendimento

            phone = remote_jid.split("@")[0]
            # find_contacts (agenda) e a fonte mais confiavel de nome pra
            # historico — ver evolution_client.find_contacts. find_chats
            # normalmente nao traz pushName/name nenhum, entao chat.get(...)
            # quase sempre fica None; mantido so como fallback caso alguma
            # versao da Evolution devolva.
            contact_name = contacts_map.get(phone) or chat.get("pushName") or chat.get("name")
            session = _get_or_create_session_quiet(connection.tenant_id, connection.id, phone, contact_name, db)
            db.flush()  # garante id da Session persistido antes do insert de Message com FK

            try:
                messages = await evolution_client.find_messages(connection.instance_name, remote_jid, limit=messages_per_chat)
            except Exception:
                logger.exception(f"Falha ao importar mensagens do chat {remote_jid}")
                continue

            if not session.contact_name:
                # findChats normalmente NAO devolve pushName/name (isso vem
                # nos registros de mensagem, nao no chat) — sem isso o nome
                # do contato nunca era preenchido na importacao e a lista
                # ficava so com numero de telefone. Usa o pushName da
                # primeira mensagem recebida do proprio contato (fromMe=false)
                # como fallback.
                for raw in messages:
                    raw_fields = evolution_client.extract_message_fields(raw if isinstance(raw, dict) else {})
                    if raw_fields["role"] == "user" and raw_fields["contact_name"]:
                        session.contact_name = raw_fields["contact_name"]
                        break

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
            chats_processed += 1

        db.commit()
    except Exception:
        # Erro de banco (conexao caiu, etc.) durante o import nao pode
        # derrubar o GET /connections inteiro — reflete o mesmo "best-effort"
        # ja documentado acima, que ate aqui so cobria as chamadas a
        # Evolution, nao a escrita no banco.
        db.rollback()
        logger.exception(f"Falha ao persistir historico importado da instancia {connection.instance_name}")
        return

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

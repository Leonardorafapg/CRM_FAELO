"""Regras de negocio de Connection. Chamadas a Evolution API ficam em
app.evolution.client — aqui so orquestra + persiste. Tudo escopado por
tenant_id vindo do JWT."""
import os
import time
import uuid

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as DbSession

from app.connections.models import Connection
from app.evolution import client as evolution_client
from shared.logging_config import get_logger

logger = get_logger("whatsapp-service")

# Limite fixo por tenant nesta fase — sem plano/config por tenant ainda, so
# um numero fixo pra todo mundo (ver conversa que definiu isso). Se virar
# variavel por plano no futuro, isso migra pra um campo em Tenant
# (platform-service) consultado aqui.
MAX_CONNECTIONS_PER_TENANT = 1

# Cooldown do reimport de historico (ver list_connections abaixo): sem isso,
# import_history (que varre ate 200 chats x ate 5 paginas de mensagens cada)
# rodava por INTEIRO a cada carregamento/poll da tela de Conexoes — rapido
# logo depois de conectar (pouco historico), mas ficava cada vez mais lento
# conforme a conta acumulava conversas reais, ate estourar o timeout do
# proprio gateway pra este servico (502). Cache em memoria simples (mesmo
# espirito do _foto_cache em evolution/client.py): no maximo 1 reimport
# completo por conexao a cada 60s, nao a cada request.
_last_resync: dict[str, float] = {}
_RESYNC_COOLDOWN_SECONDS = 60


def _new_id() -> str:
    return str(uuid.uuid4())


async def list_connections(tenant_id: str, db: DbSession) -> list[Connection]:
    """Toda chamada (ou seja, todo carregamento da tela de Conexoes/login)
    reconcilia com a Evolution: conexoes ainda nao conectadas tem o status
    atualizado, e conexoes ja conectadas tem o historico reimportado (no
    maximo 1x a cada _RESYNC_COOLDOWN_SECONDS, ver acima) — sem isso o
    usuario so pegava o historico uma vez, na transicao inicial pra
    "connected", e ficava sem jeito de puxar mensagens novas trocadas fora
    do app (ex.: direto no celular) sem excluir e recriar a conexao.

    Consultas ao banco rodam via run_in_threadpool: db.query/commit/refresh
    sao chamadas SINCRONAS (driver psycopg2) — sem isso, cada uma bloqueava
    a unica thread do event loop, travando TODAS as outras requisicoes
    concorrentes deste processo (inclusive o healthcheck) enquanto essa
    rodava, o que e o suspeito mais provavel do crash-loop em producao
    (Railway achando o processo travado e reiniciando)."""
    connections = await run_in_threadpool(
        lambda: db.query(Connection).filter(Connection.tenant_id == tenant_id).order_by(Connection.created_at).all()
    )
    for connection in connections:
        if connection.status == "connected":
            last = _last_resync.get(connection.id, 0.0)
            if time.monotonic() - last >= _RESYNC_COOLDOWN_SECONDS:
                from app.chat.service import import_history
                await import_history(connection, db)
                _last_resync[connection.id] = time.monotonic()
        else:
            await _refresh_status_from_evolution(connection, db)
    return connections


async def _refresh_status_from_evolution(connection: Connection, db: DbSession) -> None:
    """Consulta o estado real da instancia na Evolution e persiste a
    transicao — sem isso, o status ficava travado em "connecting" pra
    sempre (nada mais no codigo chamava get_instance_status/update_status).
    Chamado a cada GET /connections, que o frontend ja fica repetindo em
    polling enquanto o QR code nao e escaneado."""
    try:
        payload = await evolution_client.get_instance_status(connection.instance_name)
    except HTTPException:
        # Evolution fora do ar momentaneamente — nao derruba a listagem,
        # so mantem o status anterior ate a proxima tentativa.
        return

    state = evolution_client.extract_state(payload)
    just_connected = state == "open" and connection.status != "connected"

    if state == "open":
        connection.status = "connected"
    elif state in ("close", "closed"):
        connection.status = "disconnected"
    # qualquer outro valor (ex.: "connecting") mantem o status atual

    await run_in_threadpool(db.commit)
    await run_in_threadpool(db.refresh, connection)

    if just_connected:
        # Import local pra evitar ciclo: app.chat.service ja importa
        # get_connection_or_404 deste modulo.
        from app.chat.service import import_history
        await import_history(connection, db)


def get_connection_or_404(connection_id: str, tenant_id: str, db: DbSession) -> Connection:
    conn = db.query(Connection).filter(Connection.id == connection_id, Connection.tenant_id == tenant_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Conexao não encontrada")
    return conn


def _extract_qrcode(evolution_payload: dict) -> str | None:
    """O shape exato do QR code na resposta varia entre versoes da Evolution
    API (qrcode.base64, base64, code) — tenta os formatos mais comuns em vez
    de travar em um so."""
    qrcode = evolution_payload.get("qrcode") or {}
    if isinstance(qrcode, dict):
        return qrcode.get("base64") or qrcode.get("code")
    return evolution_payload.get("base64")


async def create_connection(tenant_id: str, db: DbSession, webhook_base_url: str) -> tuple[Connection, str | None]:
    existing = db.query(Connection).filter(Connection.tenant_id == tenant_id).count()
    if existing >= MAX_CONNECTIONS_PER_TENANT:
        raise HTTPException(
            status_code=400,
            detail=f"Limite de {MAX_CONNECTIONS_PER_TENANT} conexão(ões) por conta atingido. Exclua uma conexão existente antes de criar outra.",
        )

    instance_name = f"tenant-{tenant_id}-{uuid.uuid4().hex[:8]}"

    evolution_payload = await evolution_client.create_instance(instance_name)
    qrcode_base64 = _extract_qrcode(evolution_payload)

    connection = Connection(
        id=_new_id(),
        tenant_id=tenant_id,
        instance_name=instance_name,
        status="connecting",
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)

    await evolution_client.set_webhook(instance_name, f"{webhook_base_url}/webhook/evolution")

    logger.info(f"Conexao criada: tenant={tenant_id} instance={instance_name}")
    return connection, qrcode_base64


async def delete_connection(connection_id: str, tenant_id: str, db: DbSession) -> None:
    connection = get_connection_or_404(connection_id, tenant_id, db)
    await evolution_client.delete_instance(connection.instance_name)
    db.delete(connection)
    db.commit()
    _last_resync.pop(connection_id, None)
    logger.info(f"Conexao removida: tenant={tenant_id} instance={connection.instance_name}")


def get_connection_by_instance(instance_name: str, db: DbSession) -> Connection | None:
    return db.query(Connection).filter(Connection.instance_name == instance_name).first()


def update_status(connection: Connection, status: str, phone: str | None, db: DbSession) -> Connection:
    connection.status = status
    if phone:
        connection.phone = phone
    db.commit()
    db.refresh(connection)
    return connection

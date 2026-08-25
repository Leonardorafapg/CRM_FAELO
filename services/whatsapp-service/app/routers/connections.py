"""Rotas de Connection — so parsing/roteamento HTTP. Regra de negocio em
app/connections/service.py. CRUD de conexao e config, nao operacional —
restrito a owner/admin (require_admin)."""
import os

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.connections import service
from app.connections.schemas import ConnectionOut, ConnectionCreateResponse
from shared.auth_deps import get_current_user
from shared.policy import require_admin

router = APIRouter(prefix="/connections", tags=["connections"])


def _webhook_base_url(request: Request) -> str:
    """URL publica deste proprio servico, usada pra configurar o webhook na
    Evolution API. Usa a env var se configurada (producao, atras de proxy);
    senao deriva da propria requisicao (dev local)."""
    configured = os.getenv("WEBHOOK_BASE_URL")
    if configured:
        return configured.rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("", response_model=list[ConnectionOut])
async def list_connections(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await service.list_connections(current_user["tenant_id"], db)


@router.post("", response_model=ConnectionCreateResponse)
async def create_connection(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    connection, qrcode_base64 = await service.create_connection(
        current_user["tenant_id"], db, _webhook_base_url(request)
    )
    return {"connection": connection, "qrcode_base64": qrcode_base64}


@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    await service.delete_connection(connection_id, current_user["tenant_id"], db)
    return {"ok": True}

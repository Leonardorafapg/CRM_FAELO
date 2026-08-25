"""Rotas de Sessao/Mensagem (atendimento) — so parsing/roteamento HTTP.
Regra de negocio em app/chat/service.py. Qualquer usuario logado do tenant
pode ver/responder (nao restrito a admin — atendimento e operacional)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.chat import service
from app.chat.schemas import SessionOut, MessageOut, ResponderBody
from app.ws.registry import broadcast
from shared.auth_deps import get_current_user

router = APIRouter(tags=["chat"])


@router.get("/sessoes", response_model=list[SessionOut])
def list_sessoes(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return service.list_sessoes(current_user["tenant_id"], db, limit=limit, offset=offset)


@router.get("/chat/{session_id}/mensagens", response_model=list[MessageOut])
def list_mensagens(
    session_id: str,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return service.list_mensagens(session_id, current_user["tenant_id"], db, limit=limit, offset=offset)


@router.post("/chat/{session_id}/responder", response_model=MessageOut)
async def responder(
    session_id: str,
    body: ResponderBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    message = await service.responder(session_id, current_user["tenant_id"], body.content, db)
    await broadcast(current_user["tenant_id"], {
        "type": "message",
        "session_id": session_id,
        "message": MessageOut.model_validate(message).model_dump(mode="json"),
    })
    return message


@router.patch("/chat/{session_id}/encerrar", response_model=SessionOut)
def encerrar(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return service.encerrar_atendimento(session_id, current_user["tenant_id"], db)

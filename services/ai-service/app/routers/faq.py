"""Rotas de FaqItem — so parsing/roteamento HTTP. Regra de negocio em
app/faq/service.py. tenant_id sempre vem do JWT (current_user), nunca de
path — diferente do legado (que aceitava tenant_id no path), pra seguir a
convencao deste projeto (nao existe rota que aceite tenant_id como
parametro, ver app/routers/stages.py do crm-service). Escrita restrita a
owner/admin (e config, nao operacional)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.faq import service
from app.faq.schemas import FaqItemOut, FaqItemCreate, FaqItemUpdate, FaqItemList
from shared.auth_deps import get_current_user
from shared.policy import require_admin

router = APIRouter(prefix="/ai/faq", tags=["faq"])


@router.get("", response_model=FaqItemList)
def list_faq(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    q: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return service.list_faq(current_user["tenant_id"], db, page=page, limit=limit, q=q)


@router.post("", response_model=FaqItemOut)
def create_faq(
    body: FaqItemCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    return service.create_faq(current_user["tenant_id"], body, db)


@router.patch("/{faq_id}", response_model=FaqItemOut)
def update_faq(
    faq_id: str,
    body: FaqItemUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    return service.update_faq(faq_id, current_user["tenant_id"], body, db)


@router.delete("/{faq_id}")
def delete_faq(
    faq_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    service.delete_faq(faq_id, current_user["tenant_id"], db)
    return {"ok": True}

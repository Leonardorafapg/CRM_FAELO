"""Rotas de ContactStatus — so parsing/roteamento HTTP. Regra de negocio em
app/contacts/service.py."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.contacts import service
from app.contacts.schemas import ContactStatusCreate, ContactStatusUpdate
from shared.auth_deps import get_current_user
from shared.policy import require_admin

router = APIRouter(prefix="/contact-statuses", tags=["contact-statuses"])


def _serialize(s) -> dict:
    return {"id": s.id, "name": s.name, "active": s.active, "order": s.order}


@router.get("")
def list_statuses(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    statuses = service.list_statuses(current_user["tenant_id"], db)
    return [_serialize(s) for s in statuses]


@router.post("")
def create_status(
    body: ContactStatusCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    status = service.create_status(current_user["tenant_id"], body, db)
    return _serialize(status)


@router.patch("/{status_id}")
def update_status(
    status_id: str,
    body: ContactStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    status = service.update_status(status_id, current_user["tenant_id"], body, db)
    return _serialize(status)


@router.delete("/{status_id}")
def delete_status(
    status_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    service.delete_status(status_id, current_user["tenant_id"], db)
    return {"ok": True}

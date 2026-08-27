"""Rotas de Contact — so parsing/roteamento HTTP. Regra de negocio em
app/contacts/service.py. CRUD completo aberto a qualquer usuario logado do
tenant (inclusive attendant) — e trabalho operacional, nao configuracao
(diferente de stages/status, restritos a admin)."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.contacts import service
from app.contacts.schemas import ContactCreate, ContactUpdate
from shared.auth_deps import get_current_user

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _serialize(c) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "email": c.email,
        "source": c.source,
        "tags": c.tags,
        "status_id": c.status_id,
        "assigned_to": c.assigned_to,
        "stage_id": c.stage_id,
        "created_at": c.created_at,
    }


@router.get("")
def list_contacts(
    stage_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """`?stage_id=...` filtra por coluna do Kanban — usado pela tela de
    Kanban pra carregar uma coluna por vez em vez do tenant inteiro."""
    contacts = service.list_contacts(current_user["tenant_id"], db, stage_id=stage_id)
    return [_serialize(c) for c in contacts]


@router.post("")
def create_contact(
    body: ContactCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    contact = service.create_contact(current_user["tenant_id"], body, db)
    return _serialize(contact)


@router.get("/{contact_id}")
def get_contact(contact_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return _serialize(service.get_contact_or_404(contact_id, current_user["tenant_id"], db))


@router.patch("/{contact_id}")
def update_contact(
    contact_id: str,
    body: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Cobre tanto edicao de dado (nome/telefone/etc.) quanto mover no
    Kanban (stage_id) e mudar situacao (status_id) — mesmo endpoint, so um
    PATCH generico (ver docstring de ContactUpdate)."""
    contact = service.update_contact(contact_id, current_user["tenant_id"], body, db)
    return _serialize(contact)


@router.delete("/{contact_id}")
def delete_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    service.delete_contact(contact_id, current_user["tenant_id"], db)
    return {"ok": True}

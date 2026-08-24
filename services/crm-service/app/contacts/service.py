"""Regras de negocio de Contact/ContactStatus — acesso a banco e decisoes
de dominio, sem nada de HTTP. Todo acesso e sempre escopado por tenant_id
(vem do JWT, nunca de path/query)."""
import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.contacts.models import Contact, ContactStatus
from app.contacts.schemas import ContactCreate, ContactUpdate, ContactStatusCreate, ContactStatusUpdate
from app.pipeline.service import get_stage_or_404


def _new_id() -> str:
    return str(uuid.uuid4())


# --- ContactStatus ---

def list_statuses(tenant_id: str, db: Session) -> list[ContactStatus]:
    return db.query(ContactStatus).filter(ContactStatus.tenant_id == tenant_id).order_by(ContactStatus.order).all()


def get_status_or_404(status_id: str, tenant_id: str, db: Session) -> ContactStatus:
    status = db.query(ContactStatus).filter(ContactStatus.id == status_id, ContactStatus.tenant_id == tenant_id).first()
    if not status:
        raise HTTPException(status_code=404, detail="Status não encontrado")
    return status


def create_status(tenant_id: str, body: ContactStatusCreate, db: Session) -> ContactStatus:
    max_order = db.query(ContactStatus).filter(ContactStatus.tenant_id == tenant_id).count()
    status = ContactStatus(id=_new_id(), tenant_id=tenant_id, name=body.name, order=max_order)
    db.add(status)
    db.commit()
    db.refresh(status)
    return status


def update_status(status_id: str, tenant_id: str, body: ContactStatusUpdate, db: Session) -> ContactStatus:
    status = get_status_or_404(status_id, tenant_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(status, field, value)
    db.commit()
    return status


def delete_status(status_id: str, tenant_id: str, db: Session) -> None:
    status = get_status_or_404(status_id, tenant_id, db)
    db.delete(status)
    db.commit()


# --- Contact ---

def list_contacts(tenant_id: str, db: Session, stage_id: str | None = None) -> list[Contact]:
    """`stage_id` opcional filtra por coluna do Kanban — e assim que a tela
    de Kanban busca "os contacts dessa coluna", sem precisar carregar o
    tenant inteiro de uma vez."""
    query = db.query(Contact).filter(Contact.tenant_id == tenant_id)
    if stage_id is not None:
        query = query.filter(Contact.stage_id == stage_id)
    return query.order_by(Contact.created_at.desc()).all()


def get_contact_or_404(contact_id: str, tenant_id: str, db: Session) -> Contact:
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.tenant_id == tenant_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact não encontrado")
    return contact


def _validate_references(tenant_id: str, status_id: str | None, stage_id: str | None, db: Session) -> None:
    """status_id/stage_id, se informados, precisam pertencer ao MESMO
    tenant — sem essa checagem seria possivel um contact apontar pra uma
    stage/status de outro tenant so adivinhando o id."""
    if status_id is not None:
        get_status_or_404(status_id, tenant_id, db)
    if stage_id is not None:
        get_stage_or_404(stage_id, tenant_id, db)


def create_contact(tenant_id: str, body: ContactCreate, db: Session) -> Contact:
    _validate_references(tenant_id, body.status_id, body.stage_id, db)

    contact = Contact(
        id=_new_id(),
        tenant_id=tenant_id,
        name=body.name,
        phone=body.phone,
        email=body.email,
        source=body.source,
        tags=body.tags,
        status_id=body.status_id,
        assigned_to=body.assigned_to,
        stage_id=body.stage_id,
    )
    db.add(contact)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe um contact com esse telefone")
    db.refresh(contact)
    return contact


def update_contact(contact_id: str, tenant_id: str, body: ContactUpdate, db: Session) -> Contact:
    contact = get_contact_or_404(contact_id, tenant_id, db)
    data = body.model_dump(exclude_unset=True)

    _validate_references(tenant_id, data.get("status_id"), data.get("stage_id"), db)

    for field, value in data.items():
        setattr(contact, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe um contact com esse telefone")
    return contact


def delete_contact(contact_id: str, tenant_id: str, db: Session) -> None:
    contact = get_contact_or_404(contact_id, tenant_id, db)
    db.delete(contact)
    db.commit()

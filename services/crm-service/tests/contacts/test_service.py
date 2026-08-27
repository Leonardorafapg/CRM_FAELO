"""Unit tests de app/contacts/service.py."""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.contacts import service
from app.contacts.schemas import ContactCreate, ContactUpdate, ContactStatusCreate
from app.stages import service as stages_service
from app.stages.schemas import StageCreate


def _tenant() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


def test_create_contact(db: Session):
    tenant = _tenant()
    contact = service.create_contact(tenant, ContactCreate(name="Carlos", phone="11999999999"), db)
    assert contact.tenant_id == tenant
    assert contact.tags == []


def test_create_contact_com_telefone_duplicado_levanta_400(db: Session):
    tenant = _tenant()
    service.create_contact(tenant, ContactCreate(name="Carlos", phone="11999999999"), db)
    with pytest.raises(HTTPException) as exc:
        service.create_contact(tenant, ContactCreate(name="Outro", phone="11999999999"), db)
    assert exc.value.status_code == 400


def test_create_contact_mesmo_telefone_em_tenants_diferentes_e_permitido(db: Session):
    tenant_a, tenant_b = _tenant(), _tenant()
    service.create_contact(tenant_a, ContactCreate(name="Carlos", phone="11999999999"), db)
    # Nao levanta excecao — unicidade e por (tenant_id, phone), nao so phone.
    contact_b = service.create_contact(tenant_b, ContactCreate(name="Carlos", phone="11999999999"), db)
    assert contact_b.tenant_id == tenant_b


def test_create_contact_com_status_de_outro_tenant_levanta_404(db: Session):
    tenant_a, tenant_b = _tenant(), _tenant()
    status = service.create_status(tenant_a, ContactStatusCreate(name="Ativo"), db)
    with pytest.raises(HTTPException) as exc:
        service.create_contact(tenant_b, ContactCreate(name="X", phone="123", status_id=status.id), db)
    assert exc.value.status_code == 404


def test_create_contact_com_stage_de_outro_tenant_levanta_404(db: Session):
    tenant_a, tenant_b = _tenant(), _tenant()
    stage = stages_service.create_stage(tenant_a, StageCreate(name="Entrada"), db)
    with pytest.raises(HTTPException) as exc:
        service.create_contact(tenant_b, ContactCreate(name="X", phone="123", stage_id=stage.id), db)
    assert exc.value.status_code == 404


def test_get_contact_or_404_de_outro_tenant_levanta_404(db: Session):
    tenant_a, tenant_b = _tenant(), _tenant()
    contact = service.create_contact(tenant_a, ContactCreate(name="Carlos", phone="11999999999"), db)
    with pytest.raises(HTTPException) as exc:
        service.get_contact_or_404(contact.id, tenant_b, db)
    assert exc.value.status_code == 404


def test_update_contact_move_de_stage(db: Session):
    tenant = _tenant()
    stage_a = stages_service.create_stage(tenant, StageCreate(name="Entrada"), db)
    stage_b = stages_service.create_stage(tenant, StageCreate(name="Proposta"), db)
    contact = service.create_contact(tenant, ContactCreate(name="Carlos", phone="11999999999", stage_id=stage_a.id), db)

    updated = service.update_contact(contact.id, tenant, ContactUpdate(stage_id=stage_b.id), db)
    assert updated.stage_id == stage_b.id


def test_update_contact_para_telefone_ja_usado_levanta_400(db: Session):
    tenant = _tenant()
    service.create_contact(tenant, ContactCreate(name="Carlos", phone="11111111111"), db)
    contact_2 = service.create_contact(tenant, ContactCreate(name="Outro", phone="22222222222"), db)

    with pytest.raises(HTTPException) as exc:
        service.update_contact(contact_2.id, tenant, ContactUpdate(phone="11111111111"), db)
    assert exc.value.status_code == 400


def test_delete_contact(db: Session):
    tenant = _tenant()
    contact = service.create_contact(tenant, ContactCreate(name="Carlos", phone="11999999999"), db)
    service.delete_contact(contact.id, tenant, db)
    with pytest.raises(HTTPException):
        service.get_contact_or_404(contact.id, tenant, db)


def test_list_contacts_filtra_por_stage(db: Session):
    tenant = _tenant()
    stage_a = stages_service.create_stage(tenant, StageCreate(name="Entrada"), db)
    stage_b = stages_service.create_stage(tenant, StageCreate(name="Proposta"), db)
    service.create_contact(tenant, ContactCreate(name="A", phone="1", stage_id=stage_a.id), db)
    service.create_contact(tenant, ContactCreate(name="B", phone="2", stage_id=stage_b.id), db)

    result = service.list_contacts(tenant, db, stage_id=stage_a.id)
    assert len(result) == 1
    assert result[0].name == "A"

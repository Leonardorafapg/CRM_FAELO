"""Unit tests de app/stages/service.py."""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.stages import service
from app.stages.schemas import StageCreate, StageUpdate


def _tenant() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


def test_create_stage_entra_no_final_da_ordem(db: Session):
    tenant = _tenant()
    s1 = service.create_stage(tenant, StageCreate(name="Entrada"), db)
    s2 = service.create_stage(tenant, StageCreate(name="Proposta"), db)
    assert s1.order == 0
    assert s2.order == 1


def test_create_stage_entry_desmarca_a_anterior(db: Session):
    tenant = _tenant()
    s1 = service.create_stage(tenant, StageCreate(name="Entrada", is_entry=True), db)
    s2 = service.create_stage(tenant, StageCreate(name="Outra Entrada", is_entry=True), db)
    db.refresh(s1)
    assert s1.is_entry is False
    assert s2.is_entry is True


def test_get_stage_or_404_de_outro_tenant_levanta_404(db: Session):
    tenant_a = _tenant()
    tenant_b = _tenant()
    stage = service.create_stage(tenant_a, StageCreate(name="Entrada"), db)
    with pytest.raises(HTTPException) as exc:
        service.get_stage_or_404(stage.id, tenant_b, db)
    assert exc.value.status_code == 404


def test_list_stages_escopado_por_tenant(db: Session):
    tenant_a, tenant_b = _tenant(), _tenant()
    service.create_stage(tenant_a, StageCreate(name="Entrada"), db)
    service.create_stage(tenant_b, StageCreate(name="Outra"), db)
    result = service.list_stages(tenant_a, db)
    assert len(result) == 1
    assert result[0].name == "Entrada"


def test_update_stage_muda_ordem(db: Session):
    tenant = _tenant()
    stage = service.create_stage(tenant, StageCreate(name="Entrada"), db)
    updated = service.update_stage(stage.id, tenant, StageUpdate(order=5), db)
    assert updated.order == 5


def test_delete_stage(db: Session):
    tenant = _tenant()
    stage = service.create_stage(tenant, StageCreate(name="Entrada"), db)
    service.delete_stage(stage.id, tenant, db)
    with pytest.raises(HTTPException):
        service.get_stage_or_404(stage.id, tenant, db)

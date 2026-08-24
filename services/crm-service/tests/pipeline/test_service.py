"""Unit tests de app/pipeline/service.py."""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.pipeline import service
from app.pipeline.schemas import PipelineCreate, PipelineUpdate, StageCreate, StageUpdate


def _tenant() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


# --- Pipeline ---

def test_create_pipeline(db: Session):
    tenant = _tenant()
    pipeline = service.create_pipeline(tenant, PipelineCreate(name="Vendas"), db)
    assert pipeline.tenant_id == tenant
    assert pipeline.active is True


def test_create_pipeline_default_desmarca_o_anterior(db: Session):
    tenant = _tenant()
    p1 = service.create_pipeline(tenant, PipelineCreate(name="Vendas", is_default=True), db)
    p2 = service.create_pipeline(tenant, PipelineCreate(name="Suporte", is_default=True), db)
    db.refresh(p1)
    assert p1.is_default is False
    assert p2.is_default is True


def test_get_pipeline_or_404_de_outro_tenant_levanta_404(db: Session):
    tenant_a = _tenant()
    tenant_b = _tenant()
    pipeline = service.create_pipeline(tenant_a, PipelineCreate(name="Vendas"), db)
    with pytest.raises(HTTPException) as exc:
        service.get_pipeline_or_404(pipeline.id, tenant_b, db)
    assert exc.value.status_code == 404


def test_update_pipeline_muda_campo(db: Session):
    tenant = _tenant()
    pipeline = service.create_pipeline(tenant, PipelineCreate(name="Vendas"), db)
    updated = service.update_pipeline(pipeline.id, tenant, PipelineUpdate(name="Vendas B2B"), db)
    assert updated.name == "Vendas B2B"


def test_delete_pipeline(db: Session):
    tenant = _tenant()
    pipeline = service.create_pipeline(tenant, PipelineCreate(name="Vendas"), db)
    service.delete_pipeline(pipeline.id, tenant, db)
    with pytest.raises(HTTPException):
        service.get_pipeline_or_404(pipeline.id, tenant, db)


# --- Stage ---

def test_create_stage_entra_no_final_da_ordem(db: Session):
    tenant = _tenant()
    pipeline = service.create_pipeline(tenant, PipelineCreate(name="Vendas"), db)
    s1 = service.create_stage(pipeline.id, tenant, StageCreate(name="Entrada"), db)
    s2 = service.create_stage(pipeline.id, tenant, StageCreate(name="Proposta"), db)
    assert s1.order == 0
    assert s2.order == 1


def test_create_stage_entry_desmarca_a_anterior(db: Session):
    tenant = _tenant()
    pipeline = service.create_pipeline(tenant, PipelineCreate(name="Vendas"), db)
    s1 = service.create_stage(pipeline.id, tenant, StageCreate(name="Entrada", is_entry=True), db)
    s2 = service.create_stage(pipeline.id, tenant, StageCreate(name="Outra Entrada", is_entry=True), db)
    db.refresh(s1)
    assert s1.is_entry is False
    assert s2.is_entry is True


def test_create_stage_em_pipeline_de_outro_tenant_levanta_404(db: Session):
    tenant_a = _tenant()
    tenant_b = _tenant()
    pipeline = service.create_pipeline(tenant_a, PipelineCreate(name="Vendas"), db)
    with pytest.raises(HTTPException) as exc:
        service.create_stage(pipeline.id, tenant_b, StageCreate(name="Entrada"), db)
    assert exc.value.status_code == 404


def test_get_stage_or_404_de_outro_tenant_levanta_404(db: Session):
    tenant_a = _tenant()
    tenant_b = _tenant()
    pipeline = service.create_pipeline(tenant_a, PipelineCreate(name="Vendas"), db)
    stage = service.create_stage(pipeline.id, tenant_a, StageCreate(name="Entrada"), db)
    with pytest.raises(HTTPException) as exc:
        service.get_stage_or_404(stage.id, tenant_b, db)
    assert exc.value.status_code == 404


def test_update_stage_muda_ordem(db: Session):
    tenant = _tenant()
    pipeline = service.create_pipeline(tenant, PipelineCreate(name="Vendas"), db)
    stage = service.create_stage(pipeline.id, tenant, StageCreate(name="Entrada"), db)
    updated = service.update_stage(stage.id, tenant, StageUpdate(order=5), db)
    assert updated.order == 5


def test_delete_stage(db: Session):
    tenant = _tenant()
    pipeline = service.create_pipeline(tenant, PipelineCreate(name="Vendas"), db)
    stage = service.create_stage(pipeline.id, tenant, StageCreate(name="Entrada"), db)
    service.delete_stage(stage.id, tenant, db)
    with pytest.raises(HTTPException):
        service.get_stage_or_404(stage.id, tenant, db)

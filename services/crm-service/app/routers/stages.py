"""Rotas de Stage — so parsing/roteamento HTTP. Regra de negocio em
app/pipeline/service.py."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.pipeline import service
from app.pipeline.schemas import StageCreate, StageUpdate
from shared.auth_deps import get_current_user
from shared.policy import require_admin

# Nao tem prefix proprio: /pipelines/{id}/stages (list/create) fica no
# mesmo router de pipelines por semantica de URL, mas a logica mora aqui.
# PATCH/DELETE de uma stage especifica usam /stages/{id} direto (nao
# precisam do pipeline_id no path pra identificar o recurso).
router = APIRouter(tags=["stages"])


def _serialize(s) -> dict:
    return {
        "id": s.id,
        "pipeline_id": s.pipeline_id,
        "name": s.name,
        "order": s.order,
        "color": s.color,
        "active": s.active,
        "is_entry": s.is_entry,
    }


@router.get("/pipelines/{pipeline_id}/stages")
def list_stages(pipeline_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    stages = service.list_stages(pipeline_id, current_user["tenant_id"], db)
    return [_serialize(s) for s in stages]


@router.post("/pipelines/{pipeline_id}/stages")
def create_stage(
    pipeline_id: str,
    body: StageCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    stage = service.create_stage(pipeline_id, current_user["tenant_id"], body, db)
    return _serialize(stage)


@router.patch("/stages/{stage_id}")
def update_stage(
    stage_id: str,
    body: StageUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    stage = service.update_stage(stage_id, current_user["tenant_id"], body, db)
    return _serialize(stage)


@router.delete("/stages/{stage_id}")
def delete_stage(
    stage_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    service.delete_stage(stage_id, current_user["tenant_id"], db)
    return {"ok": True}

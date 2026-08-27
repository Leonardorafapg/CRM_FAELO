"""Rotas de Stage — so parsing/roteamento HTTP. Regra de negocio em
app/stages/service.py. Quadro unico e fixo por tenant (sem multi-pipeline):
Stage e um recurso direto do tenant, sem aninhamento em nenhum path pai."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.stages import service
from app.stages.schemas import StageCreate, StageUpdate
from shared.auth_deps import get_current_user
from shared.policy import require_admin

router = APIRouter(prefix="/stages", tags=["stages"])


def _serialize(s) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "order": s.order,
        "color": s.color,
        "active": s.active,
        "is_entry": s.is_entry,
    }


@router.get("")
def list_stages(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    stages = service.list_stages(current_user["tenant_id"], db)
    return [_serialize(s) for s in stages]


@router.post("")
def create_stage(
    body: StageCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    stage = service.create_stage(current_user["tenant_id"], body, db)
    return _serialize(stage)


@router.patch("/{stage_id}")
def update_stage(
    stage_id: str,
    body: StageUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    stage = service.update_stage(stage_id, current_user["tenant_id"], body, db)
    return _serialize(stage)


@router.delete("/{stage_id}")
def delete_stage(
    stage_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    service.delete_stage(stage_id, current_user["tenant_id"], db)
    return {"ok": True}

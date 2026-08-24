"""Rotas de Pipeline — so parsing/roteamento HTTP. Regra de negocio em
app/pipeline/service.py. tenant_id sempre vem do JWT (current_user), nunca
de path/query — nao existe rota que aceite tenant_id como parametro aqui."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.pipeline import service
from app.pipeline.schemas import PipelineCreate, PipelineUpdate
from shared.auth_deps import get_current_user
from shared.policy import require_admin

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def _serialize(p) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "active": p.active,
        "is_default": p.is_default,
    }


@router.get("")
def list_pipelines(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    pipelines = service.list_pipelines(current_user["tenant_id"], db)
    return [_serialize(p) for p in pipelines]


@router.post("")
def create_pipeline(
    body: PipelineCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    pipeline = service.create_pipeline(current_user["tenant_id"], body, db)
    return _serialize(pipeline)


@router.get("/{pipeline_id}")
def get_pipeline(pipeline_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return _serialize(service.get_pipeline_or_404(pipeline_id, current_user["tenant_id"], db))


@router.patch("/{pipeline_id}")
def update_pipeline(
    pipeline_id: str,
    body: PipelineUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    pipeline = service.update_pipeline(pipeline_id, current_user["tenant_id"], body, db)
    return _serialize(pipeline)


@router.delete("/{pipeline_id}")
def delete_pipeline(
    pipeline_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    service.delete_pipeline(pipeline_id, current_user["tenant_id"], db)
    return {"ok": True}

"""Regras de negocio de Stage (coluna do quadro) — acesso a banco e decisoes
de dominio, sem nada de HTTP. Todo acesso e sempre escopado por tenant_id
(vem do JWT do usuario logado, nunca de path/query) — nao existe leitura
cross-tenant aqui. Quadro unico e fixo por tenant (sem multi-pipeline)."""
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.stages.models import Stage
from app.stages.schemas import StageCreate, StageUpdate


def _new_id() -> str:
    return str(uuid.uuid4())


def list_stages(tenant_id: str, db: Session) -> list[Stage]:
    return db.query(Stage).filter(Stage.tenant_id == tenant_id).order_by(Stage.order).all()


def get_stage_or_404(stage_id: str, tenant_id: str, db: Session) -> Stage:
    stage = db.query(Stage).filter(Stage.id == stage_id, Stage.tenant_id == tenant_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage não encontrada")
    return stage


def create_stage(tenant_id: str, body: StageCreate, db: Session) -> Stage:
    if body.is_entry:
        _clear_entry_stage(tenant_id, db)

    max_order = db.query(Stage).filter(Stage.tenant_id == tenant_id).count()
    stage = Stage(
        id=_new_id(),
        tenant_id=tenant_id,
        name=body.name,
        order=max_order,  # entra no final da lista de colunas
        color=body.color,
        is_entry=body.is_entry,
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage


def update_stage(stage_id: str, tenant_id: str, body: StageUpdate, db: Session) -> Stage:
    stage = get_stage_or_404(stage_id, tenant_id, db)
    data = body.model_dump(exclude_unset=True)

    if data.get("is_entry") is True:
        _clear_entry_stage(tenant_id, db)

    for field, value in data.items():
        setattr(stage, field, value)
    db.commit()
    return stage


def delete_stage(stage_id: str, tenant_id: str, db: Session) -> None:
    stage = get_stage_or_404(stage_id, tenant_id, db)
    db.delete(stage)
    db.commit()


def _clear_entry_stage(tenant_id: str, db: Session) -> None:
    """No maximo 1 stage de entrada por tenant."""
    db.query(Stage).filter(Stage.tenant_id == tenant_id, Stage.is_entry == True).update({"is_entry": False})  # noqa: E712

"""Regras de negocio de Pipeline/Stage — acesso a banco e decisoes de
dominio, sem nada de HTTP. Todo acesso e sempre escopado por tenant_id (vem
do JWT do usuario logado, nunca de path/query) — nao existe leitura
cross-tenant aqui."""
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.pipeline.models import Pipeline, Stage
from app.pipeline.schemas import PipelineCreate, PipelineUpdate, StageCreate, StageUpdate


def _new_id() -> str:
    return str(uuid.uuid4())


# --- Pipeline ---

def list_pipelines(tenant_id: str, db: Session) -> list[Pipeline]:
    return db.query(Pipeline).filter(Pipeline.tenant_id == tenant_id).order_by(Pipeline.created_at).all()


def get_pipeline_or_404(pipeline_id: str, tenant_id: str, db: Session) -> Pipeline:
    """Filtra por tenant_id na propria query — um pipeline de outro tenant
    nunca aparece nem como 404 diferenciavel de "nao existe", evita
    enumeracao de ids entre tenants."""
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline não encontrado")
    return pipeline


def create_pipeline(tenant_id: str, body: PipelineCreate, db: Session) -> Pipeline:
    if body.is_default:
        _clear_default_pipeline(tenant_id, db)

    pipeline = Pipeline(
        id=_new_id(),
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        is_default=body.is_default,
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return pipeline


def update_pipeline(pipeline_id: str, tenant_id: str, body: PipelineUpdate, db: Session) -> Pipeline:
    pipeline = get_pipeline_or_404(pipeline_id, tenant_id, db)
    data = body.model_dump(exclude_unset=True)

    if data.get("is_default") is True:
        _clear_default_pipeline(tenant_id, db)

    for field, value in data.items():
        setattr(pipeline, field, value)
    db.commit()
    return pipeline


def delete_pipeline(pipeline_id: str, tenant_id: str, db: Session) -> None:
    pipeline = get_pipeline_or_404(pipeline_id, tenant_id, db)
    db.delete(pipeline)
    db.commit()


def _clear_default_pipeline(tenant_id: str, db: Session) -> None:
    """No maximo 1 pipeline default por tenant — marcar um novo como default
    desmarca qualquer outro que ja fosse."""
    db.query(Pipeline).filter(Pipeline.tenant_id == tenant_id, Pipeline.is_default == True).update(  # noqa: E712
        {"is_default": False}
    )


# --- Stage ---

def list_stages(pipeline_id: str, tenant_id: str, db: Session) -> list[Stage]:
    get_pipeline_or_404(pipeline_id, tenant_id, db)  # garante que o pipeline e do tenant certo
    return db.query(Stage).filter(Stage.pipeline_id == pipeline_id).order_by(Stage.order).all()


def get_stage_or_404(stage_id: str, tenant_id: str, db: Session) -> Stage:
    """Join com Pipeline pra confirmar tenant — Stage nao guarda tenant_id
    proprio (unica fonte de verdade e Stage.pipeline.tenant_id)."""
    stage = (
        db.query(Stage)
        .join(Pipeline, Stage.pipeline_id == Pipeline.id)
        .filter(Stage.id == stage_id, Pipeline.tenant_id == tenant_id)
        .first()
    )
    if not stage:
        raise HTTPException(status_code=404, detail="Stage não encontrada")
    return stage


def create_stage(pipeline_id: str, tenant_id: str, body: StageCreate, db: Session) -> Stage:
    get_pipeline_or_404(pipeline_id, tenant_id, db)

    if body.is_entry:
        _clear_entry_stage(pipeline_id, db)

    max_order = db.query(Stage).filter(Stage.pipeline_id == pipeline_id).count()
    stage = Stage(
        id=_new_id(),
        pipeline_id=pipeline_id,
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
        _clear_entry_stage(stage.pipeline_id, db)

    for field, value in data.items():
        setattr(stage, field, value)
    db.commit()
    return stage


def delete_stage(stage_id: str, tenant_id: str, db: Session) -> None:
    stage = get_stage_or_404(stage_id, tenant_id, db)
    db.delete(stage)
    db.commit()


def _clear_entry_stage(pipeline_id: str, db: Session) -> None:
    """No maximo 1 stage de entrada por pipeline."""
    db.query(Stage).filter(Stage.pipeline_id == pipeline_id, Stage.is_entry == True).update({"is_entry": False})  # noqa: E712

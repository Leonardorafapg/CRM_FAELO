from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base


class Pipeline(Base):
    """Container de Stages — representa um processo (ex.: "Vendas",
    "Suporte"), configuravel por tenant. Multi-pipeline desde a v1: um
    tenant pode ter varios funis diferentes, cada um com suas proprias
    colunas."""
    __tablename__ = "pipelines"

    id          = Column(String, primary_key=True)
    tenant_id   = Column(String, nullable=False)  # vem do JWT, nao ha FK real (Tenant vive no platform-service)
    name        = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    active      = Column(Boolean, nullable=False, default=True)
    is_default  = Column(Boolean, nullable=False, default=False)  # usado como sugestao ao criar contact sem pipeline explicito

    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, onupdate=func.now())

    stages      = relationship("Stage", back_populates="pipeline", order_by="Stage.order")

    __table_args__ = (
        Index("ix_pipelines_tenant", "tenant_id"),
    )


class Stage(Base):
    """Coluna de um Pipeline — so posicao/visual do processo nesta fase
    (manual). Sem attendance_mode/automacao de proposito: essa fase do
    projeto e CRM manual, IA/atendimento automatizado fica pra depois."""
    __tablename__ = "stages"

    id             = Column(String, primary_key=True)
    pipeline_id    = Column(String, ForeignKey("pipelines.id"), nullable=False)
    name           = Column(String, nullable=False)
    order          = Column(Integer, nullable=False, default=0)
    color          = Column(String, nullable=True)
    active         = Column(Boolean, nullable=False, default=True)
    # Coluna sugerida ao adicionar um contact manualmente sem stage escolhida.
    # No maximo 1 por pipeline (garantido na migration + checagem no service).
    is_entry       = Column(Boolean, nullable=False, default=False)

    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, onupdate=func.now())

    pipeline       = relationship("Pipeline", back_populates="stages")
    contacts       = relationship("Contact", back_populates="stage")

    __table_args__ = (
        Index("ix_stages_pipeline_order", "pipeline_id", "order"),
    )

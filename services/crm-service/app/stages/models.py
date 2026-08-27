from sqlalchemy import Column, String, Boolean, Integer, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base


class Stage(Base):
    """Coluna do quadro (Kanban) — quadro unico e fixo por tenant nesta
    fase, sem conceito de multi-pipeline (removido; ver docs/TASKS.md).
    So posicao/visual do processo, sem attendance_mode/automacao de
    proposito: essa fase do projeto e CRM manual."""
    __tablename__ = "stages"

    id             = Column(String, primary_key=True)
    tenant_id      = Column(String, nullable=False)  # vem do JWT, nao ha FK real (Tenant vive no platform-service)
    name           = Column(String, nullable=False)
    order          = Column(Integer, nullable=False, default=0)
    color          = Column(String, nullable=True)
    active         = Column(Boolean, nullable=False, default=True)
    # Coluna sugerida ao adicionar um contact manualmente sem stage escolhida.
    # No maximo 1 por tenant (garantido na migration + checagem no service).
    is_entry       = Column(Boolean, nullable=False, default=False)

    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, onupdate=func.now())

    contacts       = relationship("Contact", back_populates="stage")

    __table_args__ = (
        Index("ix_stages_tenant_order", "tenant_id", "order"),
    )

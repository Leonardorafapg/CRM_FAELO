from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.sql import func
from app.db import Base


class Connection(Base):
    """Uma instancia de WhatsApp (Evolution API) conectada ao tenant. Config,
    nao operacional — por isso CRUD e restrito a owner/admin."""
    __tablename__ = "connections"

    id            = Column(String, primary_key=True)
    tenant_id     = Column(String, nullable=False)  # vem do JWT, sem FK real (Tenant vive no platform-service)
    instance_name = Column(String, nullable=False, unique=True)
    phone         = Column(String, nullable=True)  # preenchido apos conectar
    status        = Column(String, nullable=False, default="connecting")  # connecting/connected/disconnected

    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, onupdate=func.now())

    __table_args__ = (
        Index("ix_connections_tenant", "tenant_id"),
    )

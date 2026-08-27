from sqlalchemy import Column, String, Boolean, Integer, DateTime, JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base


class ContactStatus(Base):
    """Situacao geral do contato perante a empresa (ex.: Novo, Ativo,
    Inadimplente) — configuravel por tenant, sem enum fixo. INDEPENDENTE da
    Stage (posicao no quadro/Kanban): mudar status nunca muda a coluna do
    Kanban e vice-versa."""
    __tablename__ = "contact_statuses"

    id         = Column(String, primary_key=True)
    tenant_id  = Column(String, nullable=False)
    name       = Column(String, nullable=False)
    active     = Column(Boolean, nullable=False, default=True)
    order      = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    contacts   = relationship("Contact", back_populates="status")

    __table_args__ = (
        Index("ix_contact_statuses_tenant_order", "tenant_id", "order"),
    )


class Contact(Base):
    """Cadastro de cliente/lead — nesta fase, criado e editado manualmente
    pela equipe (sem ligacao com WhatsApp ainda, isso e fase futura).

    status_id (situacao geral) e stage_id (posicao no Kanban) sao conceitos
    INDEPENDENTES — mudar um nunca muda o outro (ver ContactStatus).
    """
    __tablename__ = "contacts"

    id              = Column(String, primary_key=True)
    tenant_id       = Column(String, nullable=False)
    name            = Column(String, nullable=False)
    phone           = Column(String, nullable=False)
    email           = Column(String, nullable=True)
    source          = Column(String, nullable=True)  # origem livre (ex.: "Instagram", "Indicacao")
    tags            = Column(JSON, nullable=False, default=list)
    status_id       = Column(String, ForeignKey("contact_statuses.id", ondelete="SET NULL"), nullable=True)
    # Id de User do platform-service — sem FK real (servico/banco diferente),
    # so guardado como referencia externa.
    assigned_to     = Column(String, nullable=True)
    stage_id        = Column(String, ForeignKey("stages.id", ondelete="SET NULL"), nullable=True)

    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, onupdate=func.now())

    status          = relationship("ContactStatus", back_populates="contacts")
    stage           = relationship("Stage", back_populates="contacts")

    __table_args__ = (
        UniqueConstraint("tenant_id", "phone", name="_tenant_phone_uc"),
        Index("ix_contacts_tenant_status", "tenant_id", "status_id"),
        # Cobre a montagem do Kanban (contacts agrupados por coluna dentro do tenant).
        Index("ix_contacts_tenant_stage", "tenant_id", "stage_id"),
    )

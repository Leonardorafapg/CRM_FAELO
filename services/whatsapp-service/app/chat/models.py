from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.db import Base


class Session(Base):
    """Uma conversa por telefone. id = "{tenant_id}:{phone}" (nao uuid) —
    garante 1 unica conversa por telefone dentro do tenant sem precisar de
    UniqueConstraint separado."""
    __tablename__ = "sessions"

    id            = Column(String, primary_key=True)
    tenant_id     = Column(String, nullable=False)
    connection_id = Column(String, ForeignKey("connections.id"), nullable=False)
    phone         = Column(String, nullable=False)
    contact_name  = Column(String, nullable=True)  # nome vindo do perfil do WhatsApp, so exibicao
    is_open       = Column(Boolean, nullable=False, default=True)
    last_activity = Column(DateTime, server_default=func.now(), onupdate=func.now())

    created_at    = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_sessions_tenant_last_activity", "tenant_id", "last_activity"),
        Index("ix_sessions_connection", "connection_id"),
    )


class Message(Base):
    __tablename__ = "messages"

    id                  = Column(String, primary_key=True)
    session_id          = Column(String, ForeignKey("sessions.id"), nullable=False)
    role                = Column(String, nullable=False)  # user (cliente) / attendant (humano)
    content             = Column(Text, nullable=False)
    # id da mensagem na Evolution API — usado so pra dedup de webhook,
    # diferente do Message.id interno (uuid gerado por nos).
    evolution_message_id = Column(String, nullable=True, unique=True)

    created_at          = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )

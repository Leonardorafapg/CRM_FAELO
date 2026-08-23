from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id             = Column(String, primary_key=True)
    business_name  = Column(String, nullable=False)
    phone          = Column(String, nullable=True)
    email          = Column(String, nullable=True)
    city           = Column(String, nullable=True)
    state          = Column(String, nullable=True)
    address        = Column(String, nullable=True)
    whatsapp       = Column(String, nullable=True)
    instagram      = Column(String, nullable=True)
    facebook       = Column(String, nullable=True)
    website        = Column(String, nullable=True)
    is_active      = Column(Boolean, default=True)
    # Config do bot/IA — consumida pelo conversation-service via chamada HTTP
    # (GET /tenants/{id}), nao replicada em banco proprio.
    system_prompt     = Column(Text, nullable=True)
    fallback_message  = Column(Text, nullable=True)
    ai_provider       = Column(String, default="groq")
    groq_key          = Column(String, nullable=True)
    openrouter_model  = Column(String, nullable=True)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, onupdate=func.now())

    users          = relationship("User", back_populates="tenant")
    business_hours = relationship("BusinessHours", back_populates="tenant")


class BusinessHours(Base):
    __tablename__ = "business_hours"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id   = Column(String, ForeignKey("tenants.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Segunda ... 6=Domingo
    slots       = Column(JSON, nullable=True)
    is_closed   = Column(Boolean, default=False)

    tenant      = relationship("Tenant", back_populates="business_hours")

    __table_args__ = (
        UniqueConstraint("tenant_id", "day_of_week", name="_tenant_day_uc"),
    )

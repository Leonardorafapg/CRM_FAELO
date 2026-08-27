from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base


class Tenant(Base):
    """A empresa/cliente do CRM — raiz do isolamento multi-tenant. Todo outro
    dado (contacts, conversas, etc., nos outros servicos) e sempre filtrado
    por tenant_id."""
    __tablename__ = "tenants"

    id             = Column(String, primary_key=True)  # slug + sufixo aleatorio, gerado no /auth/register
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
    is_active      = Column(Boolean, default=True)  # False = tenant desativado (ex.: por admin) — bloqueia login
    # Config do bot/IA — consumida pelo ai-service via chamada HTTP interna
    # (GET /internal/tenants/{id}), nao replicada em banco proprio. Nomes
    # genericos de proposito (nao amarrados a um provider especifico): troca
    # de provider e so mudar `ai_provider`, sem renomear coluna.
    system_prompt     = Column(Text, nullable=True)    # instrucoes extras pro LLM, definidas pelo tenant
    fallback_message  = Column(Text, nullable=True)    # resposta padrao quando a IA nao sabe responder
    ai_provider       = Column(String, nullable=False, default="deepseek", server_default="deepseek")  # "deepseek" por enquanto — outros providers entram depois
    ai_api_key        = Column(String, nullable=True)   # chave do provider configurado (texto puro aqui; GET publico so expoe bool)
    ai_model          = Column(String, nullable=True)    # modelo especifico do provider, se o tenant quiser sobrescrever o default
    # Libera a resposta automatica por FAQ/system_prompt (ai-service consulta
    # isso antes de responder). Sem crm_enabled aqui de proposito — vincular
    # conversa a Contact automaticamente esta fora de escopo nesta fase (ver
    # docs/features/WHATSAPP_SERVICE.md).
    faq_enabled       = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, onupdate=func.now())

    users          = relationship("User", back_populates="tenant")
    business_hours = relationship("BusinessHours", back_populates="tenant")


class BusinessHours(Base):
    """Horario de atendimento do tenant, um registro por dia da semana —
    consumido pelo conversation-service pra saber se deve responder ou nao
    fora do expediente (logica futura, ainda nao implementada nesse rebuild)."""
    __tablename__ = "business_hours"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id   = Column(String, ForeignKey("tenants.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Segunda ... 6=Domingo
    slots       = Column(JSON, nullable=True)       # lista de intervalos [{"from": "09:00", "to": "18:00"}, ...]
    is_closed   = Column(Boolean, default=False)     # True = fechado o dia inteiro, ignora slots

    tenant      = relationship("Tenant", back_populates="business_hours")

    __table_args__ = (
        # Garante no maximo 1 registro por dia por tenant — impede duplicar
        # "Segunda" duas vezes com horarios conflitantes.
        UniqueConstraint("tenant_id", "day_of_week", name="_tenant_day_uc"),
    )

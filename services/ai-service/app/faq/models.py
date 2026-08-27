from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.sql import func
from app.db import Base


class FaqItem(Base):
    """Base de conhecimento consultada pelo LLM (ai/llm/base.py::
    build_system_prompt) — mesmo model do legado (Chatbot/chat-api/ai/
    models.py::FaqItem), so pergunta/resposta, sem active/order (o legado
    chegou a remover um campo "ativo" que existia — mantido fora aqui de
    proposito). faq_enabled (liga/desliga a funcionalidade) mora em
    Tenant.faq_enabled no platform-service, nao aqui — isso e conteudo,
    aquilo e configuracao de identidade do tenant."""
    __tablename__ = "faq_items"

    id         = Column(String, primary_key=True)
    tenant_id  = Column(String, nullable=False)  # vem do JWT, sem FK real (Tenant vive no platform-service)
    pergunta   = Column(Text, nullable=False)
    resposta   = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_faq_items_tenant_created", "tenant_id", "created_at"),
    )

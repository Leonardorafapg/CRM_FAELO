"""Endpoints consumidos so por outros servicos internos (crm-service,
conversation-service), nunca pelo frontend — autenticados por
X-Internal-Key (shared/internal_auth.py), nao por JWT de usuario.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.tenant.models import Tenant
from shared.internal_auth import require_internal_key

# dependencies=[...] no nivel do router aplica require_internal_key em TODA
# rota deste arquivo automaticamente — nenhuma rota aqui precisa declarar de
# novo, nem existe risco de esquecer numa rota nova.
router = APIRouter(prefix="/internal/tenants", tags=["internal"], dependencies=[Depends(require_internal_key)])


@router.get("/{tenant_id}")
def get_tenant_internal(tenant_id: str, db: Session = Depends(get_db)):
    """Config completa do tenant, incluindo groq_key em TEXTO PURO (diferente
    do GET publico em routers/tenants.py, que so devolve um booleano) — uso
    exclusivo do conversation-service pra montar o system prompt e chamar o
    LLM em nome do tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.is_active == True).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado ou inativo")
    return {
        "id":               tenant.id,
        "business_name":    tenant.business_name,
        "system_prompt":    tenant.system_prompt,
        "fallback_message": tenant.fallback_message,
        "ai_provider":      tenant.ai_provider,
        "groq_key":         tenant.groq_key,
        "openrouter_model": tenant.openrouter_model,
    }

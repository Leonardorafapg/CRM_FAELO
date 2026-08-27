"""Regras de negocio de tenant/horario de atendimento — acesso a banco e
decisoes de dominio, sem nada de HTTP. app/routers/tenants.py so chama
essas funcoes."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.tenant.models import Tenant, BusinessHours
from app.tenant.schemas import TenantUpdateBody
from shared.logging_config import get_logger

logger = get_logger("platform-service")


def get_or_404(tenant_id: str, db: Session) -> Tenant:
    """Helper repetido em quase toda rota deste modulo: busca o tenant ou
    devolve 404 — centraliza pra nao duplicar o if/raise em cada handler."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant nao encontrado")
    return tenant


def serialize_tenant(tenant: Tenant) -> dict:
    """Note que ai_api_key vira bool(tenant.ai_api_key), NUNCA o valor real
    da chave. So o endpoint interno (routers/internal.py) devolve a chave em
    texto puro, pra consumo do ai-service."""
    return {
        "id":            tenant.id,
        "business_name": tenant.business_name,
        "phone":         tenant.phone,
        "email":         tenant.email,
        "city":          tenant.city,
        "state":         tenant.state,
        "address":       tenant.address,
        "whatsapp":      tenant.whatsapp,
        "instagram":     tenant.instagram,
        "facebook":      tenant.facebook,
        "website":       tenant.website,
        "system_prompt": tenant.system_prompt,
        "fallback_message": tenant.fallback_message,
        "ai_provider":   tenant.ai_provider,
        "ai_model":      tenant.ai_model,
        "ai_api_key":    bool(tenant.ai_api_key),
        "faq_enabled":   tenant.faq_enabled,
        "is_active":     tenant.is_active,
    }


def list_tenants(db: Session) -> list[dict]:
    return [{"id": t.id, "business_name": t.business_name, "is_active": t.is_active} for t in db.query(Tenant).all()]


def update_tenant(tenant_id: str, body: TenantUpdateBody, db: Session) -> None:
    tenant = get_or_404(tenant_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "ai_api_key":
            # So sobrescreve a chave real se vier uma STRING nao vazia —
            # protege contra o front reenviar o booleano do GET por engano
            # e apagar a chave ja salva.
            if isinstance(value, str) and value.strip():
                setattr(tenant, field, value.strip())
            continue
        setattr(tenant, field, value)
    db.commit()
    logger.info(f"Tenant {tenant_id} atualizado (campos: {sorted(body.model_dump(exclude_unset=True).keys())})")


def deactivate_tenant(tenant_id: str, admin_user_id: str | None, db: Session) -> None:
    """"Delete" e soft — so marca is_active=False, nunca apaga a linha (o
    historico do tenant precisa sobreviver)."""
    tenant = get_or_404(tenant_id, db)
    tenant.is_active = False
    db.commit()
    logger.warning(f"Tenant {tenant_id} desativado por admin ({admin_user_id})")


def get_business_hours(tenant_id: str, db: Session) -> list[dict]:
    """Os 7 (ou menos, se nunca configurado) registros de horario, ordenados
    por dia da semana."""
    get_or_404(tenant_id, db)
    hours = db.query(BusinessHours).filter(BusinessHours.tenant_id == tenant_id).order_by(BusinessHours.day_of_week).all()
    return [{"id": h.id, "day_of_week": h.day_of_week, "slots": h.slots or [], "is_closed": h.is_closed} for h in hours]


def update_business_hours(tenant_id: str, hours: list[dict], db: Session) -> None:
    """Substitui (upsert por dia) a configuracao de horario inteira de uma
    vez — o frontend sempre manda a semana completa, nao dia a dia."""
    get_or_404(tenant_id, db)
    if not hours:
        raise HTTPException(status_code=400, detail="Lista de horarios nao informada")
    for item in hours:
        day = item.get("day_of_week")
        if day is None:
            raise HTTPException(status_code=400, detail="day_of_week é obrigatório em todos os itens")
        # upsert: atualiza se ja existe registro pra esse dia, senao cria.
        existing = db.query(BusinessHours).filter(BusinessHours.tenant_id == tenant_id, BusinessHours.day_of_week == day).first()
        if existing:
            existing.is_closed = item.get("is_closed", False)
            existing.slots     = item.get("slots", [])
        else:
            db.add(BusinessHours(tenant_id=tenant_id, day_of_week=day, is_closed=item.get("is_closed", False), slots=item.get("slots", [])))
    db.commit()

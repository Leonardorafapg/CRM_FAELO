from typing import Literal, Optional, Union
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db import get_db
from app.tenant.models import Tenant, BusinessHours
from shared.auth_deps import get_current_user
from shared.policy import require_admin
from shared.logging_config import get_logger

logger = get_logger("platform-service")

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantUpdateBody(BaseModel):
    business_name:    Optional[str] = None
    phone:            Optional[str] = None
    email:            Optional[str] = None
    city:             Optional[str] = None
    state:            Optional[str] = None
    address:          Optional[str] = None
    whatsapp:         Optional[str] = None
    instagram:        Optional[str] = None
    facebook:         Optional[str] = None
    website:          Optional[str] = None
    system_prompt:    Optional[str] = None
    fallback_message: Optional[str] = None
    ai_provider:      Optional[Literal["groq", "openrouter"]] = None
    openrouter_model: Optional[str] = None
    # Segredo: o GET devolve um booleano ("existe chave?"), entao o front pode
    # reenviar bool sem querer — aceita bool aqui pra nao rejeitar o PATCH inteiro
    # com 422, mas so aplica quando vier string nao vazia (ver handler).
    groq_key:         Optional[Union[str, bool]] = None

def get_or_404(tenant_id: str, db: Session) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant nao encontrado")
    return tenant

def _tenant_dict(tenant: Tenant) -> dict:
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
        "groq_key":      bool(tenant.groq_key),
        "is_active":     tenant.is_active,
    }

@router.get("")
def list_tenants(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return [{"id": t.id, "business_name": t.business_name, "is_active": t.is_active} for t in db.query(Tenant).all()]

@router.get("/{tenant_id}")
def get_tenant(tenant_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin") and current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return _tenant_dict(get_or_404(tenant_id, db))

@router.patch("/{tenant_id}")
def update_tenant(tenant_id: str, body: TenantUpdateBody, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user), _role: dict = Depends(require_admin)):
    if not current_user.get("is_admin") and current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    tenant = get_or_404(tenant_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "groq_key":
            if isinstance(value, str) and value.strip():
                setattr(tenant, field, value.strip())
            continue
        setattr(tenant, field, value)
    db.commit()
    logger.info(f"Tenant {tenant_id} atualizado (campos: {sorted(body.model_dump(exclude_unset=True).keys())})")
    return {"message": "Tenant atualizado com sucesso"}

@router.delete("/{tenant_id}")
def deactivate_tenant(tenant_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    tenant = get_or_404(tenant_id, db)
    tenant.is_active = False
    db.commit()
    logger.warning(f"Tenant {tenant_id} desativado por admin ({current_user.get('user_id')})")
    return {"message": f"Tenant desativado"}

@router.get("/{tenant_id}/business-hours")
def get_business_hours(tenant_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin") and current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    get_or_404(tenant_id, db)
    hours = db.query(BusinessHours).filter(BusinessHours.tenant_id == tenant_id).order_by(BusinessHours.day_of_week).all()
    return [{"id": h.id, "day_of_week": h.day_of_week, "slots": h.slots or [], "is_closed": h.is_closed} for h in hours]

@router.put("/{tenant_id}/business-hours")
def update_business_hours(tenant_id: str, body: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user), _role: dict = Depends(require_admin)):
    if not current_user.get("is_admin") and current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    get_or_404(tenant_id, db)
    hours = body.get("hours", [])
    if not hours:
        raise HTTPException(status_code=400, detail="Lista de horarios nao informada")
    for item in hours:
        day = item.get("day_of_week")
        if day is None:
            raise HTTPException(status_code=400, detail="day_of_week é obrigatório em todos os itens")
        existing = db.query(BusinessHours).filter(BusinessHours.tenant_id == tenant_id, BusinessHours.day_of_week == day).first()
        if existing:
            existing.is_closed = item.get("is_closed", False)
            existing.slots     = item.get("slots", [])
        else:
            db.add(BusinessHours(tenant_id=tenant_id, day_of_week=day, is_closed=item.get("is_closed", False), slots=item.get("slots", [])))
    db.commit()
    return {"message": "Horarios atualizados com sucesso"}

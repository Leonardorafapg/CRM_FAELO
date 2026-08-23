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
    """Schema do PATCH: todo campo opcional (so atualiza o que vier
    preenchido — ver model_dump(exclude_unset=True) no handler). Validar com
    Pydantic aqui evita que um valor de tipo errado (ex.: numero no lugar de
    texto) vire erro 500 direto do Postgres."""
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
    # reenviar esse bool sem querer. Aceita bool aqui pra nao rejeitar o PATCH
    # inteiro com 422 — o handler so aplica de fato quando vier string nao vazia.
    groq_key:         Optional[Union[str, bool]] = None

def get_or_404(tenant_id: str, db: Session) -> Tenant:
    """Helper repetido em quase toda rota deste arquivo: busca o tenant ou
    devolve 404 — centraliza pra nao duplicar o if/raise em cada handler."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant nao encontrado")
    return tenant

def _tenant_dict(tenant: Tenant) -> dict:
    """Serializacao do Tenant pra resposta JSON — note que groq_key vira
    bool(tenant.groq_key), NUNCA o valor real da chave. So o endpoint interno
    (routers/internal.py) devolve a chave em texto puro, pra consumo do
    conversation-service."""
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
    """Lista TODOS os tenants do sistema — restrita a platform admin
    (equipe da Faelo), nunca a um dono de tenant normal."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return [{"id": t.id, "business_name": t.business_name, "is_active": t.is_active} for t in db.query(Tenant).all()]

@router.get("/{tenant_id}")
def get_tenant(tenant_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Le os dados de UM tenant especifico — qualquer usuario logado pode ler
    o proprio tenant (nao exige require_admin), so nao pode ler o de outro."""
    if not current_user.get("is_admin") and current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return _tenant_dict(get_or_404(tenant_id, db))

@router.patch("/{tenant_id}")
def update_tenant(tenant_id: str, body: TenantUpdateBody, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user), _role: dict = Depends(require_admin)):
    """Atualiza campos do tenant — exige role admin/owner (require_admin) E
    pertencer ao proprio tenant (ou ser platform admin)."""
    if not current_user.get("is_admin") and current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    tenant = get_or_404(tenant_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "groq_key":
            # So sobrescreve a chave real se vier uma STRING nao vazia —
            # protege contra o front reenviar o booleano do GET por engano
            # e apagar a chave ja salva.
            if isinstance(value, str) and value.strip():
                setattr(tenant, field, value.strip())
            continue
        setattr(tenant, field, value)
    db.commit()
    logger.info(f"Tenant {tenant_id} atualizado (campos: {sorted(body.model_dump(exclude_unset=True).keys())})")
    return {"message": "Tenant atualizado com sucesso"}

@router.delete("/{tenant_id}")
def deactivate_tenant(tenant_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """"Delete" e soft — so marca is_active=False, nunca apaga a linha (o
    historico do tenant precisa sobreviver). Restrito a platform admin."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    tenant = get_or_404(tenant_id, db)
    tenant.is_active = False
    db.commit()
    logger.warning(f"Tenant {tenant_id} desativado por admin ({current_user.get('user_id')})")
    return {"message": f"Tenant desativado"}

@router.get("/{tenant_id}/business-hours")
def get_business_hours(tenant_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Lista os 7 (ou menos, se nunca configurado) registros de horario,
    ordenados por dia da semana."""
    if not current_user.get("is_admin") and current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    get_or_404(tenant_id, db)
    hours = db.query(BusinessHours).filter(BusinessHours.tenant_id == tenant_id).order_by(BusinessHours.day_of_week).all()
    return [{"id": h.id, "day_of_week": h.day_of_week, "slots": h.slots or [], "is_closed": h.is_closed} for h in hours]

@router.put("/{tenant_id}/business-hours")
def update_business_hours(tenant_id: str, body: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user), _role: dict = Depends(require_admin)):
    """Substitui (upsert por dia) a configuracao de horario inteira de uma
    vez — o frontend sempre manda a semana completa, nao dia a dia."""
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
        # upsert: atualiza se ja existe registro pra esse dia, senao cria.
        existing = db.query(BusinessHours).filter(BusinessHours.tenant_id == tenant_id, BusinessHours.day_of_week == day).first()
        if existing:
            existing.is_closed = item.get("is_closed", False)
            existing.slots     = item.get("slots", [])
        else:
            db.add(BusinessHours(tenant_id=tenant_id, day_of_week=day, is_closed=item.get("is_closed", False), slots=item.get("slots", [])))
    db.commit()
    return {"message": "Horarios atualizados com sucesso"}

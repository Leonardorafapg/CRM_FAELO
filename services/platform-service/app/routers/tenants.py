"""Rotas de tenant — so fazem parsing/roteamento HTTP e checagem de acesso.
Toda regra de negocio vive em app/tenant/service.py; schemas em
app/tenant/schemas.py."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.tenant import service
from app.tenant.schemas import TenantUpdateBody
from shared.auth_deps import get_current_user
from shared.policy import require_admin

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _require_same_tenant_or_admin(tenant_id: str, current_user: dict) -> None:
    if not current_user.get("is_admin") and current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")


@router.get("")
def list_tenants(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Lista TODOS os tenants do sistema — restrita a platform admin
    (equipe da Faelo), nunca a um dono de tenant normal."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return service.list_tenants(db)


@router.get("/{tenant_id}")
def get_tenant(tenant_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Qualquer usuario logado pode ler o proprio tenant (nao exige
    require_admin), so nao pode ler o de outro."""
    _require_same_tenant_or_admin(tenant_id, current_user)
    return service.serialize_tenant(service.get_or_404(tenant_id, db))


@router.patch("/{tenant_id}")
def update_tenant(
    tenant_id: str,
    body: TenantUpdateBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    _require_same_tenant_or_admin(tenant_id, current_user)
    service.update_tenant(tenant_id, body, db)
    return {"message": "Tenant atualizado com sucesso"}


@router.delete("/{tenant_id}")
def deactivate_tenant(tenant_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    service.deactivate_tenant(tenant_id, current_user.get("user_id"), db)
    return {"message": "Tenant desativado"}


@router.get("/{tenant_id}/business-hours")
def get_business_hours(tenant_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    _require_same_tenant_or_admin(tenant_id, current_user)
    return service.get_business_hours(tenant_id, db)


@router.put("/{tenant_id}/business-hours")
def update_business_hours(
    tenant_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    _require_same_tenant_or_admin(tenant_id, current_user)
    service.update_business_hours(tenant_id, body.get("hours", []), db)
    return {"message": "Horarios atualizados com sucesso"}

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from shared.auth_deps import get_current_user, require_own_tenant  # re-exportado
from app.db import get_db
from app.tenant.models import Tenant

__all__ = ["get_current_user", "require_own_tenant", "get_current_tenant", "get_tenant"]


def get_current_tenant(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == current_user.get("tenant_id")).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Conta inativa")
    return tenant


def get_tenant(tenant_id: str, db: Session = Depends(get_db)) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.is_active == True).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' não encontrado ou inativo")
    return tenant

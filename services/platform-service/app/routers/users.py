"""Rotas de gestao de equipe — so fazem parsing/roteamento HTTP. Toda regra
de negocio vive em app/identity/service.py; schemas em app/identity/schemas.py."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.identity import service
from app.identity.schemas import InviteCreate, UserUpdate
from shared.auth_deps import require_own_tenant, get_current_user
from shared.policy import require_admin
from app.infra.rate_limit import limiter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{tenant_id}")
def listar_usuarios(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_own_tenant),
    _role: dict = Depends(require_admin),
):
    """Exige admin/owner — attendant nao ve a lista de usuarios."""
    users = service.list_users(tenant_id, db)
    return [service.serialize_user(u) for u in users]


@router.get("/{tenant_id}/invites")
def listar_convites(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_own_tenant),
    _role: dict = Depends(require_admin),
):
    invites = service.list_pending_invites(tenant_id, db)
    return [service.serialize_invite(i) for i in invites]


@router.post("/{tenant_id}/invite")
@limiter.limit("20/hour")  # protege contra spam de convites (e de envio de email)
async def criar_convite(
    request: Request,
    tenant_id: str,
    body: InviteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_own_tenant),
    _role: dict = Depends(require_admin),
):
    await service.create_invite(tenant_id, body, current_user, db)
    return {"message": "Convite enviado"}


@router.delete("/invites/{invite_id}")
def cancelar_convite(
    invite_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    service.cancel_invite(invite_id, current_user, db)
    return {"ok": True}


@router.patch("/{user_id}")
def editar_usuario(
    user_id: str,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    user = service.update_user(user_id, body, current_user, db)
    return service.serialize_user(user)

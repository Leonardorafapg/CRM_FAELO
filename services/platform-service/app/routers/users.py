"""Gestao de equipe dentro do tenant: listar/convidar/editar usuarios.
Mesmas regras de permissao do chat-api atual — ver docstrings dos handlers.
"""
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.db import get_db
from app.identity.models import User, Invite
from shared.roles import UserRole
from app.tenant.models import Tenant
from shared.auth_deps import require_own_tenant, get_current_user
from shared.policy import require_admin
from app.infra.email import send_team_invite_email
from app.infra.rate_limit import limiter
from app.auth.routes import _hash_token, EMAIL_REGEX

router = APIRouter(prefix="/users", tags=["users"])

INVITE_TTL_DAYS = 7


class InviteCreate(BaseModel):
    email: str
    role:  UserRole

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: str) -> str:
        if not re.match(EMAIL_REGEX, v):
            raise ValueError("Email inválido")
        return v


class UserUpdate(BaseModel):
    role:      UserRole | None = None
    is_active: bool | None = None


def _serialize_user(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role.value,
        "is_active": u.is_active,
        "created_at": u.created_at,
    }


def _serialize_invite(i: Invite) -> dict:
    return {
        "id": i.id,
        "email": i.email,
        "role": i.role.value,
        "expires_at": i.expires_at,
        "created_at": i.created_at,
    }


@router.get("/{tenant_id}")
def listar_usuarios(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_own_tenant),
    _role: dict = Depends(require_admin),
):
    users = db.query(User).filter(User.tenant_id == tenant_id).order_by(User.created_at).all()
    return [_serialize_user(u) for u in users]


@router.get("/{tenant_id}/invites")
def listar_convites(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_own_tenant),
    _role: dict = Depends(require_admin),
):
    invites = (
        db.query(Invite)
        .filter(Invite.tenant_id == tenant_id, Invite.accepted_at.is_(None))
        .order_by(Invite.created_at.desc())
        .all()
    )
    return [_serialize_invite(i) for i in invites]


@router.post("/{tenant_id}/invite")
@limiter.limit("20/hour")
async def criar_convite(
    request: Request,
    tenant_id: str,
    body: InviteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_own_tenant),
    _role: dict = Depends(require_admin),
):
    if body.role == UserRole.owner and current_user.get("role") != UserRole.owner.value:
        raise HTTPException(status_code=403, detail="Só um owner pode convidar outro owner")

    if db.query(User).filter(User.email == body.email, User.tenant_id == tenant_id).first():
        raise HTTPException(status_code=400, detail="Este email já pertence a um usuário do time")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    db.query(Invite).filter(
        Invite.tenant_id == tenant_id,
        Invite.email == body.email,
        Invite.accepted_at.is_(None),
    ).delete()

    raw_token = secrets.token_urlsafe(32)
    invite = Invite(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        email=body.email,
        role=body.role,
        token_hash=_hash_token(raw_token),
        invited_by=current_user.get("user_id"),
        expires_at=datetime.utcnow() + timedelta(days=INVITE_TTL_DAYS),
    )
    db.add(invite)
    db.commit()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    invite_url = f"{frontend_url}/accept-invite?token={raw_token}"
    inviter = db.query(User).filter(User.id == current_user.get("user_id")).first()
    await send_team_invite_email(
        body.email, invite_url,
        tenant_name=tenant.business_name if tenant else "",
        inviter_name=inviter.name if inviter else None,
    )

    return {"message": "Convite enviado"}


@router.delete("/invites/{invite_id}")
def cancelar_convite(
    invite_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    invite = db.query(Invite).filter(Invite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    if not current_user.get("is_admin") and invite.tenant_id != current_user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    db.delete(invite)
    db.commit()
    return {"ok": True}


@router.patch("/{user_id}")
def editar_usuario(
    user_id: str,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role: dict = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if not current_user.get("is_admin") and user.tenant_id != current_user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    if user.id == current_user.get("user_id"):
        raise HTTPException(status_code=400, detail="Você não pode editar sua própria conta por aqui")

    is_caller_owner = current_user.get("role") == UserRole.owner.value

    if user.role == UserRole.owner and not is_caller_owner:
        raise HTTPException(status_code=403, detail="Só um owner pode editar outro owner")

    if body.role is not None:
        if body.role == UserRole.owner and not is_caller_owner:
            raise HTTPException(status_code=403, detail="Só um owner pode conceder o papel de owner")
        if user.role == UserRole.owner and body.role != UserRole.owner:
            _assert_not_last_owner(db, user)
        user.role = body.role

    if body.is_active is not None and body.is_active is False:
        if user.role == UserRole.owner:
            _assert_not_last_owner(db, user)
        user.is_active = False
    elif body.is_active is not None:
        user.is_active = True

    db.commit()
    return _serialize_user(user)


def _assert_not_last_owner(db: Session, user: User) -> None:
    other_owners = (
        db.query(User)
        .filter(
            User.tenant_id == user.tenant_id,
            User.role == UserRole.owner,
            User.is_active == True,  # noqa: E712
            User.id != user.id,
        )
        .count()
    )
    if other_owners == 0:
        raise HTTPException(status_code=400, detail="O tenant precisa ter pelo menos um owner ativo")

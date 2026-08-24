"""Regras de negocio de gestao de equipe (usuarios/convites) — acesso a
banco e decisoes de dominio, sem nada de HTTP. app/routers/users.py so
chama essas funcoes.

Regras de permissao concentradas aqui (alem de require_admin no nivel da
rota):
- so owner pode conceder/manter role=owner (admin nao promove a owner nem
  edita um owner existente);
- ninguem edita a propria linha (role ou is_active) por aqui — evita
  autopromocao e autolockout;
- tenant precisa manter pelo menos 1 owner ativo — bloqueia rebaixar/
  desativar o ultimo.
"""
import os
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.identity.models import User, Invite
from app.identity.schemas import InviteCreate, UserUpdate
from app.tenant.models import Tenant
from app.auth.security import hash_token
from app.infra.email import send_team_invite_email
from shared.roles import UserRole

INVITE_TTL_DAYS = 7  # janela de validade do link de convite


def serialize_user(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role.value,
        "is_active": u.is_active,
        "created_at": u.created_at,
    }


def serialize_invite(i: Invite) -> dict:
    return {
        "id": i.id,
        "email": i.email,
        "role": i.role.value,
        "expires_at": i.expires_at,
        "created_at": i.created_at,
    }


def list_users(tenant_id: str, db: Session) -> list[User]:
    """Do mais antigo pro mais recente."""
    return db.query(User).filter(User.tenant_id == tenant_id).order_by(User.created_at).all()


def list_pending_invites(tenant_id: str, db: Session) -> list[Invite]:
    """So os convites AINDA PENDENTES (accepted_at is None) — convites ja
    aceitos ou expirados nao aparecem aqui, viraram User de verdade ou
    ficaram mortos."""
    return (
        db.query(Invite)
        .filter(Invite.tenant_id == tenant_id, Invite.accepted_at.is_(None))
        .order_by(Invite.created_at.desc())
        .all()
    )


async def create_invite(tenant_id: str, body: InviteCreate, current_user: dict, db: Session) -> None:
    """Cria e envia um convite por email. So um owner pode convidar outro
    owner (um admin nao pode elevar ninguem ao proprio nivel do dono).
    Gerar um convite novo pro mesmo email invalida qualquer um anterior
    ainda pendente, pra nunca existir 2 links validos e divergentes."""
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
        token_hash=hash_token(raw_token),
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


def cancel_invite(invite_id: str, current_user: dict, db: Session) -> None:
    """Apaga a linha de fato (nao e soft delete, convite cancelado nao tem
    valor historico)."""
    invite = db.query(Invite).filter(Invite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    if not current_user.get("is_admin") and invite.tenant_id != current_user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    db.delete(invite)
    db.commit()


def update_user(user_id: str, body: UserUpdate, current_user: dict, db: Session) -> User:
    """Edita role e/ou is_active de um membro da equipe — ver docstring do
    modulo pra lista completa das regras de protecao."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if not current_user.get("is_admin") and user.tenant_id != current_user.get("tenant_id"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    if user.id == current_user.get("user_id"):
        # Impede autopromocao (virar owner sozinho) e autolockout
        # (desativar a propria conta e ficar sem acesso).
        raise HTTPException(status_code=400, detail="Você não pode editar sua própria conta por aqui")

    is_caller_owner = current_user.get("role") == UserRole.owner.value

    # So um owner mexe em outro owner — nem role nem is_active. Sem isso um
    # admin poderia desativar todos os owners exceto o ultimo (bloqueado so
    # pela regra de "ultimo owner", abaixo) e efetivamente assumir controle
    # do tenant.
    if user.role == UserRole.owner and not is_caller_owner:
        raise HTTPException(status_code=403, detail="Só um owner pode editar outro owner")

    if body.role is not None:
        if body.role == UserRole.owner and not is_caller_owner:
            raise HTTPException(status_code=403, detail="Só um owner pode conceder o papel de owner")
        if user.role == UserRole.owner and body.role != UserRole.owner:
            # Rebaixando um owner — confere que sobra outro owner ativo antes.
            _assert_not_last_owner(db, user)
        user.role = body.role

    if body.is_active is not None and body.is_active is False:
        if user.role == UserRole.owner:
            _assert_not_last_owner(db, user)
        user.is_active = False
    elif body.is_active is not None:
        user.is_active = True

    db.commit()
    return user


def _assert_not_last_owner(db: Session, user: User) -> None:
    """Levanta 400 se `user` for o UNICO owner ativo do tenant — chamado
    antes de rebaixar ou desativar um owner, garante que o tenant nunca fica
    sem ninguem no nivel mais alto de permissao."""
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

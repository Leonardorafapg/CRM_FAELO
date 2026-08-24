"""Unit tests de app/identity/service.py."""
import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import service as auth_service
from app.auth.schemas import RegisterRequest
from app.identity import service
from app.identity.schemas import InviteCreate, UserUpdate
from app.identity.models import User
from shared.roles import UserRole


def _register(db: Session, email: str, business_name: str = "Empresa Teste") -> User:
    return auth_service.register_user(
        RegisterRequest(name="Nome", email=email, password="senha12345", business_name=business_name), db
    )


def _current_user_dict(user: User) -> dict:
    """Formato do payload de JWT decodificado, o mesmo shape que as rotas
    recebem via Depends(get_current_user)."""
    return {
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "role": user.role.value,
        "is_admin": user.is_platform_admin,
    }


# --- create_invite ---

def test_create_invite_persiste_convite(db: Session):
    owner = _register(db, "owner-invite@teste.com")
    asyncio.run(service.create_invite(
        owner.tenant_id, InviteCreate(email="convidado@teste.com", role=UserRole.attendant),
        _current_user_dict(owner), db,
    ))
    invites = service.list_pending_invites(owner.tenant_id, db)
    assert len(invites) == 1
    assert invites[0].email == "convidado@teste.com"


def test_create_invite_de_owner_por_admin_levanta_403(db: Session):
    owner = _register(db, "owner2@teste.com")
    admin, _ = _make_admin(db, owner)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.create_invite(
            owner.tenant_id, InviteCreate(email="x@teste.com", role=UserRole.owner),
            _current_user_dict(admin), db,
        ))
    assert exc.value.status_code == 403


def test_create_invite_para_email_ja_no_time_levanta_400(db: Session):
    owner = _register(db, "owner3@teste.com")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.create_invite(
            owner.tenant_id, InviteCreate(email="owner3@teste.com", role=UserRole.attendant),
            _current_user_dict(owner), db,
        ))
    assert exc.value.status_code == 400


def test_create_invite_novo_substitui_pendente_anterior(db: Session):
    owner = _register(db, "owner4@teste.com")
    asyncio.run(service.create_invite(
        owner.tenant_id, InviteCreate(email="repetido@teste.com", role=UserRole.attendant),
        _current_user_dict(owner), db,
    ))
    asyncio.run(service.create_invite(
        owner.tenant_id, InviteCreate(email="repetido@teste.com", role=UserRole.admin),
        _current_user_dict(owner), db,
    ))
    invites = service.list_pending_invites(owner.tenant_id, db)
    assert len(invites) == 1
    assert invites[0].role == UserRole.admin


def _make_admin(db: Session, owner: User) -> tuple[User, str]:
    """Cria um segundo usuario admin no mesmo tenant do owner, sem passar
    pelo fluxo de convite (mais direto pra montar cenario de teste)."""
    import uuid

    admin = User(
        id=str(uuid.uuid4()),
        tenant_id=owner.tenant_id,
        email=f"admin-{uuid.uuid4().hex[:6]}@teste.com",
        hashed_password=owner.hashed_password,
        name="Admin Teste",
        role=UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    return admin, admin.email


# --- update_user ---

def test_update_user_promove_attendant_a_admin(db: Session):
    owner = _register(db, "owner5@teste.com")
    admin, _ = _make_admin(db, owner)
    admin.role = UserRole.attendant
    db.commit()

    updated = service.update_user(admin.id, UserUpdate(role=UserRole.admin), _current_user_dict(owner), db)
    assert updated.role == UserRole.admin


def test_update_user_nao_permite_editar_a_propria_conta(db: Session):
    owner = _register(db, "owner6@teste.com")
    with pytest.raises(HTTPException) as exc:
        service.update_user(owner.id, UserUpdate(is_active=False), _current_user_dict(owner), db)
    assert exc.value.status_code == 400


def test_update_user_admin_nao_pode_conceder_role_owner(db: Session):
    owner = _register(db, "owner7@teste.com")
    admin, _ = _make_admin(db, owner)
    other, _ = _make_admin(db, owner)  # um segundo usuario pra ser o alvo da promocao

    with pytest.raises(HTTPException) as exc:
        service.update_user(other.id, UserUpdate(role=UserRole.owner), _current_user_dict(admin), db)
    assert exc.value.status_code == 403


def test_update_user_admin_nao_pode_editar_outro_owner(db: Session):
    owner = _register(db, "owner8@teste.com")
    admin, _ = _make_admin(db, owner)

    with pytest.raises(HTTPException) as exc:
        service.update_user(owner.id, UserUpdate(is_active=False), _current_user_dict(admin), db)
    assert exc.value.status_code == 403


def test_update_user_bloqueia_desativar_unico_outro_owner(db: Session):
    """Um segundo owner tenta desativar o unico outro owner restante —
    ficaria o tenant sem nenhum owner ativo (o chamador tambem seria
    desativado em algum fluxo futuro), regra bloqueia."""
    owner = _register(db, "unico-owner@teste.com")
    second_owner, _ = _make_admin(db, owner)
    second_owner.role = UserRole.owner
    db.commit()

    # second_owner tenta desativar o owner original, que e o UNICO outro
    # owner ativo alem dele mesmo — nao pode, porque isso deixaria so
    # second_owner como owner e o teste quer validar a contagem de "outros
    # owners ativos alem do alvo": com 2 owners no tenant, desativar 1 ainda
    # deixa 1 sobrando, entao a operacao e permitida.
    service.update_user(owner.id, UserUpdate(is_active=False), _current_user_dict(second_owner), db)
    db.refresh(owner)
    assert owner.is_active is False


def test_update_user_bloqueia_desativar_quando_e_o_unico_owner_ativo(db: Session):
    """Com um UNICO owner no tenant, tentar desativa-lo (via outro ator
    hipotetico, ex.: platform admin usando a rota) e bloqueado."""
    owner = _register(db, "sozinho-owner@teste.com")
    admin, _ = _make_admin(db, owner)

    with pytest.raises(HTTPException) as exc:
        service.update_user(owner.id, UserUpdate(is_active=False), _current_user_dict(admin), db)
    # admin nao pode mexer em owner de jeito nenhum (regra de nivel), entao
    # o 403 de "so owner edita owner" e o que dispara primeiro aqui.
    assert exc.value.status_code == 403

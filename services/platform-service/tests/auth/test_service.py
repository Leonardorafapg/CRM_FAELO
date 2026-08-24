"""Unit tests de app/auth/service.py — chama as funcoes direto, sem subir o
app (ver TESTING.md: teste de service.py e unitario)."""
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.schemas import LoginRequest, RegisterRequest, AcceptInviteRequest
from app.identity.models import User, Invite
from shared.roles import UserRole


def _register(db: Session, email: str = "owner@teste.com", password: str = "senha12345") -> User:
    body = RegisterRequest(
        name="Dono Teste",
        email=email,
        password=password,
        business_name="Empresa Teste",
    )
    return service.register_user(body, db)


# --- register_user ---

def test_register_user_cria_tenant_e_owner(db: Session):
    user = _register(db)
    assert user.role == UserRole.owner
    assert user.tenant_id is not None
    assert user.is_active is True


def test_register_user_com_email_invalido_levanta_400(db: Session):
    body = RegisterRequest(name="X", email="nao-e-email", password="senha12345", business_name="X")
    with pytest.raises(HTTPException) as exc:
        service.register_user(body, db)
    assert exc.value.status_code == 400


def test_register_user_com_senha_curta_levanta_400(db: Session):
    body = RegisterRequest(name="X", email="curta@teste.com", password="1234567", business_name="X")
    with pytest.raises(HTTPException) as exc:
        service.register_user(body, db)
    assert exc.value.status_code == 400


def test_register_user_com_email_duplicado_levanta_400(db: Session):
    _register(db, email="duplicado@teste.com")
    with pytest.raises(HTTPException) as exc:
        _register(db, email="duplicado@teste.com")
    assert exc.value.status_code == 400


def test_register_gera_tenant_id_diferente_para_mesmo_nome_de_empresa(db: Session):
    u1 = service.register_user(
        RegisterRequest(name="A", email="a@teste.com", password="senha12345", business_name="Mesma Empresa"), db
    )
    u2 = service.register_user(
        RegisterRequest(name="B", email="b@teste.com", password="senha12345", business_name="Mesma Empresa"), db
    )
    assert u1.tenant_id != u2.tenant_id


# --- authenticate_user ---

def test_authenticate_user_com_credenciais_corretas(db: Session):
    _register(db, email="login@teste.com", password="senha12345")
    user = service.authenticate_user(LoginRequest(email="login@teste.com", password="senha12345"), db)
    assert user.email == "login@teste.com"


def test_authenticate_user_com_senha_errada_levanta_401(db: Session):
    _register(db, email="senhaerrada@teste.com", password="senha12345")
    with pytest.raises(HTTPException) as exc:
        service.authenticate_user(LoginRequest(email="senhaerrada@teste.com", password="outrasenha"), db)
    assert exc.value.status_code == 401


def test_authenticate_user_com_email_inexistente_levanta_401(db: Session):
    with pytest.raises(HTTPException) as exc:
        service.authenticate_user(LoginRequest(email="naoexiste@teste.com", password="senha12345"), db)
    assert exc.value.status_code == 401


def test_authenticate_user_inativo_levanta_403(db: Session):
    user = _register(db, email="inativo@teste.com", password="senha12345")
    user.is_active = False
    db.commit()
    with pytest.raises(HTTPException) as exc:
        service.authenticate_user(LoginRequest(email="inativo@teste.com", password="senha12345"), db)
    assert exc.value.status_code == 403


def test_authenticate_user_com_tenant_inativo_levanta_403(db: Session):
    from app.tenant.models import Tenant

    user = _register(db, email="tenantinativo@teste.com", password="senha12345")
    db.query(Tenant).filter(Tenant.id == user.tenant_id).update({"is_active": False})
    db.commit()
    with pytest.raises(HTTPException) as exc:
        service.authenticate_user(LoginRequest(email="tenantinativo@teste.com", password="senha12345"), db)
    assert exc.value.status_code == 403


# --- build_token ---

def test_build_token_contem_claims_esperados(db: Session):
    user = _register(db, email="token@teste.com")
    payload = service.build_token(user)
    assert payload["access_token"]
    assert payload["tenant_id"] == user.tenant_id
    assert payload["role"] == "owner"
    assert payload["is_admin"] is False


# --- reset de senha ---

def test_create_password_reset_token_para_email_existente(db: Session):
    _register(db, email="reset@teste.com")
    result = service.create_password_reset_token("reset@teste.com", db)
    assert result is not None
    user, raw_token = result
    assert user.email == "reset@teste.com"
    assert len(raw_token) > 20


def test_create_password_reset_token_para_email_inexistente_retorna_none(db: Session):
    assert service.create_password_reset_token("fantasma@teste.com", db) is None


def test_reset_password_com_token_valido(db: Session):
    _register(db, email="reset2@teste.com", password="senhaantiga1")
    _, raw_token = service.create_password_reset_token("reset2@teste.com", db)

    service.reset_password(raw_token, "senhanova123", db)

    # A nova senha autentica; a antiga nao autentica mais.
    service.authenticate_user(LoginRequest(email="reset2@teste.com", password="senhanova123"), db)
    with pytest.raises(HTTPException):
        service.authenticate_user(LoginRequest(email="reset2@teste.com", password="senhaantiga1"), db)


def test_reset_password_com_token_invalido_levanta_400(db: Session):
    with pytest.raises(HTTPException) as exc:
        service.reset_password("token-que-nao-existe", "senhanova123", db)
    assert exc.value.status_code == 400


def test_reset_password_com_token_usado_duas_vezes_levanta_400_na_segunda(db: Session):
    _register(db, email="reset3@teste.com")
    _, raw_token = service.create_password_reset_token("reset3@teste.com", db)

    service.reset_password(raw_token, "senhanova123", db)
    with pytest.raises(HTTPException) as exc:
        service.reset_password(raw_token, "outrasenha123", db)
    assert exc.value.status_code == 400


def test_reset_password_com_senha_curta_levanta_400(db: Session):
    _register(db, email="reset4@teste.com")
    _, raw_token = service.create_password_reset_token("reset4@teste.com", db)
    with pytest.raises(HTTPException) as exc:
        service.reset_password(raw_token, "curta", db)
    assert exc.value.status_code == 400


# --- convites ---

def _create_invite(db: Session, tenant_id: str, invited_by: str, email: str = "convidado@teste.com", role: UserRole = UserRole.attendant) -> tuple[Invite, str]:
    from datetime import datetime, timedelta
    import uuid
    from app.auth.security import hash_token
    import secrets

    raw_token = secrets.token_urlsafe(32)
    invite = Invite(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        email=email,
        role=role,
        token_hash=hash_token(raw_token),
        invited_by=invited_by,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invite)
    db.commit()
    return invite, raw_token


def test_resolve_valid_invite_com_token_valido(db: Session):
    owner = _register(db, email="convidante@teste.com")
    invite, raw_token = _create_invite(db, owner.tenant_id, owner.id)
    resolved = service.resolve_valid_invite(raw_token, db)
    assert resolved.id == invite.id


def test_resolve_valid_invite_com_token_invalido_levanta_400(db: Session):
    with pytest.raises(HTTPException) as exc:
        service.resolve_valid_invite("token-inexistente", db)
    assert exc.value.status_code == 400


def test_resolve_valid_invite_ja_aceito_levanta_400(db: Session):
    from datetime import datetime

    owner = _register(db, email="convidante2@teste.com")
    invite, raw_token = _create_invite(db, owner.tenant_id, owner.id)
    invite.accepted_at = datetime.utcnow()
    db.commit()
    with pytest.raises(HTTPException) as exc:
        service.resolve_valid_invite(raw_token, db)
    assert exc.value.status_code == 400


def test_resolve_valid_invite_expirado_levanta_400(db: Session):
    from datetime import datetime, timedelta

    owner = _register(db, email="convidante3@teste.com")
    invite, raw_token = _create_invite(db, owner.tenant_id, owner.id)
    invite.expires_at = datetime.utcnow() - timedelta(days=1)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        service.resolve_valid_invite(raw_token, db)
    assert exc.value.status_code == 400


def test_accept_invite_cria_user_com_role_do_convite(db: Session):
    owner = _register(db, email="convidante4@teste.com")
    _, raw_token = _create_invite(db, owner.tenant_id, owner.id, email="novo@teste.com", role=UserRole.admin)

    user = service.accept_invite(
        AcceptInviteRequest(token=raw_token, name="Novo Usuario", password="senha12345"), db
    )

    assert user.email == "novo@teste.com"
    assert user.role == UserRole.admin
    assert user.tenant_id == owner.tenant_id


def test_accept_invite_com_email_ja_cadastrado_levanta_400(db: Session):
    owner = _register(db, email="convidante5@teste.com")
    _register(db, email="jaexiste@teste.com")  # alguem ja se registrou com esse email
    _, raw_token = _create_invite(db, owner.tenant_id, owner.id, email="jaexiste@teste.com")

    with pytest.raises(HTTPException) as exc:
        service.accept_invite(AcceptInviteRequest(token=raw_token, name="X", password="senha12345"), db)
    assert exc.value.status_code == 400


def test_accept_invite_com_senha_curta_levanta_400(db: Session):
    owner = _register(db, email="convidante6@teste.com")
    _, raw_token = _create_invite(db, owner.tenant_id, owner.id)
    with pytest.raises(HTTPException) as exc:
        service.accept_invite(AcceptInviteRequest(token=raw_token, name="X", password="curta"), db)
    assert exc.value.status_code == 400

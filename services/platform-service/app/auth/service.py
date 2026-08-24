"""Regras de negocio de auth — acesso a banco e decisoes de dominio, sem
nada de HTTP (nao conhece Request/status code, so levanta HTTPException
quando a regra e violada). app/auth/routes.py so chama essas funcoes e
devolve o resultado."""
import re
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.identity.models import User, PasswordResetToken, Invite
from app.tenant.models import Tenant
from app.auth.jwt_issue import create_token
from app.auth.schemas import RegisterRequest, LoginRequest, AcceptInviteRequest
from app.auth.security import EMAIL_REGEX, hash_password, verify_password, hash_token
from shared.roles import UserRole
from shared.logging_config import get_logger

logger = get_logger("platform-service")

RESET_TOKEN_TTL_MINUTES = 60  # janela de validade do link de recuperacao de senha


def build_token(user: User) -> dict:
    """Monta o payload do JWT (claims: quem e o usuario, de qual tenant, com
    qual role) e devolve o dict de resposta que o frontend recebe apos
    login/registro/aceite de convite — mesmo formato nos 3 casos."""
    token = create_token({
        "user_id":   user.id,
        "tenant_id": user.tenant_id,
        "role":      user.role.value,
        "is_admin":  user.is_platform_admin
    })
    return {
        "access_token": token,
        "token_type":   "bearer",
        "tenant_id":    user.tenant_id,
        "name":         user.name,
        "role":         user.role.value,
        "is_admin":     user.is_platform_admin
    }


def _generate_tenant_id(business_name: str, db: Session) -> str:
    """Gera o id do tenant a partir do nome da empresa (slug) + 6 caracteres
    aleatorios, pra ficar legivel mas ainda unico. Confere colisao contra o
    banco (raro, mas o sufixo aleatorio nao garante unicidade absoluta) e
    tenta de novo se precisar."""
    slug      = business_name.lower().strip()
    slug      = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    tenant_id = f"{slug}_{uuid.uuid4().hex[:6]}"
    while db.query(Tenant).filter(Tenant.id == tenant_id).first():
        tenant_id = f"{slug}_{uuid.uuid4().hex[:6]}"
    return tenant_id


def register_user(body: RegisterRequest, db: Session) -> User:
    """Cadastro publico: cria um Tenant novo + um User owner pra ele, na
    mesma transacao (se o User falhar, o Tenant tambem nao fica salvo)."""
    if not re.match(EMAIL_REGEX, body.email):
        raise HTTPException(status_code=400, detail="Email inválido")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email ja cadastrado")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 8 caracteres")

    tenant_id = _generate_tenant_id(body.business_name, db)
    try:
        db.add(Tenant(
            id            = tenant_id,
            business_name = body.business_name,
            phone         = body.phone,
            city          = body.city,
            state         = body.state,
            is_active     = True
        ))
        user = User(
            id              = str(uuid.uuid4()),
            tenant_id       = tenant_id,
            email           = body.email,
            hashed_password = hash_password(body.password),
            name            = body.name,
            role            = UserRole.owner,  # quem cria a conta e sempre owner — nao ha registro publico como attendant
            is_active       = True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar conta: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao criar conta")
    return user


def authenticate_user(body: LoginRequest, db: Session) -> User:
    """Autenticacao normal por email+senha. Confere usuario ativo E tenant
    ativo — um usuario valido nao consegue logar se a empresa dele foi
    desativada por um admin."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        # Mensagem generica de proposito (nao diz "email nao existe" vs "senha errada")
        # pra nao ajudar quem esta tentando descobrir emails validos.
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inativo")
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Conta inativa")
    return user


def create_password_reset_token(email: str, db: Session) -> tuple[User, str] | None:
    """Gera um token de reset se o email pertencer a um usuario ativo.
    Devolve None quando nao ha nada a fazer (email nao existe/inativo) — o
    caller (route) trata isso devolvendo a MESMA mensagem generica de
    sucesso, pra nao permitir enumeracao de contas."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return None

    raw_token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        id         = str(uuid.uuid4()),
        user_id    = user.id,
        token_hash = hash_token(raw_token),
        expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
    ))
    db.commit()
    return user, raw_token


def reset_password(token: str, new_password: str, db: Session) -> None:
    """Troca a senha se o token (vindo do link do email) ainda for valido,
    nao expirado e nao usado antes."""
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 8 caracteres")

    token_hash = hash_token(token)
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()

    if (
        not reset_token
        or reset_token.used_at is not None
        or reset_token.expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=400, detail="Link de recuperação inválido ou expirado")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Link de recuperação inválido ou expirado")

    user.hashed_password = hash_password(new_password)
    reset_token.used_at = datetime.utcnow()  # marca como usado — o mesmo link nao funciona 2 vezes
    db.commit()


def resolve_valid_invite(token: str, db: Session) -> Invite:
    """Busca o Invite pelo hash do token recebido e valida que ainda pode ser
    usado (existe, nao foi aceito antes, nao expirou). Compartilhado entre
    preview_invite e accept_invite pra nao duplicar a regra de validade."""
    token_hash = hash_token(token)
    invite = db.query(Invite).filter(Invite.token_hash == token_hash).first()
    if (
        not invite
        or invite.accepted_at is not None
        or invite.expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=400, detail="Convite inválido ou expirado")
    return invite


def accept_invite(body: AcceptInviteRequest, db: Session) -> User:
    """Cria o User de fato com o role definido no Invite (o convidado nao
    escolhe o proprio role), e marca o convite como aceito (uso unico)."""
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 8 caracteres")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Nome é obrigatório")

    invite = resolve_valid_invite(body.token, db)

    if db.query(User).filter(User.email == invite.email).first():
        # Alguem ja se registrou com esse email entre o convite ser gerado e
        # aceito (ex.: se cadastrou direto por conta propria) — convite morre
        # aqui, nao ha o que fazer automaticamente por essa colisao.
        raise HTTPException(status_code=400, detail="Já existe uma conta com este email")

    user = User(
        id              = str(uuid.uuid4()),
        tenant_id       = invite.tenant_id,
        email           = invite.email,
        hashed_password = hash_password(body.password),
        name            = body.name.strip(),
        role            = invite.role,
        is_active       = True,
    )
    db.add(user)
    invite.accepted_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user

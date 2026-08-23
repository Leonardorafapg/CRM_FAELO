from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
import bcrypt
from pydantic import BaseModel
from app.db import get_db
from app.identity.models import User, PasswordResetToken, Invite
from shared.roles import UserRole
from app.tenant.models import Tenant
from app.auth.jwt_issue import create_token
from shared.logging_config import get_logger
from app.infra.email import send_password_reset_email
from app.infra.rate_limit import limiter
from datetime import datetime, timedelta
import hashlib
import secrets
import os
import uuid
import re

logger = get_logger("platform-service")

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_REGEX = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
RESET_TOKEN_TTL_MINUTES = 60  # janela de validade do link de recuperacao de senha


# --- Schemas de entrada de cada rota (validacao automatica do FastAPI) ---

class LoginRequest(BaseModel):
    email:    str
    password: str

class RegisterRequest(BaseModel):
    """Cadastro inicial: cria o Tenant E o primeiro User (sempre owner) na
    mesma chamada — nao existe fluxo de "criar empresa sem dono"."""
    name:          str
    email:         str
    password:      str
    business_name: str
    phone:         str | None = None
    city:          str | None = None
    state:         str | None = None

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token:        str
    new_password: str

class AcceptInviteRequest(BaseModel):
    token:    str
    name:     str
    password: str


# --- Helpers internos (usados so dentro deste arquivo e por routers/users.py) ---

def _hash_password(password: str) -> str:
    """bcrypt com salt aleatorio embutido no proprio hash resultante — nao
    precisa guardar o salt em coluna separada."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _verify_password(plain: str, hashed: str) -> bool:
    """Compara a senha digitada no login com o hash salvo — bcrypt.checkpw
    extrai o salt do proprio hash automaticamente."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def _build_token(user: User) -> dict:
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


# --- Rotas ---

@router.post("/register")
@limiter.limit("10/minute")  # protege contra criacao em massa de contas (bot/scraper)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """Cadastro publico: cria um Tenant novo + um User owner pra ele, na
    mesma transacao (se o User falhar, o Tenant tambem nao fica salvo).
    Devolve token ja logado (nao precisa fazer login separado depois)."""
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
            hashed_password = _hash_password(body.password),
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
    return _build_token(user)

@router.post("/login")
@limiter.limit("10/minute")  # protege contra forca bruta de senha
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    """Autenticacao normal por email+senha. Confere usuario ativo E tenant
    ativo — um usuario valido nao consegue logar se a empresa dele foi
    desativada por um admin."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not _verify_password(body.password, user.hashed_password):
        # Mensagem generica de proposito (nao diz "email nao existe" vs "senha errada")
        # pra nao ajudar quem esta tentando descobrir emails validos.
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inativo")
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Conta inativa")
    return _build_token(user)

def _hash_token(token: str) -> str:
    """sha256 usado tanto pra tokens de reset de senha quanto pra tokens de
    convite — nunca guardamos o valor puro no banco, so o hash. Reusado por
    routers/users.py na criacao/validacao de convites."""
    return hashlib.sha256(token.encode()).hexdigest()

@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Inicia o fluxo de recuperacao de senha: gera um token aleatorio,
    guarda so o hash dele no banco, e envia o link por email. Sempre devolve
    a MESMA mensagem genérica, exista ou nao o email cadastrado — evita que
    alguem descubra quais emails tem conta so testando este endpoint
    (enumeracao de contas)."""
    generic_response = {"message": "Se o email existir, enviaremos um link de recuperacao."}

    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.is_active:
        return generic_response

    raw_token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        id         = str(uuid.uuid4()),
        user_id    = user.id,
        token_hash = _hash_token(raw_token),
        expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
    ))
    db.commit()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_url = f"{frontend_url}/reset-password?token={raw_token}"
    await send_password_reset_email(user.email, reset_url)

    return generic_response

@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Segunda etapa do fluxo de recuperacao: troca a senha se o token (vindo
    do link do email) ainda for valido, nao expirado e nao usado antes."""
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 8 caracteres")

    token_hash = _hash_token(body.token)
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

    user.hashed_password = _hash_password(body.new_password)
    reset_token.used_at = datetime.utcnow()  # marca como usado — o mesmo link nao funciona 2 vezes
    db.commit()

    return {"message": "Senha redefinida com sucesso"}


def _resolve_valid_invite(token: str, db: Session) -> Invite:
    """Busca o Invite pelo hash do token recebido e valida que ainda pode ser
    usado (existe, nao foi aceito antes, nao expirou). Compartilhado entre
    preview_invite e accept_invite pra nao duplicar a regra de validade."""
    token_hash = _hash_token(token)
    invite = db.query(Invite).filter(Invite.token_hash == token_hash).first()
    if (
        not invite
        or invite.accepted_at is not None
        or invite.expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=400, detail="Convite inválido ou expirado")
    return invite


@router.get("/invite/{token}")
@limiter.limit("30/minute")
def preview_invite(request: Request, token: str, db: Session = Depends(get_db)):
    """Rota publica (sem login) que a tela de "aceitar convite" chama ANTES
    do usuario preencher nome/senha — mostra pra qual empresa/role ele foi
    convidado, sem expor nada sensivel."""
    invite = _resolve_valid_invite(token, db)
    tenant = db.query(Tenant).filter(Tenant.id == invite.tenant_id).first()
    return {
        "email":       invite.email,
        "role":        invite.role.value,
        "tenant_name": tenant.business_name if tenant else None,
    }


@router.post("/accept-invite")
@limiter.limit("10/minute")
def accept_invite(request: Request, body: AcceptInviteRequest, db: Session = Depends(get_db)):
    """Ultima etapa do convite: cria o User de fato com o role definido no
    Invite (o convidado nao escolhe o proprio role), e marca o convite como
    aceito (uso unico). Devolve token ja logado, igual ao /register."""
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 8 caracteres")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Nome é obrigatório")

    invite = _resolve_valid_invite(body.token, db)

    if db.query(User).filter(User.email == invite.email).first():
        # Alguem ja se registrou com esse email entre o convite ser gerado e
        # aceito (ex.: se cadastrou direto por conta propria) — convite morre
        # aqui, nao ha o que fazer automaticamente por essa colisao.
        raise HTTPException(status_code=400, detail="Já existe uma conta com este email")

    user = User(
        id              = str(uuid.uuid4()),
        tenant_id       = invite.tenant_id,
        email           = invite.email,
        hashed_password = _hash_password(body.password),
        name            = body.name.strip(),
        role            = invite.role,
        is_active       = True,
    )
    db.add(user)
    invite.accepted_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return _build_token(user)

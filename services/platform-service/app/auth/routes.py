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
RESET_TOKEN_TTL_MINUTES = 60


class LoginRequest(BaseModel):
    email:    str
    password: str

class RegisterRequest(BaseModel):
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

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def _build_token(user: User) -> dict:
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
    slug      = business_name.lower().strip()
    slug      = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    tenant_id = f"{slug}_{uuid.uuid4().hex[:6]}"
    while db.query(Tenant).filter(Tenant.id == tenant_id).first():
        tenant_id = f"{slug}_{uuid.uuid4().hex[:6]}"
    return tenant_id

@router.post("/register")
@limiter.limit("10/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
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
            role            = UserRole.owner,
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
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inativo")
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Conta inativa")
    return _build_token(user)

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
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
    reset_token.used_at = datetime.utcnow()
    db.commit()

    return {"message": "Senha redefinida com sucesso"}


def _resolve_valid_invite(token: str, db: Session) -> Invite:
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
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 8 caracteres")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Nome é obrigatório")

    invite = _resolve_valid_invite(body.token, db)

    if db.query(User).filter(User.email == invite.email).first():
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

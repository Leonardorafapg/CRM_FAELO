"""Rotas de auth — so fazem parsing/roteamento HTTP. Toda regra de negocio
vive em app/auth/service.py; schemas em app/auth/schemas.py."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.auth import service
from app.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    AcceptInviteRequest,
)
from app.tenant.models import Tenant
from app.infra.email import send_password_reset_email
from app.infra.rate_limit import limiter
import os

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
@limiter.limit("10/minute")  # protege contra criacao em massa de contas (bot/scraper)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """Devolve token ja logado — nao precisa fazer login separado depois."""
    user = service.register_user(body, db)
    return service.build_token(user)


@router.post("/login")
@limiter.limit("10/minute")  # protege contra forca bruta de senha
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = service.authenticate_user(body, db)
    return service.build_token(user)


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Sempre devolve a MESMA mensagem generica, exista ou nao o email
    cadastrado — evita enumeracao de contas."""
    generic_response = {"message": "Se o email existir, enviaremos um link de recuperacao."}

    result = service.create_password_reset_token(body.email, db)
    if result is None:
        return generic_response

    user, raw_token = result
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_url = f"{frontend_url}/reset-password?token={raw_token}"
    await send_password_reset_email(user.email, reset_url)

    return generic_response


@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    service.reset_password(body.token, body.new_password, db)
    return {"message": "Senha redefinida com sucesso"}


@router.get("/invite/{token}")
@limiter.limit("30/minute")
def preview_invite(request: Request, token: str, db: Session = Depends(get_db)):
    """Rota publica (sem login) que a tela de "aceitar convite" chama ANTES
    do usuario preencher nome/senha — mostra pra qual empresa/role ele foi
    convidado, sem expor nada sensivel."""
    invite = service.resolve_valid_invite(token, db)
    tenant = db.query(Tenant).filter(Tenant.id == invite.tenant_id).first()
    return {
        "email":       invite.email,
        "role":        invite.role.value,
        "tenant_name": tenant.business_name if tenant else None,
    }


@router.post("/accept-invite")
@limiter.limit("10/minute")
def accept_invite(request: Request, body: AcceptInviteRequest, db: Session = Depends(get_db)):
    """Ultima etapa do convite — devolve token ja logado, igual ao /register."""
    user = service.accept_invite(body, db)
    return service.build_token(user)

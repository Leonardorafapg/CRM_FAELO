"""Schemas de entrada das rotas de auth (validacao automatica do FastAPI)."""
from pydantic import BaseModel


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

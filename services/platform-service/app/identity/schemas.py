"""Schemas de entrada das rotas de equipe/convites."""
import re
from pydantic import BaseModel, field_validator

from shared.roles import UserRole
from app.auth.security import EMAIL_REGEX


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
    """PATCH parcial: so mexe no campo que vier preenchido (role e/ou
    is_active), os dois opcionais e independentes um do outro."""
    role:      UserRole | None = None
    is_active: bool | None = None

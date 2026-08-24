from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base
from shared.roles import UserRole  # unica fonte de verdade do enum, compartilhada com os outros servicos


class User(Base):
    """Uma pessoa com login no painel, pertencente a UM tenant. Nao confundir
    com Contact (do crm-service) — User e quem OPERA o sistema, Contact e o
    cliente sendo atendido."""
    __tablename__ = "users"

    id                = Column(String, primary_key=True)
    tenant_id         = Column(String, ForeignKey("tenants.id"), nullable=False)
    email             = Column(String, unique=True, nullable=False)  # unico GLOBALMENTE, nao so por tenant
    hashed_password   = Column(String, nullable=False)                # nunca a senha em texto puro — ver auth/security.py::hash_password
    name              = Column(String, nullable=True)
    role              = Column(Enum(UserRole), default=UserRole.owner)  # nivel de permissao dentro do tenant
    is_platform_admin = Column(Boolean, default=False)  # super-admin cross-tenant (equipe da Faelo, nao do cliente)
    is_active         = Column(Boolean, default=True)   # False = usuario desativado, nao consegue mais logar
    created_at        = Column(DateTime, server_default=func.now())

    tenant            = relationship("Tenant", back_populates="users")


class PasswordResetToken(Base):
    """Token de recuperacao de senha. Guardamos so o hash (sha256) do token,
    nunca o valor puro — o valor puro so existe no link enviado por email.
    used_at setado torna o token inutilizavel mesmo dentro da janela de
    expiracao (uso unico)."""
    __tablename__ = "password_reset_tokens"

    id           = Column(String, primary_key=True)
    user_id      = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash   = Column(String, nullable=False, unique=True)  # sha256 do token que foi enviado por email
    expires_at   = Column(DateTime, nullable=False)              # janela de validade (1h, ver ROUTES.RESET_TOKEN_TTL_MINUTES)
    used_at      = Column(DateTime, nullable=True)                # setado no primeiro uso — impede reuso do link
    created_at   = Column(DateTime, server_default=func.now())

    user         = relationship("User")

    __table_args__ = (
        Index("ix_password_reset_tokens_user", "user_id"),
    )


class Invite(Base):
    """Convite pra alguem entrar num tenant existente como User. Mesmo padrao
    do PasswordResetToken: so o hash do token e guardado. Gerar um novo
    convite pro mesmo email invalida o anterior (ver routers/users.py::criar_convite)
    — nao existe update de convite, so substituicao."""
    __tablename__ = "invites"

    id           = Column(String, primary_key=True)
    tenant_id    = Column(String, ForeignKey("tenants.id"), nullable=False)
    email        = Column(String, nullable=False)                # email de quem foi convidado (ainda nao tem User)
    role         = Column(Enum(UserRole), nullable=False)         # role que o convidado vai receber ao aceitar
    token_hash   = Column(String, nullable=False, unique=True)
    invited_by   = Column(String, ForeignKey("users.id"), nullable=False)  # quem enviou o convite
    expires_at   = Column(DateTime, nullable=False)                # janela de validade (7 dias, ver routers/users.py::INVITE_TTL_DAYS)
    accepted_at  = Column(DateTime, nullable=True)                 # setado quando o convidado aceita — uso unico
    created_at   = Column(DateTime, server_default=func.now())

    tenant       = relationship("Tenant")
    inviter      = relationship("User")

    __table_args__ = (
        Index("ix_invites_tenant", "tenant_id"),
    )

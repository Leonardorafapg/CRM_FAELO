from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base
from shared.roles import UserRole  # unica fonte de verdade do enum, compartilhada com os outros servicos


class User(Base):
    __tablename__ = "users"

    id                = Column(String, primary_key=True)
    tenant_id         = Column(String, ForeignKey("tenants.id"), nullable=False)
    email             = Column(String, unique=True, nullable=False)
    hashed_password   = Column(String, nullable=False)
    name              = Column(String, nullable=True)
    role              = Column(Enum(UserRole), default=UserRole.owner)
    is_platform_admin = Column(Boolean, default=False)
    is_active         = Column(Boolean, default=True)
    created_at        = Column(DateTime, server_default=func.now())

    tenant            = relationship("Tenant", back_populates="users")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id           = Column(String, primary_key=True)
    user_id      = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash   = Column(String, nullable=False, unique=True)
    expires_at   = Column(DateTime, nullable=False)
    used_at      = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, server_default=func.now())

    user         = relationship("User")

    __table_args__ = (
        Index("ix_password_reset_tokens_user", "user_id"),
    )


class Invite(Base):
    __tablename__ = "invites"

    id           = Column(String, primary_key=True)
    tenant_id    = Column(String, ForeignKey("tenants.id"), nullable=False)
    email        = Column(String, nullable=False)
    role         = Column(Enum(UserRole), nullable=False)
    token_hash   = Column(String, nullable=False, unique=True)
    invited_by   = Column(String, ForeignKey("users.id"), nullable=False)
    expires_at   = Column(DateTime, nullable=False)
    accepted_at  = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, server_default=func.now())

    tenant       = relationship("Tenant")
    inviter      = relationship("User")

    __table_args__ = (
        Index("ix_invites_tenant", "tenant_id"),
    )

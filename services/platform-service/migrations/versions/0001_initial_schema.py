"""schema inicial do platform-service (tenants, business_hours, users, password_reset_tokens, invites)

Revision ID: 0001
Revises:
Create Date: 2026-08-23

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tenant: raiz do isolamento multi-tenant + config do bot/IA usada pelo
    # conversation-service (via chamada interna, nao replicacao de tabela).
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("business_name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("whatsapp", sa.String(), nullable=True),
        sa.Column("instagram", sa.String(), nullable=True),
        sa.Column("facebook", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("fallback_message", sa.Text(), nullable=True),
        sa.Column("ai_provider", sa.String(), server_default="groq"),
        sa.Column("groq_key", sa.String(), nullable=True),
        sa.Column("openrouter_model", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )

    # Um registro por dia da semana por tenant (garantido pela UniqueConstraint).
    op.create_table(
        "business_hours",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("slots", sa.JSON(), nullable=True),
        sa.Column("is_closed", sa.Boolean(), server_default=sa.false()),
        sa.UniqueConstraint("tenant_id", "day_of_week", name="_tenant_day_uc"),
    )

    # Enum reaproveitado em users.role e invites.role — precisa ser dropado
    # explicitamente no downgrade (Postgres nao remove o tipo so por dropar
    # as tabelas que o usam).
    user_role_enum = sa.Enum("owner", "admin", "attendant", name="userrole")

    # Quem loga no painel — email unico GLOBALMENTE (nao so por tenant).
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("role", user_role_enum, server_default="owner"),
        sa.Column("is_platform_admin", sa.Boolean(), server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # So o hash (sha256) do token fica aqui — o valor puro so existe no link
    # que foi mandado por email, nunca persistido.
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_password_reset_tokens_user", "password_reset_tokens", ["user_id"])

    # Mesmo padrao de token hasheado do password_reset_tokens, mas pra
    # convite de entrada num tenant (email ainda nao tem User).
    op.create_table(
        "invites",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("invited_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_invites_tenant", "invites", ["tenant_id"])


def downgrade() -> None:
    # Ordem inversa da criacao — respeita as foreign keys (nao da pra dropar
    # "tenants" antes de "users", que referencia "tenants.id").
    op.drop_table("invites")
    op.drop_table("password_reset_tokens")
    op.drop_table("users")
    op.drop_table("business_hours")
    op.drop_table("tenants")
    # O tipo enum precisa ser dropado a parte, depois das tabelas que o usam.
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)

"""renomeia campos de IA pra nomes genericos de provider + adiciona faq_enabled

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-27

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # groq_key/openrouter_model eram nomes amarrados a um provider especifico
    # — viram genericos (ai_api_key/ai_model) pra trocar de provider sem
    # precisar renomear coluna de novo.
    op.alter_column("tenants", "groq_key", new_column_name="ai_api_key")
    op.alter_column("tenants", "openrouter_model", new_column_name="ai_model")

    # Provider inicial passa a ser deepseek (nao mais groq).
    op.execute("UPDATE tenants SET ai_provider = 'deepseek' WHERE ai_provider = 'groq'")
    op.alter_column("tenants", "ai_provider", server_default="deepseek")

    op.add_column("tenants", sa.Column("faq_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("tenants", "faq_enabled")
    op.alter_column("tenants", "ai_provider", server_default="groq")
    op.execute("UPDATE tenants SET ai_provider = 'groq' WHERE ai_provider = 'deepseek'")
    op.alter_column("tenants", "ai_model", new_column_name="openrouter_model")
    op.alter_column("tenants", "ai_api_key", new_column_name="groq_key")

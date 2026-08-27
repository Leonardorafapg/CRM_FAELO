"""schema inicial do ai-service (faq_items)

Revision ID: 0001
Revises:
Create Date: 2026-08-27

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "faq_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("pergunta", sa.Text(), nullable=False),
        sa.Column("resposta", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_faq_items_tenant_created", "faq_items", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_table("faq_items")

"""schema inicial do whatsapp-service (connections, sessions, messages)

Revision ID: 0001
Revises:
Create Date: 2026-08-25

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connections",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("instance_name", sa.String(), nullable=False, unique=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="connecting"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_connections_tenant", "connections", ["tenant_id"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), primary_key=True),  # "{tenant_id}:{phone}"
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("connection_id", sa.String(), sa.ForeignKey("connections.id"), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("contact_name", sa.String(), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_activity", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_sessions_tenant_last_activity", "sessions", ["tenant_id", "last_activity"])
    op.create_index("ix_sessions_connection", "sessions", ["connection_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("evolution_message_id", sa.String(), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_messages_session_created", "messages", ["session_id", "created_at"])


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("sessions")
    op.drop_table("connections")

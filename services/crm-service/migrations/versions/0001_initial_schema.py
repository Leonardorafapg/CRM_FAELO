"""schema inicial do crm-service (pipelines, stages, contact_statuses, contacts)

Revision ID: 0001
Revises:
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Multi-pipeline desde a v1 — tenant_id sem FK real (Tenant vive no
    # platform-service, banco diferente).
    op.create_table(
        "pipelines",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_pipelines_tenant", "pipelines", ["tenant_id"])

    # Sem attendance_mode de proposito (fase de CRM manual) e sem
    # tenant_id proprio — deriva de stages.pipeline_id -> pipelines.tenant_id.
    op.create_table(
        "stages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("pipeline_id", sa.String(), sa.ForeignKey("pipelines.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_entry", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_stages_pipeline_order", "stages", ["pipeline_id", "order"])

    op.create_table(
        "contact_statuses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
    )
    op.create_index("ix_contact_statuses_tenant_order", "contact_statuses", ["tenant_id", "order"])

    # UniqueConstraint(tenant_id, phone): impede cadastro duplicado do
    # mesmo telefone dentro de um tenant.
    op.create_table(
        "contacts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status_id", sa.String(), sa.ForeignKey("contact_statuses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to", sa.String(), nullable=True),
        sa.Column("stage_id", sa.String(), sa.ForeignKey("stages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, onupdate=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "phone", name="_tenant_phone_uc"),
    )
    op.create_index("ix_contacts_tenant_status", "contacts", ["tenant_id", "status_id"])
    op.create_index("ix_contacts_tenant_stage", "contacts", ["tenant_id", "stage_id"])


def downgrade() -> None:
    op.drop_table("contacts")
    op.drop_table("contact_statuses")
    op.drop_table("stages")
    op.drop_table("pipelines")

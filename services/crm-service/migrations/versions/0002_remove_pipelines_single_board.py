"""remove multi-pipeline: quadro unico e fixo por tenant, Stage vira recurso direto do tenant

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
    # 1. Adiciona tenant_id em stages (nullable por enquanto) e faz backfill
    #    a partir do pipeline que a stage pertencia — depois disso, stage nao
    #    depende mais de pipeline pra saber de qual tenant e.
    op.add_column("stages", sa.Column("tenant_id", sa.String(), nullable=True))
    op.execute(
        """
        UPDATE stages
        SET tenant_id = pipelines.tenant_id
        FROM pipelines
        WHERE stages.pipeline_id = pipelines.id
        """
    )
    op.alter_column("stages", "tenant_id", nullable=False)

    # 2. Troca o indice antigo (pipeline_id, order) pelo novo (tenant_id, order).
    op.drop_index("ix_stages_pipeline_order", table_name="stages")
    op.create_index("ix_stages_tenant_order", "stages", ["tenant_id", "order"])

    # 3. Remove a FK/coluna pipeline_id — Stage nao pertence mais a um Pipeline.
    op.drop_column("stages", "pipeline_id")

    # 4. Remove a tabela pipelines inteira (multi-quadro descontinuado —
    #    quadro passa a ser unico e fixo por tenant, so as Stages sao
    #    configuraveis).
    op.drop_index("ix_pipelines_tenant", table_name="pipelines")
    op.drop_table("pipelines")


def downgrade() -> None:
    # Best-effort: recria a estrutura de pipelines, mas a associacao
    # stage -> pipeline original nao e recuperavel (foi perdida no upgrade).
    # Cria 1 pipeline "Padrao" por tenant que ja tem stage, e reaponta todas
    # as stages daquele tenant pra ele — nao reconstroi multi-pipeline.
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

    op.add_column("stages", sa.Column("pipeline_id", sa.String(), nullable=True))

    connection = op.get_bind()
    tenant_ids = [row[0] for row in connection.execute(sa.text("SELECT DISTINCT tenant_id FROM stages"))]
    for tenant_id in tenant_ids:
        pipeline_id = str(__import__("uuid").uuid4())
        connection.execute(
            sa.text(
                "INSERT INTO pipelines (id, tenant_id, name, is_default) VALUES (:id, :tenant_id, 'Padrão', true)"
            ),
            {"id": pipeline_id, "tenant_id": tenant_id},
        )
        connection.execute(
            sa.text("UPDATE stages SET pipeline_id = :pipeline_id WHERE tenant_id = :tenant_id"),
            {"pipeline_id": pipeline_id, "tenant_id": tenant_id},
        )

    op.alter_column("stages", "pipeline_id", nullable=False)
    op.create_foreign_key("stages_pipeline_id_fkey", "stages", "pipelines", ["pipeline_id"], ["id"])

    op.drop_index("ix_stages_tenant_order", table_name="stages")
    op.create_index("ix_stages_pipeline_order", "stages", ["pipeline_id", "order"])
    op.drop_column("stages", "tenant_id")

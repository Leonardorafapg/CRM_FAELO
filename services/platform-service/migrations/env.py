from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()  # nao usa override=True: main.py ja carregou .env antes de chamar run_migrations() (ver main.py), e em testes o conftest.py seta os env vars manualmente antes -- override=True aqui sobrescrevia esses valores toda vez que a migration rodava no boot, quebrando a suite

from app.db import Base
# Todo modulo que define tabela precisa ser importado aqui — e o ato de
# importar que registra as classes em Base.metadata.
from app.tenant import models as _tenant_models      # noqa: F401  Tenant, BusinessHours
from app.identity import models as _identity_models  # noqa: F401  User, PasswordResetToken, Invite

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# "%" precisa ser escapado como "%%" porque o ConfigParser do alembic.ini usa
# "%" como caractere especial de interpolacao — sem isso, uma senha com "%"
# (ex.: "%40" url-encoded) quebra a leitura do arquivo de config.
db_url = os.environ["DATABASE_URL"].replace("%", "%%")
config.set_main_option("sqlalchemy.url", db_url)

# target_metadata e o que o `alembic revision --autogenerate` compara contra
# o estado atual do banco pra gerar o diff — precisa ser o metadata que JA
# tem todos os models importados acima registrados nele.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera o SQL da migration sem se conectar ao banco de verdade (usado
    com `alembic upgrade head --sql`, pra revisar o SQL antes de rodar em
    producao) — nao usado no fluxo normal de dev."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Fluxo normal: conecta de verdade no banco (via sqlalchemy.url do
    alembic.ini/env var) e aplica a migration dentro de uma transacao."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # sem pool de conexao — a migration roda uma vez e fecha, nao precisa reusar conexao
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


# Alembic decide qual dos dois fluxos usar com base em como foi invocado
# (--sql = offline, comando normal = online).
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

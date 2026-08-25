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
from app.pipeline import models as _pipeline_models    # noqa: F401  Pipeline, Stage
from app.contacts import models as _contacts_models    # noqa: F401  Contact, ContactStatus

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db_url = os.environ["DATABASE_URL"].replace("%", "%%")
config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

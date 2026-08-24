"""Fixtures compartilhadas por toda a suite (ver TESTING.md pro padrao geral).

IMPORTANTE: as env vars abaixo precisam ser definidas ANTES de qualquer
`import app...` — app/db.py, app/auth/jwt_issue.py e shared/jwt_verify.py
leem a env e criam engine/validam segredo no momento do import do modulo,
nao sob demanda. Por isso ficam no topo do arquivo, antes dos outros imports.
"""
import os

os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:Minhasenha%40123@localhost:5432/crm_faelo_platform_test",
)
os.environ["JWT_SECRET_KEY"] = "test-secret-key-nao-usar-em-producao"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRE_HOURS"] = "8"
os.environ["INTERNAL_SERVICE_KEY"] = "test-internal-key"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["RESEND_API_KEY"] = ""  # vazio de proposito: email nunca sai de verdade nos testes

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base, engine
import app.tenant.models  # noqa: F401 — registra Tenant/BusinessHours em Base.metadata
import app.identity.models  # noqa: F401 — registra User/PasswordResetToken/Invite


@pytest.fixture(scope="session", autouse=True)
def _schema():
    """Cria o schema uma vez por sessao de testes e derruba no final — o
    banco de teste (crm_faelo_platform_test) nao guarda estado entre rodadas."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db() -> Session:
    """Uma conexao + transacao externa por teste, com um SAVEPOINT interno
    que e reaberto automaticamente toda vez que o codigo sob teste chama
    `db.commit()` — assim o service/rota testado pode commitar normalmente,
    mas nada sobrevive ao rollback da transacao externa no final do teste."""
    connection = engine.connect()
    outer_transaction = connection.begin()
    TestSession = sessionmaker(bind=connection)
    session = TestSession()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session):
    """TestClient com get_db substituido pela sessao de teste (mesma
    transacao revertida no final) e o rate limiter resetado — sem isso,
    testes que batem varias vezes na mesma rota (ex.: login com senha errada
    em loop) tomariam 429 do slowapi em vez do status esperado."""
    from fastapi.testclient import TestClient
    from main import app
    from app.db import get_db
    from app.infra.rate_limit import limiter

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    limiter.reset()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

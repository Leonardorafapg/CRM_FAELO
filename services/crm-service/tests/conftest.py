"""Fixtures compartilhadas por toda a suite (ver docs/TESTING.md). Mesmo
padrao do platform-service — ver comentarios la pra detalhe de cada fixture."""
import os

os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:Minhasenha%40123@localhost:5432/crm_faelo_crm_test",
)
os.environ["JWT_SECRET_KEY"] = "test-secret-key-nao-usar-em-producao"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["INTERNAL_SERVICE_KEY"] = "test-internal-key"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"

import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base, engine
import app.pipeline.models  # noqa: F401 — registra Pipeline/Stage em Base.metadata
import app.contacts.models  # noqa: F401 — registra Contact/ContactStatus
from shared.roles import UserRole


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db() -> Session:
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
    transacao revertida no final)."""
    from fastapi.testclient import TestClient
    from main import app
    from app.db import get_db

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_token(tenant_id: str, role: UserRole = UserRole.owner, is_admin: bool = False) -> str:
    """Gera um JWT valido pra testes de rota, sem precisar do
    platform-service rodando — mesma logica de emissao (jose.jwt.encode com
    o SECRET_KEY de teste), so pra montar o header Authorization."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    payload = {
        "user_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "role": role.value,
        "is_admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET_KEY"], algorithm=os.environ["JWT_ALGORITHM"])


def auth_headers(tenant_id: str, role: UserRole = UserRole.owner, is_admin: bool = False) -> dict:
    return {"Authorization": f"Bearer {make_token(tenant_id, role, is_admin)}"}

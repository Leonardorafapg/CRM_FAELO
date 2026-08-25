import uuid
from unittest.mock import AsyncMock, patch

from tests.conftest import auth_headers
from shared.roles import UserRole
from app.connections.models import Connection


def _create_connection_mocks():
    """Mocka as chamadas HTTP a Evolution API — nunca a real."""
    create_mock = AsyncMock(return_value={"qrcode": {"base64": "data:image/png;base64,FAKE"}})
    webhook_mock = AsyncMock(return_value=None)
    delete_mock = AsyncMock(return_value=None)
    return create_mock, webhook_mock, delete_mock


def test_admin_can_create_connection(client, db):
    tenant_id = str(uuid.uuid4())
    create_mock, webhook_mock, _ = _create_connection_mocks()

    with patch("app.connections.service.evolution_client.create_instance", create_mock), \
         patch("app.connections.service.evolution_client.set_webhook", webhook_mock):
        resp = client.post("/connections", headers=auth_headers(tenant_id, UserRole.admin))

    assert resp.status_code == 200
    body = resp.json()
    assert body["connection"]["status"] == "connecting"
    assert body["qrcode_base64"] == "data:image/png;base64,FAKE"
    create_mock.assert_awaited_once()
    webhook_mock.assert_awaited_once()


def test_attendant_cannot_create_connection(client, db):
    tenant_id = str(uuid.uuid4())
    resp = client.post("/connections", headers=auth_headers(tenant_id, UserRole.attendant))
    assert resp.status_code == 403


def test_criar_segunda_conexao_do_mesmo_tenant_retorna_400(client, db):
    """Limite fixo de 1 conexao por tenant nesta fase (ver
    MAX_CONNECTIONS_PER_TENANT em app/connections/service.py)."""
    tenant_id = str(uuid.uuid4())
    create_mock, webhook_mock, _ = _create_connection_mocks()

    with patch("app.connections.service.evolution_client.create_instance", create_mock), \
         patch("app.connections.service.evolution_client.set_webhook", webhook_mock):
        resp1 = client.post("/connections", headers=auth_headers(tenant_id, UserRole.admin))
        resp2 = client.post("/connections", headers=auth_headers(tenant_id, UserRole.admin))

    assert resp1.status_code == 200
    assert resp2.status_code == 400
    create_mock.assert_awaited_once()  # segunda tentativa nao chega a chamar a Evolution


def test_criar_conexao_apos_excluir_a_unica_existente_funciona(client, db):
    tenant_id = str(uuid.uuid4())
    create_mock, webhook_mock, delete_mock = _create_connection_mocks()

    with patch("app.connections.service.evolution_client.create_instance", create_mock), \
         patch("app.connections.service.evolution_client.set_webhook", webhook_mock):
        resp1 = client.post("/connections", headers=auth_headers(tenant_id, UserRole.admin))
    conn_id = resp1.json()["connection"]["id"]

    with patch("app.connections.service.evolution_client.delete_instance", delete_mock):
        resp_del = client.delete(f"/connections/{conn_id}", headers=auth_headers(tenant_id, UserRole.admin))
    assert resp_del.status_code == 200

    with patch("app.connections.service.evolution_client.create_instance", create_mock), \
         patch("app.connections.service.evolution_client.set_webhook", webhook_mock):
        resp2 = client.post("/connections", headers=auth_headers(tenant_id, UserRole.admin))
    assert resp2.status_code == 200


def test_list_connections_scoped_by_tenant(client, db):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    db.add(Connection(id=str(uuid.uuid4()), tenant_id=tenant_a, instance_name="inst-a", status="connected"))
    db.add(Connection(id=str(uuid.uuid4()), tenant_id=tenant_b, instance_name="inst-b", status="connected"))
    db.commit()

    resp = client.get("/connections", headers=auth_headers(tenant_a, UserRole.attendant))
    assert resp.status_code == 200
    names = [c["instance_name"] for c in resp.json()]
    assert names == ["inst-a"]


def test_admin_can_delete_connection(client, db):
    tenant_id = str(uuid.uuid4())
    conn = Connection(id=str(uuid.uuid4()), tenant_id=tenant_id, instance_name="inst-x", status="connected")
    db.add(conn)
    db.commit()

    with patch("app.connections.service.evolution_client.delete_instance", AsyncMock(return_value=None)) as delete_mock:
        resp = client.delete(f"/connections/{conn.id}", headers=auth_headers(tenant_id, UserRole.owner))

    assert resp.status_code == 200
    delete_mock.assert_awaited_once_with("inst-x")


def test_attendant_cannot_delete_connection(client, db):
    tenant_id = str(uuid.uuid4())
    conn = Connection(id=str(uuid.uuid4()), tenant_id=tenant_id, instance_name="inst-y", status="connected")
    db.add(conn)
    db.commit()

    resp = client.delete(f"/connections/{conn.id}", headers=auth_headers(tenant_id, UserRole.attendant))
    assert resp.status_code == 403


def test_cannot_delete_connection_of_other_tenant(client, db):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    conn = Connection(id=str(uuid.uuid4()), tenant_id=tenant_a, instance_name="inst-z", status="connected")
    db.add(conn)
    db.commit()

    resp = client.delete(f"/connections/{conn.id}", headers=auth_headers(tenant_b, UserRole.owner))
    assert resp.status_code == 404

"""Integration tests de app/routers/contacts.py e contact_statuses.py."""
import uuid

from fastapi.testclient import TestClient
from shared.roles import UserRole

from tests.conftest import auth_headers


def _tenant() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


def test_criar_e_listar_contact_como_attendant(client: TestClient):
    """CRUD de contact e operacional — aberto a attendant, diferente de
    stages/status (config, restritos a admin)."""
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.attendant)

    resp = client.post("/contacts", json={"name": "Carlos", "phone": "11999999999"}, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/contacts", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_criar_contact_com_telefone_duplicado_retorna_400(client: TestClient):
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.owner)
    client.post("/contacts", json={"name": "Carlos", "phone": "11999999999"}, headers=headers)
    resp = client.post("/contacts", json={"name": "Outro", "phone": "11999999999"}, headers=headers)
    assert resp.status_code == 400


def test_isolamento_multi_tenant_em_contacts(client: TestClient):
    tenant_a, tenant_b = _tenant(), _tenant()
    resp = client.post("/contacts", json={"name": "Carlos", "phone": "11999999999"}, headers=auth_headers(tenant_a, UserRole.owner))
    contact_id = resp.json()["id"]

    resp = client.get(f"/contacts/{contact_id}", headers=auth_headers(tenant_b, UserRole.owner))
    assert resp.status_code == 404

    resp = client.get("/contacts", headers=auth_headers(tenant_b, UserRole.owner))
    assert resp.json() == []


def test_mover_contact_no_kanban_via_patch(client: TestClient):
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.attendant)
    stage_id = client.post(
        "/stages", json={"name": "Proposta"}, headers=auth_headers(tenant, UserRole.owner)
    ).json()["id"]
    contact_id = client.post("/contacts", json={"name": "Carlos", "phone": "11999999999"}, headers=headers).json()["id"]

    resp = client.patch(f"/contacts/{contact_id}", json={"stage_id": stage_id}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["stage_id"] == stage_id


def test_filtrar_contacts_por_stage(client: TestClient):
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.owner)
    stage_a = client.post("/stages", json={"name": "Entrada"}, headers=headers).json()["id"]
    stage_b = client.post("/stages", json={"name": "Proposta"}, headers=headers).json()["id"]
    client.post("/contacts", json={"name": "A", "phone": "1", "stage_id": stage_a}, headers=headers)
    client.post("/contacts", json={"name": "B", "phone": "2", "stage_id": stage_b}, headers=headers)

    resp = client.get(f"/contacts?stage_id={stage_a}", headers=headers)
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "A"


def test_deletar_contact(client: TestClient):
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.owner)
    contact_id = client.post("/contacts", json={"name": "Carlos", "phone": "11999999999"}, headers=headers).json()["id"]

    resp = client.delete(f"/contacts/{contact_id}", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/contacts/{contact_id}", headers=headers)
    assert resp.status_code == 404


def test_attendant_nao_pode_criar_contact_status(client: TestClient):
    tenant = _tenant()
    resp = client.post("/contact-statuses", json={"name": "Ativo"}, headers=auth_headers(tenant, UserRole.attendant))
    assert resp.status_code == 403


def test_criar_e_listar_contact_status_como_admin(client: TestClient):
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.admin)
    resp = client.post("/contact-statuses", json={"name": "Ativo"}, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/contact-statuses", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

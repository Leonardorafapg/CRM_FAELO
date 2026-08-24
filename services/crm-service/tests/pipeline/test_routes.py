"""Integration tests de app/routers/pipelines.py e stages.py — RBAC e
isolamento multi-tenant sao o foco (ver docs/TESTING.md)."""
import uuid

from fastapi.testclient import TestClient
from shared.roles import UserRole

from tests.conftest import auth_headers


def _tenant() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


def test_criar_e_listar_pipeline_como_owner(client: TestClient):
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.owner)

    resp = client.post("/pipelines", json={"name": "Vendas"}, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/pipelines", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_attendant_nao_pode_criar_pipeline(client: TestClient):
    tenant = _tenant()
    resp = client.post("/pipelines", json={"name": "Vendas"}, headers=auth_headers(tenant, UserRole.attendant))
    assert resp.status_code == 403


def test_attendant_pode_listar_pipeline(client: TestClient):
    tenant = _tenant()
    client.post("/pipelines", json={"name": "Vendas"}, headers=auth_headers(tenant, UserRole.owner))
    resp = client.get("/pipelines", headers=auth_headers(tenant, UserRole.attendant))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_isolamento_multi_tenant_em_pipelines(client: TestClient):
    tenant_a, tenant_b = _tenant(), _tenant()
    resp = client.post("/pipelines", json={"name": "Vendas A"}, headers=auth_headers(tenant_a, UserRole.owner))
    pipeline_id = resp.json()["id"]

    resp = client.get(f"/pipelines/{pipeline_id}", headers=auth_headers(tenant_b, UserRole.owner))
    assert resp.status_code == 404

    resp = client.get("/pipelines", headers=auth_headers(tenant_b, UserRole.owner))
    assert resp.json() == []


def test_criar_e_listar_stage(client: TestClient):
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.owner)
    pipeline_id = client.post("/pipelines", json={"name": "Vendas"}, headers=headers).json()["id"]

    resp = client.post(f"/pipelines/{pipeline_id}/stages", json={"name": "Entrada", "is_entry": True}, headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/pipelines/{pipeline_id}/stages", headers=headers)
    assert resp.status_code == 200
    assert resp.json()[0]["is_entry"] is True


def test_attendant_nao_pode_criar_stage(client: TestClient):
    tenant = _tenant()
    pipeline_id = client.post("/pipelines", json={"name": "Vendas"}, headers=auth_headers(tenant, UserRole.owner)).json()["id"]
    resp = client.post(
        f"/pipelines/{pipeline_id}/stages",
        json={"name": "Entrada"},
        headers=auth_headers(tenant, UserRole.attendant),
    )
    assert resp.status_code == 403


def test_mover_stage_de_outro_tenant_via_patch_retorna_404(client: TestClient):
    tenant_a, tenant_b = _tenant(), _tenant()
    headers_a = auth_headers(tenant_a, UserRole.owner)
    pipeline_id = client.post("/pipelines", json={"name": "Vendas"}, headers=headers_a).json()["id"]
    stage_id = client.post(f"/pipelines/{pipeline_id}/stages", json={"name": "Entrada"}, headers=headers_a).json()["id"]

    resp = client.patch(f"/stages/{stage_id}", json={"order": 3}, headers=auth_headers(tenant_b, UserRole.owner))
    assert resp.status_code == 404

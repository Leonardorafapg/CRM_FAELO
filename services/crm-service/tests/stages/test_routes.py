"""Integration tests de app/routers/stages.py — RBAC e isolamento
multi-tenant sao o foco (ver docs/TESTING.md). Quadro unico e fixo por
tenant (sem multi-pipeline): Stage e um recurso direto do tenant."""
import uuid

from fastapi.testclient import TestClient
from shared.roles import UserRole

from tests.conftest import auth_headers


def _tenant() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


def test_criar_e_listar_stage_como_owner(client: TestClient):
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.owner)

    resp = client.post("/stages", json={"name": "Entrada", "is_entry": True}, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/stages", headers=headers)
    assert resp.status_code == 200
    assert resp.json()[0]["is_entry"] is True


def test_attendant_nao_pode_criar_stage(client: TestClient):
    tenant = _tenant()
    resp = client.post("/stages", json={"name": "Entrada"}, headers=auth_headers(tenant, UserRole.attendant))
    assert resp.status_code == 403


def test_attendant_pode_listar_stage(client: TestClient):
    tenant = _tenant()
    client.post("/stages", json={"name": "Entrada"}, headers=auth_headers(tenant, UserRole.owner))
    resp = client.get("/stages", headers=auth_headers(tenant, UserRole.attendant))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_isolamento_multi_tenant_em_stages(client: TestClient):
    tenant_a, tenant_b = _tenant(), _tenant()
    client.post("/stages", json={"name": "Entrada A"}, headers=auth_headers(tenant_a, UserRole.owner))

    resp = client.get("/stages", headers=auth_headers(tenant_b, UserRole.owner))
    assert resp.json() == []


def test_mover_stage_de_outro_tenant_via_patch_retorna_404(client: TestClient):
    tenant_a, tenant_b = _tenant(), _tenant()
    stage_id = client.post(
        "/stages", json={"name": "Entrada"}, headers=auth_headers(tenant_a, UserRole.owner)
    ).json()["id"]

    resp = client.patch(f"/stages/{stage_id}", json={"order": 3}, headers=auth_headers(tenant_b, UserRole.owner))
    assert resp.status_code == 404


def test_deletar_stage(client: TestClient):
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.owner)
    stage_id = client.post("/stages", json={"name": "Entrada"}, headers=headers).json()["id"]

    resp = client.delete(f"/stages/{stage_id}", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/stages", headers=headers)
    assert resp.json() == []

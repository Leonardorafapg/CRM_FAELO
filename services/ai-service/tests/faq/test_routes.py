"""Integration tests de app/routers/faq.py — RBAC e isolamento multi-tenant
sao o foco (ver docs/TESTING.md)."""
import uuid

from fastapi.testclient import TestClient
from shared.roles import UserRole

from tests.conftest import auth_headers


def _tenant() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


def test_criar_e_listar_faq_como_owner(client: TestClient):
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.owner)

    resp = client.post("/ai/faq", json={"pergunta": "Qual o horário?", "resposta": "Seg-Sex 9h-18h"}, headers=headers)
    assert resp.status_code == 200

    resp = client.get("/ai/faq", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_criar_faq_com_pergunta_vazia_retorna_400(client: TestClient):
    tenant = _tenant()
    resp = client.post("/ai/faq", json={"pergunta": "  ", "resposta": "A"}, headers=auth_headers(tenant, UserRole.owner))
    assert resp.status_code == 400


def test_attendant_nao_pode_criar_faq(client: TestClient):
    tenant = _tenant()
    resp = client.post(
        "/ai/faq", json={"pergunta": "Q", "resposta": "A"}, headers=auth_headers(tenant, UserRole.attendant)
    )
    assert resp.status_code == 403


def test_attendant_pode_listar_faq(client: TestClient):
    tenant = _tenant()
    client.post("/ai/faq", json={"pergunta": "Q", "resposta": "A"}, headers=auth_headers(tenant, UserRole.owner))
    resp = client.get("/ai/faq", headers=auth_headers(tenant, UserRole.attendant))
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_isolamento_multi_tenant_em_faq(client: TestClient):
    tenant_a, tenant_b = _tenant(), _tenant()
    client.post("/ai/faq", json={"pergunta": "Q", "resposta": "A"}, headers=auth_headers(tenant_a, UserRole.owner))

    resp = client.get("/ai/faq", headers=auth_headers(tenant_b, UserRole.owner))
    assert resp.json()["total"] == 0


def test_atualizar_faq_de_outro_tenant_retorna_404(client: TestClient):
    tenant_a, tenant_b = _tenant(), _tenant()
    faq_id = client.post(
        "/ai/faq", json={"pergunta": "Q", "resposta": "A"}, headers=auth_headers(tenant_a, UserRole.owner)
    ).json()["id"]

    resp = client.patch(
        f"/ai/faq/{faq_id}", json={"pergunta": "Q", "resposta": "Nova"}, headers=auth_headers(tenant_b, UserRole.owner)
    )
    assert resp.status_code == 404


def test_deletar_faq(client: TestClient):
    tenant = _tenant()
    headers = auth_headers(tenant, UserRole.owner)
    faq_id = client.post("/ai/faq", json={"pergunta": "Q", "resposta": "A"}, headers=headers).json()["id"]

    resp = client.delete(f"/ai/faq/{faq_id}", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/ai/faq", headers=headers)
    assert resp.json()["total"] == 0

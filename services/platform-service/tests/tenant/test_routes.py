"""Integration tests de app/routers/tenants.py — RBAC e isolamento
multi-tenant (ver TESTING.md)."""
from fastapi.testclient import TestClient


def _register(client: TestClient, email: str, business_name: str) -> dict:
    resp = client.post("/auth/register", json={
        "name": "Nome",
        "email": email,
        "password": "senha12345",
        "business_name": business_name,
    })
    return resp.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_get_tenant_do_proprio_tenant(client: TestClient):
    auth = _register(client, "tenantrota@teste.com", "Rota Tenant")
    resp = client.get(f"/tenants/{auth['tenant_id']}", headers=_headers(auth["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["groq_key"] is False


def test_get_tenant_de_outro_tenant_retorna_403(client: TestClient):
    auth_a = _register(client, "tenanta-rota@teste.com", "Tenant A Rota")
    auth_b = _register(client, "tenantb-rota@teste.com", "Tenant B Rota")

    resp = client.get(f"/tenants/{auth_a['tenant_id']}", headers=_headers(auth_b["access_token"]))
    assert resp.status_code == 403


def test_patch_tenant_atualiza_campo(client: TestClient):
    auth = _register(client, "tenantpatch@teste.com", "Rota Patch")
    resp = client.patch(
        f"/tenants/{auth['tenant_id']}",
        json={"business_name": "Nome Atualizado"},
        headers=_headers(auth["access_token"]),
    )
    assert resp.status_code == 200

    get_resp = client.get(f"/tenants/{auth['tenant_id']}", headers=_headers(auth["access_token"]))
    assert get_resp.json()["business_name"] == "Nome Atualizado"


def test_patch_tenant_de_outro_tenant_retorna_403(client: TestClient):
    auth_a = _register(client, "tenanta-patch@teste.com", "Tenant A Patch")
    auth_b = _register(client, "tenantb-patch@teste.com", "Tenant B Patch")

    resp = client.patch(
        f"/tenants/{auth_a['tenant_id']}",
        json={"business_name": "Hackeado"},
        headers=_headers(auth_b["access_token"]),
    )
    assert resp.status_code == 403


def test_business_hours_get_e_put(client: TestClient):
    auth = _register(client, "tenanthoursrota@teste.com", "Rota Hours")
    headers = _headers(auth["access_token"])
    tenant_id = auth["tenant_id"]

    resp = client.put(
        f"/tenants/{tenant_id}/business-hours",
        json={"hours": [{"day_of_week": 1, "is_closed": False, "slots": []}]},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.get(f"/tenants/{tenant_id}/business-hours", headers=headers)
    assert resp.status_code == 200
    assert resp.json()[0]["day_of_week"] == 1


def test_list_tenants_sem_ser_platform_admin_retorna_403(client: TestClient):
    auth = _register(client, "naoeadmin@teste.com", "Rota NaoAdmin")
    resp = client.get("/tenants", headers=_headers(auth["access_token"]))
    assert resp.status_code == 403

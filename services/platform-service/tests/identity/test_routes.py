"""Integration tests de app/routers/users.py — RBAC e isolamento
multi-tenant sao o foco aqui (ver TESTING.md)."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _register_and_login(client: TestClient, email: str, business_name: str) -> dict:
    resp = client.post("/auth/register", json={
        "name": "Nome",
        "email": email,
        "password": "senha12345",
        "business_name": business_name,
    })
    return resp.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_listar_usuarios_como_owner(client: TestClient):
    auth = _register_and_login(client, "owner-rota@teste.com", "Rota Users")
    resp = client.get(f"/users/{auth['tenant_id']}", headers=_headers(auth["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_listar_usuarios_sem_token_retorna_401(client: TestClient):
    resp = client.get("/users/algum-tenant")
    assert resp.status_code in (401, 403)  # HTTPBearer sem header retorna 403 por padrao do FastAPI


def test_criar_convite_e_listar_convites_pendentes(client: TestClient):
    auth = _register_and_login(client, "owner-convite-rota@teste.com", "Rota Convites")
    headers = _headers(auth["access_token"])
    tenant_id = auth["tenant_id"]

    resp = client.post(f"/users/{tenant_id}/invite", json={"email": "convidado-rota@teste.com", "role": "attendant"}, headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/users/{tenant_id}/invites", headers=headers)
    assert resp.status_code == 200
    assert resp.json()[0]["email"] == "convidado-rota@teste.com"


def test_criar_convite_de_owner_por_email_invalido_retorna_422(client: TestClient):
    auth = _register_and_login(client, "owner-emailinvalido@teste.com", "Rota X")
    resp = client.post(
        f"/users/{auth['tenant_id']}/invite",
        json={"email": "nao-e-email", "role": "attendant"},
        headers=_headers(auth["access_token"]),
    )
    assert resp.status_code == 422  # validado no schema (InviteCreate.email_valido)


def test_isolamento_multi_tenant_nao_acessa_usuarios_de_outro_tenant(client: TestClient):
    auth_a = _register_and_login(client, "tenant-a@teste.com", "Tenant A")
    auth_b = _register_and_login(client, "tenant-b@teste.com", "Tenant B")

    # Usuario do tenant B tenta listar usuarios do tenant A.
    resp = client.get(f"/users/{auth_a['tenant_id']}", headers=_headers(auth_b["access_token"]))
    assert resp.status_code == 403


def test_accept_invite_route_loga_o_convidado(client: TestClient, db: Session):
    auth = _register_and_login(client, "owner-aceite-rota@teste.com", "Rota Aceite")
    client.post(
        f"/users/{auth['tenant_id']}/invite",
        json={"email": "convidado-aceite@teste.com", "role": "attendant"},
        headers=_headers(auth["access_token"]),
    )

    from app.identity.models import Invite
    import secrets
    from app.auth.security import hash_token

    invite = db.query(Invite).filter(Invite.email == "convidado-aceite@teste.com").first()
    raw_token = secrets.token_urlsafe(32)
    invite.token_hash = hash_token(raw_token)
    db.commit()

    resp = client.post("/auth/accept-invite", json={"token": raw_token, "name": "Convidado", "password": "senha12345"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "attendant"


def test_attendant_nao_consegue_listar_usuarios(client: TestClient, db: Session):
    """Fronteira de RBAC: rota exige require_admin, attendant deve tomar 403
    (ver TESTING.md — testar o nivel ABAIXO do exigido, nao so o permitido)."""
    auth = _register_and_login(client, "owner-rbac@teste.com", "Rota RBAC")
    client.post(
        f"/users/{auth['tenant_id']}/invite",
        json={"email": "attendant-rbac@teste.com", "role": "attendant"},
        headers=_headers(auth["access_token"]),
    )

    from app.identity.models import Invite
    import secrets
    from app.auth.security import hash_token

    invite = db.query(Invite).filter(Invite.email == "attendant-rbac@teste.com").first()
    raw_token = secrets.token_urlsafe(32)
    invite.token_hash = hash_token(raw_token)
    db.commit()

    accept_resp = client.post("/auth/accept-invite", json={"token": raw_token, "name": "Attendant", "password": "senha12345"})
    attendant_token = accept_resp.json()["access_token"]

    resp = client.get(f"/users/{auth['tenant_id']}", headers=_headers(attendant_token))
    assert resp.status_code == 403

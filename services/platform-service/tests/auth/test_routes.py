"""Integration tests de app/auth/routes.py — via TestClient, HTTP de
verdade contra o app (ver TESTING.md: teste de routes.py e de integracao)."""
from fastapi.testclient import TestClient


def test_register_retorna_token(client: TestClient):
    resp = client.post("/auth/register", json={
        "name": "Leo",
        "email": "rota-register@teste.com",
        "password": "senha12345",
        "business_name": "Rota Teste",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["role"] == "owner"


def test_register_com_email_ja_cadastrado_retorna_400(client: TestClient):
    payload = {
        "name": "Leo",
        "email": "duplicado-rota@teste.com",
        "password": "senha12345",
        "business_name": "Rota Teste",
    }
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 400


def test_login_com_credenciais_corretas_retorna_token(client: TestClient):
    client.post("/auth/register", json={
        "name": "Leo",
        "email": "rota-login@teste.com",
        "password": "senha12345",
        "business_name": "Rota Teste",
    })
    resp = client.post("/auth/login", json={"email": "rota-login@teste.com", "password": "senha12345"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_com_senha_errada_retorna_401_com_mensagem_generica(client: TestClient):
    client.post("/auth/register", json={
        "name": "Leo",
        "email": "rota-login2@teste.com",
        "password": "senha12345",
        "business_name": "Rota Teste",
    })
    resp = client.post("/auth/login", json={"email": "rota-login2@teste.com", "password": "senhaerrada"})
    assert resp.status_code == 401
    # Mesma mensagem generica pra email inexistente e senha errada — ver SECURITY.md.
    assert resp.json()["detail"] == "Email ou senha incorretos"


def test_login_com_email_inexistente_retorna_401_com_mesma_mensagem(client: TestClient):
    resp = client.post("/auth/login", json={"email": "fantasma-rota@teste.com", "password": "qualquer123"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Email ou senha incorretos"


def test_forgot_password_sempre_retorna_mensagem_generica(client: TestClient):
    """Existindo ou nao o email, a resposta e identica — evita enumeracao de
    contas (ver SECURITY.md)."""
    resp_existente = client.post("/auth/forgot-password", json={"email": "fantasma-forgot@teste.com"})
    assert resp_existente.status_code == 200
    assert "Se o email existir" in resp_existente.json()["message"]


def test_forgot_password_e_reset_password_fluxo_completo(client: TestClient, db):
    client.post("/auth/register", json={
        "name": "Leo",
        "email": "rota-reset@teste.com",
        "password": "senhaantiga1",
        "business_name": "Rota Teste",
    })
    client.post("/auth/forgot-password", json={"email": "rota-reset@teste.com"})

    # A rota nunca devolve o token puro (foi so por email) — pega direto do
    # banco pra simular o link que o usuario clicaria.
    from app.identity.models import User, PasswordResetToken
    import secrets
    from app.auth.security import hash_token
    from datetime import datetime, timedelta

    user = db.query(User).filter(User.email == "rota-reset@teste.com").first()
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).first()
    # Sobrescreve com um token conhecido (o gerado de verdade so existe hasheado).
    raw_token = secrets.token_urlsafe(32)
    reset_token.token_hash = hash_token(raw_token)
    reset_token.expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    resp = client.post("/auth/reset-password", json={"token": raw_token, "new_password": "senhanova123"})
    assert resp.status_code == 200

    login_resp = client.post("/auth/login", json={"email": "rota-reset@teste.com", "password": "senhanova123"})
    assert login_resp.status_code == 200


def test_reset_password_com_token_invalido_retorna_400(client: TestClient):
    resp = client.post("/auth/reset-password", json={"token": "invalido", "new_password": "senhanova123"})
    assert resp.status_code == 400

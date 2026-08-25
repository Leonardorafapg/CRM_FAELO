import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from tests.conftest import auth_headers
from shared.roles import UserRole
from app.connections.models import Connection
from app.chat.models import Session as ChatSession, Message


def _make_session(db, tenant_id):
    conn = Connection(id=str(uuid.uuid4()), tenant_id=tenant_id, instance_name=f"inst-{uuid.uuid4().hex[:6]}", status="connected")
    db.add(conn)
    db.commit()

    session = ChatSession(
        id=f"{tenant_id}:5511888888888",
        tenant_id=tenant_id,
        connection_id=conn.id,
        phone="5511888888888",
        contact_name="Fulano",
        is_open=True,
        last_activity=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    return conn, session


def test_list_sessoes_scoped_by_tenant(client, db):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    _make_session(db, tenant_a)
    _make_session(db, tenant_b)

    resp = client.get("/sessoes", headers=auth_headers(tenant_a, UserRole.attendant))
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) == 1
    assert sessions[0]["id"] == f"{tenant_a}:5511888888888"


def test_attendant_can_responder(client, db):
    tenant_id = str(uuid.uuid4())
    conn, session = _make_session(db, tenant_id)

    with patch("app.chat.service.evolution_client.send_message", AsyncMock(return_value=None)) as send_mock:
        resp = client.post(
            f"/chat/{session.id}/responder",
            json={"content": "Oi, tudo bem?"},
            headers=auth_headers(tenant_id, UserRole.attendant),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "attendant"
    assert body["content"] == "Oi, tudo bem?"
    send_mock.assert_awaited_once_with(conn.instance_name, session.phone, "Oi, tudo bem?")


def test_responder_to_other_tenant_session_404(client, db):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    _, session = _make_session(db, tenant_a)

    resp = client.post(
        f"/chat/{session.id}/responder",
        json={"content": "oi"},
        headers=auth_headers(tenant_b, UserRole.owner),
    )
    assert resp.status_code == 404


def test_encerrar_atendimento(client, db):
    tenant_id = str(uuid.uuid4())
    _, session = _make_session(db, tenant_id)

    resp = client.patch(f"/chat/{session.id}/encerrar", headers=auth_headers(tenant_id, UserRole.attendant))
    assert resp.status_code == 200
    assert resp.json()["is_open"] is False


def test_list_mensagens_paginated(client, db):
    tenant_id = str(uuid.uuid4())
    _, session = _make_session(db, tenant_id)

    for i in range(5):
        db.add(Message(id=str(uuid.uuid4()), session_id=session.id, role="user", content=f"msg{i}"))
    db.commit()

    resp = client.get(f"/chat/{session.id}/mensagens?limit=2&offset=0", headers=auth_headers(tenant_id, UserRole.attendant))
    assert resp.status_code == 200
    assert len(resp.json()) == 2

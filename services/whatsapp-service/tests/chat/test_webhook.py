import uuid

from app.connections.models import Connection
from app.chat.models import Session as ChatSession, Message


def _make_connection(db, tenant_id=None, instance_name=None):
    tenant_id = tenant_id or f"tenant-{uuid.uuid4().hex[:8]}"
    instance_name = instance_name or f"inst-{uuid.uuid4().hex[:8]}"
    conn = Connection(id=str(uuid.uuid4()), tenant_id=tenant_id, instance_name=instance_name, status="connected")
    db.add(conn)
    db.commit()
    return conn


def _payload(instance_name, message_id, phone="5511999999999", text="oi", from_me=False):
    return {
        "instance": instance_name,
        "data": {
            "key": {"id": message_id, "remoteJid": f"{phone}@s.whatsapp.net", "fromMe": from_me},
            "message": {"conversation": text},
            "pushName": "Cliente Teste",
        },
    }


def test_webhook_rejects_invalid_secret(client, db):
    conn = _make_connection(db)
    resp = client.post(
        "/webhook/evolution",
        json=_payload(conn.instance_name, "msg-1"),
        headers={"X-Webhook-Secret": "secret-errado"},
    )
    assert resp.status_code == 401


def test_webhook_creates_session_and_message(client, db):
    conn = _make_connection(db)
    resp = client.post(
        "/webhook/evolution",
        json=_payload(conn.instance_name, "msg-2"),
        headers={"X-Webhook-Secret": "test-webhook-secret"},
    )
    assert resp.status_code == 200

    session = db.query(ChatSession).filter(ChatSession.id == f"{conn.tenant_id}:5511999999999").first()
    assert session is not None
    assert session.contact_name == "Cliente Teste"

    message = db.query(Message).filter(Message.evolution_message_id == "msg-2").first()
    assert message is not None
    assert message.role == "user"
    assert message.content == "oi"


def test_webhook_dedups_by_message_id(client, db):
    conn = _make_connection(db)
    headers = {"X-Webhook-Secret": "test-webhook-secret"}
    payload = _payload(conn.instance_name, "msg-dup")

    resp1 = client.post("/webhook/evolution", json=payload, headers=headers)
    resp2 = client.post("/webhook/evolution", json=payload, headers=headers)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp2.json().get("duplicate") is True

    count = db.query(Message).filter(Message.evolution_message_id == "msg-dup").count()
    assert count == 1


def test_webhook_marks_from_me_as_attendant(client, db):
    conn = _make_connection(db)
    resp = client.post(
        "/webhook/evolution",
        json=_payload(conn.instance_name, "msg-3", from_me=True),
        headers={"X-Webhook-Secret": "test-webhook-secret"},
    )
    assert resp.status_code == 200
    message = db.query(Message).filter(Message.evolution_message_id == "msg-3").first()
    assert message.role == "attendant"


def test_webhook_triggers_ai_autoresponse(client, db, monkeypatch):
    """Mensagem de cliente deve disparar autoresponder(): consulta o
    ai-service (mockado aqui) e, se vier resposta, envia via Evolution
    (tambem mockada) e grava como mensagem do atendente."""
    import app.chat.service as chat_service

    conn = _make_connection(db)

    async def fake_get_ai_reply(tenant_id, history, user_message):
        assert tenant_id == conn.tenant_id
        assert user_message == "oi"
        return "Ola! Como posso ajudar?"

    sent = {}

    async def fake_send_message(instance_name, phone, content):
        sent["instance_name"] = instance_name
        sent["phone"] = phone
        sent["content"] = content

    monkeypatch.setattr(chat_service.ai_client, "get_ai_reply", fake_get_ai_reply)
    monkeypatch.setattr(chat_service.evolution_client, "send_message", fake_send_message)

    resp = client.post(
        "/webhook/evolution",
        json=_payload(conn.instance_name, "msg-ai-1"),
        headers={"X-Webhook-Secret": "test-webhook-secret"},
    )
    assert resp.status_code == 200

    assert sent == {
        "instance_name": conn.instance_name,
        "phone": "5511999999999",
        "content": "Ola! Como posso ajudar?",
    }

    session = db.query(ChatSession).filter(ChatSession.id == f"{conn.tenant_id}:5511999999999").first()
    ai_message = (
        db.query(Message)
        .filter(Message.session_id == session.id, Message.role == "attendant")
        .first()
    )
    assert ai_message is not None
    assert ai_message.content == "Ola! Como posso ajudar?"


def test_webhook_unknown_instance_returns_404(client, db):
    resp = client.post(
        "/webhook/evolution",
        json=_payload("instancia-inexistente", "msg-4"),
        headers={"X-Webhook-Secret": "test-webhook-secret"},
    )
    assert resp.status_code == 404

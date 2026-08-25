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


def test_list_connections_atualiza_status_para_connected_e_importa_historico(client, db):
    """Cobre o bug real: status ficava travado em "connecting" pra sempre
    porque nada chamava get_instance_status. Agora todo GET /connections
    consulta a Evolution pra conexoes ainda nao conectadas e, na transicao
    pra "connected", importa o historico de chats existente (ver
    app/connections/service.py::_refresh_status_from_evolution e
    app/chat/service.py::import_history)."""
    tenant_id = str(uuid.uuid4())
    conn = Connection(id=str(uuid.uuid4()), tenant_id=tenant_id, instance_name="inst-connecting", status="connecting")
    db.add(conn)
    db.commit()

    status_mock = AsyncMock(return_value={"instance": {"state": "open"}})
    chats_mock = AsyncMock(return_value=[{"remoteJid": "5511999999999@s.whatsapp.net", "pushName": "Cliente Teste"}])
    messages_mock = AsyncMock(return_value=[
        {"key": {"id": "MSG1", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
         "message": {"conversation": "Oi, tudo bem?"}},
    ])

    with patch("app.connections.service.evolution_client.get_instance_status", status_mock), \
         patch("app.evolution.client.find_chats", chats_mock), \
         patch("app.evolution.client.find_messages", messages_mock):
        resp = client.get("/connections", headers=auth_headers(tenant_id, UserRole.attendant))

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["status"] == "connected"
    chats_mock.assert_awaited_once_with("inst-connecting")

    sessoes = client.get(f"/sessoes?limit=50&offset=0", headers=auth_headers(tenant_id, UserRole.attendant)).json()
    assert len(sessoes) == 1
    assert sessoes[0]["phone"] == "5511999999999"

    mensagens = client.get(
        f"/chat/{sessoes[0]['id']}/mensagens?limit=50&offset=0", headers=auth_headers(tenant_id, UserRole.attendant)
    ).json()
    assert len(mensagens) == 1
    assert mensagens[0]["content"] == "Oi, tudo bem?"


def test_import_historico_nao_descarta_mensagem_de_midia(client, db):
    """Bug real: mensagem de midia (imagem/audio/etc.) nao tem "conversation"
    nem "extendedTextMessage" -- content ficava "" e a importacao descartava
    a mensagem inteira em silencio (ver evolution.client.extract_message_fields
    e chat.service.import_history)."""
    tenant_id = str(uuid.uuid4())
    conn = Connection(id=str(uuid.uuid4()), tenant_id=tenant_id, instance_name="inst-connecting", status="connecting")
    db.add(conn)
    db.commit()

    status_mock = AsyncMock(return_value={"instance": {"state": "open"}})
    chats_mock = AsyncMock(return_value=[{"remoteJid": "5511999999999@s.whatsapp.net", "pushName": "Cliente Teste"}])
    messages_mock = AsyncMock(return_value=[
        {"key": {"id": "MSG-TEXTO", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
         "message": {"conversation": "Oi"}},
        {"key": {"id": "MSG-FOTO", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
         "message": {"imageMessage": {"caption": "Segue o comprovante"}}},
        {"key": {"id": "MSG-AUDIO", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": True},
         "message": {"audioMessage": {}}},
    ])

    with patch("app.connections.service.evolution_client.get_instance_status", status_mock), \
         patch("app.evolution.client.find_chats", chats_mock), \
         patch("app.evolution.client.find_messages", messages_mock):
        client.get("/connections", headers=auth_headers(tenant_id, UserRole.attendant))

    sessoes = client.get("/sessoes?limit=50&offset=0", headers=auth_headers(tenant_id, UserRole.attendant)).json()
    mensagens = client.get(
        f"/chat/{sessoes[0]['id']}/mensagens?limit=50&offset=0", headers=auth_headers(tenant_id, UserRole.attendant)
    ).json()

    assert len(mensagens) == 3  # antes do fix, so a de texto sobrevivia
    contents = {m["content"] for m in mensagens}
    assert "Oi" in contents
    assert "[Imagem] Segue o comprovante" in contents
    assert "[Áudio]" in contents


def test_list_connections_ja_conectada_nao_chama_get_instance_status(client, db):
    """Conexao ja "connected" nao precisa consultar o estado de novo (nao
    muda), mas ainda reimporta o historico a cada listagem (ver teste
    abaixo) — e esse reimport, nao get_instance_status, que cobre "logar de
    novo e puxar mensagens novas"."""
    tenant_id = str(uuid.uuid4())
    conn = Connection(id=str(uuid.uuid4()), tenant_id=tenant_id, instance_name="inst-ok", status="connected")
    db.add(conn)
    db.commit()

    status_mock = AsyncMock(return_value={"instance": {"state": "open"}})
    with patch("app.connections.service.evolution_client.get_instance_status", status_mock), \
         patch("app.evolution.client.find_chats", AsyncMock(return_value=[])):
        resp = client.get("/connections", headers=auth_headers(tenant_id, UserRole.attendant))

    assert resp.status_code == 200
    status_mock.assert_not_awaited()


def test_list_connections_reimporta_historico_a_cada_chamada_sem_duplicar(client, db):
    """"Toda vez ao logar precisa puxar o historico" — cada GET /connections
    de uma conexao ja conectada reimporta (nao so na primeira transicao).
    Mensagem repetida na segunda chamada nao duplica (dedup por
    evolution_message_id) e nao bumpa last_activity da sessao sem mensagem
    nova de verdade (ver _get_or_create_session_quiet)."""
    tenant_id = str(uuid.uuid4())
    conn = Connection(id=str(uuid.uuid4()), tenant_id=tenant_id, instance_name="inst-ok", status="connected")
    db.add(conn)
    db.commit()

    chats_mock = AsyncMock(return_value=[{"remoteJid": "5511999999999@s.whatsapp.net", "pushName": "Cliente Teste"}])
    messages_mock = AsyncMock(return_value=[
        {"key": {"id": "MSG1", "remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
         "message": {"conversation": "Oi, tudo bem?"}},
    ])

    with patch("app.evolution.client.find_chats", chats_mock), patch("app.evolution.client.find_messages", messages_mock):
        client.get("/connections", headers=auth_headers(tenant_id, UserRole.attendant))
        first = client.get("/sessoes?limit=50&offset=0", headers=auth_headers(tenant_id, UserRole.attendant)).json()

        # "loga de novo" -- segunda chamada, mesma mensagem no historico
        client.get("/connections", headers=auth_headers(tenant_id, UserRole.attendant))
        second = client.get("/sessoes?limit=50&offset=0", headers=auth_headers(tenant_id, UserRole.attendant)).json()

    assert chats_mock.await_count == 2  # reimportou nas duas chamadas
    assert len(second) == 1
    assert first[0]["last_activity"] == second[0]["last_activity"]  # sem mensagem nova, nao pulou no inbox

    mensagens = client.get(
        f"/chat/{second[0]['id']}/mensagens?limit=50&offset=0", headers=auth_headers(tenant_id, UserRole.attendant)
    ).json()
    assert len(mensagens) == 1  # nao duplicou


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

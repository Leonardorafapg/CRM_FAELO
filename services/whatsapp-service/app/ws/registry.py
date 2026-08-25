"""Registry simples de conexoes WebSocket por tenant_id, em memoria (dict de
modulo). Suficiente pra 1 processo — sem Redis/pubsub nesta fase, revisitar
so se o servico precisar escalar horizontalmente."""
from fastapi import WebSocket

_connections: dict[str, list[WebSocket]] = {}


def register(tenant_id: str, ws: WebSocket) -> None:
    _connections.setdefault(tenant_id, []).append(ws)


def unregister(tenant_id: str, ws: WebSocket) -> None:
    conns = _connections.get(tenant_id)
    if conns and ws in conns:
        conns.remove(ws)
        if not conns:
            _connections.pop(tenant_id, None)


async def broadcast(tenant_id: str, payload: dict) -> None:
    """Manda pra todas as conexoes WS abertas daquele tenant_id. Remove
    conexoes que falharem ao enviar (provavelmente ja caidas)."""
    conns = list(_connections.get(tenant_id, []))
    dead = []
    for ws in conns:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        unregister(tenant_id, ws)

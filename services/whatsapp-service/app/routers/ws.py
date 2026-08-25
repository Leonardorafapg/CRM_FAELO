"""WS /ws/{tenant_id} — JWT via query param (nao da pra usar o Depends de
HTTPBearer em WebSocket, decodifica manualmente com shared.jwt_verify)."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError, ExpiredSignatureError

from shared.jwt_verify import decode_token
from shared.logging_config import get_logger
from app.ws.registry import register, unregister

logger = get_logger("whatsapp-service")

router = APIRouter(tags=["ws"])


@router.websocket("/ws/{tenant_id}")
async def ws_endpoint(websocket: WebSocket, tenant_id: str):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_token(token)
    except (JWTError, ExpiredSignatureError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not payload.get("is_admin") and payload.get("tenant_id") != tenant_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    register(tenant_id, websocket)
    try:
        while True:
            # Este canal e so de broadcast servidor->cliente; ainda assim
            # precisa dar receive() pra detectar desconexao do cliente.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        unregister(tenant_id, websocket)

"""So o platform-service EMITE tokens. crm-service/conversation-service so
verificam (shared/jwt_verify.py) — mesmo SECRET_KEY, mesmo algoritmo."""
import os
from datetime import datetime, timedelta, timezone
from jose import jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY não definida nas variáveis de ambiente")

ALGORITHM    = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))  # validade do token — depois disso o usuario precisa logar de novo


def create_token(data: dict) -> str:
    """Recebe os claims que vao dentro do token (user_id, tenant_id, role,
    is_admin — montados em auth/routes.py::_build_token) e devolve o JWT
    assinado. Adiciona automaticamente `exp` (expiracao) e `iat` (quando foi
    emitido) — o chamador nao precisa se preocupar com isso."""
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS)
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

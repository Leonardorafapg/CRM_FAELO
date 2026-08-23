"""So o platform-service EMITE tokens. crm-service/conversation-service so
verificam (shared/jwt_verify.py) — mesmo SECRET_KEY, mesmo algoritmo."""
import os
from datetime import datetime, timedelta, timezone
from jose import jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY não definida nas variáveis de ambiente")

ALGORITHM    = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS)
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

"""Dependencies de FastAPI reutilizaveis em qualquer servico que so precisa
LER o usuario autenticado a partir do JWT (nao emite token, nao toca no banco
de identity — isso e exclusividade do platform-service)."""
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, ExpiredSignatureError

from shared.jwt_verify import decode_token

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = decode_token(credentials.credentials)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    return payload


def require_own_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("is_admin") and current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return current_user

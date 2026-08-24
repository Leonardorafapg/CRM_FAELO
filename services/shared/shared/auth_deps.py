"""Dependencies de FastAPI reutilizaveis em qualquer servico que so precisa
LER o usuario autenticado a partir do JWT (nao emite token, nao toca no banco
de identity — isso e exclusividade do platform-service)."""
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, ExpiredSignatureError

from shared.jwt_verify import decode_token

# HTTPBearer extrai o token do header "Authorization: Bearer <token>"
# automaticamente — se o header nao vier, o FastAPI ja responde 403 antes
# mesmo de chamar get_current_user.
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency principal de autenticacao: decodifica o JWT do header e
    devolve o payload (user_id, tenant_id, role, is_admin) como dict. Usada
    como Depends() em toda rota que exige usuario logado. Converte falha de
    decodificacao em 401 HTTP (nao deixa a excecao crua do jose subir)."""
    try:
        payload = decode_token(credentials.credentials)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    return payload


def require_own_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency pra rotas cujo path tem {tenant_id}: garante que o usuario
    logado pertence a ESSE tenant (ou e platform admin, que sempre passa).
    So checa "e desse tenant?" — nao checa nivel de permissao (role), isso e
    trabalho do policy.py, os dois costumam ser usados juntos na mesma rota."""
    if not current_user.get("is_admin") and current_user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return current_user

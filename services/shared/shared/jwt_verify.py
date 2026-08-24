"""Verificacao de JWT compartilhada entre os 3 servicos.

Apenas platform-service EMITE tokens (auth/jwt_issue.py la dentro, com
create_token). Os outros dois servicos so decodificam/validam usando o mesmo
JWT_SECRET_KEY (env compartilhada) — sem round-trip HTTP a cada request
autenticado.
"""
import os
from jose import JWTError, jwt, ExpiredSignatureError

# Le a chave secreta da env no momento em que o modulo e importado — se nao
# existir, o servico nem sobe (falha rapido, em vez de quebrar so quando
# alguem tentar logar).
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY não definida nas variáveis de ambiente")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def decode_token(token: str) -> dict:
    """Recebe o token cru (string) vindo do header Authorization e devolve o
    payload (dict) se a assinatura for valida e o token nao tiver expirado.
    Repassa as duas excecoes que interessam pro chamador tratar (token
    expirado vs token invalido/adulterado) — quem chama decide o status HTTP."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise ExpiredSignatureError("Token expirado")
    except JWTError:
        raise JWTError("Token inválido")

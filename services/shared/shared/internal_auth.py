"""Autenticacao servico-a-servico simples: um header compartilhado
(X-Internal-Key), sem service mesh/gRPC — suficiente pro volume atual entre
os 3 servicos internos (nao exposto a clientes externos)."""
import os
from fastapi import Header, HTTPException, status

INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY")
if not INTERNAL_SERVICE_KEY:
    raise RuntimeError("INTERNAL_SERVICE_KEY não definida nas variáveis de ambiente")


def require_internal_key(x_internal_key: str = Header(default="")) -> None:
    if x_internal_key != INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chave de servico invalida")

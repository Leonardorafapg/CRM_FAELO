"""Autenticacao servico-a-servico simples: um header compartilhado
(X-Internal-Key), sem service mesh/gRPC — suficiente pro volume atual entre
os 3 servicos internos (nao exposto a clientes externos)."""
import os
from fastapi import Header, HTTPException, status

# Mesma chave precisa estar configurada em TODOS os servicos que vao chamar
# uns aos outros — funciona como uma senha compartilhada fixa (nao rotaciona
# sozinha, e trocada manualmente se vazar).
INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY")
if not INTERNAL_SERVICE_KEY:
    raise RuntimeError("INTERNAL_SERVICE_KEY não definida nas variáveis de ambiente")


def require_internal_key(x_internal_key: str = Header(default="")) -> None:
    """Dependency pra rotas que SO outros servicos devem chamar (nunca o
    frontend/usuario final) — ex.: /internal/tenants/{id} no platform-service.
    FastAPI ja injeta o valor do header X-Internal-Key automaticamente pelo
    nome do parametro; se nao bater com a chave configurada, barra com 401."""
    if x_internal_key != INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chave de servico invalida")

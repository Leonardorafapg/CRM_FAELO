"""Gateway: unico ponto de entrada publico do sistema. O frontend (e qualquer
cliente externo) chama SO o gateway (uma URL, ex.: api.crmfaelo.com) — ele
decide, pelo prefixo do path, pra qual servico interno encaminhar a
requisicao. Os servicos internos (platform-service, crm-service,
conversation-service) nunca sao expostos diretamente na internet.

Isso e so um proxy reverso simples (path-based routing) — nao faz
autenticacao, nao faz rate limit proprio, nao cacheia nada. Cada servico
continua responsavel pela propria autenticacao (JWT) e pelas proprias regras
(RBAC, rate limit) — o gateway so decide "pra onde essa requisicao vai".
"""
from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from shared.logging_config import setup_logging, get_logger, set_request_id, reset_request_id, get_request_id
from shared.http_client import get_async_client, close_async_client

setup_logging("gateway")
logger = get_logger("gateway")


# Tabela de roteamento: prefixo do path publico -> URL base do servico
# interno que atende esse prefixo. Ordem importa pouco aqui porque o match e
# feito pelo primeiro segmento do path (ver _resolve_upstream), nao por
# prefixo mais especifico vencendo o mais generico.
#
# So platform-service e crm-service existem ate agora — nenhuma rota de
# servico que ainda nao foi construido fica aqui (adicionar quando o
# servico de fato existir).
#
# "/internal/*" de proposito NAO esta nessa tabela — endpoints internos
# (protegidos por X-Internal-Key) sao chamados servico-a-servico direto,
# nunca atraves do gateway publico.
#
# .rstrip("/"): se a env var vier com barra no final (ex.:
# "https://host.up.railway.app/"), upstream_url = f"{base}/{path}" geraria
# "https://host.up.railway.app//auth/login" (barra dupla) — o servico de
# destino nao reconhece essa rota e devolve 404. Normaliza aqui pra nao
# depender de ninguem configurar a env var sem barra final.
def _service_url(env_var: str, default: str) -> str:
    return os.getenv(env_var, default).rstrip("/")


SERVICE_ROUTES: dict[str, str] = {
    "auth":      _service_url("PLATFORM_SERVICE_URL", "http://localhost:8001"),
    "tenants":   _service_url("PLATFORM_SERVICE_URL", "http://localhost:8001"),
    "users":     _service_url("PLATFORM_SERVICE_URL", "http://localhost:8001"),

    "pipelines":        _service_url("CRM_SERVICE_URL", "http://localhost:8002"),
    "stages":           _service_url("CRM_SERVICE_URL", "http://localhost:8002"),
    "contact-statuses": _service_url("CRM_SERVICE_URL", "http://localhost:8002"),
    "contacts":         _service_url("CRM_SERVICE_URL", "http://localhost:8002"),

    # whatsapp-service: so rotas HTTP. O WS /ws/{tenant_id} NAO passa por
    # aqui — o proxy abaixo e HTTP puro (@app.api_route), nao suporta
    # WebSocket. O frontend conecta o WS diretamente na URL do
    # whatsapp-service (NEXT_PUBLIC_WHATSAPP_WS_URL), nao pelo gateway.
    "connections": _service_url("WHATSAPP_SERVICE_URL", "http://localhost:8003"),
    "webhook":     _service_url("WHATSAPP_SERVICE_URL", "http://localhost:8003"),
    "sessoes":     _service_url("WHATSAPP_SERVICE_URL", "http://localhost:8003"),
    "chat":        _service_url("WHATSAPP_SERVICE_URL", "http://localhost:8003"),
}

# Headers que NAO devem ser repassados adiante — sao especificos da conexao
# entre cliente e gateway (hop-by-hop), reencaminha-los pro upstream (ou
# devolver os do upstream pro cliente) causa bug de encoding/tamanho.
HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "transfer-encoding", "content-length",
    "content-encoding", "host",
}


def _resolve_upstream(path: str) -> str | None:
    """Pega o primeiro segmento do path (ex.: "/tenants/abc123" -> "tenants")
    e busca na tabela de roteamento. Devolve None se nenhum servico atende
    esse prefixo (vira 404 do gateway, nao um erro de servico)."""
    first_segment = path.strip("/").split("/", 1)[0]
    return SERVICE_ROUTES.get(first_segment)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_async_client()
    logger.info("Recursos de rede finalizados com sucesso")


app = FastAPI(title="Gateway", version="0.1.0", lifespan=lifespan)

origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Request-ID"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Mesmo padrao dos outros servicos: gera/reaproveita um X-Request-ID.
    Aqui e ainda mais importante — o gateway gera o id UMA VEZ por requisicao
    do cliente e repassa pro servico interno (ver proxy() abaixo), entao o
    mesmo id aparece nos logs do gateway E do servico que atendeu, permitindo
    rastrear a requisicao completa atraves dos dois."""
    token = set_request_id(request.headers.get("x-request-id"))
    request.state.request_id = get_request_id()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = get_request_id()
        return response
    finally:
        reset_request_id(token)


@app.get("/")
def root():
    """Health check do proprio gateway (nao verifica se os upstreams estao
    de pe — so confirma que o processo do gateway esta rodando)."""
    return {"status": "online", "service": "gateway", "version": "0.1.0"}


# Rota catch-all: casa QUALQUER path e metodo HTTP que nao seja "/" (a rota
# acima). E aqui que o proxy de fato acontece — nao existe uma rota por
# servico, uma unica funcao encaminha tudo com base em SERVICE_ROUTES.
@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy(path: str, request: Request):
    upstream_base = _resolve_upstream(path)
    if upstream_base is None:
        return Response(
            content=f'{{"detail":"Nenhum servico atende /{path}"}}',
            status_code=404,
            media_type="application/json",
        )

    upstream_url = f"{upstream_base}/{path}"
    client = get_async_client()

    # Repassa os headers recebidos do cliente, exceto os hop-by-hop, e
    # adiciona o X-Request-ID gerado/reaproveitado pra correlacionar logs
    # entre gateway e servico interno.
    forward_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS
    }
    forward_headers["X-Request-ID"] = get_request_id()

    body = await request.body()

    try:
        upstream_response = await client.request(
            method=request.method,
            url=upstream_url,
            params=request.query_params,
            headers=forward_headers,
            content=body,
        )
    except Exception as e:
        # Upstream fora do ar (ex.: crm-service ainda nao construido/nao
        # subiu) — devolve 502 em vez de deixar a excecao estourar como 500
        # generico, deixa claro que o problema e de infraestrutura, nao da
        # requisicao em si.
        logger.error(f"Falha ao encaminhar para {upstream_url}: {type(e).__name__}: {e}")
        return Response(
            content='{"detail":"Servico interno indisponivel"}',
            status_code=502,
            media_type="application/json",
        )

    # Repassa a resposta do servico interno pro cliente tal como veio
    # (status code, corpo, headers), exceto os hop-by-hop de novo — dessa vez
    # do lado da resposta do upstream.
    response_headers = {
        k: v for k, v in upstream_response.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS
    }
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )

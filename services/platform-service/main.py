from dotenv import load_dotenv
load_dotenv()  # precisa rodar antes de qualquer import que leia env var no nivel do modulo

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shared.logging_config import setup_logging, get_logger, set_request_id, reset_request_id, get_request_id
setup_logging("platform-service")
logger = get_logger("platform-service")

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.infra.rate_limit import limiter

from app.auth.routes import router as auth_router
from app.routers.tenants import router as tenants_router
from app.routers.users import router as users_router
from app.routers.internal import router as internal_router
from shared.http_client import close_async_client
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida do app: nada a fazer no startup por enquanto (o cleanup
    periodico de mensagens antigas e responsabilidade do conversation-service,
    nao deste). No shutdown, fecha o client HTTP assincrono compartilhado."""
    yield
    await close_async_client()
    logger.info("Recursos de rede finalizados com sucesso")

app = FastAPI(title="Platform Service", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# strip() em cada origem: "https://a.com, https://b.com" (espaco apos a
# virgula) fazia a segunda origem nunca casar — falha silenciosa de CORS.
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Gera (ou reaproveita, se o caller mandar X-Request-ID — ex.: outro
    servico repassando o mesmo id) um id por requisicao e injeta em toda
    linha de log emitida durante o processamento dela. E a peca que permite
    reconstruir "o que aconteceu com a requisicao X" so lendo o log."""
    token = set_request_id(request.headers.get("x-request-id"))
    # Guardado tambem em request.state: o handler de excecao para `Exception`
    # roda numa camada MAIS EXTERNA (por cima deste middleware) — quando uma
    # excecao nao tratada sobe ate la, o `finally` abaixo ja rodou e resetou
    # a contextvar. request.state sobrevive a essa subida.
    request.state.request_id = get_request_id()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = get_request_id()
        return response
    finally:
        reset_request_id(token)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Rede de seguranca: qualquer excecao que escapou de um endpoint sem
    try/except explicito passa por aqui antes de virar 500 — sempre com
    traceback e request_id, nunca um erro silencioso sem rastro. HTTPException
    tem handler proprio mais especifico no FastAPI e NAO passa por aqui (nao
    intercepta os 4xx/403/404 esperados)."""
    request_id = getattr(request.state, "request_id", get_request_id())
    logger.error(
        f"Excecao nao tratada em {request.method} {request.url.path} "
        f"[request_id={request_id}]: {type(exc).__name__}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"},
        headers={"X-Request-ID": request_id},
    )


app.include_router(auth_router)
app.include_router(tenants_router)
app.include_router(users_router)
app.include_router(internal_router)


@app.get("/")
def root():
    """Health check simples — usado pra confirmar que o processo subiu."""
    return {"status": "online", "service": "platform-service", "version": "0.1.0"}

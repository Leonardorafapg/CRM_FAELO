from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shared.logging_config import setup_logging, get_logger, set_request_id, reset_request_id, get_request_id
setup_logging("ai-service")
logger = get_logger("ai-service")

from app.routers.faq import router as faq_router
from shared.http_client import close_async_client
import os

from alembic.config import Config
from alembic import command


def run_migrations() -> None:
    """Roda `alembic upgrade head` via API do Python no boot do processo —
    mesmo padrao dos outros servicos (ver crm-service/whatsapp-service),
    evita depender do Procfile/Pre-Deploy Command da plataforma de deploy."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg = Config(os.path.join(base_dir, "alembic.ini"))
    command.upgrade(cfg, "head")
    logger.info("Migrations aplicadas (alembic upgrade head)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # PYTEST_CURRENT_TEST e setada automaticamente pelo pytest durante os
    # testes — nesse caso a fixture _schema do conftest.py ja cria o schema
    # via Base.metadata.create_all, entao rodar alembic tambem colidiria
    # ("relation already exists").
    if not os.getenv("PYTEST_CURRENT_TEST"):
        run_migrations()
    yield
    await close_async_client()
    logger.info("Recursos de rede finalizados com sucesso")

app = FastAPI(title="AI Service", version="0.1.0", lifespan=lifespan)

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
    token = set_request_id(request.headers.get("x-request-id"))
    request.state.request_id = get_request_id()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = get_request_id()
        return response
    finally:
        reset_request_id(token)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
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


app.include_router(faq_router)


@app.get("/")
def root():
    return {"status": "online", "service": "ai-service", "version": "0.1.0"}

from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shared.logging_config import setup_logging, get_logger, set_request_id, reset_request_id, get_request_id
setup_logging("crm-service")
logger = get_logger("crm-service")

from app.routers.pipelines import router as pipelines_router
from app.routers.stages import router as stages_router
from app.routers.contact_statuses import router as contact_statuses_router
from app.routers.contacts import router as contacts_router
from shared.http_client import close_async_client
import os

from alembic.config import Config
from alembic import command


def run_migrations() -> None:
    """Roda `alembic upgrade head` via API do Python no boot do processo, em
    vez de depender do Procfile/Pre-Deploy Command da plataforma de deploy
    (Railway) rodar isso por fora — visto na pratica que essa etapa por fora
    pode silenciosamente nao executar dependendo de como o builder trata o
    Procfile. Caminho do alembic.ini resolvido a partir deste arquivo (nao do
    cwd), pra funcionar independente de onde o processo foi iniciado."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg = Config(os.path.join(base_dir, "alembic.ini"))
    command.upgrade(cfg, "head")
    logger.info("Migrations aplicadas (alembic upgrade head)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Testes criam um TestClient novo por teste (ver conftest.py de cada
    # servico), disparando este lifespan repetidas vezes contra um banco cujo
    # schema a fixture _schema ja criou via Base.metadata.create_all -- rodar
    # alembic tambem ali colidiria ("relation already exists"). PYTEST_CURRENT_TEST
    # e setada automaticamente pelo pytest durante a execucao dos testes.
    if not os.getenv("PYTEST_CURRENT_TEST"):
        run_migrations()
    yield
    await close_async_client()
    logger.info("Recursos de rede finalizados com sucesso")

app = FastAPI(title="CRM Service", version="0.1.0", lifespan=lifespan)

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


app.include_router(pipelines_router)
app.include_router(stages_router)
app.include_router(contact_statuses_router)
app.include_router(contacts_router)


@app.get("/")
def root():
    return {"status": "online", "service": "crm-service", "version": "0.1.0"}

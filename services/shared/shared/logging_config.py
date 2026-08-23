import contextvars
import logging
import sys
import uuid

# Um request_id por requisicao HTTP (setado pelo middleware em main.py de cada
# servico), injetado em TODA linha de log via RequestIdFilter. ContextVar
# porque cada requisicao roda numa Task asyncio diferente — precisa de um
# valor "por tarefa", nao uma variavel global compartilhada (que misturaria
# request_id de requisicoes concorrentes).
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Filtro de logging que injeta o request_id atual em todo LogRecord
    antes de ser formatado — e o que permite o %(request_id)s aparecer em
    cada linha de log sem precisar passar isso manualmente em todo logger.info(...)."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True


def setup_logging(service_name: str = "app"):
    """Configura o logging global do processo (chamada uma vez, no boot de
    cada servico). Formato inclui o nome do servico (util quando varios logs
    de servicos diferentes acabam no mesmo agregador), o request_id, e
    modulo:funcao:linha de origem de cada mensagem."""
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s [%(levelname)s] [{service_name}] [%(request_id)s] %(module)s:%(funcName)s:%(lineno)d: %(message)s",
        handlers=[handler],
        force=True,
    )


def get_logger(service_name: str = "app") -> logging.Logger:
    """Devolve o logger nomeado — cada modulo/servico pega o seu proprio
    (mesmo nome usado em setup_logging), so pra organizacao/filtragem."""
    return logging.getLogger(service_name)


def new_request_id() -> str:
    """Gera um id curto (12 hex) pra correlacionar todas as linhas de log de
    uma mesma requisicao."""
    return uuid.uuid4().hex[:12]


def set_request_id(value: str | None = None) -> contextvars.Token:
    """Define o request_id do contexto atual (asyncio Task) — chamado no
    inicio de cada requisicao pelo middleware. Se o caller ja mandou um
    X-Request-ID (ex.: veio de outro servico), reaproveita em vez de gerar
    outro, mantendo o rastro atraves de varios servicos. Devolve um Token
    pra poder restaurar o valor anterior depois (ver reset_request_id)."""
    return _request_id_var.set(value or new_request_id())


def reset_request_id(token: contextvars.Token) -> None:
    """Desfaz o set_request_id, chamado no finally do middleware — evita que
    o valor "vaze" pra fora do escopo da requisicao."""
    _request_id_var.reset(token)


def get_request_id() -> str:
    """Le o request_id do contexto atual — usado, por exemplo, no handler de
    excecao nao tratada pra incluir o id na resposta de erro."""
    return _request_id_var.get()

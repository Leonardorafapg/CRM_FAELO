import contextvars
import logging
import sys
import uuid

# Um request_id por requisicao HTTP (setado pelo middleware em main.py de cada
# servico), injetado em TODA linha de log via RequestIdFilter.
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True


def setup_logging(service_name: str = "app"):
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s [%(levelname)s] [{service_name}] [%(request_id)s] %(module)s:%(funcName)s:%(lineno)d: %(message)s",
        handlers=[handler],
        force=True,
    )


def get_logger(service_name: str = "app") -> logging.Logger:
    return logging.getLogger(service_name)


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def set_request_id(value: str | None = None) -> contextvars.Token:
    return _request_id_var.set(value or new_request_id())


def reset_request_id(token: contextvars.Token) -> None:
    _request_id_var.reset(token)


def get_request_id() -> str:
    return _request_id_var.get()

"""Rate limiting (slowapi) — instanciado aqui, e nao em main.py, pra que os
routers possam aplicar `@limiter.limit(...)` sem importar `main` de volta."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

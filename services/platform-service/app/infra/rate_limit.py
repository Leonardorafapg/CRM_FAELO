"""Rate limiting (slowapi) — instanciado aqui, e nao em main.py, pra que os
routers possam aplicar `@limiter.limit(...)` sem importar `main` de volta
(isso criaria um ciclo: main importa os routers, os routers importariam
main de volta). main.py so registra o handler/middleware a partir daqui."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Limita por IP de origem (get_remote_address) — cada rota decora com seu
# proprio limite (@limiter.limit("10/minute")) nas rotas de auth.
limiter = Limiter(key_func=get_remote_address)

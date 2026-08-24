import os
from shared.db import Base, make_db  # Base re-exportada pra os models importarem daqui

# Cria o engine/SessionLocal/get_db deste servico especificamente, apontando
# pro banco proprio do platform-service (nunca o mesmo banco do crm-service
# ou conversation-service).
engine, SessionLocal, get_db = make_db(os.getenv("DATABASE_URL"))

import os
from shared.db import Base, make_db  # Base re-exportada pra os models importarem daqui

# Banco proprio do crm-service — nunca o mesmo banco do platform-service.
engine, SessionLocal, get_db = make_db(os.getenv("DATABASE_URL"))

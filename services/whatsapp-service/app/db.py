import os
from shared.db import Base, make_db  # Base re-exportada pra os models importarem daqui

# Banco proprio do whatsapp-service — nunca o mesmo banco dos outros servicos.
engine, SessionLocal, get_db = make_db(os.getenv("DATABASE_URL"))

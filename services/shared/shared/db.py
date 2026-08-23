"""Base SQLAlchemy + factory de sessao, parametrizada por DATABASE_URL —
cada servico chama `make_db(os.getenv("DATABASE_URL"))` com a URL do seu
proprio schema/banco."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def make_db(database_url: str):
    if not database_url:
        raise RuntimeError("DATABASE_URL não definida nas variáveis de ambiente")

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    return engine, SessionLocal, get_db

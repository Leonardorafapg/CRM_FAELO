"""Base SQLAlchemy + factory de sessao, parametrizada por DATABASE_URL —
cada servico chama `make_db(os.getenv("DATABASE_URL"))` com a URL do seu
proprio schema/banco."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Classe base que todo model SQLAlchemy de qualquer servico herda. Cada
# processo (platform-service, crm-service, ...) so importa os models que ele
# proprio define, entao Base.metadata acaba contendo so as tabelas DAQUELE
# servico mesmo sendo a mesma classe Base importada do shared.
Base = declarative_base()


def make_db(database_url: str):
    """Recebe a connection string do banco do servico chamador e devolve 3
    coisas prontas pra usar: o engine (conexao crua), o SessionLocal (fabrica
    de sessoes) e get_db (a dependency do FastAPI que abre/fecha sessao por
    requisicao)."""
    if not database_url:
        raise RuntimeError("DATABASE_URL não definida nas variáveis de ambiente")

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_db():
        # Padrao FastAPI de dependency com yield: abre a sessao, entrega pra
        # rota usar, e SEMPRE fecha no finally — mesmo se a rota levantar
        # excecao, a conexao nao fica presa aberta.
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    return engine, SessionLocal, get_db

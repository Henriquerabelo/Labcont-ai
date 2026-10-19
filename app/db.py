from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL, FUSO

# A sessão do banco usa o mesmo fuso do sistema, para que now() do PostgreSQL e datetime.now() do Python coincidam.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)


@event.listens_for(engine, "connect")
def _fuso_da_sessao(conexao, _registro):
    cur = conexao.cursor()
    try:
        cur.execute(f"SET TIME ZONE '{FUSO}'")
    except Exception:  # banco sem a base de fusos: UTC-3 fixo
        conexao.rollback()
        cur.execute("SET TIME ZONE INTERVAL '-03:00' HOUR TO MINUTE")
    conexao.commit()
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

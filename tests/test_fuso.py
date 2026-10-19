"""Horário de Brasília: Python e PostgreSQL no mesmo fuso; correção única das horas antigas em UTC."""
import os
from datetime import UTC, datetime, timedelta

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from sqlalchemy import text  # noqa: E402

import app.main  # noqa: E402,F401  (registra as tabelas)
from app import acesso, fuso  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402


def test_python_e_banco_no_mesmo_fuso():
    with SessionLocal() as db:
        banco = db.execute(text("select localtimestamp")).scalar()
        assert db.execute(text("show timezone")).scalar() == fuso.FUSO
    assert abs((datetime.now() - banco).total_seconds()) < 60
    utc = datetime.now(UTC).replace(tzinfo=None)
    assert round((datetime.now() - utc).total_seconds() / 3600) == -3


def test_correcao_unica_das_horas_utc(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    antes = datetime(2026, 10, 6, 16, 50)
    with SessionLocal() as db:
        db.add(acesso.Acao(login="admin", perfil="admin", descricao="Entrou no sistema", caminho="/entrar", quando=antes))
        db.commit()
        monkeypatch.delenv("CORRIGIR_FUSO_UTC", raising=False)
        assert fuso.corrigir_registros_utc(db) == 0  # sem a variável (ambiente local), nada muda
        monkeypatch.setenv("CORRIGIR_FUSO_UTC", "1")
        assert fuso.corrigir_registros_utc(db) > 0
        assert fuso.corrigir_registros_utc(db) == 0  # só uma vez
        q = db.execute(text("select quando from historico_acoes")).scalar()
        assert q == antes - timedelta(hours=3)

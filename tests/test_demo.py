"""Etapa 7c: turma de demonstração com dados fictícios e acessos de avaliação."""
import os
import re

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app import analytics, demo  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Discente  # noqa: E402


@pytest.fixture(scope="module")
def c():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app=main.app) as cli:
        yield cli


def test_criar_pela_tela_e_dados(c):
    assert "ainda não existe" in c.get("/admin/demonstracao").text
    r = c.post("/admin/demonstracao", data={"acao": "criar"})
    assert "Acessos de demonstração" in r.text
    senha_vis = re.search(r"avaliador · <span class=\"mono\">([^<]+)</span>", r.text).group(1)
    senha_alu = re.search(r"(9000\d+) · <span class=\"mono\">([^<]+)</span>", r.text)
    with SessionLocal() as db:
        t = demo._turma_demo(db)
        assert len(t.matriculas) == 20 and all(m.discente.matricula.startswith("9000") for m in t.matriculas)
        an = analytics.analisar_turma(db, t.id)
        titulos = {a[1] for g in an["grupos"] for a in g["alertas"]}
        assert {"Sem acesso", "Inativo", "Travado em J24", "Participação desigual", "Busca respostas prontas", "Prévia baixa"} <= titulos
        assert an["resumo"]["enviados"] == 3 and an["resumo"]["perguntas"] > 10
        homolog = db.query(analytics.NotaPeriodo).filter_by(turma_id=t.id, homologada=True).count()
        assert homolog == 4
        tid = t.id
    # visitante: entra, vê a turma de demonstração e não altera nada
    c.cookies.clear()
    c.post("/entrar", data={"login": "avaliador", "senha": senha_vis})
    home = c.get("/").text
    assert "DEMO" in home
    assert "Matriz de calor" in c.get(f"/turmas/{tid}/painel").text
    assert c.post(f"/turmas/{tid}/duplas/codigos", follow_redirects=False).status_code == 403
    # aluno de demonstração entra com matrícula e senha
    c.cookies.clear()
    r = c.post("/aluno/entrar", data={"matricula": senha_alu.group(1), "senha": senha_alu.group(2)}, follow_redirects=False)
    assert r.status_code == 303
    assert "Empresa" in c.get("/aluno").text
    c.cookies.clear()


def test_recriar_e_apagar(c):
    with SessionLocal() as db:
        r1 = demo.criar(db)
        r2 = demo.criar(db)  # idempotente: substitui a anterior
        assert r1["turma_id"] != r2["turma_id"]
        assert db.query(Discente).filter(Discente.matricula.like("9000%")).count() == 20
        demo.apagar(db)
        db.commit()
        assert demo._turma_demo(db) is None
        assert db.query(Discente).filter(Discente.matricula.like("9000%")).count() == 0

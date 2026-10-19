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
    assert "ainda não existem" in c.get("/admin/demonstracao").text
    r = c.post("/admin/demonstracao", data={"acao": "criar"})
    assert "Acessos de demonstração" in r.text
    senha_vis = re.search(r"avaliador · <span class=\"mono\">([^<]+)</span>", r.text).group(1)
    senha_alu = re.search(r"(9000\d+) · <span class=\"mono\">([^<]+)</span>", r.text)
    with SessionLocal() as db:
        ts = demo._turmas_demo(db)
        assert [x.codigo for x in ts] == ["DEMO-01A", "DEMO-02A", "DEMO-03A"]
        assert [x.docentes[0].docente.nome for x in ts] == [c["docente"] for c in demo.TURMAS]
        assert all(len(x.matriculas) == 20 for x in ts)
        t = ts[0]
        assert all(m.discente.matricula.startswith("9000") for m in t.matriculas)
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
    assert "DEMO-01A" in home and "DEMO-03A" in home
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
        assert db.query(Discente).filter(Discente.matricula.like("9000%")).count() == 60
        demo.apagar(db)
        db.commit()
        assert demo._turma_demo(db) is None and demo._turmas_demo(db) == []
        assert db.query(Discente).filter(Discente.matricula.like("9000%")).count() == 0


def test_cada_professor_ve_a_sua_turma(c):
    with SessionLocal() as db:
        r = demo.criar(db)
    profs = r["credenciais"]["professores"]
    assert [p["login"] for p in profs] == ["danival.demo", "eduardo.demo", "rosangela.demo"]
    ids = {t["codigo"]: t["id"] for t in r["turmas"]}
    c.cookies.clear()
    c.post("/entrar", data={"login": profs[1]["login"], "senha": profs[1]["senha"]})
    assert c.get(f"/turmas/{ids['DEMO-02A']}/painel").status_code == 200
    assert c.get(f"/turmas/{ids['DEMO-01A']}/painel", follow_redirects=False).status_code in (303, 403)
    c.cookies.clear()
    assert len(r["credenciais"]["alunos"]) == 3 and r["grupos"] == 30 and r["alunos"] == 60

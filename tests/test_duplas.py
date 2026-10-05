"""Testes das duplas (formação voluntária) e da geração das empresas por dupla."""
import os
import re

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

from app.caso_servico import carregar_caso_base  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.geracao import gerar  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Disciplina, Discente, Matricula, Turma  # noqa: E402
from app.models_caso import Caso  # noqa: E402
from app.models_dupla import Dupla  # noqa: E402

NOMES = ["Ana Souza", "Bruno Lima", "Carla Dias", "Davi Rocha", "Elisa Prado", "Fábio Nunes", "Gabi Torres"]


@pytest.fixture(scope="module")
def ctx():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        d = Disciplina(codigo="EH0012", nome="LABORATÓRIO DE PRÁTICA CONTÁBIL")
        t = Turma(disciplina=d, periodo="2026.2", codigo="01")
        db.add(t)
        ids = []
        for i, n in enumerate(NOMES):
            a = Discente(matricula=f"5100{i:02d}", nome=n.upper())
            db.add(a)
            db.add(Matricula(turma=t, discente=a, situacao="ATIVO"))
            db.flush()
            ids.append(a.id)
        tr = Discente(matricula="510099", nome="TRANCADO DA SILVA")
        db.add(Matricula(turma=t, discente=tr, situacao="TRANCADO"))
        caso = carregar_caso_base(db)
        db.commit()
        tid, cid, trid = t.id, caso.id, tr.id
    with TestClient(app) as c:
        yield {"c": c, "tid": tid, "cid": cid, "ids": ids, "trancado": trid}


def _duplas(tid):
    with SessionLocal() as db:
        return [(d.numero, sorted(m.discente_id for m in d.membros)) for d in
                db.query(Dupla).filter_by(turma_id=tid).order_by(Dupla.numero)]


def test_formar_e_validar(ctx):
    c, tid, ids = ctx["c"], ctx["tid"], ctx["ids"]
    assert c.get(f"/turmas/{tid}/duplas").status_code == 200
    r = c.post(f"/turmas/{tid}/duplas", data={"discente_id": [str(ids[0]), str(ids[1])], "nome": "Equipe A"},
               follow_redirects=False)
    assert r.status_code == 303 and "erro" not in r.headers["location"]
    # discente já em dupla, não ativo, ou mais de 3 integrantes -> recusado
    for ruim in ([ids[1], ids[2]], [ctx["trancado"], ids[2]], ids[2:6]):
        r = c.post(f"/turmas/{tid}/duplas", data={"discente_id": [str(i) for i in ruim]}, follow_redirects=False)
        assert "erro=" in r.headers["location"]
    assert _duplas(tid) == [(1, sorted(ids[:2]))]


def test_lote_por_matricula_e_nome(ctx):
    c, tid, ids = ctx["c"], ctx["tid"], ctx["ids"]
    lista = "510002; 510003\ncarla e davi\nElisa Prado / Fábio\nGabi"
    r = c.post(f"/turmas/{tid}/duplas/lote", data={"lista": lista}, follow_redirects=False)
    loc = r.headers["location"]
    assert "msg=" in loc and "erro=" in loc  # linha 2 repete Carla e Davi
    assert _duplas(tid) == [(1, sorted(ids[:2])), (2, sorted(ids[2:4])), (3, sorted(ids[4:6])), (4, [ids[6]])]
    pagina = c.get(f"/turmas/{tid}/duplas").text
    assert "1 integrante" in pagina


def test_desfazer_e_renumerar(ctx):
    c, tid, ids = ctx["c"], ctx["tid"], ctx["ids"]
    with SessionLocal() as db:
        d4 = db.query(Dupla).filter_by(turma_id=tid, numero=4).one()
        d3 = db.query(Dupla).filter_by(turma_id=tid, numero=3).one()
        d4id, d3id = d4.id, d3.id
    c.post(f"/duplas/{d4id}/excluir")
    c.post(f"/duplas/{d3id}/membros", data={"discente_id": str(ids[6])})  # vira trio
    assert _duplas(tid)[-1] == (3, sorted(ids[4:7]))
    c.post(f"/duplas/{d3id}/editar", data={"nome": "Trio C"})
    with SessionLocal() as db:
        assert db.get(Dupla, d3id).nome == "Trio C"


def test_gerar_empresas_reproduziveis_e_dentro_das_faixas(ctx):
    c, tid, cid = ctx["c"], ctx["tid"], ctx["cid"]
    r = c.post(f"/turmas/{tid}/duplas/gerar", data={"caso_id": str(cid), "modo": "faltantes"}, follow_redirects=False)
    assert "3%20dupla" in r.headers["location"]
    with SessionLocal() as db:
        duplas = db.query(Dupla).filter_by(turma_id=tid).order_by(Dupla.numero).all()
        sementes = {d.empresa.semente for d in duplas}
        assert len(sementes) == 3
        v = duplas[0].empresa.valores
        for p in v["parametros"]:
            if p["varia"] and not p.get("ajustado") and p["min"] is not None and isinstance(p["valor"], (int, float)):
                lo, hi = sorted((p["min"], p["max"]))
                assert lo - 1e-9 <= p["valor"] <= hi + 1e-9, p
        # compra = necessidade + sobra; sobra 100-300; vendas < produção
        for i in v["producao"]["insumos"]:
            assert i["compra"] == i["necessidade"] + i["sobra"] + i["devolucao"] and 100 <= i["sobra"] <= 300
        for p in v["producao"]["produtos"]:
            assert 15000 <= p["quantidade"] <= 25000 and 0 < p["vendido"] < p["quantidade"]
        sal = [f["salario_fev"] for f in v["folha"] if f["salario_fev"] is not None]
        assert all(s >= 1621 and (s == 1621 or s % 10 == 0) for s in sal)
        # mesma semente + mesmo caso => mesmos valores
        caso = db.get(Caso, cid)
        assert gerar(caso, duplas[0].empresa.semente, duplas[0].rotulo, duplas[0].numero)["producao"] == v["producao"]
        # duplas diferentes => empresas diferentes
        assert duplas[1].empresa.valores["producao"] != v["producao"]
        d1, sem1 = duplas[0].id, duplas[0].empresa.semente
    pag = c.get(f"/duplas/{d1}/empresa")
    assert pag.status_code == 200 and "Empresa LAB 01" in pag.text
    assert c.get(f"/duplas/{d1}/empresa.json").json()["semente"] == sem1
    c.post(f"/duplas/{d1}/empresa/sortear", data={"manter": "1"})
    with SessionLocal() as db:
        assert db.get(Dupla, d1).empresa.semente == sem1
    c.post(f"/duplas/{d1}/empresa/sortear")
    with SessionLocal() as db:
        assert db.get(Dupla, d1).empresa.semente != sem1
    csv = c.get(f"/turmas/{tid}/duplas.csv").text
    assert csv.count("\n") == 1 + 7 and "Empresa LAB 03" in csv


def test_recalcular_aplica_alteracao_do_caso(ctx):
    c, tid, cid = ctx["c"], ctx["tid"], ctx["cid"]
    with SessionLocal() as db:
        p = next(p for p in db.get(Caso, cid).params("producao") if "Produto X" in p.nome)
        p.minimo = p.maximo = 20000
        db.commit()
    c.post(f"/turmas/{tid}/duplas/gerar", data={"caso_id": str(cid), "modo": "recalcular"})
    with SessionLocal() as db:
        for d in db.query(Dupla).filter_by(turma_id=tid):
            x = next(p for p in d.empresa.valores["producao"]["produtos"] if p["codigo"] == "X")
            assert x["quantidade"] == 20000
    assert re.search(r"Gerar empresas", c.get(f"/turmas/{tid}/duplas").text)


def test_visao_geral_no_menu(ctx):
    r = ctx["c"].get("/duplas")
    assert r.status_code == 200 and f'/turmas/{ctx["tid"]}/duplas' in r.text and 'href="/duplas"' in r.text


def test_orientacao_docx(ctx):
    import io as _io
    import zipfile as _zip
    from docx import Document
    c, tid = ctx["c"], ctx["tid"]
    with SessionLocal() as db:
        d = db.query(Dupla).filter_by(turma_id=tid).order_by(Dupla.numero).first()
        did, v = d.id, d.empresa.valores
    r = c.get(f"/duplas/{did}/orientacao.docx")
    assert r.status_code == 200 and r.content[:2] == b"PK"
    texto = "\n".join(p.text for p in Document(_io.BytesIO(r.content)).paragraphs)
    assert "Empresa LAB 01" in texto and "ANA SOUZA" in texto
    x = next(p for p in v["producao"]["produtos"] if p["codigo"] == "X")
    assert f"⇨{x['quantidade']:,}".replace(",", ".") + " unidades" in texto
    from app.orientacao import gerar_docx
    _b, avisos = gerar_docx(v, "Dupla 01")
    assert avisos == [], avisos
    z = c.get(f"/turmas/{tid}/duplas/orientacoes.zip")
    assert z.status_code == 200 and len(_zip.ZipFile(_io.BytesIO(z.content)).namelist()) >= 1

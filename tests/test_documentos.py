"""Central de documentos: geração por dupla e telas."""
import os
import re

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from app.documentos import cnpj_ficticio, gerar_documentos  # noqa: E402
from app.gabarito import gerar_gabarito  # noqa: E402
from app.geracao import gerar  # noqa: E402
from app.models_caso import Caso  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.caso_servico import carregar_caso_base  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Disciplina, Discente, Matricula, Turma  # noqa: E402
from app.models_dupla import Dupla  # noqa: E402


@pytest.fixture(scope="module")
def ctx():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        t = Turma(disciplina=Disciplina(codigo="EH0012", nome="LAB"), periodo="2026.2", codigo="01")
        db.add(t)
        ids = []
        for i in range(2):
            a = Discente(matricula=f"52000{i}", nome=f"ALUNO {i}")
            db.add(Matricula(turma=t, discente=a, situacao="ATIVO"))
            db.flush()
            ids.append(a.id)
        caso = carregar_caso_base(db)
        db.commit()
        tid, cid = t.id, caso.id
    with TestClient(app) as c:
        c.post(f"/turmas/{tid}/duplas", data={"discente_id": [str(i) for i in ids]})
        yield {"c": c, "tid": tid, "cid": cid}


def test_cnpj_valido_e_estavel():
    c = cnpj_ficticio("Ar Frio Ltda.")
    assert c == cnpj_ficticio("Ar Frio Ltda.") and re.fullmatch(r"\d\d\.\d{3}\.\d{3}/0001-\d\d", c)


def test_documentos_batem_com_o_gabarito(ctx):
    with SessionLocal() as db:
        caso = db.get(Caso, ctx["cid"])
        v = gerar(caso, 0, "base", None, base=True)
    docs = {d["id"]: d for d in gerar_documentos(v)}
    g = gerar_gabarito(v)
    memo = lambda ev, t: next(m["valor"] for m in g["memoria"][ev] if t in m["descricao"])  # noqa: E731
    assert docs["J15-1"]["total"] == memo("J15", "valor líquido")
    assert docs["J30-1"]["total"] == memo("J30", "Total da NF")
    assert docs["J39-1"]["liquido"] == memo("J39", "Líquido")
    assert docs["J27-1"]["total"] is None  # preço da venda é calculado pela dupla
    assert {d["tipo"] for d in docs.values()} >= {"nfe", "cte", "nfse", "fatura", "rpa", "contrato", "auto"}


def test_telas(ctx):
    c, tid = ctx["c"], ctx["tid"]
    c.post(f"/turmas/{tid}/duplas/gerar", data={"caso_id": str(ctx["cid"]), "modo": "faltantes"})
    with SessionLocal() as db:
        did = db.query(Dupla).filter_by(turma_id=tid).first().id
    r = c.get(f"/duplas/{did}/documentos")
    assert r.status_code == 200 and "Comercial Elegante" in r.text
    ids = re.findall(rf'/duplas/{did}/documentos/([A-Z0-9-]+)"', r.text)
    assert len(ids) >= 12
    for i in ids:
        assert c.get(f"/duplas/{did}/documentos/{i}").status_code == 200, i

"""Testes do cadastro do caso da empresa (parâmetros e faixas editáveis)."""
import io
import json
import os
import re

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models_caso import Caso  # noqa: E402


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def _caso_id(client) -> int:
    r = client.get("/casos")
    assert r.status_code == 200
    return int(re.search(r'href="/casos/(\d+)/empresa"', r.text).group(1))


def test_caso_base_carregado(client):
    cid = _caso_id(client)
    with SessionLocal() as db:
        c = db.get(Caso, cid)
        assert len(c.contratos) == 12 and len(c.eventos) == 90 and len(c.funcionarios) == 15
        assert len(c.socios) == 4 and len(c.inconsistencias) == 20
        assert {(f.produto, f.insumo): f.quantidade for f in c.ficha}[("X", "MP-A")] == 4
        leasing = {p.nome: p for p in c.params("contrato", "C04")}
        assert leasing["Valor das máquinas"].minimo == 250000 and leasing["Valor das máquinas"].maximo == 400000
    for aba in ("empresa", "contratos", "folha", "producao", "eventos", "inconsistencias"):
        assert client.get(f"/casos/{cid}/{aba}").status_code == 200, aba


def test_editar_parametro_e_incluir(client):
    cid = _caso_id(client)
    with SessionLocal() as db:
        p = db.get(Caso, cid).params("contrato", "C04")[0]
        pid = p.id
    form = {"pid": str(pid), f"nome_{pid}": "Valor das máquinas", f"unidade_{pid}": "R$", f"base_{pid}": "300.000,00",
            f"min_{pid}": "280.000,00", f"max_{pid}": "350000", f"passo_{pid}": "1.000,00", f"varia_{pid}": "on",
            "escopo": "contrato", "ref": "C04", "volta": f"/casos/{cid}/contratos",
            "novo_nome": "Carência", "novo_unidade": "meses", "novo_base": "0", "novo_min": "0", "novo_max": "3", "novo_passo": "1",
            "novo_varia": "on"}
    r = client.post(f"/casos/{cid}/parametros", data=form, follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        ps = {p.nome: p for p in db.get(Caso, cid).params("contrato", "C04")}
        assert ps["Valor das máquinas"].minimo == 280000 and ps["Valor das máquinas"].maximo == 350000
        assert ps["Valor das máquinas"].passo == 1000
        assert ps["Carência"].maximo == 3


def test_duplicar_isola_alteracoes(client):
    cid = _caso_id(client)
    r = client.post(f"/casos/{cid}/duplicar", data={"nome": "Versão Prof. Teste"}, follow_redirects=False)
    novo = int(re.search(r"/casos/(\d+)/", r.headers["location"]).group(1))
    assert novo != cid
    with SessionLocal() as db:
        p = db.get(Caso, novo).params("contrato", "C04")[0]
        pid, total_novo = p.id, len(db.get(Caso, novo).parametros)
        assert total_novo == len(db.get(Caso, cid).parametros)
    client.post(f"/casos/{novo}/parametros", data={"pid": str(pid), f"nome_{pid}": p.nome, f"base_{pid}": "1",
                                                   f"min_{pid}": "1", f"max_{pid}": "2", "escopo": "contrato"})
    with SessionLocal() as db:
        assert db.get(Caso, cid).params("contrato", "C04")[0].minimo == 280000  # original intacto
        assert db.get(Caso, novo).params("contrato", "C04")[0].minimo == 1


def test_ficha_funcionario_evento_inconsistencia(client):
    cid = _caso_id(client)
    client.post(f"/casos/{cid}/producao", data={"secao": "ficha", "ft|X|MP-A": "5", "ft|Y|MS-Q": "1", "ft|X|MS-Q": "0"})
    client.post(f"/casos/{cid}/folha", data={"secao": "funcionarios", "f_setor_novo": "Comercial", "f_nome_novo": "Nova Pessoa",
                                             "f_salario_fev_novo": "3.200,00"})
    with SessionLocal() as db:
        c = db.get(Caso, cid)
        ficha = {(f.produto, f.insumo): f.quantidade for f in c.ficha}
        assert ficha[("X", "MP-A")] == 5 and ficha[("Y", "MS-Q")] == 1 and ("X", "MS-Q") not in ficha
        assert any(f.nome == "Nova Pessoa" and f.salario_fev == 3200 for f in c.funcionarios)
        ev = next(e for e in c.eventos if e.codigo == "J30")
        inc = c.inconsistencias[0]
    r = client.post(f"/casos/{cid}/eventos/{ev.id}", data={"codigo": "J30", "data": "2026-01-27", "descricao": "Compra de MP-A",
                                                          "natureza": "V", "grupo": "Compra"}, follow_redirects=False)
    assert r.status_code == 303
    client.post(f"/casos/{cid}/inconsistencias", data={f"n_onde_{inc.id}": inc.onde, f"n_descricao_{inc.id}": inc.descricao,
                                                       f"n_decisao_{inc.id}": "Usar R$ 970.000,00", f"n_status_{inc.id}": "RESOLVIDA"})
    with SessionLocal() as db:
        c = db.get(Caso, cid)
        assert next(e for e in c.eventos if e.codigo == "J30").data.isoformat() == "2026-01-27"
        assert c.inconsistencias[0].status == "RESOLVIDA"
    assert client.get(f"/casos/{cid}/eventos/{ev.id}").status_code == 200


def test_exportar_importar(client):
    cid = _caso_id(client)
    r = client.get(f"/casos/{cid}/exportar")
    dados = r.json()
    assert len(dados["eventos"]) == 90 and dados["formato"] == "labcont-caso/1"
    arq = io.BytesIO(json.dumps(dados).encode())
    r = client.post("/casos/importar", files={"arquivo": ("caso.json", arq, "application/json")}, follow_redirects=False)
    assert r.status_code == 303 and "erro" not in r.headers["location"]
    novo = int(re.search(r"/casos/(\d+)/", r.headers["location"]).group(1))
    with SessionLocal() as db:
        a, b = db.get(Caso, cid), db.get(Caso, novo)
        assert len(a.parametros) == len(b.parametros) and len(a.eventos) == len(b.eventos)
        assert {(p.escopo, p.ref, p.nome, p.minimo, p.maximo) for p in a.parametros} == \
               {(p.escopo, p.ref, p.nome, p.minimo, p.maximo) for p in b.parametros}

"""Etapa 7b: Painel de Gestão e Learning Analytics (alertas, matriz de calor, engajamento, notas)."""
import os
import re

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app import acesso, analytics  # noqa: E402
from app import tutor as tutor_ia  # noqa: E402
from app.caso_servico import carregar_caso_base  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.gabarito import gerar_gabarito  # noqa: E402
from app.models import Disciplina, Discente, Matricula, Turma  # noqa: E402
from app.models_dupla import Dupla  # noqa: E402
from app.models_escrita import DuplaAcesso  # noqa: E402


@pytest.fixture(scope="module")
def ctx():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        t = Turma(disciplina=Disciplina(codigo="EH0012", nome="LAB"), periodo="2026.2", codigo="01")
        db.add(t)
        ids = []
        for i in range(6):
            a = Discente(matricula=f"56000{i}", nome=f"ALUNO {i}")
            db.add(Matricula(turma=t, discente=a, situacao="ATIVO"))
            db.flush()
            ids.append(a.id)
        caso = carregar_caso_base(db)
        db.commit()
        tid, cid = t.id, caso.id
    with TestClient(app=main.app) as c:
        for k in range(3):
            c.post(f"/turmas/{tid}/duplas", data={"discente_id": [str(ids[2 * k]), str(ids[2 * k + 1])]})
        c.post(f"/turmas/{tid}/duplas/gerar", data={"caso_id": str(cid), "modo": "faltantes"})
        c.post(f"/turmas/{tid}/duplas/codigos")
        with SessionLocal() as db:
            ds = db.query(Dupla).filter_by(turma_id=tid).order_by(Dupla.numero).all()
            cods = [db.query(DuplaAcesso).filter_by(dupla_id=d.id).one().codigo for d in ds]
            g1 = gerar_gabarito(ds[0].empresa.valores)
        yield {"c": c, "tid": tid, "d": [d.id for d in ds], "cod": cods, "g1": g1}


def _entrar(c, codigo, mat):
    c.cookies.clear()
    r = c.post("/aluno/primeiro-acesso", data={"codigo": codigo, "ciente": "1", "matricula_pa": mat, "nova": "senha-teste-1",
                                                "nova2": "senha-teste-1"}, follow_redirects=False)
    if r.status_code != 303:
        c.post("/aluno/entrar", data={"matricula": mat, "senha": "senha-teste-1"})


def _partidas(g, ev):
    rows = []
    for l in g["lancamentos"]:
        if l["evento"] == ev:
            rows += [(p["conta"], "D", f"{p['valor']:.2f}") for p in l["debitos"]]
            rows += [(p["conta"], "C", f"{p['valor']:.2f}") for p in l["creditos"]]
    return rows


def test_nota_por_niveis():
    assert analytics.nota_por_niveis({"a": "correto", "b": "valor", "c": "conta", "d": "pendente"}, 4) == 3.8
    assert analytics.nota_por_niveis({}, 0) == 0.0


def test_fluxo_e_painel(ctx, monkeypatch):
    c, g = ctx["c"], ctx["g1"]
    # grupo 1: lança 8 eventos corretos, todos pelo mesmo integrante, e envia janeiro
    _entrar(c, ctx["cod"][0], "560000")
    evs = [e for e in ("J02", "J03", "J05", "J06", "J07", "J10", "J11", "J12") if _partidas(g, e)]
    for ev in evs:
        rows = _partidas(g, ev)
        r = c.post("/aluno/lancar", data={"evento": ev, "data": "2026-01-15", "historico": ev, "conta": [x[0] for x in rows],
                                          "natureza": [x[1] for x in rows], "valor": [x[2] for x in rows]}, follow_redirects=False)
        assert "erro" not in r.headers["location"], ev
    c.post("/aluno/fechamento", data={"confirmo": "1"})
    # grupo 2: só pergunta ao tutor sobre o leasing (evento crítico), sem lançar
    monkeypatch.setattr(tutor_ia, "LIMITE_DIARIO", 99)
    _entrar(c, ctx["cod"][1], "560002")
    for i in range(3):
        c.post("/aluno/tutor", data={"evento": "J24", "pergunta": f"Como registro o leasing? {i}"})
    # grupo 3: nunca entrou
    c.cookies.clear()
    t = c.get(f"/turmas/{ctx['tid']}/painel").text
    assert "Matriz de calor" in t and "Alertas precoces" in t and "Dificuldades conceituais" in t and "Engajamento" in t
    assert "Sem acesso" in t and "Travado em J24" in t and "Participação desigual" in t
    assert "cel cel-correto" in t and re.search(r"\d+% oficial", t)
    an = None
    with SessionLocal() as db:
        an = analytics.analisar_turma(db, ctx["tid"])
    assert an["resumo"]["enviados"] == 1 and an["resumo"]["perguntas"] == 3
    assert an["grupos"][0]["risco"] >= 2  # ordenado por risco
    tema = next(x for x in an["temas"] if x["tema"].startswith("Financeiro"))
    assert tema["perguntas"] == 3
    assert sum(an["engaj"]["series"]["lancamentos"]) >= len(evs)


def test_notas_e_homologacao(ctx):
    c = ctx["c"]
    c.cookies.clear()
    t = c.get(f"/turmas/{ctx['tid']}/notas").text
    assert "Aguardando envio" in t and "Proposta" in t
    with SessionLocal() as db:
        ns = db.query(analytics.NotaPeriodo).filter_by(turma_id=ctx["tid"]).all()
        n1 = [n for n in ns if n.dupla_id == ctx["d"][0]]
        assert len(ns) == 6 and len(n1) == 2 and all(n.nota_sistema is not None and n.nota_sistema > 0 for n in n1)
        alvo = n1[0]
        base = alvo.nota_sistema
    c.post(f"/turmas/{ctx['tid']}/notas", data={f"ajuste_{alvo.id}": "0,5", f"obs_{alvo.id}": "Boa participação",
                                                f"sel_{alvo.id}": "on", "acao": "homologar"})
    with SessionLocal() as db:
        n = db.get(analytics.NotaPeriodo, alvo.id)
        assert n.homologada and n.nota_final == round(min(10, base + 0.5), 1)
        mat = db.get(Discente, n.discente_id).matricula
    csv = c.get(f"/turmas/{ctx['tid']}/notas.csv").text
    assert "Boa participação" in csv and mat in csv
    # o aluno vê a nota homologada; o colega (não homologado) não vê
    _entrar(c, ctx["cod"][0], mat)
    assert "Nota de janeiro (homologada" in c.get("/aluno").text
    outro = "560001" if mat == "560000" else "560000"
    _entrar(c, ctx["cod"][0], outro)
    assert "Nota de janeiro (homologada" not in c.get("/aluno").text
    # desfazer
    c.cookies.clear()
    c.post(f"/turmas/{ctx['tid']}/notas", data={f"sel_{alvo.id}": "on", "acao": "desfazer"})
    with SessionLocal() as db:
        assert not db.get(analytics.NotaPeriodo, alvo.id).homologada


def test_painel_de_gestao_e_monitor(ctx):
    c = ctx["c"]
    c.cookies.clear()
    t = c.get("/").text
    assert "Painel de Gestão" in t and "Turma 01" in t and "Adesão" in t and "Acesso ao sistema" in t
    with SessionLocal() as db:
        u = acesso.Usuario(login="mon@ufc", nome="Monitor", senha_hash=acesso.gerar_hash("senha-forte-1"))
        u.perfis.append(acesso.UsuarioPerfil(perfil="monitor", turma_id=ctx["tid"]))
        db.add(u)
        db.commit()
        uid = u.id
    try:
        c.post("/entrar", data={"login": "mon@ufc", "senha": "senha-forte-1"})
        t = c.get(f"/turmas/{ctx['tid']}/painel").text
        assert "Matriz de calor" in t and "% erro" in t and "prévia" not in t.split("id=\"visao\"")[1].split("</section>")[0].split("<tbody>")[1]
        assert "Contas com mais divergências" in t and "Disponível para professores" in t
        assert c.get(f"/turmas/{ctx['tid']}/notas", follow_redirects=False).status_code == 403
        assert "Acesso ao sistema" not in c.get("/").text
    finally:
        with SessionLocal() as db:
            db.delete(db.get(acesso.Usuario, uid))
            db.commit()
        c.cookies.clear()

"""Etapa 8a: fevereiro no sistema (mês livre desde o início, fechamento próprio) e eventos sem produção."""
import os
from datetime import date

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app import demo  # noqa: E402
from app import plano_contas as pc  # noqa: E402
from app.auditoria import auditar, eventos_mes  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.gabarito import Gabarito, gerar_gabarito  # noqa: E402
from app.models_dupla import Dupla  # noqa: E402
from app.models_escrita import Lancamento  # noqa: E402
from app.periodos import mes_do_evento  # noqa: E402


@pytest.fixture(scope="module")
def ctx():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app=main.app) as c:
        with SessionLocal() as db:
            r = demo.criar(db)
            tid = r["turma_id"]
            ds = db.query(Dupla).filter_by(turma_id=tid).order_by(Dupla.numero).all()
            for u in db.query(main.acesso.Usuario).filter(main.acesso.Usuario.login.in_(["avaliador", "professor.demo"])).all():
                db.delete(u)
            db.commit()
            aluno = r["credenciais"]["aluno"]
            did = next(d.id for d in ds if any(m.discente.matricula == aluno["login"] for m in d.membros))
            valores = db.get(Dupla, did).empresa.valores
        yield {"c": c, "tid": tid, "did": did, "aluno": aluno, "v": valores}


def _partidas(g, ev):
    rows = []
    for l in g["lancamentos"]:
        if l["evento"] == ev:
            rows += [(p["conta"], "D", f"{p['valor']:.2f}") for p in l["debitos"]]
            rows += [(p["conta"], "C", f"{p['valor']:.2f}") for p in l["creditos"]]
    return rows


def _entrar(c, aluno):
    c.cookies.clear()
    c.post("/aluno/entrar", data={"matricula": aluno["login"], "senha": aluno["senha"]})


def test_gabarito_fevereiro(ctx):
    v = ctx["v"]
    jan = gerar_gabarito(v)
    fev = gerar_gabarito(v, "2026-02")
    assert jan["mes"] == "2026-01" and fev["mes"] == "2026-02"
    assert fev["totais"]["fecha"]
    assert all(l["evento"].startswith("F") for l in fev["lancamentos"])
    # abertura de fevereiro = fechamento de janeiro
    fim_jan = {x["conta"]: x["final"] for x in jan["balancete"]}
    for x in fev["balancete"]:
        assert x["inicial"] == pytest.approx(fim_jan.get(x["conta"], 0.0), abs=0.005)
    # pagamentos da competência 01 pelo saldo de 31/01 (IRRF e CSRF de dezembro ficam)
    net = lambda ev, conta: sum(p["valor"] for l in fev["lancamentos"] if l["evento"] == ev for p in l["debitos"] if p["conta"] == conta)  # noqa: E731
    assert net("F12", pc.FGTS_REC) == pytest.approx(-fim_jan[pc.FGTS_REC], abs=0.01)
    assert net("F29", pc.IRRF_RECOL) == pytest.approx(-fim_jan[pc.IRRF_RECOL] - 348.93, abs=0.01)
    assert net("F16", pc.ISS_RECOL) == pytest.approx(-fim_jan[pc.ISS_RECOL], abs=0.01)
    # eventos de produção, vendas e folha ainda em preparação (etapas 8b a 8e); tesouraria provisória
    assert {"F05", "F20", "F34", "F48", "FTES", "FAJ"} <= set(fev["sem_gabarito"])
    assert "F08" not in fev["sem_gabarito"] and "F33" not in fev["sem_gabarito"]
    # leasing: parcela = amortização + juros desde 20/01; uma parcela passa do longo para o curto prazo
    f33 = [l for l in fev["lancamentos"] if l["evento"] == "F33"]
    prazo = Gabarito(v).p("contrato", "C04", "prazo", 18)
    if prazo > 12:
        assert len(f33) == 2 and f33[1]["debitos"][0]["conta"] == pc.LEASING_LP
    else:
        assert len(f33) == 1
    # reforma concluída: em andamento zerado e transferido para edifícios
    assert next(x for x in fev["balancete"] if x["conta"] == pc.OBRAS)["final"] == pytest.approx(0, abs=0.005)


def test_eventos_e_mes_do_codigo():
    evs = eventos_mes(None, "2026-02")
    cods = [e["codigo"] for e in evs]
    assert cods[0] == "F01" and "F48" in cods and cods[-2:] == ["FTES", "FAJ"] and len(cods) == 50
    assert all(e["data"].month == 2 for e in evs)
    assert mes_do_evento("F08") == "2026-02" and mes_do_evento("J08") == "2026-01" and mes_do_evento("TES") == "2026-01"


def test_fluxo_aluno_fevereiro(ctx):
    c, v = ctx["c"], ctx["v"]
    _entrar(c, ctx["aluno"])
    c.get("/aluno/mes/2026-02?volta=/aluno")
    t = c.get("/aluno").text
    assert "Fevereiro/2026" in t and "Fechamento de fevereiro" in t and "F08" in t
    # data fora do mês é recusada
    g = gerar_gabarito(v, "2026-02")
    rows = _partidas(g, "F08")
    r = c.post("/aluno/lancar", data={"evento": "F08", "data": "2026-01-20", "historico": "NFS-e 003 comissão",
                                      "conta": [x[0] for x in rows], "natureza": [x[1] for x in rows], "valor": [x[2] for x in rows]})
    assert "é de fevereiro" in r.text
    for ev in ("F08", "F13", "F27", "F45"):
        rows = _partidas(g, ev)
        r = c.post("/aluno/lancar", data={"evento": ev, "data": f"2026-02-{dict(F08=6, F13=10, F27=20, F45=27)[ev]:02d}",
                                          "historico": f"Lançamento do evento {ev}", "conta": [x[0] for x in rows],
                                          "natureza": [x[1] for x in rows], "valor": [x[2] for x in rows]}, follow_redirects=False)
        assert r.status_code == 303 and "mes=2026-02" in r.headers["location"], ev
    # diário e balancete de fevereiro
    assert "Livro Diário · fevereiro/2026" in c.get("/aluno/diario").text
    bal = c.get("/aluno/balancete").text
    assert "Fevereiro/2026" in bal and "Mútuo a Receber" in bal
    docs = c.get("/aluno/documentos").text
    assert "988.333" in docs and "987321" not in docs  # só os de fevereiro
    # envia fevereiro: correção aparece; janeiro continua aberto (se ainda não enviado)
    with SessionLocal() as db:
        from app.models_escrita import fechamento_ativo
        jan_enviado = bool(fechamento_ativo(db, ctx["did"], "2026-01"))
    r = c.post("/aluno/fechamento", data={"mes": "2026-02", "confirmo": "1"}, follow_redirects=False)
    assert r.status_code == 303
    t = c.get("/aluno?mes=2026-02").text
    assert "Eventos corretos em fevereiro" in t and "Correção em preparação" in t
    with SessionLocal() as db:
        from app.models_escrita import fechamento_ativo
        f = fechamento_ativo(db, ctx["did"], "2026-02")
        assert f and f.resultado["eventos"]["F08"]["nivel"] == "correto" and f.resultado["eventos"]["F45"]["nivel"] == "correto"
        assert bool(fechamento_ativo(db, ctx["did"], "2026-01")) == jan_enviado
    # fevereiro bloqueado; janeiro segue a própria regra
    r = c.get("/aluno/lancar?evento=F01", follow_redirects=False)
    assert r.status_code == 303 and "mes=2026-02" in r.headers["location"]
    if not jan_enviado:
        assert c.get("/aluno/lancar?evento=J01").status_code == 200


def test_telas_da_equipe_por_mes(ctx):
    c = ctx["c"]
    c.cookies.clear()
    did, tid = ctx["did"], ctx["tid"]
    t = c.get(f"/duplas/{did}/escrituracao?mes=2026-02").text
    assert "Fevereiro/2026" in t and "fevereiro enviado" in t.lower()
    t = c.get(f"/duplas/{did}/gabarito?mes=2026-02").text
    assert "Fevereiro em construção" in t and "Balancete de verificação em 28/02/2026" in t and "P33" in t
    assert c.get(f"/duplas/{did}/gabarito.xlsx?mes=2026-02").status_code == 200
    t = c.get(f"/turmas/{tid}/painel?mes=2026-02").text
    assert "Acompanhamento de fevereiro" in t and "Matriz de calor" in t
    t = c.get(f"/turmas/{tid}/notas?mes=2026-02").text
    assert "Notas de fevereiro" in t
    assert "Gabarito de fevereiro" in c.get(f"/duplas/{did}/empresa").text
    assert c.get(f"/duplas/{did}/demonstracoes?mes=2026-02").status_code == 200
    # janeiro continua como antes
    assert "Balancete de verificação em 31/01/2026" in c.get(f"/duplas/{did}/gabarito").text


def test_auditoria_filtra_o_mes(ctx):
    v = ctx["v"]
    with SessionLocal() as db:
        lancs = db.query(Lancamento).filter_by(dupla_id=ctx["did"]).all()
        a_jan = auditar(gerar_gabarito(v), lancs)
        a_fev = auditar(gerar_gabarito(v, "2026-02"), lancs)
    assert all(not e["codigo"].startswith("F") for e in a_jan["eventos"])
    assert all(e["codigo"].startswith("F") for e in a_fev["eventos"])
    assert a_fev["total"] == len([e for e in a_fev["eventos"] if not e["sem_gabarito"]])
    assert Gabarito(v).L.ini  # saldos de 31/12/2025 seguem acessíveis
    assert date(2026, 2, 28) == eventos_mes(None, "2026-02")[-1]["data"]

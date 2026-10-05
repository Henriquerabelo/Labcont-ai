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
    assert fev["sem_gabarito"] == []  # fevereiro completo (8e)
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
    assert cods[0] == "F01" and "F48" in cods and cods[-2:] == ["FTES", "FAJ"] and len(cods) == 52 and "FP1" in cods and "FP2" in cods
    assert all(e["data"].month == 2 for e in evs)
    assert mes_do_evento("F08") == "2026-02" and mes_do_evento("J08") == "2026-01" and mes_do_evento("TES") == "2026-01"


def test_demo_tem_fevereiro(ctx):
    with SessionLocal() as db:
        n = db.query(Lancamento).filter(Lancamento.dupla_id == ctx["did"], Lancamento.evento.like("F%")).count()
    assert n > 0  # o grupo do acesso de aluno da demonstração já mostra fevereiro


def test_fluxo_aluno_fevereiro(ctx):
    c, v = ctx["c"], ctx["v"]
    with SessionLocal() as db:  # parte do zero em fevereiro para conferir a correção
        for l in db.query(Lancamento).filter(Lancamento.dupla_id == ctx["did"], Lancamento.evento.like("F%")).all():
            db.delete(l)
        db.commit()
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
    assert "Eventos corretos em fevereiro" in t and "Correção em preparação" not in t
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
    assert "Fevereiro em construção" not in t and "Balancete de verificação em 28/02/2026" in t and "P33" in t
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


def test_8b_compras_e_estoques(ctx):
    from app.gabarito import NCM, TIPI
    from app.orientacao import Valores
    v = ctx["v"]
    x = Valores(v)
    g = gerar_gabarito(v, "2026-02")
    lancs = {}
    for l in g["lancamentos"]:
        lancs.setdefault(l["evento"], []).append(l)
    deb = lambda ev, c: round(sum(p["valor"] for l in lancs.get(ev, []) for p in l["debitos"] if p["conta"] == c), 2)  # noqa: E731
    cred = lambda ev, c: round(sum(p["valor"] for l in lancs.get(ev, []) for p in l["creditos"] if p["conta"] == c), 2)  # noqa: E731
    mpb = x.insumo("MP-B")
    prod = round(mpb["compra"] * mpb["custo_unit"], 2)
    assert deb("F05", pc.IPI_REC) == pytest.approx(round(prod * TIPI[NCM["MP-B"]], 2), abs=0.01)  # IPI 13% recuperável
    total = prod + deb("F05", pc.IPI_REC)
    dp = Gabarito(v).p("evento", "F05", "desconto", 4)
    assert cred("F05", pc.DESC_OBTIDOS) == pytest.approx(round(round(total * 0.35, 2) * dp / 100, 2), abs=0.02)
    assert deb("F05", pc.ESTOQUE["MP-B"]) > 0 and cred("F05", pc.F_FRETE) > 0  # frete FOB no custo
    # materiais secundários: sem IPI (distribuidor), ICMS 7%
    assert deb("F10", pc.IPI_REC) == 0 and all(deb("F10", pc.ESTOQUE[c]) > 0 for c in ("MS-Z", "MS-K"))
    # devolução: baixa do estoque, estorno de créditos e abatimento no fornecedor
    assert deb("F28", pc.F_SOFISTICADA) > 0 and cred("F28", pc.ESTOQUE["MP-A"]) > 0 and cred("F28", pc.IPI_REC) > 0
    assert deb("F23", pc.F_FRETE) == cred("F05", pc.F_FRETE)
    assert deb("F35", pc.F_FRETE) == cred("F22", pc.F_FRETE)
    assert any("custo médio" in m["descricao"] for m in g["memoria"]["F28"])
    assert {"P38", "P40", "P42"} <= set(g["premissas"])
    from app.documentos import gerar_documentos
    ids = {d["id"] for d in gerar_documentos(v)}
    assert {"F05-1", "F05-2", "F10-1", "F22-1", "F22-2", "F28-1"} <= ids


def test_8c_folha_depreciacao_producao(ctx):
    v = ctx["v"]
    g = gerar_gabarito(v, "2026-02")
    bal = {x["conta"]: x["final"] for x in g["balancete"]}
    # contas de passagem zeradas: CIF, MOD a apropriar e produtos em elaboração
    for c in pc.CIF_CONTAS + list(pc.MOD.values()) + list(pc.PEP.values()):
        assert abs(bal.get(c, 0.0)) < 0.01, c
    # produtos acabados = materiais + MOD + CIF; estoques de insumos ficam só com as sobras
    prods = {p["codigo"]: p["quantidade"] for p in v["producao"]["produtos"]}
    assert bal[pc.PA["X"]] > 0 and bal[pc.PA["Y"]] > 0
    for i in v["producao"]["insumos"]:
        assert bal.get(pc.ESTOQUE[i["codigo"]], 0) < 0.02 * i["valor_compra"], i["codigo"]  # só a sobra
    lancs = {}
    for l in g["lancamentos"]:
        lancs.setdefault(l["evento"], []).append(l)
    deb = lambda ev, c: round(sum(p["valor"] for l in lancs.get(ev, []) for p in l["debitos"] if p["conta"] == c), 2)  # noqa: E731
    # folha: MOD de X e Y vai para "a apropriar"; MOI e pró-labore industrial para CIF
    assert deb("F20", pc.MOD["X"]) > 0 and deb("F20", pc.MOD["Y"]) > 0 and deb("F20", pc.CIF_MOI) > 0
    assert deb("F20", pc.CIF_PROLAB) > 0  # sócio industrial
    assert deb("F21", pc.CIF_DEPREC) > 0
    # CIF rateado pelos materiais diretos
    md = {p: deb("FP1", pc.PEP[p]) for p in ("X", "Y")}
    cif_tot = sum(deb(ev, c) for ev in lancs for c in pc.CIF_CONTAS)
    apr = {p: deb("FP2", pc.PEP[p]) - (deb("F20", pc.MOD[p])) for p in ("X", "Y")}
    assert apr["X"] / cif_tot == pytest.approx(md["X"] / (md["X"] + md["Y"]), abs=0.001)
    # custo unitário na memória
    assert any("custo unitário" in m["descricao"] for m in g["memoria"]["FP2"])
    assert prods["X"] > 0 and {"P43", "P46", "P47"} <= set(g["premissas"])
    from app.documentos import gerar_documentos
    ids = {d["id"] for d in gerar_documentos(v)}
    assert {"FP1-1", "FP2-1"} <= ids


def test_8c_tela_documento_producao(ctx):
    c = ctx["c"]
    c.cookies.clear()
    t = c.get(f"/duplas/{ctx['did']}/documentos/FP1-1").text
    assert "Requisição de materiais" in t and "MP-A" in t and "Total requisitado" in t


def test_8d_vendas(ctx):
    from app.gabarito import NCM, TIPI
    v = ctx["v"]
    g = gerar_gabarito(v, "2026-02")
    lancs = {}
    for l in g["lancamentos"]:
        lancs.setdefault(l["evento"], []).append(l)
    deb = lambda ev, c: round(sum(p["valor"] for l in lancs.get(ev, []) for p in l["debitos"] if p["conta"] == c), 2)  # noqa: E731
    cred = lambda ev, c: round(sum(p["valor"] for l in lancs.get(ev, []) for p in l["creditos"] if p["conta"] == c), 2)  # noqa: E731
    # F04: consumidor final no MA, ICMS 12% + DIFAL 11%
    rec = cred("F04", pc.REC_REVENDA)
    assert deb("F04", pc.DED_ICMS) == pytest.approx(round(rec * 0.12, 2), abs=0.01)
    assert cred("F04", pc.DIFAL_MA) == pytest.approx(round(rec * 0.11, 2), abs=0.01)
    # F34: IPI fora da receita, ICMS 12% sobre os produtos, desconto como despesa financeira, CPV pelo custo de produção
    rp = cred("F34", pc.REC_PRODUTOS)
    assert cred("F34", pc.IPI_RECOL) > 0 and deb("F34", pc.DED_ICMS) == pytest.approx(round(rp * 0.12, 2), abs=0.05)
    assert deb("F34", pc.DESC_CONCEDIDOS) > 0 and deb("F34", pc.CPV) > 0
    assert TIPI[NCM["Y"]] == 0.195
    bal = {x["conta"]: x["final"] for x in g["balancete"]}
    vend = {p["codigo"]: p for p in v["producao"]["produtos"]}
    # sobra no estoque de produtos acabados = produzido − vendido
    assert bal[pc.PA["X"]] > 0 and vend["X"]["estoque_final"] > 0
    # F36 devolução e F44 recebimento líquido zeram o cliente da NF 003
    assert deb("F36", pc.DEVOLUCOES) > 0 and deb("F36", pc.ALPHA) > 0
    assert deb("F44", pc.BANCO) == pytest.approx(deb("F26", pc.CLIENTES) - cred("F36", pc.CLIENTES), abs=0.01)
    assert {"P48", "P49", "P50", "P51", "P52"} <= set(g["premissas"])
    from app.documentos import gerar_documentos
    ids = {d["id"] for d in gerar_documentos(v)}
    assert {"F04-1", "F26-1", "F34-1", "F36-1"} <= ids


def test_8e_apuracao_e_mes_completo(ctx):
    v = ctx["v"]
    g = gerar_gabarito(v, "2026-02")
    bal = {x["conta"]: x["final"] for x in g["balancete"]}
    f48 = [l for l in g["lancamentos"] if l["evento"] == "F48"]
    hist = " | ".join(l["historico"] for l in f48)
    assert "Apuração do ICMS de fevereiro" in hist and "Apuração do IPI de fevereiro" in hist and "IRPJ e CSLL por estimativa" in hist
    # depois da apuração, cada imposto fica só de um lado (a recolher ou a recuperar)
    for rec, recol in ((pc.ICMS_REC, pc.ICMS_RECOL), (pc.IPI_REC, pc.IPI_RECOL), (pc.PIS_REC, pc.PIS_RECOL), (pc.COFINS_REC, pc.COFINS_RECOL)):
        assert not (bal.get(rec, 0) > 0.01 and bal.get(recol, 0) < -0.01), rec
    assert bal.get(pc.ICMS_ANT_REC, 0) == pytest.approx(0, abs=0.01)  # antecipado de janeiro aproveitado
    assert bal[pc.IRPJ_RECOL] < 0 and bal[pc.CSLL_RECOL] < 0
    assert {"P53", "P54"} <= set(g["premissas"])
    assert g["sem_gabarito"] == [] and any(l["evento"] == "FAJ" for l in g["lancamentos"])

"""Ajustes rápidos (verificação de 05/10): DRE/BP, avisos estruturais, fichas, tempo até o envio, privacidade, marcas."""
import os
import re
from datetime import date

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app import analytics, consistencia, demo  # noqa: E402
from app import demonstracoes as dm  # noqa: E402
from app import plano_contas as pc  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.gabarito import gerar_gabarito  # noqa: E402
from app.models_dupla import Dupla  # noqa: E402
from app.models_escrita import DuplaAcesso  # noqa: E402
from app.normas import Norma  # noqa: E402


@pytest.fixture(scope="module")
def ctx():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app=main.app) as c:
        with SessionLocal() as db:
            r = demo.criar(db)
            tid = r["turma_id"]
            ds = db.query(Dupla).filter_by(turma_id=tid).order_by(Dupla.numero).all()
            cod3 = db.query(DuplaAcesso).filter_by(dupla_id=ds[2].id).one().codigo
            # sem usuários de equipe, os testes entram nas telas do professor em modo local
            for u in db.query(main.acesso.Usuario).filter(main.acesso.Usuario.login.in_(["avaliador", "professor.demo"])).all():
                db.delete(u)
            db.commit()
        yield {"c": c, "tid": tid, "d": [d.id for d in ds], "cod3": cod3, "aluno": r["credenciais"]["aluno"]}


def test_dre_bp_do_gabarito_fecham(ctx):
    with SessionLocal() as db:
        d = db.get(Dupla, ctx["d"][0])
        g = gerar_gabarito(d.empresa.valores)
    r = dm.montar(dm.de_gabarito(g))
    assert r["lucro"] == pytest.approx(g["totais"]["resultado"], abs=0.01)
    assert r["bp"]["fecha"] and r["are"][-1]["final"]
    rotulos = [x["rotulo"] for x in r["dre"]]
    assert "Receita líquida" in rotulos and "Lucro bruto" in rotulos and rotulos[-1] == "Resultado líquido do período"


def test_telas_demonstracoes(ctx):
    c = ctx["c"]
    c.cookies.clear()
    t = c.get(f"/duplas/{ctx['d'][0]}/demonstracoes").text
    assert "DRE · dupla" in t and "Balanço · gabarito" in t
    c.post("/aluno/entrar", data={"matricula": ctx["aluno"]["login"], "senha": ctx["aluno"]["senha"]})
    t = c.get("/aluno/demonstracoes").text
    assert "Demonstração do resultado" in t and "Balanço patrimonial" in t and "Prévia do encerramento" in t
    assert "Balanço · gabarito" not in t


class P:
    def __init__(s, conta, nat, valor):
        s.conta, s.natureza, s.valor = conta, nat, valor


class L:
    def __init__(s, i, ev, dt, hist, parts):
        s.id, s.evento, s.data, s.historico, s.partidas = i, ev, dt, hist, parts


def test_avisos_estruturais():
    ini = {pc.BANCO: 100.0}
    lancs = [L(1, "J10", date(2026, 2, 3), "x", [P(pc.F_INTERNET, "D", 500), P(pc.BANCO, "C", 500)]),
             L(2, "J10", date(2026, 2, 3), "x", [P(pc.F_INTERNET, "D", 500), P(pc.BANCO, "C", 500)])]
    av = consistencia.verificar(ini, lancs, {"J10": date(2026, 1, 10)})
    titulos = " | ".join(a["titulo"] for a in av)
    assert "data fora de janeiro" in titulos and "histórico curto" in titulos and "lançamento repetido" in titulos
    assert any(a["nivel"] == "erro" and "Banco" in a["titulo"] for a in av)
    assert av[0]["nivel"] == "erro"
    ok = [L(3, "J10", date(2026, 1, 10), "Pagamento da fatura de telefonia", [P(pc.F_INTERNET, "D", 50), P(pc.BANCO, "C", 50)])]
    assert not [a for a in consistencia.verificar(ini, ok, {"J10": date(2026, 1, 10)}) if a.get("lancamento_id") == 3]


def test_aviso_no_painel_e_mensagem(ctx):
    c = ctx["c"]
    c.cookies.clear()
    c.post("/aluno/entrar", data={"matricula": ctx["aluno"]["login"], "senha": ctx["aluno"]["senha"]})
    r = c.post("/aluno/lancar", data={"evento": "J20", "data": "2026-01-20", "historico": "x",
                                      "conta": [pc.BANCO, pc.CAPITAL["Marcela Soares"][1]],
                                      "natureza": ["D", "C"], "valor": ["1,00", "1,00"]}, follow_redirects=False)
    assert r.status_code == 303 and "avisos" in r.headers["location"]
    assert "Conferência imediata" in c.get("/aluno").text


def test_fichas_novas_e_atualizacao(ctx):
    with SessionLocal() as db:
        cods = {n.codigo for n in db.query(Norma).all()}
        assert {"CPC26-01", "CPC26-02", "ICMS-08", "ISS-FOR"} <= cods
        assert "Lei estadual 12.670/1996" in db.query(Norma).filter_by(codigo="ICMS-05").one().fonte
        assert {"ISS-FOR-02", "ISS-FOR-03", "ISS-FOR-04", "ICMS-09"} <= cods
        assert "229, 240 e 245" in db.query(Norma).filter_by(codigo="ISS-FOR").one().fonte
        assert "35.061/2022" in db.query(Norma).filter_by(codigo="ICMS-09").one().fonte


def test_busca_ctm_e_ricms():
    from app.dados_normas.fichas import FICHAS
    from app.normas import buscar
    ns = [Norma(**f, ativa=True) for f in FICHAS]
    assert buscar(ns, "Qual a alíquota do ISS da reforma do galpão? O material entra?", "J26")[0][0].codigo == "ISS-FOR-03"
    assert buscar(ns, "Onde encontro o regulamento do ICMS do Ceará?")[0][0].codigo == "ICMS-09"
    assert "ISS-FOR-04" in [n.codigo for n, _ in buscar(ns, "O arquiteto autônomo do RPA: preciso reter ISS?", "J23")]


def test_tempo_ate_envio_e_privacidade(ctx):
    c = ctx["c"]
    c.cookies.clear()
    with SessionLocal() as db:
        an = analytics.analisar_turma(db, ctx["tid"])
    assert an["resumo"]["tempo_medio"] is not None and an["resumo"]["tempo_medio"] > 0
    assert "Tempo médio até o envio" in c.get(f"/turmas/{ctx['tid']}/painel").text
    assert "Tempo médio" in c.get("/").text
    t = c.get("/privacidade").text
    assert "Aviso de privacidade" in t and "art. 18" in t
    with SessionLocal() as db:
        d3 = db.get(Dupla, ctx["d"][2])
        outro = [m.discente.matricula for m in d3.membros if m.discente.matricula != ctx["aluno"]["login"]][0]
    r = c.post("/aluno/primeiro-acesso", data={"codigo": ctx["cod3"], "matricula_pa": outro, "nova": "senha-xyz-12", "nova2": "senha-xyz-12"})
    assert "aviso de privacidade" in r.text


def test_sem_marcas_reais(ctx):
    c = ctx["c"]
    with SessionLocal() as db:
        from app.models_caso import Evento
        assert not db.query(Evento).filter(Evento.descricao.ilike("%enel%") | Evento.descricao.ilike("%cagece%")).count()
    c.cookies.clear()
    lista = c.get(f"/duplas/{ctx['d'][0]}/documentos").text
    assert "Luz do Sertão" in lista or "Águas do Litoral" in lista
    assert not re.search(r"Enel|CAGECE|Companhia de Água e Esgoto do Ceará", lista)

"""Decisões do professor sobre as inconsistências (11/10/2026): caso-base, gabarito, documentos e casos existentes."""
import os
from datetime import date

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from app import ajuste_exercicio  # noqa: E402
from app import plano_contas as pc  # noqa: E402
from app.caso_servico import carregar_caso_base  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.documentos import gerar_documentos  # noqa: E402
from app.fuso import AjusteSistema  # noqa: E402
from app.gabarito import gerar_gabarito  # noqa: E402
from app.geracao import gerar  # noqa: E402
from app.models import Disciplina, Turma  # noqa: E402
from app.models_caso import Caso  # noqa: E402
from app.models_dupla import Dupla, EmpresaGerada  # noqa: E402


@pytest.fixture(scope="module")
def base():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        caso = carregar_caso_base(db)
        v = gerar(caso, 0, "Caso-base", None, base=True)
        db.commit()
    return v


def _memo(g, ev):
    return {m["descricao"].strip(): m["valor"] for m in g["memoria"].get(ev, [])}


def _lancs(g, ev):
    return [l for l in g["lancamentos"] if l["evento"] == ev]


def test_gabarito_com_as_decisoes(base):
    gj, g = gerar_gabarito(base), gerar_gabarito(base, "2026-02")
    assert g["totais"]["fecha"] and g["totais"]["diferenca"] == 0
    assert any("28,80%" in x["descricao"] for m in gj["memoria"].values() for x in m)
    # Ar Frio: 40%
    assert "40% do valor da NF 7.852" in _memo(g, "F11")
    # mútuo pelo contrato C10 (R$ 30.000,00 no caso-base)
    assert next(v for k, v in _memo(g, "F27").items() if k.startswith("Mútuo cedido")) == 30000
    # recrutamento: pagamento único na emissão (26/02), sem saldo a pagar no fim de fevereiro
    pag = [l for l in _lancs(g, "F41") if l["historico"].startswith("Pagamento")]
    assert len(pag) == 1 and pag[0]["data"].startswith("2026-02-26")
    mov = sum(p["valor"] for l in gj["lancamentos"] + g["lancamentos"] for p in l["creditos"] if p["conta"] == pc.F_RECRUT) - \
        sum(p["valor"] for l in gj["lancamentos"] + g["lancamentos"] for p in l["debitos"] if p["conta"] == pc.F_RECRUT)
    assert abs(mov) < 0.01
    # datas: leasing 19/01, auto 05/02, contador 10/02
    assert _lancs(gj, "J24")[0]["data"].startswith("2026-01-19")
    assert _lancs(g, "F06")[0]["data"].startswith("2026-02-05")
    assert _lancs(g, "F17")[0]["data"].startswith("2026-02-10")
    # comissões recebidas com atraso, sem juros (P56)
    assert "P56" in _lancs(gj, "J25")[0]["premissas"] and "P56" in _lancs(g, "F13")[0]["premissas"]


def test_documentos_com_as_decisoes(base):
    docs = {d["id"]: d for d in gerar_documentos(base)}
    assert docs["J08-1"]["data"] == "2026-01-05" and "08/01/2026" in docs["J08-1"]["obs"]
    assert docs["J30-1"]["data"] == "2026-01-24" and "26/01/2026" in docs["J30-1"]["obs"]
    assert docs["F41-1"]["vencimento"] == "2026-02-26"
    assert docs["F45-1"]["vencimento"] == "2026-03-10"
    assert "Contador Formado S/A" in str(docs["F45-1"]["emitente"])


def test_orientacao_com_as_decisoes(base):
    import io
    from docx import Document
    from app.orientacao import gerar_docx
    dados, _ = gerar_docx(base, "Caso-base")
    doc = Document(io.BytesIO(dados))
    txt = "\n".join(p.text for p in doc.paragraphs)
    for trecho in ("28,80%", "Contador Formado S/A", "R$ 410,00", "R$ 580,00", "R$ 30.000,00", "Pagamento parcial 40%",
                   "19.01.2026 ⇨Valor do Leasing", "05.02.2026 ⇨Pagamento do auto", "10.02.2026 ⇨Pagamento da Nota Fiscal de Serviço n.º 023",
                   "a serem pagos em 10.03.2026", "serão pagos em 26.02.2026"):
        assert trecho in txt, trecho
    assert "27,80%" not in txt and "Contador Formado S/S" not in txt


def test_atualiza_casos_ja_cadastrados():
    with SessionLocal() as db:
        db.query(AjusteSistema).filter_by(chave=ajuste_exercicio.CHAVE_1110).delete()
        caso = carregar_caso_base(db, "Caso de 07/10")
        # volta o caso para a versão anterior às decisões de 11/10
        for p in caso.parametros:
            for (cod, ini), (antigo, _n, _mn, _mx) in ajuste_exercicio.PARAMS_1110.items():
                if p.ref == cod and p.nome.lower().startswith(ini):
                    p.base = str(antigo)
        for e in caso.eventos:
            if ajuste_exercicio.EVENTOS_1110.get(e.codigo):
                e.data = date.fromisoformat(ajuste_exercicio.EVENTOS_1110[e.codigo])
            if e.codigo in ajuste_exercicio.DESCRICOES_ANTIGAS_1110:
                e.descricao = ajuste_exercicio.DESCRICOES_ANTIGAS_1110[e.codigo]
        next(c for c in caso.contratos if c.codigo == "C06").parte = "Contador Formado S/S (Fortaleza)"
        next(f for f in caso.funcionarios if f.nome == "Marena Russa").dependentes_fev = "1 (6 anos)"
        dados = dict(caso.dados)
        dados["folha_regras"] = {**dados["folha_regras"], "encargos": "INSS patronal + RAT + Terceiros 27,80%; FGTS 8,00%"}
        caso.dados = dados
        for x in caso.inconsistencias:
            if x.onde.startswith("Mútuo"):
                x.status, x.decisao = "PENDENTE", None
            if x.onde.startswith("Arquiteto"):
                x.status, x.decisao = "MANTIDA", "Decisão própria do professor"
        disc = Disciplina(codigo="EH8", nome="Teste"); db.add(disc); db.flush()
        t = Turma(disciplina_id=disc.id, codigo="98A", periodo="2026.2"); db.add(t); db.flush()
        d = Dupla(turma_id=t.id, numero=1); db.add(d); db.flush()
        d.empresa = EmpresaGerada(caso_id=caso.id, semente=11, valores=gerar(caso, 11, d.rotulo, d.numero))
        db.commit()
        cid, did = caso.id, d.id

        assert ajuste_exercicio.aplicar_1110(db) >= 1
        assert ajuste_exercicio.aplicar_1110(db) == 0  # só uma vez
        db.expire_all()
        caso = db.get(Caso, cid)
        par = {(p.ref, p.nome): p.base for p in caso.parametros}
        assert par[("C10", "Valor do mútuo")] == "30000" and par[("C07", "Mensalidade")] == "410"
        ev = {e.codigo: e for e in caso.eventos}
        assert (ev["J24"].data, ev["F06"].data, ev["F17"].data) == (date(2026, 1, 19), date(2026, 2, 5), date(2026, 2, 10))
        assert "40%" in ev["F11"].descricao
        assert next(c for c in caso.contratos if c.codigo == "C06").parte.startswith("Contador Formado S/A")
        assert next(f for f in caso.funcionarios if f.nome == "Marena Russa").dependentes_fev == "1 (9 anos)"
        assert "28,80%" in caso.dados["folha_regras"]["encargos"]
        inc = {x.onde: x for x in caso.inconsistencias}
        assert inc["Mútuo (C10, F27)"].status == "RESOLVIDA"
        assert inc["Arquiteto (C11, J23, F30)"].decisao == "Decisão própria do professor"  # decisão do professor preservada
        v = db.get(Dupla, did).empresa.valores
        g = gerar_gabarito(v, "2026-02")
        assert g["totais"]["fecha"] and g["totais"]["diferenca"] == 0

"""Correções da análise completa do exercício (11/10/2026): itens 5 (sistema) e 6 (texto do exercício)."""
import io
import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

import app.main  # noqa: E402,F401
from app import ajuste_exercicio  # noqa: E402
from app.caso_servico import carregar_caso_base, fmt_unit  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.documentos import gerar_documentos  # noqa: E402
from app.fuso import AjusteSistema  # noqa: E402
from app.gabarito import gerar_gabarito  # noqa: E402
from app.geracao import gerar  # noqa: E402
from app.models import Disciplina, Turma  # noqa: E402
from app.models_caso import Caso  # noqa: E402
from app.models_dupla import Dupla, EmpresaGerada  # noqa: E402
from app.orientacao import gerar_docx, texto, W  # noqa: E402


@pytest.fixture(scope="module")
def vals():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        caso = carregar_caso_base(db, "Análise 11/10")
        base = gerar(caso, 0, "Caso-base", None, base=True)
        dupla = gerar(caso, 906, "Dupla 07", 7)
        db.rollback()
    return base, dupla


def _texto_orientacao(v, rotulo):
    from docx import Document
    dados, avisos = gerar_docx(v, rotulo)
    assert not avisos
    d = Document(io.BytesIO(dados))
    return "\n".join(texto(p) for p in d.element.body.iter(W + "p")), d


def test_caso_base_reproduz_totais_do_exercicio(vals):
    docs = {d["id"]: d for d in gerar_documentos(vals[0])}
    totais = {"J15-1": 355541.51, "J30-1": 1216710.63, "F05-1": 1494922.36, "F10-1": 3812043.57, "F22-1": 215888.18}
    for doc, total in totais.items():
        assert docs[doc]["produtos"] == total, doc
    assert [i["total"] for i in docs["F10-1"]["itens"]] == [1349353.96, 224602.84, 472319.15, 1765767.62]
    assert fmt_unit(19.6703463) == "19,6703463" and fmt_unit(10.5) == "10,5000"
    for mes in ("2026-01", "2026-02"):
        t = gerar_gabarito(vals[0], mes)["totais"]
        assert t["fecha"] and t["diferenca"] == 0


def test_documentos_corrigidos(vals):
    docs = {d["id"]: d for d in gerar_documentos(vals[0])}
    assert docs["J24-1"]["data"] == "2026-01-19"
    assert docs["J05-1"]["vencimento"] == "2026-01-14" and docs["J05-2"]["vencimento"] == "2026-02-09"
    assert docs["J27-1"]["duplicatas"][0][1] == "2026-01-28"
    assert docs["F26-1"]["duplicatas"][0][1] == "2026-02-27" and docs["F36-1"]["duplicatas"][0][1] == "2026-02-27"
    assert "20260001/00" in docs["J29-1"]["numero"]


def test_angela_com_salario_minimo(vals):
    angela = next(f for f in vals[0]["folha"] if f["nome"] == "Ângela Peruana")
    assert angela["salario_fev"] == 1621.0


def test_orientacao_telefonia_de_fevereiro_por_dupla(vals):
    txt, d = _texto_orientacao(vals[1], "Dupla 07")
    alvo = None
    for p in d.element.body.iter(W + "p"):
        if "telefonia e internet utilizados no mês de fevereiro" in texto(p):
            alvo = p
            break
    el = alvo
    while el.getparent() is not d.element.body:
        el = el.getparent()
    while el.tag != W + "tbl":
        el = el.getnext()
    linhas = {"".join(t.text or "" for t in tr.findall(W + "tc")[0].iter(W + "t")).strip():
              ["".join(t.text or "" for t in tc.iter(W + "t")) for tc in tr.findall(W + "tc")] for tr in el.iter(W + "tr")}
    docs = {x["id"]: x for x in gerar_documentos(vals[1])}
    from app.orientacao import brl
    assert linhas["Telefone Fixo"][2:] == ["13.02.2026", brl(docs["F03-1"]["total"])]
    assert linhas["Celular"][2:] == ["09.03.2026", brl(docs["F03-2"]["total"])]
    assert linhas["Internet"][3] == brl(docs["F03-3"]["total"])


def test_orientacao_textos_corrigidos(vals):
    txt, _ = _texto_orientacao(vals[0], "Caso-base")
    for trecho in ("realizada no dia 12/01/2026", "20260001/00", "pago pelo fornecedor (sem pagamento pela empresa)",
                   "emitido por Frete Confiança Ltda. em 04.02.2026", "a receber em 28.01.2026", "a receber em 27.02.2026",
                   "de 19.02.2026, a deduzir do valor do boleto a vencer em 27.02.2026", "Turma 01A – 06/11/2026, sex",
                   "Janeiro / 2026.", "Ângela"):
        assert trecho in txt, trecho
    for velho in ("11/01/2026", "20230001/00", "20220001/00", "24.02.2025", "15.02.2026", "15/11/2026", "2026.1", "1.530,00"):
        assert velho not in txt, velho
    ultimos = [l for l in txt.split("\n") if l.startswith("27.02.2026 ⇨")]
    assert any(l.startswith("27.02.2026 ⇨Resgate") for l in ultimos) and any(l.startswith("27.02.2026 ⇨Apuração") for l in ultimos)
    assert "1.621,00" in txt


def test_atualiza_casos_ja_cadastrados():
    with SessionLocal() as db:
        db.query(AjusteSistema).filter_by(chave=ajuste_exercicio.CHAVE_1110B).delete()
        caso = carregar_caso_base(db, "Caso antes da análise")
        for i in caso.itens:
            if i.codigo in ajuste_exercicio.CUSTOS_1110B:
                i.custo_base = ajuste_exercicio.CUSTOS_1110B[i.codigo][0]
        for p in caso.parametros:
            if p.escopo == "evento" and p.ref == "J15" and p.nome.startswith("Custo unit"):
                p.base = "19,6703"
            if p.ref == "C10" and p.nome.startswith("Valor"):
                p.base = "30000"
        next(f for f in caso.funcionarios if f.nome == "Ângela Peruana").salario_fev = 1530.0
        next(e for e in caso.eventos if e.codigo == "J27").descricao = "NF 001 Comercial Caribe - venda de ALPHA, boleto em 25/01"
        for x in list(caso.inconsistencias):
            if x.onde in ("Telefonia (J05, F03)", "Quadro de prazos"):
                caso.inconsistencias.remove(x)
            if x.onde.startswith("Vendas ALPHA"):
                x.status, x.decisao = "PENDENTE", None
        disc = Disciplina(codigo="EH7", nome="Teste"); db.add(disc); db.flush()
        t = Turma(disciplina_id=disc.id, codigo="97A", periodo="2026.2"); db.add(t); db.flush()
        d = Dupla(turma_id=t.id, numero=1); db.add(d); db.flush()
        d.empresa = EmpresaGerada(caso_id=caso.id, semente=5, valores=gerar(caso, 5, d.rotulo, d.numero))
        db.commit()
        cid, did = caso.id, d.id

        assert ajuste_exercicio.aplicar_1110b(db) >= 1
        assert ajuste_exercicio.aplicar_1110b(db) == 0
        db.expire_all()
        caso = db.get(Caso, cid)
        assert next(i for i in caso.itens if i.codigo == "ALPHA").custo_base == 19.6703463
        par = {(p.ref, p.nome): p.base for p in caso.parametros}
        assert par[("J15", "Custo unitário")] == "19,6703463" and par[("C10", "Valor do mútuo")] == "30.000,00"
        assert next(f for f in caso.funcionarios if f.nome == "Ângela Peruana").salario_fev == 1621.0
        assert next(e for e in caso.eventos if e.codigo == "J27").descricao.endswith("boleto em 28/01")
        inc = {x.onde: x for x in caso.inconsistencias}
        assert {"Telefonia (J05, F03)", "Quadro de prazos"} <= set(inc)
        assert inc["Vendas ALPHA (J27, J33, F26, F36, F44)"].status == "RESOLVIDA"
        g = gerar_gabarito(db.get(Dupla, did).empresa.valores, "2026-02")
        assert g["totais"]["fecha"] and g["totais"]["diferenca"] == 0

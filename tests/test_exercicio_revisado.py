"""Exercício revisado pelo professor (PDF de 07/10/2026): caso-base, gabarito, orientação e atualização dos casos existentes."""
import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app import ajuste_exercicio  # noqa: E402
from app import plano_contas as pc  # noqa: E402
from app.caso_servico import carregar_caso_base  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.fuso import AjusteSistema  # noqa: E402
from app.gabarito import gerar_gabarito  # noqa: E402
from app.geracao import gerar  # noqa: E402
from app.models_caso import Inconsistencia  # noqa: E402
from app.models_dupla import Dupla, EmpresaGerada  # noqa: E402
from app.models import Disciplina, Turma  # noqa: E402


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


def test_balanco_de_abertura_fecha_sem_centavo(base):
    for mes in ("2026-01", "2026-02"):
        t = gerar_gabarito(base, mes)["totais"]
        assert t["fecha"] and t["diferenca"] == 0, (mes, t["diferenca"])


def test_dividendos_50_por_cento(base):
    m = _memo(gerar_gabarito(base), "J01")
    # quadro de destinação do exercício: 41.481,77 e 41.481,78 (a metade de 82.963,55 tem meio centavo)
    assert m["Dividendos (50,00%)"] + m["Reserva estatutária (saldo)"] == pytest.approx(82963.55, abs=0.001)
    assert abs(m["Dividendos (50,00%)"] - 41481.775) < 0.006


def test_seguro_agua_e_renato(base):
    gj, g = gerar_gabarito(base), gerar_gabarito(base, "2026-02")
    hist = {l["evento"]: l["historico"] for l in gj["lancamentos"]}
    assert "3ª e última" in hist["J21"]
    j03 = _memo(gj, "J03")
    assert (j03["Área administrativa"], j03["Área comercial"]) == (210, 380)
    f02 = _memo(g, "F02")
    assert (f02["Produto X"], f02["Produto Y"]) == (610, 570)
    assert _memo(g, "F01")["Área administrativa"] == 530
    renato = next(f for f in base["folha"] if f["nome"] == "Renato Português")
    assert renato["salario_fev"] == 2120 and not renato["pendente"]
    assert not any("não informado" in m["descricao"] for m in g["memoria"].get("F20", []))


def test_orientacao_com_tabelas_completas(base):
    import io, re
    from docx import Document
    from app.orientacao import gerar_docx
    dados, _ = gerar_docx(base, "Caso-base")
    texto = "\n".join(" | ".join(c.text for c in r.cells) for t in Document(io.BytesIO(dados)).tables for r in t.rows)
    assert re.search(r"Área Comercial \| 16,088 \| 23,62 \| 380,00", texto)
    assert "Área Administrativa | 370,215 kWh | 1,432 / kWh | R$ 530,00" in texto
    assert "Área Industrial - Produto Y | 24,1321 m³ | 23,62 / m³ | R$ 570,00" in texto
    assert "Renato Português | Empregado | 8 anos e 10 anos | 2.120,00" in texto
    assert "43.361,80 C" in texto and "821.591,66 D" in texto


def test_atualiza_casos_ja_cadastrados(base):
    with SessionLocal() as db:
        db.query(AjusteSistema).filter_by(chave=ajuste_exercicio.CHAVE).delete()
        caso = carregar_caso_base(db, "Caso antigo")
        # volta o caso para a versão de 04/09
        for p in caso.parametros:
            if p.nome.startswith("Dividendos"):
                p.base, p.maximo = "60", 60.0
            if p.ref == "C09" and p.nome.startswith("Número de parcelas"):
                p.base, p.minimo, p.maximo, p.passo, p.varia = "4", 3.0, 4.0, 1.0, True
        next(e for e in caso.eventos if e.codigo == "J21").descricao = "Pagamento da 4ª parcela do seguro (Seguro Verdade)"
        next(f for f in caso.funcionarios if f.nome == "Renato Português").salario_fev = None
        dados = dict(caso.dados)
        si = dict(dados["saldos_iniciais"]); si["passivo"] = {**si["passivo"], "ICMS a recolher": 43361.81}
        dados["saldos_iniciais"] = si; caso.dados = dados
        for x in list(caso.inconsistencias):
            if x.onde.startswith("Balanço de 31/12"):
                caso.inconsistencias.remove(x)
            if x.onde == "Imobilizado":
                x.status, x.decisao = "PENDENTE", None
        disc = Disciplina(codigo="EH9", nome="Teste"); db.add(disc); db.flush()
        t = Turma(disciplina_id=disc.id, codigo="99A", periodo="2026.2"); db.add(t); db.flush()
        d = Dupla(turma_id=t.id, numero=1); db.add(d); db.flush()
        db.flush()
        d.empresa = EmpresaGerada(caso_id=caso.id, semente=7, valores=gerar(caso, 7, d.rotulo, d.numero))
        db.commit()
        antes = next(f for f in d.empresa.valores["folha"] if f["nome"] == "Renato Português")
        assert antes["pendente"]
        cid, did = caso.id, d.id

        assert ajuste_exercicio.aplicar(db) >= 1
        assert ajuste_exercicio.aplicar(db) == 0  # só uma vez
        db.expire_all()
        from app.models_caso import Caso
        caso = db.get(Caso, cid)
        div = next(p for p in caso.parametros if p.nome.startswith("Dividendos"))
        assert (div.base, div.maximo) == ("50", 50.0)
        assert "3ª e última" in next(e for e in caso.eventos if e.codigo == "J21").descricao
        assert caso.dados["saldos_iniciais"]["passivo"]["ICMS a recolher"] == 43361.80
        assert next(x for x in caso.inconsistencias if x.onde == "Imobilizado").status == "RESOLVIDA"
        assert any(x.onde.startswith("Balanço de 31/12") for x in caso.inconsistencias)
        v = db.get(Dupla, did).empresa.valores
        renato = next(f for f in v["folha"] if f["nome"] == "Renato Português")
        assert renato["salario_fev"] and not renato["pendente"]
        assert gerar_gabarito(v)["totais"]["diferenca"] == 0

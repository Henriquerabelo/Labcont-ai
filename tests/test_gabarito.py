"""Gabarito de janeiro: partidas dobradas, valores-chave do caso-base e telas."""
import io
import os
import re

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.gabarito import gerar_gabarito, inss_empregado, irrf  # noqa: E402
from app.geracao import gerar  # noqa: E402
from app.main import app  # noqa: E402
from app.models_caso import Caso  # noqa: E402


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def _caso_id(client):
    r = client.get("/casos")
    return int(re.search(r'href="/casos/(\d+)/empresa"', r.text).group(1))


def _memo(g, ev, trecho):
    return next(m["valor"] for m in g["memoria"][ev] if trecho in m["descricao"])


def test_tabelas_2026():
    assert inss_empregado(1621.00) == 121.58
    assert inss_empregado(8475.55) == pytest.approx(988.09, abs=0.01)
    assert irrf(4500, inss_empregado(4500), 0)[0] == 0  # isento pela Lei 15.270/2025 (até R$ 5.000)
    assert irrf(10600, 932.31, 0)[0] == 1749.88


def test_gabarito_caso_base(client):
    cid = _caso_id(client)
    with SessionLocal() as db:
        g = gerar_gabarito(gerar(db.get(Caso, cid), 0, "base", None, base=True))
    assert g["totais"]["fecha"]
    for l in g["lancamentos"]:
        assert round(sum(p["valor"] for p in l["debitos"]), 2) == round(sum(p["valor"] for p in l["creditos"]), 2)
    assert _memo(g, "J39", "CSRF") == 255.75  # confere com o saldo de dezembro (5.500 → 5.161,75)
    assert _memo(g, "J16", "IRRF") == 1470.00
    assert _memo(g, "J29", "Total a pagar") == 15435.00
    assert _memo(g, "J15", "valor líquido") == 337764.43  # NF 3.369: 355.541,51 − 5% (valor exato do exercício)
    bal = {x["conta"]: x["final"] for x in g["balancete"]}
    assert bal["2.07.07.01.01.0001-7"] == 0  # lucro de 2025 destinado
    assert all(k in g["premissas"] for k in ("P01", "P15", "P22"))


def test_gabarito_por_dupla_fecha_em_varias_sementes(client):
    cid = _caso_id(client)
    with SessionLocal() as db:
        caso = db.get(Caso, cid)
        for s in range(1, 16):
            g = gerar_gabarito(gerar(caso, s * 7919, "D", 1))
            assert g["totais"]["fecha"], s


def test_telas_e_planilha(client):
    cid = _caso_id(client)
    r = client.get(f"/casos/{cid}/gabarito")
    assert r.status_code == 200 and "Balancete de verificação" in r.text and "P15" in r.text
    x = client.get(f"/casos/{cid}/gabarito.xlsx")
    assert x.status_code == 200 and x.content[:2] == b"PK"
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(x.content))
    assert wb.sheetnames == ["Diário", "Balancete", "Memória de cálculo", "Premissas"]


def test_validacao_das_premissas_no_site(client):
    cid = _caso_id(client)
    r = client.post(f"/casos/{cid}/gabarito/premissas", data={"st_P03": "VALIDADA", "com_P03": "",
                                                             "st_P06": "AJUSTAR", "com_P06": "usar preço cheio"},
                    follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        val = db.get(Caso, cid).dados["premissas_validacao"]
        assert val["P03"]["status"] == "VALIDADA" and val["P06"]["comentario"] == "usar preço cheio"
    pagina = client.get(f"/casos/{cid}/gabarito").text
    assert "usar preço cheio" in pagina and "a validar" in pagina

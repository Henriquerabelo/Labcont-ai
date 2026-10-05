"""Testes da Etapa 1. Os PDFs reais do SIGAA não vão para o GitHub (LGPD);
informe a pasta com eles em SIGAA_PDFS para rodar os testes de importação."""
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.importers.sigaa import ler_pdf  # noqa: E402
from app.main import app  # noqa: E402

PASTA = Path(os.getenv("SIGAA_PDFS", "dados_sigaa"))
TURMAS = PASTA / "Turmas 2026.2.pdf"
PART_12 = PASTA / "Participantes - EH0012 - Lab Prática Contábil.pdf"
PART_333 = PASTA / "Participantes - EH0333 - Perícia Contábil.pdf"
tem_pdfs = pytest.mark.skipif(not TURMAS.exists(), reason="PDFs do SIGAA não disponíveis")


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def _importar(client, caminho: Path) -> int:
    with open(caminho, "rb") as f:
        r = client.post("/importacao", files={"arquivo": (caminho.name, f, "application/pdf")}, follow_redirects=False)
    assert r.status_code == 303, r.text
    imp_id = int(re.search(r"/importacao/(\d+)", r.headers["location"]).group(1))
    assert client.get(f"/importacao/{imp_id}").status_code == 200
    r = client.post(f"/importacao/{imp_id}/confirmar", follow_redirects=False)
    assert r.status_code == 303 and "erro" not in r.headers["location"]
    return imp_id


@tem_pdfs
def test_parser_turmas():
    r = ler_pdf(str(TURMAS))
    assert r.tipo == "turmas" and len(r.turmas) == 69 and not r.avisos
    lab = [t for t in r.turmas if t.disciplina_codigo == "EH0012"]
    assert [t.codigo for t in lab] == ["01A", "02A", "03A"]
    assert all(t.data_inicio == "2026-08-10" for t in r.turmas if t.horario)
    etica = next(t for t in r.turmas if t.disciplina_codigo == "EH0026" and t.codigo == "01A")
    assert [d.nome for d in etica.docentes] == ["CINTIA DE ALMEIDA", "TATIANA AQUINO ALMEIDA"]


@tem_pdfs
def test_parser_participantes():
    r = ler_pdf(str(PART_333))
    t = r.turmas[0]
    assert (t.disciplina_codigo, t.codigo, t.periodo) == ("EH0333", "01A", "2026.2")
    assert len(t.discentes) == 50 and not r.avisos
    assert len({d.matricula for d in t.discentes}) == 50
    r12 = ler_pdf(str(PART_12)).turmas[0]
    assert len(r12.discentes) == 29
    assert sum(d.situacao == "TRANCADO" for d in r12.discentes) == 2
    assert r12.docentes[0].email == "danival@ufc.br"


@tem_pdfs
def test_importacao_completa_e_idempotente(client):
    for p in (TURMAS, PART_12, PART_333):
        _importar(client, p)
    _importar(client, PART_333)  # repetir não duplica
    from sqlalchemy import func, select
    from app.db import SessionLocal
    from app.models import Discente, Docente, Matricula, Turma
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Turma.id))) == 70  # 69 + EH0012/03A em 2026.1
        n_disc = db.scalar(select(func.count(Discente.id)))
        assert n_disc == len({*[d.matricula for d in ler_pdf(str(PART_12)).turmas[0].discentes],
                              *[d.matricula for d in ler_pdf(str(PART_333)).turmas[0].discentes]})
        assert db.scalar(select(func.count(Matricula.id))) == 79
        naiara = db.scalar(select(Docente).where(Docente.nome.like("NAIARA%")))
        assert naiara.email == "naisantana13@gmail.com" and len(naiara.turmas) == 2


def test_crud_manual(client):
    r = client.post("/disciplinas/nova", data={"codigo": "zz9999", "nome": "Disciplina teste"}, follow_redirects=False)
    assert r.status_code == 303
    did = int(r.headers["location"].split("/")[2].split("?")[0])
    assert "ZZ9999" in client.get(f"/disciplinas/{did}").text
    r = client.post("/disciplinas/nova", data={"codigo": "ZZ9999", "nome": "Duplicada"})
    assert "Já existe" in r.text
    r = client.post("/turmas/nova", data={"disciplina_id": did, "periodo": "2026.2", "codigo": "01a"}, follow_redirects=False)
    tid = int(r.headers["location"].split("/")[2].split("?")[0])
    r = client.post("/docentes/novo", data={"nome": "Professora Teste", "ativo": "on"}, follow_redirects=False)
    doc_id = int(r.headers["location"].split("/")[2].split("?")[0])
    client.post(f"/turmas/{tid}/docentes", data={"docente_id": doc_id, "carga_horaria": "64"})
    r = client.post(f"/turmas/{tid}/discentes", data={"matricula": "999001"}, follow_redirects=False)
    assert "erro" in r.headers["location"]  # matrícula nova sem nome
    client.post(f"/turmas/{tid}/discentes", data={"matricula": "999001", "nome": "Aluno Teste", "turno": "NOTURNO"})
    pagina = client.get(f"/turmas/{tid}").text
    assert "ALUNO TESTE" in pagina and "PROFESSORA TESTE" in pagina
    r = client.post("/discentes/novo", data={"matricula": "12a", "nome": "x"})
    assert "apenas números" in r.text
    client.post(f"/disciplinas/{did}/excluir")
    assert client.get(f"/disciplinas/{did}", follow_redirects=False).status_code == 303
    for url in ("/", "/disciplinas", "/docentes", "/discentes", "/importacao", "/disciplinas/nova", "/turmas/nova", "/docentes/novo", "/discentes/novo"):
        assert client.get(url).status_code == 200, url

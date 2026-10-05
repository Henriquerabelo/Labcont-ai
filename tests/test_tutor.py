"""Etapa 6: tutor (IA local com roteiro de reserva) e painel da turma."""
import json
import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app import plano_contas as pc  # noqa: E402
from app import tutor as tutor_ia  # noqa: E402
from app.caso_servico import carregar_caso_base  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.gabarito import gerar_gabarito  # noqa: E402
from app.models import Disciplina, Discente, Matricula, Turma  # noqa: E402
from app.models_dupla import Dupla  # noqa: E402
from app.models_escrita import DuplaAcesso, TutorMensagem  # noqa: E402


@pytest.fixture(scope="module")
def ctx():
    for v in ("TUTOR_LLM_URL", "TUTOR_LLM_MODEL", "TUTOR_LLM_KEY"):
        os.environ.pop(v, None)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        t = Turma(disciplina=Disciplina(codigo="EH0012", nome="LAB"), periodo="2026.2", codigo="01")
        db.add(t)
        ids = []
        for i in range(4):
            a = Discente(matricula=f"54000{i}", nome=f"ALUNO {i}")
            db.add(Matricula(turma=t, discente=a, situacao="ATIVO"))
            db.flush()
            ids.append(a.id)
        caso = carregar_caso_base(db)
        db.commit()
        tid, cid = t.id, caso.id
    with TestClient(app=main.app) as c:
        c.post(f"/turmas/{tid}/duplas", data={"discente_id": [str(ids[0]), str(ids[1])]})
        c.post(f"/turmas/{tid}/duplas", data={"discente_id": [str(ids[2]), str(ids[3])]})
        c.post(f"/turmas/{tid}/duplas/gerar", data={"caso_id": str(cid), "modo": "faltantes"})
        c.post(f"/turmas/{tid}/duplas/codigos")
        with SessionLocal() as db:
            d1, d2 = db.query(Dupla).filter_by(turma_id=tid).order_by(Dupla.numero).all()
            cod1 = db.query(DuplaAcesso).filter_by(dupla_id=d1.id).one().codigo
            cod2 = db.query(DuplaAcesso).filter_by(dupla_id=d2.id).one().codigo
            g1 = gerar_gabarito(d1.empresa.valores)
        yield {"c": c, "tid": tid, "d1": d1.id, "d2": d2.id, "cod1": cod1, "cod2": cod2, "g1": g1}


def _entrar(c, codigo, mat):
    """Primeiro acesso (cria a senha com o código do grupo) ou, se já existir, entrada com matrícula + senha."""
    c.cookies.clear()
    r = c.post("/aluno/primeiro-acesso", data={"codigo": codigo, "ciente": "1", "matricula_pa": mat, "nova": "senha-teste-1",
                                                "nova2": "senha-teste-1"}, follow_redirects=False)
    if r.status_code != 303:
        r = c.post("/aluno/entrar", data={"matricula": mat, "senha": "senha-teste-1"}, follow_redirects=False)
    return r


def _msgs(dupla_id):
    with SessionLocal() as db:
        return db.query(TutorMensagem).filter_by(dupla_id=dupla_id).order_by(TutorMensagem.id).all()


def test_sem_ia_responde_com_roteiro(ctx):
    c = ctx["c"]
    _entrar(c, ctx["cod1"], "540000")
    assert "Sobre qual evento?" in c.get("/aluno/tutor?evento=J06").text
    r = c.post("/aluno/tutor", data={"evento": "J06", "pergunta": "Quais tributos recupero nesta nota?"}, follow_redirects=False)
    assert r.status_code == 303 and "J06" in r.headers["location"]
    m = _msgs(ctx["d1"])
    assert [x.papel for x in m] == ["aluno", "tutor"] and m[1].origem == "roteiro" and m[0].matricula == "540000"
    pagina = c.get("/aluno/tutor?evento=J06").text
    assert "Quais tributos recupero" in pagina and "Tutor · roteiro" in pagina
    # pergunta vazia é recusada
    assert "erro=" in c.post("/aluno/tutor", data={"evento": "J06", "pergunta": "  "}, follow_redirects=False).headers["location"]


def test_contexto_nao_leva_gabarito(ctx, monkeypatch):
    """O que vai para a IA: documentos e lançamentos da dupla, nunca as partidas do gabarito."""
    capturado = {}

    async def falsa(mensagens, timeout=90.0):
        capturado["m"] = mensagens
        return "Pense no que a nota fiscal destaca. Qual imposto é recuperável?"
    monkeypatch.setattr(tutor_ia, "chamar_ia", falsa)
    c, g = ctx["c"], ctx["g1"]
    _entrar(c, ctx["cod1"], "540001")
    c.post("/aluno/tutor", data={"evento": "J06", "pergunta": "Como lanço?"})
    sistema = capturado["m"][0]["content"]
    assert "J06" in sistema and "só acontece" in sistema  # regra de antes do fechamento
    assert capturado["m"][-1]["content"].startswith("Como lanço?") and "Lembrete ao tutor" in capturado["m"][-1]["content"]
    assert any(x["role"] == "assistant" for x in capturado["m"])  # histórico anterior do evento
    gab_txt = json.dumps([l for l in g["lancamentos"] if l["evento"] == "J06"], ensure_ascii=False)
    assert "Livro" not in sistema and "debitos" not in sistema
    # nenhum código de conta do gabarito deste evento aparece no contexto (a dupla ainda não lançou)
    contas = {p["conta"] for l in g["lancamentos"] if l["evento"] == "J06" for p in l["debitos"] + l["creditos"]}
    assert contas and not any(ct in sistema for ct in contas), gab_txt[:200]
    assert _msgs(ctx["d1"])[-1].origem == "ia"


def test_depois_do_fechamento_tutor_comenta_a_correcao(ctx, monkeypatch):
    capturado = {}

    async def falsa(mensagens, timeout=90.0):
        capturado["m"] = mensagens
        return "Veja a correção. O que mudaria?"
    monkeypatch.setattr(tutor_ia, "chamar_ia", falsa)
    c = ctx["c"]
    _entrar(c, ctx["cod1"], "540000")
    v = "100,00"
    c.post("/aluno/lancar", data={"evento": "J10", "data": "2026-01-10", "historico": "x",
                                  "conta": [pc.F_INTERNET, pc.BANCO], "natureza": ["D", "C"], "valor": [v, v]})
    assert c.post("/aluno/fechamento", data={"confirmo": "1"}, follow_redirects=False).status_code == 303
    c.post("/aluno/tutor", data={"evento": "J10", "pergunta": "Por que errei?"})
    sistema = capturado["m"][0]["content"]
    assert "Correção do fechamento para este evento" in sistema and "já foi enviado" in sistema
    # o tutor continua disponível após o envio, mas a escrituração segue bloqueada
    assert c.get("/aluno/tutor?evento=J10").status_code == 200


def test_limite_diario(ctx, monkeypatch):
    monkeypatch.setattr(tutor_ia, "LIMITE_DIARIO", 1)
    c = ctx["c"]
    _entrar(c, ctx["cod2"], "540002")
    assert "erro=" not in c.post("/aluno/tutor", data={"pergunta": "O que é mark-up?"}, follow_redirects=False).headers["location"]
    r = c.post("/aluno/tutor", data={"pergunta": "E o ICMS?"}, follow_redirects=False)
    assert "Limite" in r.headers["location"] or "limite" in r.headers["location"].lower() or "erro=" in r.headers["location"]
    assert len([m for m in _msgs(ctx["d2"]) if m.papel == "aluno"]) == 1


def test_isolamento_conversas(ctx):
    c = ctx["c"]
    _entrar(c, ctx["cod2"], "540003")
    assert "Quais tributos recupero" not in c.get("/aluno/tutor?evento=J06").text


def test_painel_professor(ctx, monkeypatch):
    c = ctx["c"]
    c.cookies.clear()
    r = c.get(f"/turmas/{ctx['tid']}/painel")
    assert r.status_code == 200
    t = r.text
    assert "Painel da turma" in t and "modo roteiro" in t and "TUTOR_LLM_URL" in t
    assert "Matriz de calor" in t and "J10" in t and "Quais tributos recupero" in t and "Alertas precoces" in t
    r = c.get(f"/duplas/{ctx['d1']}/tutor")
    assert r.status_code == 200 and "Por que errei?" in r.text and "Tutor · IA" in r.text and "540000" in r.text
    assert f"/turmas/{ctx['tid']}/painel" in c.get(f"/turmas/{ctx['tid']}/duplas").text
    # aluno logado não entra nas telas do professor
    _entrar(c, ctx["cod1"], "540000")
    assert c.get(f"/turmas/{ctx['tid']}/painel", follow_redirects=False).headers["location"] == "/aluno"
    assert c.get(f"/duplas/{ctx['d1']}/tutor", follow_redirects=False).headers["location"] == "/aluno"
    c.cookies.clear()


def test_status_ia_nao_expoe_chave(monkeypatch):
    import asyncio
    monkeypatch.setenv("TUTOR_LLM_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("TUTOR_LLM_MODEL", "x")
    monkeypatch.setenv("TUTOR_LLM_KEY", "segredo-123")
    st = asyncio.run(tutor_ia.status_ia())
    assert not st["ok"] and "segredo-123" not in json.dumps(st) and st["chave_definida"]


def test_filtro_bloqueia_valor_da_dupla(ctx, monkeypatch):
    """Caso real (05/10): a IA repetiu o valor digitado pela dupla como se fosse a resposta."""
    chamadas = []

    async def teimosa(mensagens, timeout=90.0):
        chamadas.append(mensagens)
        return "O valor a ser destinado é o saldo de Lucros Acumulados de R$ 94.920,00."
    monkeypatch.setattr(tutor_ia, "chamar_ia", teimosa)
    c = ctx["c"]
    _entrar(c, ctx["cod2"], "540002")
    c.post("/aluno/lancar", data={"evento": "J01", "data": "2026-01-02", "historico": "x",
                                  "conta": [pc.BANCO, pc.CAPITAL["Marcela Soares"][1]], "natureza": ["D", "C"],
                                  "valor": ["94.920,00", "94.920,00"]})
    monkeypatch.setattr(tutor_ia, "LIMITE_DIARIO", 99)
    c.post("/aluno/tutor", data={"evento": "J01", "pergunta": "Qual o valor a ser destinado do exercício 2025?"})
    assert len(chamadas) == 2  # tentou de novo explicando a regra
    assert "94.920" not in chamadas[0][0]["content"]  # valor da dupla não vai no contexto antes do fechamento
    assert "Lembrete ao tutor" in chamadas[0][-1]["content"]
    m = _msgs(ctx["d2"])[-1]
    assert m.origem == "filtro" and "94.920" not in m.texto and "lucro líquido de 2025" in m.texto


def test_violacoes():
    v = tutor_ia.violacoes
    assert v("Pela Lei 6.404/76 a reserva é 5%: num lucro de R$ 1.000,00 seriam 50,00. Qual é o seu lucro?", "", False) == []
    assert v("ICMS destacado de 1.234,56 no CFOP 6.102.", "ICMS destacado: 1.234,56; cfop: 6.102", False) == []
    assert v("Seu lançamento está correto.", "", False) and not v("Seu lançamento está correto.", "", True)
    assert v("O total é 3.210,77.", "", True)


def test_base_normativa_no_tutor(ctx, monkeypatch):
    capturado = {}

    async def falsa(mensagens, timeout=90.0):
        capturado["m"] = mensagens
        return "Veja o que a lei diz sobre a reserva legal. Qual é a base de cálculo?"
    monkeypatch.setattr(tutor_ia, "chamar_ia", falsa)
    monkeypatch.setattr(tutor_ia, "LIMITE_DIARIO", 99)
    c = ctx["c"]
    _entrar(c, ctx["cod2"], "540002")
    c.post("/aluno/tutor", data={"evento": "J01", "pergunta": "Como calculo a reserva legal?"})
    sistema = capturado["m"][0]["content"]
    assert "Base normativa" in sistema and "Lei 6.404/76, art. 193" in sistema
    m = _msgs(ctx["d2"])[-1]
    assert m.origem == "ia" and "Para consultar: Lei 6.404/76, art. 193" in m.texto
    # consulta da dupla
    t = c.get("/aluno/normas?q=reserva+legal").text
    assert "Reserva legal" in t and "art. 193" in t


def test_base_normativa_professor(ctx):
    from app.normas import Norma
    c = ctx["c"]
    c.cookies.clear()
    t = c.get("/normas").text
    assert "Base normativa" in t and "ICMS-02" in t
    t = c.get("/normas?q=frete+entra+no+custo&evento=J09").text
    assert "que o tutor receberia" in t and "EST-04" in t
    r = c.post("/normas/nova", data={"codigo": "teste-01", "titulo": "Ficha de teste", "fonte": "Lei X, art. 1",
                                     "texto": "Texto sobre zebra contábil.", "palavras": "zebra", "eventos": "j02 j03", "ativa": "on"},
               follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        n = db.query(Norma).filter_by(codigo="TESTE-01").one()
        assert n.eventos == "J02,J03" and n.origem == "professor"
        padrao = db.query(Norma).filter_by(codigo="PL-03").one()
    assert "zebra" in c.get("/normas?q=zebra").text.lower()
    c.post(f"/normas/{n.id}/ativa")
    assert "Nenhuma ficha relevante" in c.get("/normas?q=zebra").text
    # editar ficha padrão marca como editada e não é sobrescrita na próxima subida
    c.post(f"/normas/{padrao.id}/editar", data={"codigo": "PL-03", "titulo": "Reserva legal (editada)", "fonte": padrao.fonte,
                                               "texto": padrao.texto, "palavras": padrao.palavras, "eventos": "J01", "ativa": "on"})
    from app.normas import semear
    with SessionLocal() as db:
        assert semear(db) == 0
        p = db.query(Norma).filter_by(codigo="PL-03").one()
        assert p.origem == "editada" and p.titulo.endswith("(editada)")
    assert "Preencha" in c.post("/normas/nova", data={"codigo": "", "titulo": "", "fonte": "", "texto": ""}).text

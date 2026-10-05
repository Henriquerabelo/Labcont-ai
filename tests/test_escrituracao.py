"""Etapa 5: acesso da dupla, escrituração e auditoria em 3 níveis."""
import os
import re

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app import plano_contas as pc  # noqa: E402
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
        for i in range(4):
            a = Discente(matricula=f"53000{i}", nome=f"ALUNO {i}")
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


def _partidas_do_gabarito(g, ev):
    rows = []
    for l in g["lancamentos"]:
        if l["evento"] == ev:
            rows += [(f"{p['conta']} {p['nome']}", "D", f"{p['valor']:.2f}") for p in l["debitos"]]
            rows += [(f"{p['conta']} {p['nome']}", "C", f"{p['valor']:.2f}") for p in l["creditos"]]
    return rows


def _lancar(c, ev, rows, data="2026-01-15"):
    return c.post("/aluno/lancar", data={"evento": ev, "data": data, "historico": f"Teste {ev}",
                                         "conta": [r[0] for r in rows], "natureza": [r[1] for r in rows],
                                         "valor": [r[2] for r in rows]}, follow_redirects=False)


def test_acesso(ctx):
    c = ctx["c"]
    c.cookies.clear()
    assert "Código do grupo" in c.get("/aluno").text
    assert "não conferem" in _entrar(c, ctx["cod1"], "530003").text  # matrícula de outra dupla
    r = _entrar(c, ctx["cod1"].lower(), "530000")
    assert r.status_code == 303 and "labcont_sessao" in r.headers.get("set-cookie", "")
    # segunda vez: o primeiro acesso é recusado e a entrada é por matrícula + senha
    c.cookies.clear()
    assert "já tem senha" in c.post("/aluno/primeiro-acesso", data={"codigo": ctx["cod1"], "ciente": "1", "matricula_pa": "530000",
                                                                     "nova": "outra-senha-1", "nova2": "outra-senha-1"}).text
    assert "não conferem" in c.post("/aluno/entrar", data={"matricula": "530000", "senha": "errada-123"}).text
    assert c.post("/aluno/entrar", data={"matricula": "530000", "senha": "senha-teste-1"}, follow_redirects=False).status_code == 303
    assert "Fechamento de janeiro" in c.get("/aluno").text


def test_auditoria_tres_niveis(ctx):
    c, g = ctx["c"], ctx["g1"]
    _entrar(c, ctx["cod1"], "530000")
    # correto: copia o gabarito do J15 (três lançamentos) em um único lançamento composto
    assert _lancar(c, "J15", _partidas_do_gabarito(g, "J15")).status_code == 303
    # valor divergente: J06 com valor errado nas duas pontas
    rows = [(r[0], r[1], f"{float(r[2]) + 10:.2f}" if r[1] == "C" else r[2]) for r in _partidas_do_gabarito(g, "J06")]
    rows = [(r[0], r[1], r[2]) for r in rows]
    tot = sum(float(r[2]) for r in rows if r[1] == "C")
    rows = [(r[0], r[1], f"{tot / 2:.2f}") if r[1] == "D" else r for r in rows]
    assert _lancar(c, "J06", rows).status_code == 303
    # conta errada: J10 pago com a conta de fornecedor errada
    v = _partidas_do_gabarito(g, "J10")[0][2]
    _lancar(c, "J10", [(pc.F_INTERNET, "D", v), (pc.BANCO, "C", v)])
    # lançamento desbalanceado é recusado
    r = _lancar(c, "J12", [(pc.ISS_RECOL, "D", "100,00"), (pc.BANCO, "C", "90,00")])
    assert r.status_code == 200 and "diferentes dos créditos" in r.text

    def nivel(painel, ev):
        return re.search(rf'id="ev-{ev}".*?class="nivel nivel-(\w+)"', painel, re.S).group(1)
    # antes do fechamento: só "lançado" / "pendente", sem correção
    painel = c.get("/aluno").text
    assert nivel(painel, "J15") == "lancado" and nivel(painel, "J06") == "lancado" and nivel(painel, "J20") == "pendente"
    assert "Valor divergente" not in painel.split("Fechamento de janeiro")[1]
    # envio sem confirmar pendências é recusado
    r = c.post("/aluno/fechamento", data={}, follow_redirects=False)
    assert "erro=" in r.headers["location"]
    assert c.post("/aluno/fechamento", data={"confirmo": "1"}, follow_redirects=False).status_code == 303
    painel = c.get("/aluno").text
    assert nivel(painel, "J15") == "correto" and nivel(painel, "J06") == "valor" and nivel(painel, "J10") == "conta"
    # escrituração bloqueada após o envio
    r = _lancar(c, "J20", [(pc.BANCO, "D", "1,00"), (pc.CAPITAL["Marcela Soares"][1], "C", "1,00")])
    assert "bloqueada" in r.headers.get("location", "") or "bloqueada" in r.text


def test_isolamento_entre_duplas(ctx):
    c = ctx["c"]
    _entrar(c, ctx["cod2"], "530002")
    assert "Teste J15" not in c.get("/aluno/diario").text
    with SessionLocal() as db:
        from app.models_escrita import Lancamento
        lid = db.query(Lancamento).filter_by(dupla_id=ctx["d1"]).first().id
    assert c.post(f"/aluno/lancamentos/{lid}/excluir", follow_redirects=False).status_code == 303
    with SessionLocal() as db:
        from app.models_escrita import Lancamento
        assert db.get(Lancamento, lid) is not None  # a outra dupla não consegue excluir


def test_area_do_aluno_fora_da_senha_e_professor_protegido(ctx):
    from app import acesso
    c = ctx["c"]
    with SessionLocal() as db:  # com um usuário de equipe cadastrado, o modo aberto termina
        u = acesso.Usuario(login="adm@teste", nome="Adm", senha_hash=acesso.gerar_hash("senha-adm-1"))
        u.perfis.append(acesso.UsuarioPerfil(perfil="admin"))
        db.add(u)
        db.commit()
        uid = u.id
    try:
        c.cookies.clear()
        assert c.get("/aluno").status_code == 200
        for url in (f"/duplas/{ctx['d1']}/gabarito", f"/duplas/{ctx['d1']}/escrituracao"):
            r = c.get(url, follow_redirects=False)
            assert r.status_code == 303 and r.headers["location"].startswith("/entrar")
        _entrar(c, ctx["cod1"], "530000")  # aluno logado também não entra nas telas do professor
        assert c.get(f"/duplas/{ctx['d1']}/gabarito", follow_redirects=False).headers["location"] == "/aluno"
    finally:
        with SessionLocal() as db:
            db.delete(db.get(acesso.Usuario, uid))
            db.commit()
        c.cookies.clear()


def test_telas_professor_e_livros(ctx):
    c = ctx["c"]
    c.cookies.clear()
    r = c.get(f"/duplas/{ctx['d1']}/escrituracao")
    assert r.status_code == 200 and "Mensagem exibida à dupla" in r.text and "Janeiro enviado" in r.text
    # professor reabre: a dupla volta a lançar e não vê mais a correção
    c.post(f"/duplas/{ctx['d1']}/fechamento/reabrir")
    _entrar(c, ctx["cod1"], "530000")
    assert "Fechamento de janeiro" in c.get("/aluno").text
    assert _lancar(c, "J20", [(pc.BANCO, "D", "25.000,00"), (pc.CAPITAL["Marcela Soares"][1], "C", "25.000,00")]).status_code == 303
    c.cookies.clear()
    assert "Acesso dos grupos" in c.get(f"/turmas/{ctx['tid']}/duplas").text
    _entrar(c, ctx["cod1"], "530001")
    for url in ("/aluno/diario", "/aluno/balancete", "/aluno/razao", "/aluno/documentos", "/aluno/documentos/J15-1", "/aluno/lancar?evento=J02"):
        assert c.get(url).status_code == 200, url

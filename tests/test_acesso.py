"""Etapa 7: login com perfis, regras de acesso, turma encerrada/demonstração, histórico e lote."""
import os
import re

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont_test")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app import acesso  # noqa: E402
from app import plano_contas as pc  # noqa: E402
from app.caso_servico import carregar_caso_base  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Disciplina, Discente, Docente, Matricula, Turma, TurmaDocente  # noqa: E402
from app.models_caso import Caso  # noqa: E402
from app.models_dupla import Dupla  # noqa: E402
from app.models_escrita import DuplaAcesso, Lancamento  # noqa: E402

SENHA = "senha-forte-1"


def _usuario(db, login, perfis, docente_id=None, turmas_monitor=()):
    u = acesso.Usuario(login=login, nome=login.split("@")[0].title(), senha_hash=acesso.gerar_hash(SENHA), docente_id=docente_id)
    for p in perfis:
        if p == "monitor":
            u.perfis += [acesso.UsuarioPerfil(perfil="monitor", turma_id=t) for t in turmas_monitor]
        else:
            u.perfis.append(acesso.UsuarioPerfil(perfil=p))
    db.add(u)
    return u


@pytest.fixture(scope="module")
def ctx():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        disc = Disciplina(codigo="EH0012", nome="LAB")
        t1 = Turma(disciplina=disc, periodo="2026.2", codigo="01")
        t2 = Turma(disciplina=disc, periodo="2026.2", codigo="02")
        prof, outro = Docente(nome="PROFA ANA", nome_normalizado="PROFA ANA", email="ana@ufc"), Docente(nome="PROF BETO", nome_normalizado="PROF BETO")
        db.add_all([t1, t2, prof, outro])
        db.flush()
        db.add_all([TurmaDocente(turma_id=t1.id, docente_id=prof.id), TurmaDocente(turma_id=t2.id, docente_id=outro.id)])
        ids = {}
        for t, base in ((t1, 0), (t2, 4)):
            ids[t.id] = []
            for i in range(4):
                a = Discente(matricula=f"55{base + i:04d}", nome=f"ALUNO {base + i}", email=f"a{base + i}@aluno")
                db.add(Matricula(turma=t, discente=a, situacao="ATIVO"))
                db.flush()
                ids[t.id].append(a.id)
        caso = carregar_caso_base(db)
        db.commit()
        tid1, tid2, cid, pid = t1.id, t2.id, caso.id, prof.id
    with TestClient(app=main.app) as c:  # ainda em modo aberto: monta os grupos
        for tid in (tid1, tid2):
            c.post(f"/turmas/{tid}/duplas", data={"discente_id": [str(ids[tid][0]), str(ids[tid][1])]})
            c.post(f"/turmas/{tid}/duplas", data={"discente_id": [str(ids[tid][2]), str(ids[tid][3])]})
            c.post(f"/turmas/{tid}/duplas/gerar", data={"caso_id": str(cid), "modo": "faltantes"})
            c.post(f"/turmas/{tid}/duplas/codigos")
        with SessionLocal() as db:
            _usuario(db, "adm@ufc", ["admin"])
            _usuario(db, "coord@ufc", ["coordenador"])
            _usuario(db, "ana@ufc", ["professor"], docente_id=pid)
            _usuario(db, "mon@ufc", ["monitor"], turmas_monitor=[tid1])
            _usuario(db, "vis@ufc", ["visitante"])
            db.commit()
            d1 = db.query(Dupla).filter_by(turma_id=tid1).order_by(Dupla.numero).first()
            d2 = db.query(Dupla).filter_by(turma_id=tid2).order_by(Dupla.numero).first()
            cod1 = db.query(DuplaAcesso).filter_by(dupla_id=d1.id).one().codigo
        yield {"c": c, "t1": tid1, "t2": tid2, "d1": d1.id, "d2": d2.id, "cod1": cod1, "caso": cid, "prof": pid}


def entrar(c, login):
    c.cookies.clear()
    return c.post("/entrar", data={"login": login, "senha": SENHA}, follow_redirects=False)


def st(c, url, metodo="get", **kw):
    return getattr(c, metodo)(url, follow_redirects=False, **kw).status_code


def test_login_e_senha(ctx):
    c = ctx["c"]
    c.cookies.clear()
    r = c.get("/disciplinas", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/entrar?volta=/disciplinas"
    assert "não conferem" in c.post("/entrar", data={"login": "adm@ufc", "senha": "errada"}).text
    r = entrar(c, "ADM@ufc")
    assert r.status_code == 303 and acesso.COOKIE in r.headers["set-cookie"]
    assert st(c, "/disciplinas") == 200 and st(c, "/historico") == 200 and st(c, "/admin/lote") == 200
    # usuário criado pelo admin recebe senha provisória e é obrigado a trocar
    r = c.post("/usuarios/novo", data={"nome": "Nova Prof", "login": "nova@ufc", "perfil": ["professor"],
                                       "docente_id": str(ctx["prof"])})
    senha = re.search(r'<strong class="mono">([^<]+)</strong>', r.text).group(1)
    c.cookies.clear()
    c.post("/entrar", data={"login": "nova@ufc", "senha": senha})
    assert c.get("/", follow_redirects=False).headers["location"] == "/conta/senha"
    assert st(c, "/conta/senha", "post", data={"atual": senha, "nova": "minha-senha-9", "nova2": "minha-senha-9"}) == 303
    assert st(c, "/") == 200
    c.get("/sair")
    assert st(c, "/") == 303


def test_coordenador(ctx):
    c = ctx["c"]
    entrar(c, "coord@ufc")
    for url in ("/disciplinas", "/docentes", "/discentes", "/importacao", f"/turmas/{ctx['t2']}", "/usuarios", "/casos"):
        assert st(c, url) == 200, url
    assert st(c, "/historico") == 403 and st(c, "/admin/lote") == 403
    r = c.get("/usuarios/novo")
    assert 'value="professor"' in r.text and 'value="admin"' not in r.text and 'value="coordenador"' not in r.text
    with SessionLocal() as db:
        adm = db.query(acesso.Usuario).filter_by(login="adm@ufc").one().id
    assert "fora do seu perfil" in c.get(f"/usuarios/{adm}").text


def test_professor_so_as_suas_turmas(ctx):
    c = ctx["c"]
    entrar(c, "ana@ufc")
    home = c.get("/").text
    assert "Turma 01" in home and "Turma 02" not in home
    assert st(c, f"/turmas/{ctx['t1']}") == 200 and st(c, f"/turmas/{ctx['t2']}") == 403
    assert st(c, f"/turmas/{ctx['t1']}/duplas") == 200 and st(c, f"/duplas/{ctx['d1']}/gabarito") == 200
    assert st(c, f"/duplas/{ctx['d2']}/escrituracao") == 403
    assert st(c, "/disciplinas") == 403 and st(c, "/usuarios") == 403 and st(c, f"/turmas/{ctx['t1']}/editar") == 403
    assert "Turma 02" not in c.get("/duplas").text
    # gera código na própria turma, não na outra
    assert st(c, f"/duplas/{ctx['d1']}/codigo/novo", "post") == 303
    assert st(c, f"/duplas/{ctx['d2']}/codigo/novo", "post") == 403
    # caso-base: lê, não altera; a cópia fica em seu nome e pode ser alterada
    assert st(c, f"/casos/{ctx['caso']}/empresa") == 200
    assert st(c, f"/casos/{ctx['caso']}/editar", "post", data={"nome": "x"}) == 403
    r = c.post(f"/casos/{ctx['caso']}/duplicar", data={"nome": "Minha cópia", "docente_id": "999"}, follow_redirects=False)
    novo = int(re.search(r"/casos/(\d+)/", r.headers["location"]).group(1))
    with SessionLocal() as db:
        assert db.get(Caso, novo).docente_id == ctx["prof"]
    assert st(c, f"/casos/{novo}/editar", "post", data={"nome": "Minha cópia 2"}) == 303
    # e-mail dos alunos aparece para o professor
    assert "a0@aluno" in c.get(f"/turmas/{ctx['t1']}").text


def test_monitor_e_visitante(ctx):
    c = ctx["c"]
    entrar(c, "mon@ufc")
    assert st(c, f"/turmas/{ctx['t1']}") == 200 and st(c, f"/duplas/{ctx['d1']}/escrituracao") == 200
    assert "a0@aluno" not in c.get(f"/turmas/{ctx['t1']}").text  # sem dados pessoais
    assert st(c, f"/duplas/{ctx['d1']}/gabarito") == 403 and st(c, f"/turmas/{ctx['t2']}") == 403
    assert st(c, f"/duplas/{ctx['d1']}/codigo/novo", "post") == 403
    assert "Somente leitura" in c.get("/").text
    entrar(c, "vis@ufc")
    assert st(c, f"/turmas/{ctx['t1']}") == 403  # ainda não é demonstração
    entrar(c, "adm@ufc")
    c.post(f"/turmas/{ctx['t1']}/demonstracao")
    entrar(c, "vis@ufc")
    assert st(c, f"/turmas/{ctx['t1']}") == 200 and st(c, f"/duplas/{ctx['d1']}/gabarito") == 200
    assert st(c, f"/turmas/{ctx['t1']}/duplas/codigos", "post") == 403 and st(c, "/casos") == 200
    # visitante vê a área do aluno do grupo, sem poder gravar
    c.get(f"/aluno/ver/{ctx['d1']}")
    t = c.get("/aluno").text
    assert "Visualização da área do aluno" in t
    r = c.post("/aluno/lancar", data={"evento": "J20", "data": "2026-01-20", "historico": "x", "conta": [pc.BANCO],
                                      "natureza": ["D"], "valor": ["1,00"]}, follow_redirects=False)
    assert r.status_code == 403
    assert st(c, f"/aluno/ver/{ctx['d2']}") == 403  # turma que não é de demonstração


def _codigo(did):
    with SessionLocal() as db:
        return db.query(DuplaAcesso).filter_by(dupla_id=did).one().codigo


def test_aluno_professor_e_turma_encerrada(ctx):
    c = ctx["c"]
    c.cookies.clear()
    ctx["cod1"] = _codigo(ctx["d1"])  # o professor gerou um código novo no teste anterior
    assert st(c, "/aluno/primeiro-acesso", "post", data={"codigo": ctx["cod1"], "ciente": "1", "matricula_pa": "550000",
                                                          "nova": "aluno-senha-1", "nova2": "aluno-senha-1"}) == 303
    lanc = {"evento": "J20", "data": "2026-01-20", "historico": "Integralização", "conta": [pc.BANCO, pc.CAPITAL["Marcela Soares"][1]],
            "natureza": ["D", "C"], "valor": ["10,00", "10,00"]}
    r = c.post("/aluno/lancar", data=lanc, follow_redirects=False)
    assert r.status_code == 303 and "erro" not in r.headers["location"]
    # professor apaga a senha do aluno; ele refaz o primeiro acesso
    entrar(c, "ana@ufc")
    with SessionLocal() as db:
        dis = db.query(Discente).filter_by(matricula="550000").one().id
    _pg = c.get(f"/turmas/{ctx['t1']}/duplas").text
    assert "senha criada" in _pg, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _pg))[:1500]
    c.post(f"/turmas/{ctx['t1']}/alunos/{dis}/senha")
    c.cookies.clear()
    assert st(c, "/aluno/primeiro-acesso", "post", data={"codigo": ctx["cod1"], "ciente": "1", "matricula_pa": "550000",
                                                          "nova": "aluno-senha-2", "nova2": "aluno-senha-2"}) == 303
    # turma encerrada: professor e aluno só leem; admin ainda altera
    entrar(c, "coord@ufc")
    c.post(f"/turmas/{ctx['t1']}/encerrar")
    entrar(c, "ana@ufc")
    assert st(c, f"/duplas/{ctx['d1']}/codigo/novo", "post") == 403
    c.cookies.clear()
    c.post("/aluno/entrar", data={"matricula": "550000", "senha": "aluno-senha-2"})
    r = c.post("/aluno/lancar", data=lanc, follow_redirects=False)
    assert "encerrada" in r.headers["location"]
    entrar(c, "adm@ufc")
    assert st(c, f"/duplas/{ctx['d1']}/codigo/novo", "post") == 303
    c.post(f"/turmas/{ctx['t1']}/reabrir")


def test_historico_e_lote(ctx):
    c = ctx["c"]
    entrar(c, "adm@ufc")
    h = c.get("/historico?q=550000").text
    assert "Lançamento da dupla" in h and "Aluno criou a senha" in h
    assert "Encerrou a turma" in c.get("/historico?q=coord").text
    with SessionLocal() as db:
        n = db.query(Lancamento).filter_by(dupla_id=ctx["d1"]).count()
    assert n >= 1
    r = c.post("/admin/lote", data={"op": "lancamentos", "turma": ctx["t1"], "id": [ctx["d1"]]})
    assert "Confirmar e executar" in r.text and f"{n} lançamento" in r.text
    with SessionLocal() as db:
        assert db.query(Lancamento).filter_by(dupla_id=ctx["d1"]).count() == n  # só a prévia
    r = c.post("/admin/lote", data={"op": "lancamentos", "turma": ctx["t1"], "id": [ctx["d1"]], "confirmo": "1"},
               follow_redirects=False)
    assert "Conclu" in r.headers["location"]
    with SessionLocal() as db:
        assert db.query(Lancamento).filter_by(dupla_id=ctx["d1"]).count() == 0
    assert "Lote: Excluir todos os lançamentos" in c.get("/historico").text


def test_garantir_admin(monkeypatch):
    with SessionLocal() as db:
        for p in db.query(acesso.UsuarioPerfil).filter(acesso.UsuarioPerfil.perfil.in_(acesso.EQUIPE)).all():
            db.delete(p)
        db.commit()
        monkeypatch.setattr(acesso, "APP_USUARIO", "Admin")
        monkeypatch.setattr(acesso, "APP_SENHA", "senha-do-env")
        acesso.garantir_admin(db)
        u = db.query(acesso.Usuario).filter_by(login="admin").one()
        assert "admin" in u.nomes_perfis and acesso.conferir("senha-do-env", u.senha_hash)

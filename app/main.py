"""LABCONT-AI · Protótipo — cadastros acadêmicos e caso da empresa."""
from __future__ import annotations

from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import APP_NOME, BASE_DIR
from .db import Base, SessionLocal, engine, get_db
from .models import Disciplina, Discente, Docente, Importacao, Matricula, Turma
from . import acesso, analytics, models_caso, models_dupla, models_escrita, normas as _normas  # noqa: F401  (registra as tabelas)
from .caso_servico import fmt as _fmt_num


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        _normas.semear(db)  # fichas padrão da base normativa que ainda não existem
        acesso.garantir_admin(db)  # primeiro administrador a partir de APP_USUARIO/APP_SENHA
        _sem_marcas_reais(db)
    yield


def _sem_marcas_reais(db) -> None:
    """A6: os casos já cadastrados trocam as concessionárias reais pelas fictícias usadas nos documentos."""
    from .models_caso import Evento
    trocas = [("Energia Enel", "Energia Luz do Sertão"), ("energia Enel", "energia Luz do Sertão"),
              ("água CAGECE", "água Águas do Litoral"), ("CAGECE", "Águas do Litoral"), ("Enel", "Luz do Sertão")]
    mudou = False
    for e in db.scalars(select(Evento).where(Evento.descricao.ilike("%enel%") | Evento.descricao.ilike("%cagece%"))).all():
        nova = e.descricao
        for a, b in trocas:
            nova = nova.replace(a, b)
        if nova != e.descricao:
            e.descricao, mudou = nova, True
    if mudou:
        db.commit()


app = FastAPI(title=APP_NOME, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")
templates.env.globals["APP_NOME"] = APP_NOME


def _fmt_data(d):
    return d.strftime("%d/%m/%Y") if d else "—"


templates.env.filters["data"] = _fmt_data
templates.env.filters["n"] = _fmt_num


_PUBLICOS = ("/static", "/saude", "/entrar", "/sair", "/aluno", "/privacidade")


def _negado(request: Request, motivo: str):
    r = templates.TemplateResponse(request, "negado.html", {"motivo": motivo, "usuario": getattr(request.state, "usuario", None)},
                                   status_code=403)
    return r


@app.middleware("http")
async def _acesso(request: Request, call_next):
    """Login com perfis (Etapa 7): identifica o usuário, aplica as regras e registra as alterações no histórico."""
    caminho = request.url.path
    request.state.usuario = None
    if caminho.startswith(("/static", "/saude")):
        return await call_next(request)
    with SessionLocal() as db:
        u = acesso.ler_sessao(db, request.cookies.get(acesso.COOKIE, ""))
        ctx = acesso.montar_ctx(db, u) if u else None
        if ctx is None and acesso.modo_aberto(db):
            ctx = acesso.ctx_dev()
        request.state.usuario = ctx
        if not caminho.startswith(_PUBLICOS) or caminho.startswith("/aluno/ver/"):
            if ctx is None:
                destino = "/entrar" + (("?volta=" + quote(caminho)) if request.method == "GET" and caminho != "/" else "")
                return RedirectResponse(destino, status_code=303)
            if not ctx.equipe:
                return RedirectResponse("/aluno", status_code=303)
            if ctx.trocar_senha and caminho != "/conta/senha":
                return RedirectResponse("/conta/senha", status_code=303)
            ok, motivo, _tid = acesso.autorizar(db, ctx, request.method, caminho)
            if not ok:
                return _negado(request, motivo)
        elif caminho.startswith("/aluno") and request.method == "POST" and ctx and ctx.equipe \
                and request.cookies.get(acesso.COOKIE_VER) and caminho not in ("/aluno/entrar", "/aluno/primeiro-acesso"):
            return _negado(request, "Visualização da área do aluno: somente leitura.")
    resposta = await call_next(request)
    if request.method == "POST" and resposta.status_code < 400 and ctx and not ctx.dev \
            and caminho not in ("/entrar", "/aluno/entrar", "/aluno/primeiro-acesso", "/admin/lote", "/admin/demonstracao"):
        with SessionLocal() as db:
            acesso.registrar(db, ctx, caminho)
    return resposta


def render(request: Request, template: str, **ctx):
    ctx.setdefault("usuario", getattr(request.state, "usuario", None))
    ctx.setdefault("msg", request.query_params.get("msg"))
    ctx.setdefault("erro", request.query_params.get("erro"))
    return templates.TemplateResponse(request, template, ctx)


def voltar(url: str, msg: str | None = None, erro: str | None = None) -> RedirectResponse:
    if msg:
        url += ("&" if "?" in url else "?") + "msg=" + quote(msg)
    if erro:
        url += ("&" if "?" in url else "?") + "erro=" + quote(erro)
    return RedirectResponse(url, status_code=303)


PRIVACIDADE_VERSAO = "2026-10"


@app.get("/privacidade")
def privacidade(request: Request):
    import os
    contato = os.getenv("APP_CONTATO_PRIVACIDADE") or "o(a) professor(a) responsável pela turma"
    return render(request, "privacidade.html", versao=PRIVACIDADE_VERSAO, contato=contato)


@app.get("/saude")
def saude(db: Session = Depends(get_db)):
    """Verificação de funcionamento (sem senha), usada no monitoramento."""
    db.execute(select(1))
    return {"status": "ok"}


@app.get("/")
async def painel(request: Request, db: Session = Depends(get_db)):
    """Painel de Gestão (Módulo 5): visão de todas as turmas do escopo do usuário, com indicadores de acompanhamento."""
    from datetime import datetime, timedelta
    from . import tutor as tutor_ia
    c = request.state.usuario
    turmas = db.scalars(select(Turma).order_by(Turma.periodo.desc(), Turma.codigo)).all()
    if c and not c.gestor:
        turmas = [t for t in turmas if t.id in c.turmas]
    else:
        turmas = [t for t in turmas if t.matriculas]
    linhas = analytics.resumo_gestao(db, turmas)
    tot = lambda k: sum(x[k] for x in linhas)  # noqa: E731
    medias = [x["media"] for x in linhas if x["media"] is not None]
    kpi = {"turmas": len(linhas), "alunos": tot("alunos"), "grupos": tot("grupos"), "contas": tot("contas"),
           "adesao": round(100 * tot("contas") / tot("alunos")) if tot("alunos") else 0, "enviados": tot("enviados"),
           "media": round(sum(medias) / len(medias)) if medias else None, "perguntas": tot("perguntas"),
           "homologadas": tot("homologadas")}
    agora = datetime.now()
    for x in linhas:
        x["parada"] = bool(x["grupos"] and (not x["ultima"] or agora - x["ultima"] > timedelta(days=7)))
    extra = {}
    if c and c.gestor:
        extra["contagens"] = {
            "disciplinas": db.scalar(select(func.count(Disciplina.id))), "turmas": db.scalar(select(func.count(Turma.id))),
            "docentes": db.scalar(select(func.count(Docente.id))), "discentes": db.scalar(select(func.count(Discente.id))),
            "matriculas": db.scalar(select(func.count(Matricula.id)))}
        extra["importacoes"] = db.scalars(select(Importacao).order_by(Importacao.id.desc()).limit(5)).all()
        sete = agora - timedelta(days=7)
        usuarios = db.scalars(select(acesso.Usuario)).all()
        por = {}
        for u in usuarios:
            for p in u.nomes_perfis:
                q = por.setdefault(p, {"total": 0, "ativos": 0})
                q["total"] += 1
                q["ativos"] += 1 if (u.ultimo_acesso and u.ultimo_acesso >= sete) else 0
        extra["usuarios"] = [(acesso.PERFIS[p], por[p]) for p in list(acesso.EQUIPE) + ["aluno"] if p in por]
        if c.admin:
            extra["acoes"] = db.scalars(select(acesso.Acao).order_by(acesso.Acao.id.desc()).limit(8)).all()
    ia = await tutor_ia.status_ia()
    return render(request, "gestao.html", linhas=linhas, kpi=kpi, ia=ia, menu="painel", **extra)


from .routers import (admin_lote, aluno, casos, conta, disciplinas, discentes, docentes, documentos, duplas, escrituracao, gabarito,  # noqa: E402
                      importacao, normas, painel_turma, turmas)

for r in (conta, admin_lote, aluno, disciplinas, duplas, gabarito, documentos, escrituracao, turmas, docentes, discentes, importacao, casos, painel_turma, normas):
    app.include_router(r.router)

"""Etapa 7 · Operações em lote do administrador (com prévia, confirmação e registro no histórico)
e redefinição da senha de aluno pelo professor."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import acesso
from ..acesso import Usuario
from ..db import get_db
from ..main import render, voltar
from ..models import Discente, Matricula, Turma
from ..models_dupla import Dupla, DuplaMembro
from ..models_escrita import FechamentoMensal, Lancamento, TutorMensagem

router = APIRouter()

OPERACOES = {
    "lancamentos": "Excluir todos os lançamentos dos grupos selecionados",
    "tutor": "Excluir as conversas com o tutor dos grupos selecionados",
    "reabrir": "Reabrir os fechamentos enviados (janeiro e fevereiro) dos grupos selecionados",
    "contas": "Excluir as senhas (contas) dos alunos selecionados — farão o primeiro acesso de novo",
    "discentes": "Excluir os discentes selecionados do sistema (com matrículas, grupos e contas)",
}
ALVO = {"lancamentos": "dupla", "tutor": "dupla", "reabrir": "dupla", "contas": "discente", "discentes": "discente"}


def _turma_dados(db: Session, tid: int) -> dict:
    t = db.get(Turma, tid)
    duplas = db.scalars(select(Dupla).where(Dupla.turma_id == tid).order_by(Dupla.numero)).all()
    info = {}
    for d in duplas:
        info[d.id] = {
            "lancamentos": db.scalar(select(func.count(Lancamento.id)).where(Lancamento.dupla_id == d.id)),
            "tutor": db.scalar(select(func.count(TutorMensagem.id)).where(TutorMensagem.dupla_id == d.id)),
            "fechado": acesso_fech(db, d.id),
        }
    mats = sorted(t.matriculas, key=lambda m: m.discente.nome) if t else []
    contas = set(db.scalars(select(Usuario.discente_id).where(Usuario.discente_id.in_([m.discente_id for m in mats]))).all()) if mats else set()
    return {"t": t, "duplas": duplas, "info": info, "mats": mats, "contas": contas}


def acesso_fech(db: Session, did: int) -> bool:
    from ..models_escrita import fechamento_ativo
    return fechamento_ativo(db, did) is not None


@router.get("/admin/lote")
def tela(request: Request, turma: int = 0, db: Session = Depends(get_db)):
    turmas = db.scalars(select(Turma).order_by(Turma.periodo.desc(), Turma.codigo)).all()
    dados = _turma_dados(db, turma) if turma else None
    return render(request, "conta/lote.html", turmas=turmas, turma=turma, dados=dados, ops=OPERACOES, menu="lote")


def _previa(db: Session, op: str, ids: list[int]) -> tuple[list[str], int]:
    linhas, total = [], 0
    if ALVO[op] == "dupla":
        for d in db.scalars(select(Dupla).where(Dupla.id.in_(ids)).order_by(Dupla.numero)).all():
            if op == "lancamentos":
                n = db.scalar(select(func.count(Lancamento.id)).where(Lancamento.dupla_id == d.id))
                linhas.append(f"{d.rotulo}: {n} lançamento(s)")
            elif op == "tutor":
                n = db.scalar(select(func.count(TutorMensagem.id)).where(TutorMensagem.dupla_id == d.id))
                linhas.append(f"{d.rotulo}: {n} mensagem(ns)")
            else:
                n = 1 if acesso_fech(db, d.id) else 0
                linhas.append(f"{d.rotulo}: {'fechamento enviado — será reaberto' if n else 'não enviou (nada a fazer)'}")
            total += n
    else:
        for a in db.scalars(select(Discente).where(Discente.id.in_(ids)).order_by(Discente.nome)).all():
            if op == "contas":
                n = db.scalar(select(func.count(Usuario.id)).where(Usuario.discente_id == a.id))
                linhas.append(f"{a.nome} ({a.matricula}): {'tem senha' if n else 'sem conta'}")
            else:
                n = 1
                ms = db.scalar(select(func.count(Matricula.id)).where(Matricula.discente_id == a.id))
                linhas.append(f"{a.nome} ({a.matricula}): {ms} matrícula(s)")
            total += n
    return linhas, total


def _executar(db: Session, op: str, ids: list[int]) -> int:
    from datetime import datetime
    if op == "lancamentos":
        ls = db.scalars(select(Lancamento).where(Lancamento.dupla_id.in_(ids))).all()
        for l in ls:
            db.delete(l)
        return len(ls)
    if op == "tutor":
        return db.execute(delete(TutorMensagem).where(TutorMensagem.dupla_id.in_(ids))).rowcount
    if op == "reabrir":
        n = 0
        for f in db.scalars(select(FechamentoMensal).where(FechamentoMensal.dupla_id.in_(ids),
                                                           FechamentoMensal.reaberto_em.is_(None))).all():
            f.reaberto_em = datetime.now()
            n += 1
        return n
    if op == "contas":
        us = db.scalars(select(Usuario).where(Usuario.discente_id.in_(ids))).all()
        n = 0
        for u in us:
            if u.nomes_perfis <= {"aluno"}:
                db.delete(u)
                n += 1
        return n
    if op == "discentes":
        db.execute(delete(DuplaMembro).where(DuplaMembro.discente_id.in_(ids)))
        alunos = db.scalars(select(Discente).where(Discente.id.in_(ids))).all()
        for a in alunos:
            db.delete(a)
        return len(alunos)
    return 0


@router.post("/admin/lote")
async def executar(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    op = form.get("op") or ""
    turma = int(form.get("turma") or 0)
    ids = [int(x) for x in form.getlist("id") if x.isdigit()]
    volta = f"/admin/lote?turma={turma}"
    if op not in OPERACOES or not ids:
        return voltar(volta, erro="Escolha a operação e marque pelo menos um item.")
    linhas, total = _previa(db, op, ids)
    if form.get("confirmo") != "1":
        return render(request, "conta/lote_confirmar.html", op=op, titulo=OPERACOES[op], ids=ids, turma=turma,
                      linhas=linhas, total=total, menu="lote")
    n = _executar(db, op, ids)
    db.commit()
    acesso.registrar(db, request.state.usuario, "/admin/lote", f"Lote: {OPERACOES[op]} ({n})",
                     detalhe="\n".join(linhas))
    return voltar(volta, f"Concluído: {n} registro(s) afetado(s). A operação ficou registrada no histórico.")


# ------------------------------------------------------------------ senha de aluno (professor)
@router.post("/turmas/{tid}/alunos/{dis}/senha")
def redefinir_aluno(tid: int, dis: int, db: Session = Depends(get_db)):
    if not db.scalar(select(Matricula).where(Matricula.turma_id == tid, Matricula.discente_id == dis)):
        return voltar(f"/turmas/{tid}/duplas#acesso", erro="Aluno não pertence a esta turma.")
    n = 0
    for u in db.scalars(select(Usuario).where(Usuario.discente_id == dis)).all():
        if u.nomes_perfis <= {"aluno"}:
            db.delete(u)
            n += 1
    db.commit()
    return voltar(f"/turmas/{tid}/duplas#acesso", "Senha apagada: o aluno fará o primeiro acesso de novo com o código do grupo."
                  if n else "O aluno ainda não tinha criado senha.")


# ------------------------------------------------------------------ turma de demonstração (dados fictícios)
@router.get("/admin/demonstracao")
def demonstracao_tela(request: Request, db: Session = Depends(get_db)):
    from .. import demo
    t = demo._turma_demo(db)
    return render(request, "conta/demonstracao.html", t=t, grupos=len(t.matriculas) // 2 if t else 0, res=None,
                  login_vis=demo.LOGIN_VISITANTE, login_prof=demo.LOGIN_PROFESSOR, menu="demo")


@router.post("/admin/demonstracao")
async def demonstracao_criar(request: Request, db: Session = Depends(get_db)):
    from .. import demo
    form = await request.form()
    if form.get("acao") == "apagar":
        demo.apagar(db)
        db.commit()
        acesso.registrar(db, request.state.usuario, "/admin/demonstracao", "Turma de demonstração apagada")
        return voltar("/admin/demonstracao", "Turma de demonstração e acessos de demonstração apagados.")
    res = demo.criar(db)
    acesso.registrar(db, request.state.usuario, "/admin/demonstracao", "Turma de demonstração recriada")
    t = demo._turma_demo(db)
    return render(request, "conta/demonstracao.html", t=t, grupos=res["grupos"], res=res,
                  login_vis=demo.LOGIN_VISITANTE, login_prof=demo.LOGIN_PROFESSOR, menu="demo")

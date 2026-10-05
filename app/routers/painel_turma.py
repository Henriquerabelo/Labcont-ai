"""Etapa 6 · visão do professor: painel da turma e conversas da dupla com o tutor."""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import analytics
from .. import tutor as tutor_ia
from ..auditoria import NIVEIS, eventos_ate
from .. import periodos
from ..periodos import MESES
from ..db import get_db
from ..main import render, voltar
from ..models import Turma
from ..models_dupla import Dupla
from ..models_escrita import TutorMensagem, fechamento_ativo

router = APIRouter()


@router.get("/turmas/{tid}/painel")
async def painel(request: Request, tid: int, db: Session = Depends(get_db)):
    """Learning Analytics da turma: visão panorâmica, alertas, matriz de calor, engajamento e tutor."""
    if not db.get(Turma, tid):
        return RedirectResponse("/duplas", status_code=303)
    mes = periodos.da_requisicao(request)
    an = analytics.analisar_turma(db, tid, mes=mes)
    c = request.state.usuario
    ve_previa = bool(c and (c.gestor or "professor" in c.perfis or "visitante" in c.perfis))  # monitor: sem correção antecipada
    ids = [g["d"].id for g in an["grupos"]]
    rot = {g["d"].id: g["d"].rotulo for g in an["grupos"]}
    msgs = db.scalars(select(TutorMensagem).where(TutorMensagem.dupla_id.in_(ids), TutorMensagem.papel == "aluno")
                      .order_by(TutorMensagem.id.desc()).limit(12)).all() if ids else []
    recentes = [{"m": m, "dupla": rot.get(m.dupla_id, ""), "dupla_id": m.dupla_id} for m in msgs]
    ia = await tutor_ia.status_ia()
    return render(request, "painel_turma/painel.html", an=an, t=an["t"], ve_previa=ve_previa, recentes=recentes, ia=ia,
                  niveis={**NIVEIS, "lancado": "Lançado"}, limite=tutor_ia.LIMITE_DIARIO,
                  criticos={k: v for k, v in analytics.EVENTOS_CRITICOS.items() if periodos.mes_do_evento(k) == mes},
                  menu="duplas", mes=mes, meses=MESES, mes_info=MESES[mes], url_mes=f"/turmas/{tid}/painel")


# ------------------------------------------------------------------ notas de janeiro (homologação)
@router.get("/turmas/{tid}/notas")
def notas(request: Request, tid: int, db: Session = Depends(get_db)):
    t = db.get(Turma, tid)
    mes = periodos.da_requisicao(request)
    linhas = analytics.propor_notas(db, tid, mes)
    hom = [l for l in linhas if l["n"].homologada]
    return render(request, "painel_turma/notas.html", t=t, linhas=linhas, pesos=analytics.PESOS_NIVEL,
                  homologadas=len(hom), prontas=sum(1 for l in linhas if l["n"].nota_sistema is not None), menu="duplas",
                  mes=mes, meses=MESES, mes_info=MESES[mes], url_mes=f"/turmas/{tid}/notas")


@router.post("/turmas/{tid}/notas")
async def notas_salvar(request: Request, tid: int, db: Session = Depends(get_db)):
    from datetime import datetime
    form = await request.form()
    acao = form.get("acao") or "salvar"
    mes = periodos.valido(form.get("mes"))
    c = request.state.usuario
    n_ok = 0
    for n in db.scalars(select(analytics.NotaPeriodo).where(analytics.NotaPeriodo.turma_id == tid,
                                                           analytics.NotaPeriodo.periodo == mes)).all():
        k = str(n.id)
        if acao == "desfazer" and form.get(f"sel_{k}"):
            n.homologada, n.homologada_em, n.homologada_por = False, None, None
            n_ok += 1
            continue
        if n.homologada:
            continue
        if f"ajuste_{k}" in form:
            try:
                n.ajuste = max(-10.0, min(10.0, float((form.get(f"ajuste_{k}") or "0").replace(",", "."))))
            except ValueError:
                return voltar(f"/turmas/{tid}/notas?mes={mes}", erro="Ajuste inválido: use números como 0,5 ou -1.")
            n.observacao = (form.get(f"obs_{k}") or "").strip() or None
            n.atualizado_em = datetime.now()
        if acao == "homologar" and form.get(f"sel_{k}") and n.nota_sistema is not None:
            n.homologada, n.homologada_em, n.homologada_por = True, datetime.now(), c.login if c else ""
            n_ok += 1
    db.commit()
    msg = {"homologar": f"{n_ok} nota(s) homologada(s). Os alunos já veem a nota de {MESES[mes]['nome']}.",
           "desfazer": f"Homologação desfeita em {n_ok} nota(s)."}.get(acao, "Ajustes salvos.")
    return voltar(f"/turmas/{tid}/notas?mes={mes}", msg)


@router.get("/turmas/{tid}/notas.csv")
def notas_csv(request: Request, tid: int, db: Session = Depends(get_db)):
    import csv
    import io
    mes = periodos.da_requisicao(request)
    linhas = analytics.propor_notas(db, tid, mes)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Matrícula", "Nome", "Grupo", "Nota do sistema", "Ajuste", "Nota final", "Homologada", "Observação"])
    for l in linhas:
        n = l["n"]
        f = lambda v: "" if v is None else f"{v:.1f}".replace(".", ",")  # noqa: E731
        w.writerow([l["m"].discente.matricula, l["m"].discente.nome, l["d"].rotulo, f(n.nota_sistema), f(n.ajuste),
                    f(n.nota_final), "sim" if n.homologada else "não", n.observacao or ""])
    return Response("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="notas_{MESES[mes]["nome"]}_turma_{tid}.csv"'})


@router.get("/duplas/{id}/tutor")
def conversas(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    if not d or not d.empresa:
        return RedirectResponse("/duplas", status_code=303)
    msgs = db.scalars(select(TutorMensagem).where(TutorMensagem.dupla_id == id).order_by(TutorMensagem.id)).all()
    desc = {e["codigo"]: e["descricao"] for e in eventos_ate(d.empresa.caso, "2026-02")}
    grupos = defaultdict(list)
    for m in msgs:
        grupos[m.evento or ""].append(m)
    ordem = sorted(grupos, key=lambda k: (k != "", min(x.id for x in grupos[k])))
    blocos = [{"evento": k, "descricao": desc.get(k, "Dúvida geral" if not k else k), "msgs": grupos[k]} for k in ordem]
    return render(request, "painel_turma/conversas.html", d=d, blocos=blocos, fech=fechamento_ativo(db, id),
                  fech_fev=fechamento_ativo(db, id, "2026-02"),
                  n_perg=sum(1 for m in msgs if m.papel == "aluno"), menu="duplas")

"""Visão do professor: códigos de acesso das duplas e auditoria detalhada da escrituração."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auditoria import NIVEIS, auditar
from ..db import get_db
from ..gabarito import gerar_gabarito
from ..main import render, voltar
from ..models_dupla import Dupla
from datetime import datetime

from ..models_escrita import DuplaAcesso, Lancamento, fechamento_ativo
from .. import periodos
from ..periodos import MESES, ate_o_mes, do_mes

router = APIRouter()
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O, 1/I


def novo_codigo(db: Session) -> str:
    while True:
        c = "".join(secrets.choice(ALFABETO) for _ in range(8))
        if not db.scalar(select(DuplaAcesso).where(DuplaAcesso.codigo == c)):
            return c


def codigos_turma(db: Session, tid: int) -> dict[int, DuplaAcesso]:
    duplas = [d.id for d in db.scalars(select(Dupla).where(Dupla.turma_id == tid)).all()]
    if not duplas:
        return {}
    return {a.dupla_id: a for a in db.scalars(select(DuplaAcesso).where(DuplaAcesso.dupla_id.in_(duplas))).all()}


def progresso_turma(db: Session, tid: int, mes: str = "2026-01") -> dict[int, dict]:
    out = {}
    for d in db.scalars(select(Dupla).where(Dupla.turma_id == tid)).all():
        if not d.empresa:
            continue
        todos = db.scalars(select(Lancamento).where(Lancamento.dupla_id == d.id)).all()
        lancs = do_mes(todos, mes)
        fech = fechamento_ativo(db, d.id, mes)
        eventos = {l.evento for l in lancs}
        info = {"lancamentos": len(lancs), "eventos": len(eventos), "enviado": fech.enviado_em if fech else None}
        if fech:
            info["percentual"] = (fech.resultado or {}).get("percentual", 0)
        elif lancs:
            info["previa"] = auditar(gerar_gabarito(d.empresa.valores, mes), lancs)["percentual"]
        out[d.id] = info
    return out


@router.post("/turmas/{tid}/duplas/codigos")
def gerar_codigos(tid: int, db: Session = Depends(get_db)):
    existentes = codigos_turma(db, tid)
    n = 0
    for d in db.scalars(select(Dupla).where(Dupla.turma_id == tid)).all():
        if d.id not in existentes:
            db.add(DuplaAcesso(dupla_id=d.id, codigo=novo_codigo(db)))
            n += 1
    db.commit()
    return voltar(f"/turmas/{tid}/duplas#acesso", f"{n} código(s) de acesso gerado(s)." if n else "Todas as duplas já têm código.")


@router.post("/duplas/{id}/codigo/novo")
def trocar_codigo(id: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    a = db.scalar(select(DuplaAcesso).where(DuplaAcesso.dupla_id == id))
    if a:
        a.codigo = novo_codigo(db)
    else:
        db.add(DuplaAcesso(dupla_id=id, codigo=novo_codigo(db)))
    db.commit()
    return voltar(f"/turmas/{d.turma_id}/duplas#d{id}", "Novo código gerado; o anterior deixou de valer.")


@router.get("/duplas/{id}/escrituracao")
def escrituracao(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    if not d or not d.empresa:
        return voltar("/duplas", erro="Gere a empresa da dupla primeiro.")
    mes = periodos.da_requisicao(request)
    todos = db.scalars(select(Lancamento).where(Lancamento.dupla_id == id).order_by(Lancamento.data, Lancamento.id)).all()
    aud = auditar(gerar_gabarito(d.empresa.valores, mes), todos, d.empresa.caso)
    acesso = db.scalar(select(DuplaAcesso).where(DuplaAcesso.dupla_id == id))
    from .. import consistencia
    from ..auditoria import eventos_mes
    from ..gabarito import Gabarito
    avisos = consistencia.verificar(Gabarito(d.empresa.valores).L.ini, ate_o_mes(todos, mes),
                                    {e["codigo"]: e["data"] for e in eventos_mes(d.empresa.caso, mes)}, mes)
    return render(request, "escrituracao/professor.html", d=d, aud=aud, niveis=NIVEIS, lancs=do_mes(todos, mes), acesso=acesso,
                  fech=fechamento_ativo(db, id, mes), avisos=avisos, avisos_cont=consistencia.contagem(avisos),
                  prof=True, menu="duplas", mes=mes, meses=MESES, mes_info=MESES[mes], url_mes=f"/duplas/{id}/escrituracao")


@router.post("/duplas/{id}/fechamento/reabrir")
async def reabrir(request: Request, id: int, db: Session = Depends(get_db)):
    mes = periodos.valido((await request.form()).get("mes"))
    f = fechamento_ativo(db, id, mes)
    if f:
        f.reaberto_em = datetime.now()
        db.commit()
    return voltar(f"/duplas/{id}/escrituracao?mes={mes}", f"{MESES[mes]['nome'].capitalize()} reaberto: a dupla pode corrigir e "
                                                          "enviar de novo. O envio anterior fica no histórico.")


@router.get("/duplas/{id}/demonstracoes")
def demonstracoes_professor(request: Request, id: int, db: Session = Depends(get_db)):
    from .. import demonstracoes as dm
    from ..gabarito import Gabarito
    d = db.get(Dupla, id)
    if not d or not d.empresa:
        return voltar("/duplas", erro="Empresa ainda não gerada.")
    mes = periodos.da_requisicao(request)
    lancs = ate_o_mes(db.scalars(select(Lancamento).where(Lancamento.dupla_id == id)).all(), mes)
    parts = [(p.conta, p.natureza, p.valor) for l in lancs for p in l.partidas]
    r = dm.montar(dm.saldos_finais(Gabarito(d.empresa.valores).L.ini, parts), mes)
    c = request.state.usuario
    ve_gab = bool(c and (c.gestor or "professor" in c.perfis or "visitante" in c.perfis))  # monitor não vê o gabarito
    g = dm.montar(dm.de_gabarito(gerar_gabarito(d.empresa.valores, mes)), mes) if ve_gab else None
    return render(request, "demonstracoes/professor.html", d=d, r=r, g=g, menu="duplas", mes=mes, meses=MESES,
                  url_mes=f"/duplas/{id}/demonstracoes")

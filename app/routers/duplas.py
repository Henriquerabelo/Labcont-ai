"""Duplas por turma (formação voluntária, registrada pelo professor) e geração das empresas."""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..geracao import gerar, nova_semente
from ..main import render, voltar
from ..models import Matricula, Turma, normalizar
from ..models_caso import Caso
from ..models_dupla import Dupla, DuplaMembro, EmpresaGerada
from .comum import inteiro, txt

router = APIRouter()
MAX_MEMBROS = 3


def _url(tid: int, ancora: str = "") -> str:
    return f"/turmas/{tid}/duplas" + (f"#{ancora}" if ancora else "")


def _duplas(db: Session, tid: int) -> list[Dupla]:
    return db.scalars(select(Dupla).where(Dupla.turma_id == tid).order_by(Dupla.numero)).all()


def _ativos(t: Turma) -> list[Matricula]:
    return sorted([m for m in t.matriculas if m.situacao == "ATIVO"], key=lambda m: m.discente.nome)


def _em_dupla(db: Session, tid: int) -> set[int]:
    return set(db.scalars(select(DuplaMembro.discente_id).where(DuplaMembro.turma_id == tid)).all())


def _proximo_numero(db: Session, tid: int) -> int:
    usados = {d.numero for d in _duplas(db, tid)}
    n = 1
    while n in usados:
        n += 1
    return n


def _criar(db: Session, t: Turma, ids: list[int], nome: str | None = None) -> tuple[Dupla | None, str | None]:
    ids = list(dict.fromkeys(ids))
    if not ids:
        return None, "Selecione ao menos um discente."
    if len(ids) > MAX_MEMBROS:
        return None, f"Uma dupla pode ter no máximo {MAX_MEMBROS} integrantes (trio como exceção)."
    validos = {m.discente_id for m in _ativos(t)}
    if any(i not in validos for i in ids):
        return None, "Há discente que não está ativo nesta turma."
    ocupados = _em_dupla(db, t.id) & set(ids)
    if ocupados:
        return None, "Há discente que já participa de outra dupla."
    d = Dupla(turma_id=t.id, numero=_proximo_numero(db, t.id), nome=nome)
    d.membros = [DuplaMembro(turma_id=t.id, discente_id=i) for i in ids]
    db.add(d)
    db.flush()
    return d, None


def _caso_padrao(db: Session, t: Turma, duplas: list[Dupla]) -> int | None:
    for d in duplas:
        if d.empresa and d.empresa.caso_id:
            return d.empresa.caso_id
    docentes = {v.docente_id for v in t.docentes}
    casos = db.scalars(select(Caso).order_by(Caso.id.desc())).all()
    for c in casos:
        if c.docente_id in docentes:
            return c.id
    return casos[-1].id if casos else None


# ------------------------------------------------------------------ visão geral (menu "Duplas")
@router.get("/duplas")
def visao_geral(request: Request, db: Session = Depends(get_db)):
    turmas = db.scalars(select(Turma)).all()
    c = request.state.usuario
    if c and not c.gestor:
        turmas = [t for t in turmas if t.id in c.turmas]
    linhas = []
    for t in turmas:
        duplas = _duplas(db, t.id)
        ativos = len(_ativos(t))
        if not ativos and not duplas:
            continue
        linhas.append({"t": t, "ativos": ativos, "duplas": len(duplas),
                       "em_dupla": len(_em_dupla(db, t.id)), "geradas": sum(1 for d in duplas if d.empresa)})
    linhas.sort(key=lambda x: (x["t"].periodo, x["t"].disciplina.codigo, x["t"].codigo), reverse=True)
    return render(request, "duplas/visao.html", linhas=linhas, menu="duplas")


# ------------------------------------------------------------------ tela de duplas
@router.get("/turmas/{tid}/duplas")
def tela(request: Request, tid: int, db: Session = Depends(get_db)):
    t = db.get(Turma, tid)
    if not t:
        return voltar("/disciplinas", erro="Turma não encontrada.")
    duplas = _duplas(db, tid)
    ocupados = _em_dupla(db, tid)
    sem_dupla = [m for m in _ativos(t) if m.discente_id not in ocupados]
    casos = db.scalars(select(Caso).order_by(Caso.nome)).all()
    from .escrituracao import codigos_turma, progresso_turma
    from ..acesso import Usuario, status_turma
    ids_alunos = [m.discente_id for d in duplas for m in d.membros]
    contas = set(db.scalars(select(Usuario.discente_id).where(Usuario.discente_id.in_(ids_alunos))).all()) if ids_alunos else set()
    c = request.state.usuario
    if c and not c.gestor:  # professor: o caso-base e as próprias cópias
        casos = [k for k in casos if k.docente_id is None or k.docente_id == c.docente_id]
    return render(request, "duplas/tela.html", t=t, duplas=duplas, sem_dupla=sem_dupla, casos=casos,
                  contas=contas, status=status_turma(db, tid), altera=bool(c and c.altera_turma(tid)),
                  caso_padrao=_caso_padrao(db, t, duplas), total_ativos=len(_ativos(t)),
                  geradas=sum(1 for d in duplas if d.empresa), codigos=codigos_turma(db, tid),
                  progresso=progresso_turma(db, tid), url_aluno=str(request.base_url).rstrip("/") + "/aluno", menu="duplas")


@router.post("/turmas/{tid}/duplas")
async def formar(request: Request, tid: int, db: Session = Depends(get_db)):
    t = db.get(Turma, tid)
    form = await request.form()
    ids = [int(x) for x in form.getlist("discente_id") if str(x).isdigit()]
    d, erro = _criar(db, t, ids, txt(form, "nome"))
    if erro:
        return voltar(_url(tid), erro=erro)
    db.commit()
    aviso = "" if len(ids) == 2 else f" (atenção: {len(ids)} integrante{'s' if len(ids) > 1 else ''})"
    return voltar(_url(tid, f"d{d.id}"), f"{d.rotulo} formada{aviso}.")


_SEP = re.compile(r"\s*(?:;|,|/|\t|\+|\s+e\s+|\s+-\s+)\s*", re.I)


def _localizar(token: str, ativos: list[Matricula]) -> tuple[int | None, str | None]:
    token = token.strip()
    so_num = re.sub(r"\D", "", token)
    if so_num and len(so_num) >= 5:
        for m in ativos:
            if m.discente.matricula == so_num:
                return m.discente_id, None
        return None, f"matrícula {so_num} não encontrada entre os ativos"
    alvo = normalizar(token)
    if not alvo:
        return None, None
    achados = [m for m in ativos if normalizar(m.discente.nome) == alvo] or \
              [m for m in ativos if normalizar(m.discente.nome).startswith(alvo)] or \
              [m for m in ativos if alvo in normalizar(m.discente.nome)]
    if len(achados) == 1:
        return achados[0].discente_id, None
    if not achados:
        return None, f"“{token}” não encontrado"
    return None, f"“{token}” é ambíguo ({len(achados)} discentes)"


@router.post("/turmas/{tid}/duplas/lote")
async def lote(request: Request, tid: int, db: Session = Depends(get_db)):
    """Uma dupla por linha: matrículas ou nomes separados por ; , / + tab ou ' e '."""
    t = db.get(Turma, tid)
    form = await request.form()
    ativos = _ativos(t)
    criadas, problemas = 0, []
    for n, linha in enumerate((form.get("lista") or "").splitlines(), 1):
        if not linha.strip():
            continue
        ids, erros = [], []
        for tok in [x for x in _SEP.split(linha) if x and x.strip()]:
            i, e = _localizar(tok, ativos)
            if i:
                ids.append(i)
            elif e:
                erros.append(e)
        if erros:
            problemas.append(f"linha {n}: " + "; ".join(erros))
            continue
        d, erro = _criar(db, t, ids)
        if erro:
            problemas.append(f"linha {n}: {erro}")
        else:
            criadas += 1
    db.commit()
    msg = f"{criadas} dupla(s) formada(s)." if criadas else None
    return voltar(_url(tid), msg, " | ".join(problemas) if problemas else None)


@router.post("/duplas/{id}/editar")
async def editar(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    form = await request.form()
    d.nome, d.observacao = txt(form, "nome"), txt(form, "observacao")
    db.commit()
    return voltar(_url(d.turma_id, f"d{d.id}"), "Dupla atualizada.")


@router.post("/duplas/{id}/membros")
async def incluir_membro(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    did = inteiro(await request.form(), "discente_id")
    if not did:
        return voltar(_url(d.turma_id, f"d{d.id}"), erro="Selecione o discente.")
    if len(d.membros) >= MAX_MEMBROS:
        return voltar(_url(d.turma_id, f"d{d.id}"), erro=f"Máximo de {MAX_MEMBROS} integrantes.")
    if did in _em_dupla(db, d.turma_id) or did not in {m.discente_id for m in _ativos(d.turma)}:
        return voltar(_url(d.turma_id, f"d{d.id}"), erro="Discente indisponível (já em dupla ou não ativo).")
    d.membros.append(DuplaMembro(turma_id=d.turma_id, discente_id=did))
    db.commit()
    return voltar(_url(d.turma_id, f"d{d.id}"), "Integrante incluído.")


@router.post("/duplas/{id}/membros/{mid}/remover")
def remover_membro(id: int, mid: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    m = db.get(DuplaMembro, mid)
    if m and m.dupla_id == d.id:
        d.membros.remove(m)
        if not d.membros:
            tid = d.turma_id
            db.delete(d)
            db.commit()
            return voltar(_url(tid), "Integrante removido; a dupla ficou vazia e foi desfeita.")
        db.commit()
    return voltar(_url(d.turma_id, f"d{d.id}"), "Integrante removido.")


@router.post("/duplas/{id}/excluir")
def desfazer(id: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    tid, rot = d.turma_id, d.rotulo
    db.delete(d)
    db.commit()
    return voltar(_url(tid), f"{rot} desfeita; integrantes voltaram para a lista sem dupla.")


# ------------------------------------------------------------------ geração
def _gerar_para(db: Session, d: Dupla, caso: Caso, semente: int | None = None) -> None:
    e = d.empresa
    if semente is None:
        semente = e.semente if e else nova_semente()
    valores = gerar(caso, semente, d.rotulo, d.numero)
    valores["integrantes"] = [{"matricula": m.discente.matricula, "nome": m.discente.nome} for m in d.membros]
    if e:
        e.caso_id, e.semente, e.valores = caso.id, semente, valores
    else:
        d.empresa = EmpresaGerada(caso_id=caso.id, semente=semente, valores=valores)


@router.post("/turmas/{tid}/duplas/gerar")
async def gerar_todas(request: Request, tid: int, db: Session = Depends(get_db)):
    form = await request.form()
    caso = db.get(Caso, inteiro(form, "caso_id") or 0)
    if not caso:
        return voltar(_url(tid, "gerar"), erro="Escolha o caso da empresa.")
    modo = form.get("modo") or "faltantes"
    n = 0
    for d in _duplas(db, tid):
        if modo == "faltantes" and d.empresa:
            continue
        semente = nova_semente() if modo == "novas" else None
        _gerar_para(db, d, caso, semente)
        n += 1
    db.commit()
    if not n:
        return voltar(_url(tid, "gerar"), "Nenhuma dupla pendente: todas já têm empresa gerada.")
    return voltar(_url(tid, "gerar"), f"Empresa gerada para {n} dupla(s) a partir de “{caso.nome}”.")


@router.get("/duplas/{id}/empresa")
def ver_empresa(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    if not d or not d.empresa:
        return voltar(_url(d.turma_id) if d else "/disciplinas", erro="Empresa ainda não gerada para esta dupla.")
    v = d.empresa.valores
    grupos: dict[tuple[str, str], list] = {}
    for p in v.get("parametros", []):
        grupos.setdefault((p["escopo"], p["ref"]), []).append(p)
    caso = d.empresa.caso
    refs = {}
    if caso:
        refs.update({("contrato", c.codigo): f"{c.codigo} · {c.tipo}" for c in caso.contratos})
        refs.update({("evento", e.codigo): f"{e.codigo} · {e.data.strftime('%d/%m') if e.data else ''} · {e.descricao}"
                     for e in caso.eventos})
    return render(request, "duplas/empresa.html", d=d, v=v, grupos=grupos, refs=refs, menu="duplas")


@router.post("/duplas/{id}/empresa/sortear")
async def sortear_novamente(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    form = await request.form()
    caso = db.get(Caso, inteiro(form, "caso_id") or (d.empresa.caso_id if d.empresa else 0) or 0)
    if not caso:
        return voltar(_url(d.turma_id), erro="Caso da empresa não encontrado.")
    manter = form.get("manter") == "1"
    _gerar_para(db, d, caso, None if manter else nova_semente())
    db.commit()
    texto = "Empresa recalculada com a mesma semente." if manter else "Novo sorteio realizado."
    return voltar(f"/duplas/{id}/empresa", texto)


@router.post("/duplas/{id}/empresa/excluir")
def excluir_empresa(id: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    if d.empresa:
        db.delete(d.empresa)
        db.commit()
    return voltar(_url(d.turma_id, f"d{d.id}"), "Empresa da dupla excluída.")


@router.get("/duplas/{id}/empresa.json")
def exportar_empresa(id: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    corpo = json.dumps(d.empresa.valores if d and d.empresa else {}, ensure_ascii=False, indent=2)
    nome = f"empresa-dupla-{d.numero:02d}.json" if d else "empresa.json"
    return Response(corpo, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


def _nome_arquivo(d: Dupla) -> str:
    t = d.turma
    return f"Orientacao {t.disciplina.codigo} {t.codigo} {t.periodo} - Dupla {d.numero:02d}.docx".replace("/", "-")


def _docx(d: Dupla) -> bytes:
    from ..orientacao import gerar_docx
    rotulo = f"Turma {d.turma.codigo} · {d.rotulo}"
    conteudo, _avisos = gerar_docx(d.empresa.valores, rotulo)
    return conteudo


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.get("/duplas/{id}/orientacao.docx")
def orientacao(id: int, db: Session = Depends(get_db)):
    d = db.get(Dupla, id)
    if not d or not d.empresa:
        return voltar(_url(d.turma_id) if d else "/duplas", erro="Gere a empresa da dupla antes do documento de orientação.")
    return Response(_docx(d), media_type=DOCX,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(_nome_arquivo(d))}"})


@router.get("/turmas/{tid}/duplas/orientacoes.zip")
def orientacoes_zip(tid: int, db: Session = Depends(get_db)):
    t = db.get(Turma, tid)
    duplas = [d for d in _duplas(db, tid) if d.empresa]
    if not duplas:
        return voltar(_url(tid, "gerar"), erro="Nenhuma dupla com empresa gerada.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for d in duplas:
            z.writestr(_nome_arquivo(d), _docx(d))
    nome = f"Orientacoes {t.disciplina.codigo} {t.codigo} {t.periodo}.zip".replace("/", "-")
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}"})


@router.get("/turmas/{tid}/duplas.csv")
def exportar_csv(tid: int, db: Session = Depends(get_db)):
    t = db.get(Turma, tid)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Dupla", "Nome", "Matrícula", "Discente", "E-mail", "Empresa", "Semente", "Produção total",
                "Compras de insumos (R$)", "Folha fev (R$)"])
    for d in _duplas(db, tid):
        r = (d.empresa.valores.get("resumo", {}) if d.empresa else {})
        emp = d.empresa.valores.get("empresa", {}).get("nome") if d.empresa else ""
        for m in d.membros:
            w.writerow([f"{d.numero:02d}", d.nome or "", m.discente.matricula, m.discente.nome, m.discente.email or "",
                        emp, d.empresa.semente if d.empresa else "", r.get("producao_total", ""),
                        str(r.get("total_compras_insumos", "")).replace(".", ","),
                        str(r.get("folha_fev", "")).replace(".", ",")])
    nome = f"duplas-{t.disciplina.codigo}-{t.codigo}-{t.periodo}.csv".replace("/", "-")
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})

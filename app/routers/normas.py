"""Etapa 6 · Base normativa do tutor: consulta, teste de busca e edição pelo professor."""
from __future__ import annotations

import re
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..main import render, voltar
from ..normas import Norma, buscar, todas

router = APIRouter()
CAMPOS = ("codigo", "titulo", "fonte", "texto", "palavras", "eventos")


@router.get("/normas")
def lista(request: Request, q: str = "", evento: str = "", db: Session = Depends(get_db)):
    normas = todas(db)
    resultado = buscar(normas, q, evento or None, k=3) if (q or evento) else None  # mesmo k do tutor
    return render(request, "normas/lista.html", normas=normas, q=q, evento=evento.upper(), resultado=resultado,
                  ativas=sum(1 for n in normas if n.ativa), menu="normas")


def _form(n: Norma | None, form) -> str | None:
    dados = {c: (form.get(c) or "").strip() for c in CAMPOS}
    dados["codigo"] = dados["codigo"].upper()
    dados["eventos"] = ",".join(e.strip().upper() for e in re.split(r"[,; ]+", dados["eventos"]) if e.strip())
    if not dados["codigo"] or not dados["titulo"] or not dados["fonte"] or not dados["texto"]:
        return "Preencha código, título, fonte e texto."
    if len(dados["texto"]) > 1500:
        return "Texto longo demais (máximo 1.500 caracteres): o tutor usa fichas curtas."
    for c, v in dados.items():
        setattr(n, c, v)
    n.ativa = form.get("ativa") == "on"
    n.atualizado_em = datetime.now()
    return None


@router.get("/normas/nova")
def nova(request: Request):
    return render(request, "normas/form.html", n=None, menu="normas")


@router.post("/normas/nova")
async def criar(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    n = Norma(origem="professor")
    erro = _form(n, form)
    if not erro and db.scalar(select(Norma).where(Norma.codigo == n.codigo)):
        erro = "Já existe uma ficha com esse código."
    if erro:
        return render(request, "normas/form.html", n=n, erro=erro, menu="normas")
    db.add(n)
    db.commit()
    return voltar(f"/normas#n{n.id}", "Ficha incluída na base normativa.")


@router.get("/normas/{id}/editar")
def editar(request: Request, id: int, db: Session = Depends(get_db)):
    return render(request, "normas/form.html", n=db.get(Norma, id), menu="normas")


@router.post("/normas/{id}/editar")
async def salvar(request: Request, id: int, db: Session = Depends(get_db)):
    n = db.get(Norma, id)
    form = await request.form()
    codigo_antes = n.codigo
    erro = _form(n, form)
    if not erro and n.codigo != codigo_antes and db.scalar(select(Norma).where(Norma.codigo == n.codigo)):
        erro = "Já existe uma ficha com esse código."
    if erro:
        db.rollback()
        return render(request, "normas/form.html", n=n, erro=erro, menu="normas")
    if n.origem == "padrao":
        n.origem = "editada"
    db.commit()
    return voltar(f"/normas#n{n.id}", "Ficha atualizada.")


@router.post("/normas/{id}/ativa")
def alternar(id: int, db: Session = Depends(get_db)):
    n = db.get(Norma, id)
    n.ativa = not n.ativa
    db.commit()
    return voltar(f"/normas#n{id}", "Ficha reativada." if n.ativa else "Ficha desativada: o tutor deixa de consultá-la.")

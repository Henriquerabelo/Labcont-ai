from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..main import render, voltar
from ..models import Disciplina
from .comum import inteiro, txt

router = APIRouter(prefix="/disciplinas")


@router.get("")
def listar(request: Request, q: str = "", db: Session = Depends(get_db)):
    stmt = select(Disciplina).order_by(Disciplina.nome)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Disciplina.codigo.ilike(like), Disciplina.nome.ilike(like)))
    return render(request, "disciplinas/lista.html", itens=db.scalars(stmt).all(), q=q, menu="disciplinas")


@router.get("/nova")
def nova(request: Request):
    return render(request, "disciplinas/form.html", d=None, menu="disciplinas")


def _preencher(d: Disciplina, form) -> str | None:
    d.codigo = txt(form, "codigo", True) or ""
    d.nome = txt(form, "nome", True) or ""
    d.nivel = txt(form, "nivel", True)
    d.carga_horaria = inteiro(form, "carga_horaria")
    d.departamento = txt(form, "departamento")
    d.observacoes = txt(form, "observacoes")
    if not d.codigo or not d.nome:
        return "Código e nome são obrigatórios."
    return None


@router.post("/nova")
async def criar(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    d = Disciplina()
    erro = _preencher(d, form)
    if not erro:
        db.add(d)
        try:
            db.commit()
            return voltar(f"/disciplinas/{d.id}", "Disciplina cadastrada.")
        except IntegrityError:
            db.rollback()
            erro = f"Já existe uma disciplina com o código {d.codigo}."
    return render(request, "disciplinas/form.html", d=d, erro=erro, menu="disciplinas")


@router.get("/{id}")
def detalhe(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Disciplina, id)
    if not d:
        return voltar("/disciplinas", erro="Disciplina não encontrada.")
    return render(request, "disciplinas/detalhe.html", d=d, menu="disciplinas")


@router.get("/{id}/editar")
def editar(request: Request, id: int, db: Session = Depends(get_db)):
    return render(request, "disciplinas/form.html", d=db.get(Disciplina, id), menu="disciplinas")


@router.post("/{id}/editar")
async def salvar(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Disciplina, id)
    form = await request.form()
    erro = _preencher(d, form)
    if not erro:
        try:
            db.commit()
            return voltar(f"/disciplinas/{id}", "Alterações salvas.")
        except IntegrityError:
            db.rollback()
            erro = "Já existe outra disciplina com esse código."
    return render(request, "disciplinas/form.html", d=d, erro=erro, menu="disciplinas")


@router.post("/{id}/excluir")
def excluir(id: int, db: Session = Depends(get_db)):
    d = db.get(Disciplina, id)
    if d:
        db.delete(d)
        db.commit()
    return voltar("/disciplinas", "Disciplina excluída, com suas turmas e vínculos.")

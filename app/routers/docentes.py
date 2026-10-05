from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..main import render, voltar
from ..models import Docente, normalizar
from .comum import txt

router = APIRouter(prefix="/docentes")


@router.get("")
def listar(request: Request, q: str = "", db: Session = Depends(get_db)):
    stmt = select(Docente).order_by(Docente.nome)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Docente.nome.ilike(like), Docente.email.ilike(like), Docente.nome_normalizado.ilike(f"%{normalizar(q)}%")))
    return render(request, "docentes/lista.html", itens=db.scalars(stmt).all(), q=q, menu="docentes")


@router.get("/novo")
def novo(request: Request):
    return render(request, "docentes/form.html", d=None, menu="docentes")


def _preencher(d: Docente, form) -> str | None:
    d.nome = txt(form, "nome", True) or ""
    d.nome_normalizado = normalizar(d.nome)
    d.email = txt(form, "email")
    d.siape = txt(form, "siape")
    d.departamento = txt(form, "departamento", True)
    d.formacao = txt(form, "formacao", True)
    d.ativo = form.get("ativo") == "on"
    return None if d.nome else "O nome é obrigatório."


@router.post("/novo")
async def criar(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    d = Docente()
    erro = _preencher(d, form)
    if not erro:
        db.add(d)
        try:
            db.commit()
            return voltar(f"/docentes/{d.id}", "Docente cadastrado.")
        except IntegrityError:
            db.rollback()
            erro = "Já existe um docente com esse nome."
    return render(request, "docentes/form.html", d=d, erro=erro, menu="docentes")


@router.get("/{id}")
def detalhe(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Docente, id)
    if not d:
        return voltar("/docentes", erro="Docente não encontrado.")
    return render(request, "docentes/detalhe.html", d=d, menu="docentes")


@router.get("/{id}/editar")
def editar(request: Request, id: int, db: Session = Depends(get_db)):
    return render(request, "docentes/form.html", d=db.get(Docente, id), menu="docentes")


@router.post("/{id}/editar")
async def salvar(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Docente, id)
    erro = _preencher(d, await request.form())
    if not erro:
        try:
            db.commit()
            return voltar(f"/docentes/{id}", "Alterações salvas.")
        except IntegrityError:
            db.rollback()
            erro = "Já existe outro docente com esse nome."
    return render(request, "docentes/form.html", d=d, erro=erro, menu="docentes")


@router.post("/{id}/excluir")
def excluir(id: int, db: Session = Depends(get_db)):
    d = db.get(Docente, id)
    if d:
        db.delete(d)
        db.commit()
    return voltar("/docentes", "Docente excluído.")

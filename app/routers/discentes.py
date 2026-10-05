from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..main import render, voltar
from ..models import Discente, Matricula, Turma, Disciplina
from .comum import txt

router = APIRouter(prefix="/discentes")
POR_PAGINA = 50


@router.get("")
def listar(request: Request, q: str = "", turno: str = "", pagina: int = 1, db: Session = Depends(get_db)):
    stmt = select(Discente)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Discente.nome.ilike(like), Discente.matricula.ilike(like), Discente.email.ilike(like)))
    if turno:
        stmt = stmt.where(Discente.turno == turno)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    itens = db.scalars(stmt.order_by(Discente.nome).offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA)).all()
    paginas = max(1, -(-total // POR_PAGINA))
    return render(request, "discentes/lista.html", itens=itens, q=q, turno=turno, total=total,
                  pagina=pagina, paginas=paginas, menu="discentes")


@router.get("/novo")
def novo(request: Request):
    return render(request, "discentes/form.html", d=None, menu="discentes")


def _preencher(d: Discente, form) -> str | None:
    d.matricula = (txt(form, "matricula") or "").replace(" ", "")
    d.nome = txt(form, "nome", True) or ""
    d.email = txt(form, "email")
    d.curso = txt(form, "curso", True)
    d.turno = txt(form, "turno", True)
    d.ativo = form.get("ativo") == "on"
    if not d.matricula or not d.nome:
        return "Matrícula e nome são obrigatórios."
    if not d.matricula.isdigit():
        return "A matrícula deve conter apenas números."
    return None


@router.post("/novo")
async def criar(request: Request, db: Session = Depends(get_db)):
    d = Discente()
    erro = _preencher(d, await request.form())
    if not erro:
        db.add(d)
        try:
            db.commit()
            return voltar(f"/discentes/{d.id}", "Discente cadastrado.")
        except IntegrityError:
            db.rollback()
            erro = f"A matrícula {d.matricula} já está cadastrada."
    return render(request, "discentes/form.html", d=d, erro=erro, menu="discentes")


@router.get("/{id}")
def detalhe(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Discente, id)
    if not d:
        return voltar("/discentes", erro="Discente não encontrado.")
    ja = {m.turma_id for m in d.matriculas}
    turmas = [t for t in db.scalars(select(Turma).join(Disciplina).order_by(Turma.periodo.desc(), Disciplina.codigo, Turma.codigo)).all() if t.id not in ja]
    return render(request, "discentes/detalhe.html", d=d, turmas=turmas, menu="discentes")


@router.get("/{id}/editar")
def editar(request: Request, id: int, db: Session = Depends(get_db)):
    return render(request, "discentes/form.html", d=db.get(Discente, id), menu="discentes")


@router.post("/{id}/editar")
async def salvar(request: Request, id: int, db: Session = Depends(get_db)):
    d = db.get(Discente, id)
    erro = _preencher(d, await request.form())
    if not erro:
        try:
            db.commit()
            return voltar(f"/discentes/{id}", "Alterações salvas.")
        except IntegrityError:
            db.rollback()
            erro = "Essa matrícula já pertence a outro discente."
    return render(request, "discentes/form.html", d=d, erro=erro, menu="discentes")


@router.post("/{id}/excluir")
def excluir(id: int, db: Session = Depends(get_db)):
    d = db.get(Discente, id)
    if d:
        db.delete(d)
        db.commit()
    return voltar("/discentes", "Discente excluído.")


@router.post("/{id}/matricular")
async def matricular(request: Request, id: int, db: Session = Depends(get_db)):
    form = await request.form()
    turma_id = int(form.get("turma_id") or 0)
    if turma_id and not db.scalar(select(Matricula).where(Matricula.turma_id == turma_id, Matricula.discente_id == id)):
        db.add(Matricula(turma_id=turma_id, discente_id=id))
        db.commit()
        return voltar(f"/discentes/{id}", "Discente incluído na turma.")
    return voltar(f"/discentes/{id}", erro="Selecione uma turma válida.")

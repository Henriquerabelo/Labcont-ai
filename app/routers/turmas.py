from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..main import render, voltar
from ..models import Disciplina, Discente, Docente, Matricula, Turma, TurmaDocente
from .comum import data, inteiro, txt

router = APIRouter(prefix="/turmas")
SITUACOES_MATRICULA = ["ATIVO", "TRANCADO", "CANCELADO", "DESISTENTE"]


def _disciplinas(db):
    return db.scalars(select(Disciplina).order_by(Disciplina.codigo)).all()


@router.get("/nova")
def nova(request: Request, disciplina_id: int | None = None, db: Session = Depends(get_db)):
    return render(request, "turmas/form.html", t=None, disciplina_id=disciplina_id,
                  disciplinas=_disciplinas(db), menu="disciplinas")


def _preencher(t: Turma, form) -> str | None:
    t.disciplina_id = inteiro(form, "disciplina_id")
    t.periodo = txt(form, "periodo") or ""
    t.codigo = txt(form, "codigo", True) or ""
    t.tipo = txt(form, "tipo", True)
    t.situacao = txt(form, "situacao", True)
    t.horario = txt(form, "horario", True)
    t.data_inicio = data(form, "data_inicio")
    t.data_fim = data(form, "data_fim")
    t.local = txt(form, "local")
    t.capacidade = inteiro(form, "capacidade")
    if not (t.disciplina_id and t.periodo and t.codigo):
        return "Disciplina, período e código da turma são obrigatórios."
    return None


@router.post("/nova")
async def criar(request: Request, db: Session = Depends(get_db)):
    t = Turma()
    erro = _preencher(t, await request.form())
    if not erro:
        db.add(t)
        try:
            db.commit()
            return voltar(f"/turmas/{t.id}", "Turma cadastrada.")
        except IntegrityError:
            db.rollback()
            erro = "Já existe essa turma para a disciplina e o período informados."
    return render(request, "turmas/form.html", t=t, disciplina_id=t.disciplina_id,
                  disciplinas=_disciplinas(db), erro=erro, menu="disciplinas")


@router.get("/{id}")
def detalhe(request: Request, id: int, db: Session = Depends(get_db)):
    t = db.get(Turma, id)
    if not t:
        return voltar("/disciplinas", erro="Turma não encontrada.")
    ja = {v.docente_id for v in t.docentes}
    docentes = [d for d in db.scalars(select(Docente).order_by(Docente.nome)).all() if d.id not in ja]
    matriculas = sorted(t.matriculas, key=lambda m: m.discente.nome)
    from ..acesso import status_turma
    return render(request, "turmas/detalhe.html", t=t, docentes=docentes, matriculas=matriculas, status=status_turma(db, id),
                  situacoes=SITUACOES_MATRICULA, menu="disciplinas")


@router.get("/{id}/editar")
def editar(request: Request, id: int, db: Session = Depends(get_db)):
    t = db.get(Turma, id)
    return render(request, "turmas/form.html", t=t, disciplina_id=t.disciplina_id,
                  disciplinas=_disciplinas(db), menu="disciplinas")


@router.post("/{id}/editar")
async def salvar(request: Request, id: int, db: Session = Depends(get_db)):
    t = db.get(Turma, id)
    erro = _preencher(t, await request.form())
    if not erro:
        try:
            db.commit()
            return voltar(f"/turmas/{id}", "Alterações salvas.")
        except IntegrityError:
            db.rollback()
            erro = "Já existe essa turma para a disciplina e o período informados."
    return render(request, "turmas/form.html", t=t, disciplina_id=t.disciplina_id,
                  disciplinas=_disciplinas(db), erro=erro, menu="disciplinas")


@router.post("/{id}/excluir")
def excluir(id: int, db: Session = Depends(get_db)):
    t = db.get(Turma, id)
    disc = t.disciplina_id if t else None
    if t:
        db.delete(t)
        db.commit()
    return voltar(f"/disciplinas/{disc}" if disc else "/disciplinas", "Turma excluída.")


# ---- docentes da turma ----------------------------------------------------
@router.post("/{id}/docentes")
async def add_docente(request: Request, id: int, db: Session = Depends(get_db)):
    form = await request.form()
    docente_id = inteiro(form, "docente_id")
    if docente_id:
        db.add(TurmaDocente(turma_id=id, docente_id=docente_id, carga_horaria=inteiro(form, "carga_horaria")))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        return voltar(f"/turmas/{id}", "Docente vinculado à turma.")
    return voltar(f"/turmas/{id}", erro="Selecione um docente.")


@router.post("/{id}/docentes/{vid}/remover")
def rem_docente(id: int, vid: int, db: Session = Depends(get_db)):
    v = db.get(TurmaDocente, vid)
    if v:
        db.delete(v)
        db.commit()
    return voltar(f"/turmas/{id}", "Docente removido da turma.")


# ---- discentes da turma ---------------------------------------------------
@router.post("/{id}/discentes")
async def add_discente(request: Request, id: int, db: Session = Depends(get_db)):
    """Inclui por matrícula. Se a matrícula não existir e houver nome, cria o discente."""
    form = await request.form()
    matricula = (txt(form, "matricula") or "").replace(" ", "")
    nome = txt(form, "nome", True)
    if not matricula.isdigit():
        return voltar(f"/turmas/{id}", erro="Informe uma matrícula numérica.")
    al = db.scalar(select(Discente).where(Discente.matricula == matricula))
    if not al:
        if not nome:
            return voltar(f"/turmas/{id}", erro=f"Matrícula {matricula} não cadastrada. Informe também o nome para criar o discente.")
        al = Discente(matricula=matricula, nome=nome, email=txt(form, "email"),
                      curso=txt(form, "curso", True), turno=txt(form, "turno", True))
        db.add(al)
        db.flush()
    if db.scalar(select(Matricula).where(Matricula.turma_id == id, Matricula.discente_id == al.id)):
        return voltar(f"/turmas/{id}", erro=f"{al.nome} já está nesta turma.")
    db.add(Matricula(turma_id=id, discente_id=al.id))
    db.commit()
    return voltar(f"/turmas/{id}", f"{al.nome} incluído(a) na turma.")


@router.post("/{id}/matriculas/{mid}/situacao")
async def situacao(request: Request, id: int, mid: int, db: Session = Depends(get_db)):
    form = await request.form()
    m = db.get(Matricula, mid)
    if m and form.get("situacao") in SITUACOES_MATRICULA:
        m.situacao = form["situacao"]
        db.commit()
    return voltar(f"/turmas/{id}", "Situação atualizada.")


@router.post("/{id}/matriculas/{mid}/remover")
def rem_matricula(id: int, mid: int, db: Session = Depends(get_db)):
    m = db.get(Matricula, mid)
    if m:
        db.delete(m)
        db.commit()
    return voltar(f"/turmas/{id}", "Discente removido da turma.")

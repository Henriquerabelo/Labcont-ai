"""Regras de gravação: aplica no banco o resultado lido de um PDF do SIGAA.

A importação é idempotente: rodar o mesmo PDF duas vezes não duplica nada.
Chaves usadas para localizar registros existentes:
  Disciplina -> código | Turma -> disciplina + período + código
  Docente -> nome normalizado | Discente -> matrícula
"""
from __future__ import annotations

from collections import Counter
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Disciplina, Discente, Docente, Matricula, Turma, TurmaDocente, normalizar


def _data(v: str | None) -> date | None:
    return date.fromisoformat(v) if v else None


def _set(obj, campo: str, valor, cont: Counter, chave: str) -> None:
    """Atualiza o campo apenas quando o PDF traz valor e ele é diferente."""
    if valor in (None, ""):
        return
    if getattr(obj, campo) != valor:
        setattr(obj, campo, valor)
        cont[chave] += 1


def obter_docente(db: Session, nome: str) -> Docente | None:
    return db.scalar(select(Docente).where(Docente.nome_normalizado == normalizar(nome)))


def aplicar_importacao(db: Session, dados: dict) -> dict:
    cont: Counter = Counter()
    novos: Counter = Counter()

    for t in dados["turmas"]:
        disc = db.scalar(select(Disciplina).where(Disciplina.codigo == t["disciplina_codigo"]))
        if not disc:
            disc = Disciplina(codigo=t["disciplina_codigo"], nome=t["disciplina_nome"])
            db.add(disc)
            db.flush()
            novos["disciplinas"] += 1
        else:
            _set(disc, "nome", t["disciplina_nome"], cont, "disciplinas")

        turma = db.scalar(
            select(Turma).where(
                Turma.disciplina_id == disc.id, Turma.periodo == t["periodo"], Turma.codigo == t["codigo"]
            )
        )
        if not turma:
            turma = Turma(disciplina_id=disc.id, periodo=t["periodo"], codigo=t["codigo"])
            db.add(turma)
            db.flush()
            novos["turmas"] += 1
        for campo, valor in (
            ("tipo", t.get("tipo")),
            ("situacao", t.get("situacao")),
            ("horario", t.get("horario")),
            ("data_inicio", _data(t.get("data_inicio"))),
            ("data_fim", _data(t.get("data_fim"))),
            ("local", t.get("local")),
            ("capacidade", t.get("capacidade")),
            ("matriculados_sigaa", t.get("matriculados")),
        ):
            _set(turma, campo, valor, cont, "turmas")

        for d in t.get("docentes", []):
            doc = obter_docente(db, d["nome"])
            if not doc:
                doc = Docente(nome=d["nome"], nome_normalizado=normalizar(d["nome"]))
                db.add(doc)
                db.flush()
                novos["docentes"] += 1
            for campo in ("email", "departamento", "formacao"):
                _set(doc, campo, d.get(campo), cont, "docentes")
            vinc = db.scalar(
                select(TurmaDocente).where(TurmaDocente.turma_id == turma.id, TurmaDocente.docente_id == doc.id)
            )
            if not vinc:
                db.add(TurmaDocente(turma_id=turma.id, docente_id=doc.id, carga_horaria=d.get("carga_horaria")))
                novos["vinculos_docentes"] += 1
            elif d.get("carga_horaria"):
                vinc.carga_horaria = d["carga_horaria"]

        for a in t.get("discentes", []):
            if not a.get("matricula"):
                continue
            al = db.scalar(select(Discente).where(Discente.matricula == a["matricula"]))
            if not al:
                al = Discente(matricula=a["matricula"], nome=a["nome"])
                db.add(al)
                db.flush()
                novos["discentes"] += 1
            for campo in ("nome", "email", "curso", "turno"):
                _set(al, campo, a.get(campo), cont, "discentes")
            mat = db.scalar(select(Matricula).where(Matricula.turma_id == turma.id, Matricula.discente_id == al.id))
            if not mat:
                db.add(Matricula(turma_id=turma.id, discente_id=al.id, situacao=a.get("situacao") or "ATIVO"))
                novos["matriculas"] += 1
            elif a.get("situacao") and mat.situacao != a["situacao"]:
                mat.situacao = a["situacao"]
                cont["matriculas"] += 1

    db.flush()
    return {"novos": dict(novos), "atualizados": dict(cont)}


def resumo_previa(dados: dict) -> dict:
    turmas = dados["turmas"]
    return {
        "disciplinas": len({t["disciplina_codigo"] for t in turmas}),
        "turmas": len(turmas),
        "docentes": len({normalizar(d["nome"]) for t in turmas for d in t.get("docentes", [])}),
        "discentes": sum(len(t.get("discentes", [])) for t in turmas),
    }

"""Modelo de dados da Etapa 1: disciplinas, turmas, docentes e discentes."""
from __future__ import annotations

import unicodedata
from datetime import date, datetime

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def normalizar(texto: str | None) -> str:
    """Remove acentos, espaços extras e caixa para comparar nomes."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.upper().split())


class Carimbo:
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Disciplina(Carimbo, Base):
    __tablename__ = "disciplinas"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(200))
    nivel: Mapped[str | None] = mapped_column(String(40), default="GRADUAÇÃO")
    carga_horaria: Mapped[int | None] = mapped_column(Integer)
    departamento: Mapped[str | None] = mapped_column(String(160))
    observacoes: Mapped[str | None] = mapped_column(Text)

    turmas: Mapped[list[Turma]] = relationship(
        back_populates="disciplina", cascade="all, delete-orphan", order_by="Turma.periodo.desc(), Turma.codigo"
    )


class Turma(Carimbo, Base):
    __tablename__ = "turmas"
    __table_args__ = (UniqueConstraint("disciplina_id", "periodo", "codigo", name="uq_turma"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    disciplina_id: Mapped[int] = mapped_column(ForeignKey("disciplinas.id", ondelete="CASCADE"), index=True)
    periodo: Mapped[str] = mapped_column(String(10), index=True)
    codigo: Mapped[str] = mapped_column(String(10))
    tipo: Mapped[str | None] = mapped_column(String(40))
    situacao: Mapped[str | None] = mapped_column(String(40))
    horario: Mapped[str | None] = mapped_column(String(160))
    data_inicio: Mapped[date | None] = mapped_column(Date)
    data_fim: Mapped[date | None] = mapped_column(Date)
    local: Mapped[str | None] = mapped_column(String(160))
    capacidade: Mapped[int | None] = mapped_column(Integer)
    matriculados_sigaa: Mapped[int | None] = mapped_column(Integer)

    disciplina: Mapped[Disciplina] = relationship(back_populates="turmas")
    docentes: Mapped[list[TurmaDocente]] = relationship(back_populates="turma", cascade="all, delete-orphan")
    matriculas: Mapped[list[Matricula]] = relationship(back_populates="turma", cascade="all, delete-orphan")

    @property
    def rotulo(self) -> str:
        return f"{self.disciplina.codigo} · Turma {self.codigo} · {self.periodo}"


class Docente(Carimbo, Base):
    __tablename__ = "docentes"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(160))
    nome_normalizado: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(160))
    siape: Mapped[str | None] = mapped_column(String(20))
    departamento: Mapped[str | None] = mapped_column(String(160))
    formacao: Mapped[str | None] = mapped_column(String(60))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    turmas: Mapped[list[TurmaDocente]] = relationship(back_populates="docente", cascade="all, delete-orphan")


class Discente(Carimbo, Base):
    __tablename__ = "discentes"
    id: Mapped[int] = mapped_column(primary_key=True)
    matricula: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(160), index=True)
    email: Mapped[str | None] = mapped_column(String(160))
    curso: Mapped[str | None] = mapped_column(String(120))
    turno: Mapped[str | None] = mapped_column(String(20))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    matriculas: Mapped[list[Matricula]] = relationship(back_populates="discente", cascade="all, delete-orphan")


class TurmaDocente(Base):
    __tablename__ = "turma_docentes"
    __table_args__ = (UniqueConstraint("turma_id", "docente_id", name="uq_turma_docente"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id", ondelete="CASCADE"))
    docente_id: Mapped[int] = mapped_column(ForeignKey("docentes.id", ondelete="CASCADE"))
    carga_horaria: Mapped[int | None] = mapped_column(Integer)

    turma: Mapped[Turma] = relationship(back_populates="docentes")
    docente: Mapped[Docente] = relationship(back_populates="turmas")


class Matricula(Base):
    __tablename__ = "matriculas"
    __table_args__ = (UniqueConstraint("turma_id", "discente_id", name="uq_matricula"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id", ondelete="CASCADE"))
    discente_id: Mapped[int] = mapped_column(ForeignKey("discentes.id", ondelete="CASCADE"))
    situacao: Mapped[str] = mapped_column(String(20), default="ATIVO")

    turma: Mapped[Turma] = relationship(back_populates="matriculas")
    discente: Mapped[Discente] = relationship(back_populates="matriculas")


class Importacao(Base):
    __tablename__ = "importacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    arquivo: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="PENDENTE")  # PENDENTE | CONCLUIDA | CANCELADA
    dados: Mapped[dict] = mapped_column(JSON)
    resumo: Mapped[dict | None] = mapped_column(JSON)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

"""Duplas de trabalho por turma e empresa gerada para cada dupla (Etapa 3).

A formação das duplas é voluntária: os discentes se organizam e o professor registra
as duplas no sistema. Depois, para cada dupla, o sistema gera uma empresa a partir de
um *Caso* (sorteio reproduzível dentro das faixas de cada parâmetro).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from . import models, models_caso  # noqa: F401  (Turma, Discente e Caso usados nas relações)


class Dupla(Base):
    __tablename__ = "duplas"
    __table_args__ = (UniqueConstraint("turma_id", "numero", name="uq_dupla_numero"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id", ondelete="CASCADE"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    nome: Mapped[str | None] = mapped_column(String(120))
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    turma = relationship("Turma")
    membros: Mapped[list[DuplaMembro]] = relationship(back_populates="dupla", cascade="all, delete-orphan",
                                                      order_by="DuplaMembro.id")
    empresa: Mapped[EmpresaGerada | None] = relationship(back_populates="dupla", cascade="all, delete-orphan",
                                                         uselist=False)

    @property
    def rotulo(self) -> str:
        return f"Dupla {self.numero:02d}" + (f" · {self.nome}" if self.nome else "")


class DuplaMembro(Base):
    """Um discente participa de no máximo uma dupla em cada turma."""
    __tablename__ = "dupla_membros"
    __table_args__ = (UniqueConstraint("turma_id", "discente_id", name="uq_membro_turma"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    dupla_id: Mapped[int] = mapped_column(ForeignKey("duplas.id", ondelete="CASCADE"), index=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id", ondelete="CASCADE"))
    discente_id: Mapped[int] = mapped_column(ForeignKey("discentes.id", ondelete="CASCADE"))

    dupla: Mapped[Dupla] = relationship(back_populates="membros")
    discente = relationship("Discente")


class EmpresaGerada(Base):
    """Valores sorteados e derivados da empresa de uma dupla. Mesma semente => mesmos valores."""
    __tablename__ = "empresas_geradas"
    id: Mapped[int] = mapped_column(primary_key=True)
    dupla_id: Mapped[int] = mapped_column(ForeignKey("duplas.id", ondelete="CASCADE"), unique=True)
    caso_id: Mapped[int | None] = mapped_column(ForeignKey("casos.id", ondelete="SET NULL"))
    semente: Mapped[int] = mapped_column(Integer)
    valores: Mapped[dict] = mapped_column(JSON, default=dict)
    gerado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    dupla: Mapped[Dupla] = relationship(back_populates="empresa")
    caso = relationship("Caso")

"""Escrituração feita pela dupla (Etapa 5) e acesso da dupla à área do aluno."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from . import models_dupla  # noqa: F401


class DuplaAcesso(Base):
    """Código de acesso da dupla (distribuído pelo professor). Tabela própria para não alterar 'duplas'."""
    __tablename__ = "dupla_acessos"
    id: Mapped[int] = mapped_column(primary_key=True)
    dupla_id: Mapped[int] = mapped_column(ForeignKey("duplas.id", ondelete="CASCADE"), unique=True)
    codigo: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime)

    dupla = relationship("Dupla")


class Lancamento(Base):
    __tablename__ = "esc_lancamentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    dupla_id: Mapped[int] = mapped_column(ForeignKey("duplas.id", ondelete="CASCADE"), index=True)
    evento: Mapped[str] = mapped_column(String(10), index=True)
    data: Mapped[date] = mapped_column(Date)
    historico: Mapped[str] = mapped_column(Text)
    autor: Mapped[str | None] = mapped_column(String(160))
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    partidas: Mapped[list[Partida]] = relationship(back_populates="lancamento", cascade="all, delete-orphan",
                                                    order_by="Partida.ordem")


class Partida(Base):
    __tablename__ = "esc_partidas"
    id: Mapped[int] = mapped_column(primary_key=True)
    lancamento_id: Mapped[int] = mapped_column(ForeignKey("esc_lancamentos.id", ondelete="CASCADE"), index=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    conta: Mapped[str] = mapped_column(String(30))
    natureza: Mapped[str] = mapped_column(String(1))  # D | C
    valor: Mapped[float] = mapped_column(Float)

    lancamento: Mapped[Lancamento] = relationship(back_populates="partidas")


class FechamentoMensal(Base):
    """Envio do mês pela dupla. Só depois do envio a dupla vê a correção; a escrituração do mês fica bloqueada.
    'resultado' guarda o retrato da correção no momento do envio (nota do mês)."""
    __tablename__ = "esc_fechamentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    dupla_id: Mapped[int] = mapped_column(ForeignKey("duplas.id", ondelete="CASCADE"), index=True)
    mes: Mapped[str] = mapped_column(String(7))  # 2026-01
    enviado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    enviado_por: Mapped[str | None] = mapped_column(String(20))
    resultado: Mapped[dict | None] = mapped_column(JSON)
    reaberto_em: Mapped[datetime | None] = mapped_column(DateTime)  # preenchido quando o professor reabre


def fechamento_ativo(db, dupla_id: int, mes: str = "2026-01") -> "FechamentoMensal | None":
    from sqlalchemy import select
    return db.scalar(select(FechamentoMensal).where(FechamentoMensal.dupla_id == dupla_id, FechamentoMensal.mes == mes,
                                                    FechamentoMensal.reaberto_em.is_(None)).order_by(FechamentoMensal.id.desc()))


class TutorMensagem(Base):
    """Conversa da dupla com o tutor (Etapa 6). Guardada para o professor acompanhar."""
    __tablename__ = "tutor_mensagens"
    id: Mapped[int] = mapped_column(primary_key=True)
    dupla_id: Mapped[int] = mapped_column(ForeignKey("duplas.id", ondelete="CASCADE"), index=True)
    evento: Mapped[str | None] = mapped_column(String(10), index=True)
    papel: Mapped[str] = mapped_column(String(10))  # aluno | tutor
    texto: Mapped[str] = mapped_column(Text)
    origem: Mapped[str | None] = mapped_column(String(20))  # ia | roteiro
    matricula: Mapped[str | None] = mapped_column(String(20))
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

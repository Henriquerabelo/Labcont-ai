"""Modelo de dados do caso da empresa (Etapa 2): estrutura parametrizável por professor.

Um *Caso* é uma versão editável da empresa-modelo (ex.: EH0012 2026.2). Cada professor
pode ter o seu caso — duplicado do caso-base — e alterar valores, faixas e regras sem
afetar os demais. A geração das empresas por dupla (próxima etapa) lerá estes dados.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

ESCOPOS = {
    "empresa": "Empresa", "socios": "Sócios", "contrato": "Contrato", "folha": "Folha",
    "producao": "Produção", "markup": "Mark-up", "evento": "Evento",
}


class Caso(Base):
    __tablename__ = "casos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(160))
    descricao: Mapped[str | None] = mapped_column(Text)
    docente_id: Mapped[int | None] = mapped_column(ForeignKey("docentes.id", ondelete="SET NULL"))
    origem_id: Mapped[int | None] = mapped_column(Integer)
    dados: Mapped[dict] = mapped_column(JSON, default=dict)  # empresa, saldos, imobilizado, vida útil, rateio, regras
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    docente = relationship("Docente")
    parametros: Mapped[list[Parametro]] = relationship(back_populates="caso", cascade="all, delete-orphan",
                                                       order_by="Parametro.ordem, Parametro.id")
    contratos: Mapped[list[Contrato]] = relationship(back_populates="caso", cascade="all, delete-orphan",
                                                     order_by="Contrato.codigo")
    socios: Mapped[list[Socio]] = relationship(cascade="all, delete-orphan", order_by="Socio.id")
    funcionarios: Mapped[list[Funcionario]] = relationship(cascade="all, delete-orphan",
                                                           order_by="Funcionario.ordem, Funcionario.id")
    itens: Mapped[list[Item]] = relationship(cascade="all, delete-orphan", order_by="Item.ordem, Item.id")
    ficha: Mapped[list[FichaTecnica]] = relationship(cascade="all, delete-orphan")
    eventos: Mapped[list[Evento]] = relationship(back_populates="caso", cascade="all, delete-orphan",
                                                 order_by="Evento.data, Evento.codigo")
    inconsistencias: Mapped[list[Inconsistencia]] = relationship(cascade="all, delete-orphan",
                                                                 order_by="Inconsistencia.id")

    def params(self, escopo: str, ref: str = "") -> list[Parametro]:
        return [p for p in self.parametros if p.escopo == escopo and (p.ref or "") == (ref or "")]


class Parametro(Base):
    """Valor de referência (base) e faixa de sorteio por dupla."""
    __tablename__ = "caso_parametros"
    id: Mapped[int] = mapped_column(primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), index=True)
    escopo: Mapped[str] = mapped_column(String(20))
    ref: Mapped[str | None] = mapped_column(String(20))
    nome: Mapped[str] = mapped_column(String(200))
    unidade: Mapped[str | None] = mapped_column(String(30))
    base: Mapped[str | None] = mapped_column(String(120))
    minimo: Mapped[float | None] = mapped_column(Float)
    maximo: Mapped[float | None] = mapped_column(Float)
    passo: Mapped[float | None] = mapped_column(Float)
    regra: Mapped[str | None] = mapped_column(Text)
    varia: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)

    caso: Mapped[Caso] = relationship(back_populates="parametros")


class Contrato(Base):
    __tablename__ = "caso_contratos"
    id: Mapped[int] = mapped_column(primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), index=True)
    codigo: Mapped[str] = mapped_column(String(10))
    tipo: Mapped[str] = mapped_column(String(160))
    parte: Mapped[str | None] = mapped_column(String(160))
    inicio: Mapped[date | None] = mapped_column(Date)
    descricao: Mapped[str | None] = mapped_column(Text)
    eventos: Mapped[str | None] = mapped_column(String(200))

    caso: Mapped[Caso] = relationship(back_populates="contratos")


class Socio(Base):
    __tablename__ = "caso_socios"
    id: Mapped[int] = mapped_column(primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(160))
    funcao: Mapped[str | None] = mapped_column(String(120))
    cotas: Mapped[int | None] = mapped_column(Integer)
    a_integralizar: Mapped[float | None] = mapped_column(Float)
    evento_integralizacao: Mapped[str | None] = mapped_column(String(10))
    pro_labore_jan: Mapped[float | None] = mapped_column(Float)
    pro_labore_fev: Mapped[float | None] = mapped_column(Float)
    dependentes: Mapped[str | None] = mapped_column(String(120))


class Funcionario(Base):
    __tablename__ = "caso_funcionarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), index=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    setor: Mapped[str] = mapped_column(String(80))
    nome: Mapped[str] = mapped_column(String(120))
    admissao: Mapped[str | None] = mapped_column(String(20))
    salario_jan: Mapped[float | None] = mapped_column(Float)
    he_jan: Mapped[float | None] = mapped_column(Float)
    comissao_jan: Mapped[float | None] = mapped_column(Float)
    dependentes_jan: Mapped[str | None] = mapped_column(String(80))
    salario_fev: Mapped[float | None] = mapped_column(Float)
    he_fev: Mapped[float | None] = mapped_column(Float)
    comissao_fev: Mapped[float | None] = mapped_column(Float)
    dependentes_fev: Mapped[str | None] = mapped_column(String(80))


class Item(Base):
    __tablename__ = "caso_itens"
    id: Mapped[int] = mapped_column(primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), index=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    codigo: Mapped[str] = mapped_column(String(20))
    descricao: Mapped[str] = mapped_column(String(160))
    tipo: Mapped[str] = mapped_column(String(40))
    ncm: Mapped[str | None] = mapped_column(String(20))
    custo_base: Mapped[float | None] = mapped_column(Float)
    custo_min: Mapped[float | None] = mapped_column(Float)
    custo_max: Mapped[float | None] = mapped_column(Float)


class FichaTecnica(Base):
    __tablename__ = "caso_ficha_tecnica"
    id: Mapped[int] = mapped_column(primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), index=True)
    produto: Mapped[str] = mapped_column(String(20))
    insumo: Mapped[str] = mapped_column(String(20))
    quantidade: Mapped[float] = mapped_column(Float)


class Evento(Base):
    __tablename__ = "caso_eventos"
    id: Mapped[int] = mapped_column(primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), index=True)
    codigo: Mapped[str] = mapped_column(String(10))
    data: Mapped[date] = mapped_column(Date)
    grupo: Mapped[str | None] = mapped_column(String(60))
    descricao: Mapped[str] = mapped_column(Text)
    natureza: Mapped[str] = mapped_column(String(1), default="V")  # V variável | D derivado | F fixo
    contrato: Mapped[str | None] = mapped_column(String(20))
    obs: Mapped[str | None] = mapped_column(Text)

    caso: Mapped[Caso] = relationship(back_populates="eventos")


class Inconsistencia(Base):
    __tablename__ = "caso_inconsistencias"
    id: Mapped[int] = mapped_column(primary_key=True)
    caso_id: Mapped[int] = mapped_column(ForeignKey("casos.id", ondelete="CASCADE"), index=True)
    onde: Mapped[str] = mapped_column(String(160))
    descricao: Mapped[str] = mapped_column(Text)
    decisao: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PENDENTE")  # PENDENTE | RESOLVIDA | MANTIDA

"""Correção única das horas gravadas em UTC antes do ajuste de fuso (06/10/2026).

Até então o servidor gravava as horas em UTC (3 horas à frente de Brasília). Na primeira subida com
CORRIGIR_FUSO_UTC=1 (definido só no docker-compose de produção), todas as colunas de data e hora
recuam a diferença do fuso uma única vez; a tabela ajustes_sistema registra que a correção foi feita.
"""
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from .config import FUSO
from .db import Base

CHAVE = "fuso_utc_para_local"


class AjusteSistema(Base):
    __tablename__ = "ajustes_sistema"
    chave: Mapped[str] = mapped_column(String(60), primary_key=True)
    aplicado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    detalhe: Mapped[str] = mapped_column(String(500), default="")


def _horas_de_diferenca() -> int:
    try:
        off = datetime.now(ZoneInfo(FUSO)).utcoffset()
    except Exception:  # sem a base de fusos
        return -3
    return int(off.total_seconds() // 3600)


def corrigir_registros_utc(db: Session) -> int:
    """Recua as horas antigas para o fuso local. Retorna quantas colunas foram ajustadas (0 se já feito)."""
    if os.getenv("CORRIGIR_FUSO_UTC", "") not in ("1", "true", "sim"):
        return 0
    if db.get(AjusteSistema, CHAVE):
        return 0
    horas = _horas_de_diferenca()
    colunas = [(t.name, c.name) for t in Base.metadata.sorted_tables if t.name != AjusteSistema.__tablename__
               for c in t.columns if isinstance(c.type, DateTime)]
    for tabela, coluna in colunas:
        db.execute(text(f'UPDATE "{tabela}" SET "{coluna}" = "{coluna}" + make_interval(hours => :h) '
                        f'WHERE "{coluna}" IS NOT NULL'), {"h": horas})
    db.add(AjusteSistema(chave=CHAVE, detalhe=f"{len(colunas)} colunas, {horas:+d} h ({FUSO})"))
    db.commit()
    return len(colunas)

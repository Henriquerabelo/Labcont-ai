"""Base normativa consultada pelo tutor (Etapa 6) — busca local, sem serviço externo.

As fichas ficam na tabela `base_normativa`. Na primeira subida (e a cada atualização) as fichas padrão de
app/dados_normas/fichas.py que ainda não existem são inseridas; fichas editadas pelo professor não são sobrescritas.
A busca é lexical (BM25) com bônus para fichas ligadas ao evento: leve, explicável e roda no próprio VPS.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base


class Norma(Base):
    __tablename__ = "base_normativa"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    titulo: Mapped[str] = mapped_column(String(200))
    fonte: Mapped[str] = mapped_column(String(300))
    texto: Mapped[str] = mapped_column(Text)
    palavras: Mapped[str] = mapped_column(Text, default="")
    eventos: Mapped[str] = mapped_column(String(300), default="")
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    origem: Mapped[str] = mapped_column(String(20), default="padrao")  # padrao | professor | editada
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    @property
    def lista_eventos(self) -> list[str]:
        return [e.strip().upper() for e in (self.eventos or "").split(",") if e.strip()]


def semear(db: Session) -> int:
    """Insere fichas padrão novas e atualiza as padrão que ninguém editou; fichas editadas ou do professor ficam como estão."""
    from .dados_normas.fichas import FICHAS
    existentes = {n.codigo: n for n in db.scalars(select(Norma)).all()}
    n = 0
    for f in FICHAS:
        atual = existentes.get(f["codigo"])
        if atual is None:
            db.add(Norma(**f, origem="padrao"))
            n += 1
        elif atual.origem == "padrao" and any(getattr(atual, k) != v for k, v in f.items()):
            for k, v in f.items():
                setattr(atual, k, v)
    db.commit()
    return n


# ------------------------------------------------------------------ busca
STOP = set("""a o e as os um uma uns umas de da do das dos em no na nos nas ao aos por pela pelo pelas pelos para com sem
que qual quais quando como onde se ser sao foi era este esta isso isto esse essa sobre entre mais menos ja nao sim ou
eu voce voces nos ele ela eles elas meu minha seu sua nosso nossa tem ter ha vai pode posso devo deve fazer faz fiz
lancar lancamento lancei valor valores conta contas evento dupla nota notas fiscal empresa""".split())


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower()


def termos(s: str) -> list[str]:
    out = []
    texto = re.sub(r"\bar[\s-]+condicionad", "arcondicionad", _sem_acento(s))
    for t in re.findall(r"[a-z0-9]+(?:-[a-z]+)*(?:,[0-9]+)?", texto):
        t = t.replace("-", "")
        if t in STOP or (len(t) < 3 and not t.isdigit() and t not in {"ir", "pl"}):
            continue
        if not t[0].isdigit():
            t = t[:6]  # radical simples: recuperar/recuperáveis, tributo/tributário, crédito/créditos
        out.append(t)
    return out


def buscar(normas: list[Norma], consulta: str, evento: str | None = None, k: int = 3,
           bonus_evento: float = 2.5, apoio: str = "") -> list[tuple[Norma, float]]:
    """Ranqueia as fichas ativas. Fichas ligadas ao evento ganham bônus; sem termo nem evento, nada volta."""
    ativas = [n for n in normas if n.ativa]
    if not ativas:
        return []
    docs = [termos(f"{n.titulo} {n.titulo} {n.palavras} {n.texto} {n.fonte}") for n in ativas]
    media = sum(map(len, docs)) / len(docs)
    df = Counter(t for d in docs for t in set(d))
    pesos = {t: 0.35 for t in termos(apoio)}  # termos de apoio (ex.: descrição do evento) pesam menos
    pesos.update({t: 1.0 for t in termos(consulta)})
    ev = (evento or "").upper()
    res = []
    for n, d in zip(ativas, docs):
        tf = Counter(d)
        s = 0.0
        for t, w in pesos.items():
            if t in tf:
                idf = math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5))
                s += w * idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(d) / media))
        if ev and ev in n.lista_eventos:
            s += bonus_evento
        if s > 0.5:
            res.append((n, round(s, 2)))
    res.sort(key=lambda x: -x[1])
    if res:
        corte = res[0][1] * 0.45  # descarta fichas muito abaixo da melhor
        res = [r for r in res if r[1] >= corte]
    return res[:k]


def todas(db: Session) -> list[Norma]:
    return db.scalars(select(Norma).order_by(Norma.codigo)).all()

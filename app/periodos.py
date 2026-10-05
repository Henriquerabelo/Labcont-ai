"""Meses do exercício (Etapa 8): janeiro e fevereiro de 2026.

O mês de um lançamento é dado pelo código do evento: J.. e TES/AJ são de janeiro; F.., FTES e FAJ de fevereiro.
Os dois meses ficam abertos desde o início (decisão do professor, 05/10); cada um tem o seu fechamento.
"""
from __future__ import annotations

from datetime import date

MESES = {
    "2026-01": {"nome": "janeiro", "rotulo": "Janeiro/2026", "curto": "Jan", "inicio": date(2026, 1, 1), "fim": date(2026, 1, 31),
                "tes": "TES", "aj": "AJ", "apuracao": "J40"},
    "2026-02": {"nome": "fevereiro", "rotulo": "Fevereiro/2026", "curto": "Fev", "inicio": date(2026, 2, 1), "fim": date(2026, 2, 28),
                "tes": "FTES", "aj": "FAJ", "apuracao": "F48"},
}
PADRAO = "2026-01"
COOKIE = "labcont_mes"


def valido(mes: str | None) -> str:
    return mes if mes in MESES else PADRAO


def mes_do_evento(codigo: str | None) -> str:
    return "2026-02" if (codigo or "").upper().startswith("F") else "2026-01"


def do_mes(lancs, mes: str) -> list:
    return [l for l in lancs if mes_do_evento(l.evento) == mes]


def ate_o_mes(lancs, mes: str) -> list:
    """Lançamentos do próprio mês e dos anteriores (a escrituração continua de um mês para o outro)."""
    return [l for l in lancs if mes_do_evento(l.evento) <= mes]


def anteriores(lancs, mes: str) -> list:
    return [l for l in lancs if mes_do_evento(l.evento) < mes]


def nome(mes: str) -> str:
    return MESES[valido(mes)]["nome"]


def da_requisicao(request) -> str:
    """Mês escolhido: ?mes= na URL ou o último escolhido (cookie)."""
    q = request.query_params.get("mes")
    if q in MESES:
        return q
    return valido(request.cookies.get(COOKIE))

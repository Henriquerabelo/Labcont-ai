"""A2 · Avisos estruturais imediatos (Módulo 3: Informativo, Aviso, Erro estrutural).

Conferem só a consistência dos lançamentos da própria dupla — nunca o gabarito. Assim a dupla recebe retorno
imediato sobre problemas de forma (datas, históricos, repetições, saldos impossíveis), enquanto a correção
contábil continua sendo mostrada apenas no fechamento mensal.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from . import plano_contas as pc
from .gabarito import r2

NIVEIS = {"erro": "Erro estrutural", "aviso": "Aviso", "info": "Informativo"}
SEM_DATA_FIXA = {"TES", "AJ", "J40"}  # eventos com lançamentos em datas variadas


def _fmt(v: float) -> str:
    return f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def verificar(saldos_ini: dict[str, float], lancs, datas_evento: dict[str, date] | None = None) -> list[dict]:
    avisos: list[dict] = []
    datas_evento = datas_evento or {}
    lancados = {l.evento for l in lancs}
    faltam = [e for e in datas_evento if e not in lancados]
    ressalva = (f" Ainda faltam {len(faltam)} evento(s) do mês: se algum deles movimenta esta conta, o saldo pode se ajustar "
                "quando for lançado.") if faltam else ""

    vistos = {}
    for l in lancs:
        ref = {"lancamento_id": l.id, "evento": l.evento}
        if not (date(2026, 1, 1) <= l.data <= date(2026, 1, 31)):
            avisos.append({"nivel": "aviso", "titulo": f"{l.evento}: data fora de janeiro",
                           "texto": f"O lançamento está em {l.data:%d/%m/%Y}. Janeiro/2026 só aceita fatos de 01 a 31/01 (regime de competência).", **ref})
        elif l.evento in datas_evento and l.evento not in SEM_DATA_FIXA and l.data != datas_evento[l.evento]:
            avisos.append({"nivel": "info", "titulo": f"{l.evento}: data diferente da do evento",
                           "texto": f"O evento é de {datas_evento[l.evento]:%d/%m}; o lançamento está em {l.data:%d/%m}. Confira a data de competência.", **ref})
        if len((l.historico or "").strip()) < 10:
            avisos.append({"nivel": "info", "titulo": f"{l.evento}: histórico curto",
                           "texto": "O histórico deve identificar a operação e o documento (ex.: “NF 3.369 — compra de mercadoria ALPHA”).", **ref})
        assinatura = (l.evento, tuple(sorted((p.conta, p.natureza, round(p.valor, 2)) for p in l.partidas)))
        if assinatura in vistos:
            avisos.append({"nivel": "aviso", "titulo": f"{l.evento}: lançamento repetido",
                           "texto": "Há dois lançamentos idênticos (mesmas contas e valores) para este evento. Verifique se não houve registro em duplicidade.", **ref})
        vistos[assinatura] = l.id

    # saldos finais com natureza invertida
    saldo = defaultdict(float, {c: float(v) for c, v in saldos_ini.items()})
    for l in lancs:
        for p in l.partidas:
            saldo[p.conta] += p.valor if p.natureza == "D" else -p.valor
    for c, v in sorted(saldo.items()):
        v = r2(v)
        info = pc.CONTAS.get(c)
        if not info or abs(v) <= 0.05:
            continue
        invertida = (info["natureza"] == "D" and v < 0) or (info["natureza"] == "C" and v > 0)
        if not invertida:
            continue
        lado = "credor" if v < 0 else "devedor"
        if c.startswith(("1", "2")):
            avisos.append({"nivel": "erro", "titulo": f"{info['nome']}: saldo {lado}",
                           "texto": f"A conta é de natureza {'devedora' if info['natureza'] == 'D' else 'credora'} e terminou janeiro com saldo {lado} de R$ {_fmt(v)}. "
                                    "Isso impede o fechamento do balanço — confira os lançamentos desta conta no Razão." + ressalva, "conta": c})
        else:
            avisos.append({"nivel": "aviso", "titulo": f"{info['nome']}: saldo {lado}",
                           "texto": f"Conta de resultado com saldo invertido (R$ {_fmt(v)}). Confira se o débito e o crédito não foram trocados.", "conta": c})

    # saldo bancário diário
    por_dia = defaultdict(float)
    for l in lancs:
        for p in l.partidas:
            if p.conta == pc.BANCO:
                por_dia[l.data] += p.valor if p.natureza == "D" else -p.valor
    s = float(saldos_ini.get(pc.BANCO, 0.0))
    for dia in sorted(por_dia):
        s += por_dia[dia]
        if r2(s) < -0.05:
            avisos.append({"nivel": "erro", "titulo": f"Banco com saldo negativo em {dia:%d/%m}",
                           "texto": f"Pelos seus lançamentos, o Banco Rico terminou o dia {dia:%d/%m} devendo R$ {_fmt(s)}. "
                                    "Uma conta corrente não fica negativa sem cobertura: releia os contratos financeiros da empresa." + ressalva, "conta": pc.BANCO})
            break
    ordem = {"erro": 0, "aviso": 1, "info": 2}
    return sorted(avisos, key=lambda a: (ordem[a["nivel"]], a.get("evento") or "", a["titulo"]))


def contagem(avisos: list[dict]) -> dict[str, int]:
    out = {"erro": 0, "aviso": 0, "info": 0}
    for a in avisos:
        out[a["nivel"]] += 1
    return out

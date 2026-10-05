"""Auditoria da escrituração da dupla contra o gabarito (Etapa 5).

Compara, evento a evento, o efeito líquido por conta (débitos − créditos) dos lançamentos da dupla com o
do gabarito. Assim a dupla pode compor os lançamentos do seu jeito (um lançamento composto ou vários simples)
sem ser penalizada. Três níveis de alerta:
  - correto: mesmas contas, mesmos lados e valores dentro da tolerância;
  - valor:   contas e lados certos, mas algum valor diverge;
  - conta:   falta conta, sobra conta ou conta no lado trocado.
Eventos sem lançamento da dupla ficam como "pendente".
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from . import plano_contas as pc
from .gabarito import Gabarito, r2

TOLERANCIA = 0.05  # R$ por conta, para diferenças de arredondamento
ESPECIAIS = {"TES": "Tesouraria: resgates automáticos e conta garantida", "AJ": "Ajustes de fim de mês (apropriações e juros)",
             "J40": "Apuração dos tributos de janeiro"}
NIVEIS = {"correto": "Correto", "valor": "Valor divergente", "conta": "Conta errada", "pendente": "Pendente"}


def eventos_janeiro(caso=None) -> list[dict]:
    desc = {}
    if caso:
        desc = {e.codigo: e.descricao for e in caso.eventos if e.data and e.data.month == 1}
    out = []
    for ev, (dia, _) in sorted(Gabarito.EVENTOS.items(), key=lambda kv: (kv[1][0], kv[0])):
        out.append({"codigo": ev, "data": date(2026, 1, dia), "descricao": desc.get(ev, ev)})
    out.append({"codigo": "TES", "data": date(2026, 1, 31), "descricao": ESPECIAIS["TES"]})
    out.append({"codigo": "AJ", "data": date(2026, 1, 31), "descricao": ESPECIAIS["AJ"]})
    out.append({"codigo": "J40", "data": date(2026, 1, 30), "descricao": desc.get("J40", ESPECIAIS["J40"])})
    return out


def _net(partidas) -> dict[str, float]:
    out = defaultdict(float)
    for conta, nat, valor in partidas:
        out[conta] += valor if nat == "D" else -valor
    return {c: r2(v) for c, v in out.items() if abs(r2(v)) >= 0.005}


def net_gabarito(g: dict) -> dict[str, dict]:
    por_ev = defaultdict(list)
    for l in g["lancamentos"]:
        por_ev[l["evento"]] += [(p["conta"], "D", p["valor"]) for p in l["debitos"]]
        por_ev[l["evento"]] += [(p["conta"], "C", p["valor"]) for p in l["creditos"]]
    return {ev: _net(ps) for ev, ps in por_ev.items()}


def net_aluno(lancs) -> dict[str, dict]:
    por_ev = defaultdict(list)
    for l in lancs:
        por_ev[l.evento] += [(p.conta, p.natureza, p.valor) for p in l.partidas]
    return {ev: _net(ps) for ev, ps in por_ev.items()}


def comparar(g: dict, a: dict) -> dict:
    contas_g, contas_a = set(g), set(a)
    faltam = sorted(contas_g - contas_a)
    sobram = sorted(contas_a - contas_g)
    trocadas = sorted(c for c in contas_g & contas_a if (g[c] > 0) != (a[c] > 0))
    divergentes = sorted(c for c in contas_g & contas_a if c not in trocadas and abs(g[c] - a[c]) > TOLERANCIA)
    if faltam or sobram or trocadas:
        nivel = "conta"
    elif divergentes:
        nivel = "valor"
    else:
        nivel = "correto"
    linhas = []
    for c in sorted(contas_g | contas_a):
        linhas.append({"conta": c, "nome": pc.CONTAS.get(c, {}).get("nome", c), "gabarito": g.get(c), "aluno": a.get(c),
                       "situacao": ("falta" if c in faltam else "sobra" if c in sobram else "lado" if c in trocadas
                                    else "valor" if c in divergentes else "ok")})
    return {"nivel": nivel, "faltam": faltam, "sobram": sobram, "trocadas": trocadas, "divergentes": divergentes, "linhas": linhas}


def dica(r: dict) -> str:
    """Mensagem para a dupla: aponta o tipo de problema sem entregar a resposta."""
    nome = lambda c: pc.CONTAS.get(c, {}).get("nome", c)  # noqa: E731
    if r["nivel"] == "correto":
        return "Lançamento confere com o gabarito."
    if r["nivel"] == "pendente":
        return "Evento ainda não escriturado."
    partes = []
    if r["sobram"]:
        partes.append("conta(s) que não se aplicam a este evento: " + ", ".join(nome(c) for c in r["sobram"]))
    if r["trocadas"]:
        partes.append("conta(s) no lado trocado (débito × crédito): " + ", ".join(nome(c) for c in r["trocadas"]))
    if r["faltam"]:
        partes.append(f"falta(m) {len(r['faltam'])} conta(s) — revise tributos, retenções e contrapartidas do documento")
    if r["nivel"] == "valor":
        partes.append("contas certas, mas o valor diverge em: " + ", ".join(nome(c) for c in r["divergentes"]))
    texto = "; ".join(partes)
    return texto[:1].upper() + texto[1:] + "."


def auditar(g: dict, lancs, caso=None) -> dict:
    ng, na = net_gabarito(g), net_aluno(lancs)
    eventos = []
    for e in eventos_janeiro(caso):
        ev = e["codigo"]
        if ev not in na:
            r = {"nivel": "pendente", "linhas": [], "faltam": [], "sobram": [], "trocadas": [], "divergentes": []}
        else:
            r = comparar(ng.get(ev, {}), na[ev])
        r.update(e)
        r["dica"] = dica(r)
        r["sem_gabarito"] = ev not in ng
        eventos.append(r)
    for ev in sorted(set(na) - {e["codigo"] for e in eventos}):  # evento digitado que não existe
        r = comparar({}, na[ev])
        r.update({"codigo": ev, "data": None, "descricao": "Evento não reconhecido", "dica": "Código de evento inexistente."})
        eventos.append(r)
    cont = defaultdict(int)
    for r in eventos:
        cont[r["nivel"]] += 1
    total = sum(1 for e in eventos if not e.get("sem_gabarito"))
    return {"eventos": eventos, "contagem": dict(cont), "total": total,
            "percentual": round(100 * cont["correto"] / total) if total else 0}


def balancete_aluno(saldos_ini: dict[str, float], lancs) -> list[dict]:
    mov_d, mov_c = defaultdict(float), defaultdict(float)
    for l in lancs:
        for p in l.partidas:
            (mov_d if p.natureza == "D" else mov_c)[p.conta] += p.valor
    out = []
    for c, info in pc.CONTAS.items():
        ini = saldos_ini.get(c, 0.0)
        d, cr = r2(mov_d.get(c, 0.0)), r2(mov_c.get(c, 0.0))
        if abs(ini) < 0.005 and not d and not cr:
            continue
        out.append({"conta": c, "nome": info["nome"], "inicial": r2(ini), "debitos": d, "creditos": cr, "final": r2(ini + d - cr)})
    return out


def resumo_resultado(aud: dict) -> dict:
    """Retrato compacto da correção, guardado no fechamento mensal."""
    return {"percentual": aud["percentual"], "contagem": aud["contagem"], "total": aud["total"],
            "eventos": {e["codigo"]: {"nivel": e["nivel"], "dica": e["dica"]} for e in aud["eventos"]}}

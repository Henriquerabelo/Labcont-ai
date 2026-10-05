"""A1 · Demonstrações contábeis automáticas (CPC 26): DRE, Balanço Patrimonial e prévia do encerramento (ARE).

Recebem os saldos finais por conta analítica (débito positivo, crédito negativo) — da dupla ou do gabarito —
e montam as demonstrações pela estrutura do plano de contas. Nada é gravado: o encerramento (ARE) é mostrado
como prévia, porque no Lucro Real anual o resultado de janeiro fica em balancete de suspensão/redução.
"""
from __future__ import annotations

from collections import defaultdict

from . import plano_contas as pc
from .gabarito import r2

LUCROS_ACUMULADOS = "2.07.07.01.01.0001-7"

LINHAS_DRE = [  # (chave, rótulo, prefixo da conta sintética, sinal na DRE: +1 receita, -1 despesa)
    ("rb", "Receita bruta", "3.01.01.01.01", +1),
    ("ded", "(−) Deduções da receita bruta", "3.01.01.01.03", -1),
    ("custo", "(−) Custo dos produtos, mercadorias e serviços vendidos", "3.01.01.03", -1),
    ("adm", "(−) Despesas administrativas", "3.01.01.07.01", -1),
    ("vendas", "(−) Despesas de vendas", "3.01.01.07.02", -1),
    ("trib", "(−) Despesas tributárias", "3.01.01.07.03", -1),
    ("outras", "Outras receitas e despesas operacionais", "3.01.01.07", +1),
    ("rfin", "Receitas financeiras", "3.01.01.09.01", +1),
    ("dfin", "(−) Despesas financeiras", "3.01.01.09.02", -1),
    ("irpj", "(−) Provisão para IRPJ e CSLL", "3.02", -1),
]


def _sintetica(conta: str, nivel: int) -> str:
    """Conta sintética do nível pedido (nº de segmentos), ex.: 1.01.05 para nível 3."""
    partes = conta.split(".")
    return ".".join(partes[:nivel])


def montar(saldos: dict[str, float], mes: str = "2026-01") -> dict:
    """Saldos acumulados até o fim do mês (no Lucro Real anual as contas de resultado só são encerradas em dezembro)."""
    s = {c: r2(v) for c, v in saldos.items() if abs(r2(v)) >= 0.005}

    # ------------------------------------------------------------ DRE
    vals = defaultdict(float)
    detalhes = defaultdict(list)
    for c, v in s.items():
        if not c.startswith("3"):
            continue
        for chave, _rot, pref, _sinal in LINHAS_DRE:
            if c.startswith(pref):
                vals[chave] += -v  # resultado: crédito = ganho
                detalhes[chave].append({"conta": c, "nome": pc.CONTAS.get(c, {}).get("nome", c), "valor": r2(abs(v))})
                break
    linha = lambda k: r2(vals.get(k, 0.0))  # noqa: E731
    rl = r2(linha("rb") + linha("ded"))
    lb = r2(rl + linha("custo"))
    rop = r2(lb + linha("adm") + linha("vendas") + linha("trib") + linha("outras"))
    rfin = r2(linha("rfin") + linha("dfin"))
    lair = r2(rop + rfin)
    ll = r2(lair + linha("irpj"))
    rot = {k: r for k, r, _p, _s in LINHAS_DRE}
    dre = []
    def item(k):  # noqa: E306
        if linha(k) or k in ("rb",):
            dre.append({"rotulo": rot[k], "valor": linha(k), "detalhe": sorted(detalhes[k], key=lambda x: -x["valor"]), "nivel": 1})
    def total(rotulo, v, forte=False):  # noqa: E306
        dre.append({"rotulo": rotulo, "valor": v, "total": True, "forte": forte})
    item("rb"); item("ded"); total("Receita líquida", rl)  # noqa: E702
    item("custo"); total("Lucro bruto", lb)  # noqa: E702
    for k in ("adm", "vendas", "trib", "outras"):
        item(k)
    total("Resultado operacional antes do resultado financeiro", rop)
    item("rfin"); item("dfin"); total("Resultado antes do IRPJ e da CSLL", lair)  # noqa: E702
    item("irpj"); total("Resultado líquido do período", ll, forte=True)  # noqa: E702

    # ------------------------------------------------------------ Balanço
    def grupo(prefixo, natureza_pos):
        out = defaultdict(lambda: {"valor": 0.0, "contas": []})
        for c, v in s.items():
            if not c.startswith(prefixo + "."):
                continue
            chave = _sintetica(c, 3)
            val = v if natureza_pos == "D" else -v
            out[chave]["valor"] += val
            out[chave]["contas"].append({"conta": c, "nome": pc.CONTAS.get(c, {}).get("nome", c), "valor": r2(val)})
        linhas = []
        for chave in sorted(out):
            info = out[chave]
            if abs(r2(info["valor"])) < 0.005 and not any(x["valor"] for x in info["contas"]):
                continue
            linhas.append({"codigo": chave, "rotulo": pc.SINTETICAS.get(chave, chave), "valor": r2(info["valor"]),
                           "contas": sorted(info["contas"], key=lambda x: x["conta"])})
        return linhas, r2(sum(x["valor"] for x in linhas))

    ac, t_ac = grupo("1.01", "D")
    anc, t_anc = grupo("1.07", "D")
    pc_, t_pc = grupo("2.01", "C")
    pnc, t_pnc = grupo("2.03", "C")
    pl, t_pl = grupo("2.07", "C")
    periodo = "janeiro" if mes == "2026-01" else "janeiro e fevereiro acumulados"
    pl.append({"codigo": "", "rotulo": f"Resultado do período ({periodo}, antes do encerramento)", "valor": ll, "contas": []})
    t_pl = r2(t_pl + ll)
    ativo = r2(t_ac + t_anc)
    passivo_pl = r2(t_pc + t_pnc + t_pl)
    bp = {"ac": ac, "t_ac": t_ac, "anc": anc, "t_anc": t_anc, "ativo": ativo,
          "pc": pc_, "t_pc": t_pc, "pnc": pnc, "t_pnc": t_pnc, "pl": pl, "t_pl": t_pl, "passivo_pl": passivo_pl,
          "diferenca": r2(ativo - passivo_pl)}
    bp["fecha"] = abs(bp["diferenca"]) <= 0.05  # o BP de 2025 do exercício tem diferença de arredondamento de R$ 0,01

    # ------------------------------------------------------------ prévia do encerramento (ARE)
    are = []
    for c, v in sorted(s.items()):
        if c.startswith("3"):
            nome = pc.CONTAS.get(c, {}).get("nome", c)
            # zera a conta: saldo devedor → crédito na conta e débito na ARE; credor → o inverso
            are.append({"debito": "Apuração do Resultado do Exercício (ARE)" if v > 0 else nome,
                        "credito": nome if v > 0 else "Apuração do Resultado do Exercício (ARE)", "valor": r2(abs(v))})
    if ll:
        are.append({"debito": "Apuração do Resultado do Exercício (ARE)" if ll > 0 else "Lucros ou Prejuízos Acumulados",
                    "credito": "Lucros ou Prejuízos Acumulados" if ll > 0 else "Apuração do Resultado do Exercício (ARE)",
                    "valor": r2(abs(ll)), "final": True})
    return {"dre": dre, "lucro": ll, "bp": bp, "are": are, "mes": mes, "periodo": periodo}


def saldos_finais(saldos_ini: dict[str, float], partidas) -> dict[str, float]:
    """partidas: iterável de (conta, natureza, valor)."""
    out = defaultdict(float, {c: float(v) for c, v in saldos_ini.items()})
    for conta, nat, valor in partidas:
        out[conta] += valor if nat == "D" else -valor
    return dict(out)


def de_gabarito(g: dict) -> dict[str, float]:
    return {x["conta"]: x["final"] for x in g["balancete"]}

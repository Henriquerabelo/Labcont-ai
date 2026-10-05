"""Gabarito contábil de janeiro/2026 por dupla (Etapa 3b).

Calcula os lançamentos corretos de cada evento de janeiro a partir dos valores sorteados da dupla
(EmpresaGerada.valores) — ou do caso-base, para conferência pelo professor. Cada evento gera
lançamentos em partidas dobradas e uma memória de cálculo. Ao final: balancete de 31/01/2026.

Todas as decisões de tratamento contábil/fiscal que não estão explícitas no exercício estão em PREMISSAS,
com código (P01...), para validação pelos professores. Cada lançamento cita as premissas que usou.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import date

from . import plano_contas as pc
from .caso_servico import num
from .orientacao import Valores

ANO = 2026
FIM_MES = date(ANO, 1, 31)

# ------------------------------------------------------------------ tabelas 2026
SALARIO_MINIMO = 1621.00
INSS_FAIXAS = [(1621.00, 0.075), (2902.84, 0.09), (4354.27, 0.12), (8475.55, 0.14)]
TETO_INSS = 8475.55
IRRF_FAIXAS = [(2428.80, 0.0, 0.0), (2826.65, 0.075, 182.16), (3751.05, 0.15, 394.16),
               (4664.68, 0.225, 675.49), (math.inf, 0.275, 908.73)]
DEDUCAO_DEPENDENTE, DESCONTO_SIMPLIFICADO = 189.59, 607.20
SALARIO_FAMILIA_COTA, SALARIO_FAMILIA_LIMITE = 67.54, 1980.38
ENCARGOS_INSS_FOLHA, FGTS, INSS_PATRONAL_CI = 0.278, 0.08, 0.20
ICMS_INTERNO_CE = 0.20
ICMS_INTERESTADUAL = {"MA": 0.12, "PB": 0.12, "MG": 0.07}
PIS, COFINS = 0.0165, 0.076
ISS_FORTALEZA = 0.05
IRRF_SERVICOS, CSRF = 0.015, 0.0465
IR_APLICACAO = 0.225  # até 180 dias
ALIQ_IPI = {"9002.11.11": 0.0975}  # TIPI - MP-A

PREMISSAS = {
    "P01": "Tabelas de 2026: INSS (Portaria MPS/MF 13/2026), IRRF com a redução da Lei 15.270/2025, salário-família R$ 67,54 (remuneração até R$ 1.980,38), salário mínimo R$ 1.621,00.",
    "P02": "ICMS interestadual: 12% para origem no Norte/Nordeste (MA, PB) e 7% para origem no Sudeste (MG). Alíquota interna do Ceará: 20%.",
    "P03": "Mercadoria para revenda vinda de outro estado (ALPHA): antecipação parcial do ICMS = valor líquido da NF × (20% − 12%), registrada como ICMS antecipado a recolher e a recuperar (mesmo tratamento do balanço de 2025). O crédito é aproveitado na apuração do mês em que é pago.",
    "P04": "Bens para uso administrativo (ar-condicionados): sem crédito de ICMS, PIS e COFINS; DIFAL = valor × (20% − 12%), incorporado ao custo do bem. Classificados em Móveis, Utensílios e Aparelhos (vida útil 12 anos, residual 10%).",
    "P05": "Créditos de PIS (1,65%) e COFINS (7,6%) não cumulativos sobre mercadorias, insumos e fretes de compra, com base no valor líquido do ICMS destacado (Lei 14.592/2023); o IPI recuperável fica fora da base.",
    "P06": "PIS e COFINS sobre vendas calculados sobre a receita bruta menos o ICMS destacado (Tema 69/STF). ICMS de 20% sobre o preço (venda interna).",
    "P07": "Preço de venda da ALPHA = custo médio ponderado móvel × multiplicador do mark-up (1 ÷ [1 − (ICMS + PIS + COFINS + margem)]), arredondado a centavos.",
    "P08": "MP-A comprada de indústria (CFOP 6.101): IPI destacado à parte pela TIPI (9,75% para a NCM 9002.11.11), recuperável; o valor informado no exercício é o valor dos produtos. Frete CIF a cargo do fornecedor (sem lançamento).",
    "P09": "Comissão de representação (NFS-e): ISS 5% (Fortaleza), PIS 1,65% e COFINS 7,6% sobre o valor do serviço; IRRF de 1,5% retido pelo tomador (IRRF a recuperar). Sem retenção de CSRF.",
    "P10": "Serviços contábeis (PJ): retenção de IRRF 1,5% e CSRF 4,65% (confere com o saldo de dezembro: R$ 5.500,00 → R$ 5.161,75).",
    "P11": "Arquiteto autônomo (RPA): INSS 11% retido (limitado ao teto), IRRF pela tabela mensal, ISS 5% retido (não recolhe por valor fixo) e INSS patronal de 20%. O projeto é da reforma do galpão e, por isso, é capitalizado em Imobilizado em andamento junto com o encargo patronal.",
    "P12": "Reforma do galpão (empreitada com material): 1ª parcela de 50% paga na entrada da NFS-e; retenção de INSS 11% e ISS 5% sobre a parcela de mão de obra; sem IRRF/CSRF. Capitalizada em Imobilizado em andamento.",
    "P13": "Arrendamento financeiro (CPC 06): máquinas reconhecidas no imobilizado em contrapartida da obrigação, separada em curto prazo (parcelas dos próximos 12 meses, SAC) e longo prazo. Juros compostos pelo ano civil (365 dias) apropriados no fim do mês; depreciação a partir de fevereiro (bem recebido após o processamento de 15/01).",
    "P14": "Aplicações: INVEST LIQUID e CDB rendem juros compostos com capitalização diária (taxa mensal, mês de 30 dias), apropriados no fim do mês e no resgate. No resgate, IR de 22,5% (até 180 dias) vai para IRRF a recuperar; IOF desconsiderado.",
    "P15": "Tesouraria diária: ao fim de cada dia, se o Banco Rico ficar negativo, resgata-se primeiro o INVEST LIQUID e depois usa-se a conta garantida (juros compostos de capitalização diária a partir do dia seguinte). A conta garantida é quitada integralmente no primeiro dia em que o saldo bancário for suficiente.",
    "P16": "Folha de janeiro: salário + horas extras + comissões; INSS e IRRF do empregado pelas tabelas de 2026 (dependentes até 21 anos); salário-família para filhos até 14 anos; encargos de 27,80% (INSS + RAT + Terceiros) e FGTS 8%. Pró-labore: INSS 11% (teto) e patronal de 20%, IRRF pela tabela.",
    "P17": "Vale-transporte e vale-alimentação de janeiro são os adiantamentos do balanço de 2025 (R$ 172,80 e R$ 1.773,00), divididos igualmente entre os empregados de janeiro; descontos de 6% do salário-base (limitado ao benefício) e 5% do benefício. Compras para fevereiro: 18 dias úteis × empregados de fevereiro.",
    "P18": "Provisões mensais: férias = remuneração ÷ 12 × 4/3; 13º = remuneração ÷ 12; encargos de 27,80% e FGTS 8% sobre as provisões.",
    "P19": "Em janeiro não há produção: os itens da área industrial são despesa administrativa (regra do exercício). Despesas rateadas pela tabela de alocação (internet 40/50/10; telefone 20/60/20; energia conforme a fatura).",
    "P20": "Depreciação de 15/01 (método linear, vida útil e residual da tabela do exercício) para os bens existentes na data, inclusive os ar-condicionados de 08/01. Máquinas pelo saldo contábil de R$ 262.000,00 (ver inconsistências do caso).",
    "P21": "Auto de infração: ICMS de 18% sobre a base e multa de 75% do ICMS com redução de 70% (pagamento em 05/02), provisionados em 26/01 como despesa tributária e multa indedutível.",
    "P22": "IRPJ e CSLL por estimativa (receita bruta): presunção de 8%/12% na revenda e 32%/32% nos serviços, mais as receitas financeiras; IRPJ 15% + adicional de 10% sobre o que exceder R$ 20.000,00; CSLL 9%. O IRRF retido sobre receitas do mês é deduzido.",
    "P23": "Apuração mensal: créditos de ICMS, PIS e COFINS compensados com os débitos do mês; saldo credor permanece em Impostos a Recuperar.",
    "P24": "Destinação de 2025 (02/01): participações sobre o lucro após IR/CS, reserva legal de 5%, dividendos sobre o lucro líquido ajustado e o saldo em reserva estatutária.",
    "P25": "Seguro: apropriação mensal de 1/12 do prêmio. Recrutamento: metade dos honorários apropriada em janeiro (serviço a faturar).",
    "P26": "Pagamento de 14/01 (água, energia e telefone de janeiro) inclui o telefone fixo, como descrito no evento, mesmo com vencimento posterior na tabela de telefonia.",
}


def r2(v: float) -> float:
    return round(v + (1e-9 if v >= 0 else -1e-9), 2)


def inss_empregado(base: float) -> float:
    total, ant = 0.0, 0.0
    for lim, aliq in INSS_FAIXAS:
        if base > ant:
            total += (min(base, lim) - ant) * aliq
        ant = lim
    return r2(total)


def _tabela_ir(base: float) -> float:
    for lim, aliq, ded in IRRF_FAIXAS:
        if base <= lim:
            return max(0.0, base * aliq - ded)
    return 0.0


def irrf(rend: float, inss: float, deps: int) -> tuple[float, str]:
    legal = rend - inss - deps * DEDUCAO_DEPENDENTE
    simpl = rend - DESCONTO_SIMPLIFICADO
    imp_l, imp_s = _tabela_ir(legal), _tabela_ir(simpl)
    imp = min(imp_l, imp_s)
    if rend <= 5000:
        red = imp
    elif rend <= 7350:
        red = max(0.0, 978.62 - 0.133145 * rend)
    else:
        red = 0.0
    final = r2(max(0.0, imp - red))
    nota = (f"base {'simplificada' if imp_s < imp_l else 'legal'} {fmt(simpl if imp_s < imp_l else legal)}; "
            f"tabela {fmt(imp)}; redução Lei 15.270 {fmt(min(red, imp))}")
    return final, nota


def idades(texto) -> list[int]:
    if not texto:
        return []
    dentro = re.findall(r"\(([^)]*)\)", str(texto))
    alvo = " ".join(dentro) if dentro else str(texto)
    if not dentro and not re.search(r"anos", alvo):
        return []
    return [int(x) for x in re.findall(r"\d+", alvo)]


def fmt(v) -> str:
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def area(setor: str) -> int:
    """0 = administrativa, 1 = vendas. Industrial em janeiro vai para administrativa (P19)."""
    return 1 if "comerc" in (setor or "").lower() else 0


# ------------------------------------------------------------------ livro
class Livro:
    def __init__(self, saldos_ini: dict[str, float]):
        self.ini = dict(saldos_ini)  # positivo = devedor
        self.mov: dict[str, float] = defaultdict(float)
        self.lancs: list[dict] = []
        self.memoria: dict[str, list] = defaultdict(list)
        self.premissas_evento: dict[str, set] = defaultdict(set)

    def saldo(self, c: str) -> float:
        return r2(self.ini.get(c, 0.0) + self.mov.get(c, 0.0))

    def lanc(self, d: date, ev: str, hist: str, deb: list, cred: list, premissas=()):
        deb = [(c, r2(v)) for c, v in deb if abs(r2(v)) >= 0.005]
        cred = [(c, r2(v)) for c, v in cred if abs(r2(v)) >= 0.005]
        td, tc = r2(sum(v for _, v in deb)), r2(sum(v for _, v in cred))
        dif = r2(td - tc)
        if dif and abs(dif) <= 0.05:  # arredondamento: ajusta a maior partida credora/devedora
            if dif > 0:
                i = max(range(len(cred)), key=lambda k: cred[k][1])
                cred[i] = (cred[i][0], r2(cred[i][1] + dif))
            else:
                i = max(range(len(deb)), key=lambda k: deb[k][1])
                deb[i] = (deb[i][0], r2(deb[i][1] - dif))
        elif dif:
            raise ValueError(f"{ev}: lançamento desbalanceado ({td} x {tc})")
        for c, v in deb:
            assert c in pc.CONTAS, c
            self.mov[c] += v
        for c, v in cred:
            assert c in pc.CONTAS, c
            self.mov[c] -= v
        self.lancs.append({"n": len(self.lancs) + 1, "data": d.isoformat(), "evento": ev, "historico": hist,
                           "debitos": [{"conta": c, "nome": pc.CONTAS[c]["nome"], "valor": v} for c, v in deb],
                           "creditos": [{"conta": c, "nome": pc.CONTAS[c]["nome"], "valor": v} for c, v in cred],
                           "premissas": sorted(premissas)})
        self.premissas_evento[ev].update(premissas)

    def memo(self, ev: str, descricao: str, valor=None, obs: str = ""):
        self.memoria[ev].append({"descricao": descricao, "valor": None if valor is None else r2(valor), "obs": obs})


# ------------------------------------------------------------------ gabarito
class Gabarito:
    def __init__(self, valores: dict):
        self.v = valores
        self.x = Valores(valores)
        self.L = Livro(self._saldos_iniciais())
        self.alpha_q, self.alpha_v = 620.0, self.L.saldo(pc.ALPHA)
        # tesouraria
        self.invest = None  # {"saldo", "custo", "data", "taxa"}
        self.cdb = None
        self.garantida = {"saldo": 0.0, "data": None}
        self.leasing = None
        self.receitas = {"revenda": 0.0, "servicos": 0.0, "financeiras": 0.0}
        self.irrf_receitas = 0.0

    # ---------------- parâmetros
    def p(self, escopo, ref, trecho, padrao=None):
        val = self.x.p(escopo, ref, trecho)
        return padrao if val is None else float(val)

    def socio(self, trecho: str) -> dict:
        return next((s for s in self.v.get("socios", []) if trecho in (s.get("funcao") or "").lower()
                     or trecho in s["nome"].lower()), {})

    # ---------------- saldos de abertura (capital da dupla; Banco Rico fecha o balanço)
    def _saldos_iniciais(self) -> dict:
        s = {}
        for c, info in pc.CONTAS.items():
            b = info["base"]
            s[c] = b if info["natureza"] == "D" else -b
        delta = 0.0
        for soc in self.v.get("socios", []):
            cap, aint = pc.CAPITAL.get(soc["nome"], (None, None))
            if not cap:
                continue
            novo_cap, novo_int = float(soc.get("cotas") or 0), float(soc.get("a_integralizar") or 0)
            delta += (novo_cap - (-s[cap])) - (novo_int - s[aint])
            s[cap], s[aint] = -novo_cap, novo_int
        s[pc.BANCO] = r2(s[pc.BANCO] + delta)
        return s

    # ---------------- tesouraria
    def _rend(self, apl: dict, ate: date) -> float:
        dias = (ate - apl["data"]).days
        if dias <= 0 or apl["saldo"] <= 0:
            return 0.0
        return r2(apl["saldo"] * ((1 + apl["taxa"] / 100) ** (dias / 30) - 1))

    def _apropria(self, apl: dict, conta: str, ate: date, ev: str, nome: str):
        y = self._rend(apl, ate)
        if y:
            self.L.lanc(ate, ev, f"Rendimento {nome} até {ate:%d/%m}", [(conta, y)], [(pc.REND_APLIC, y)], {"P14"})
            apl["saldo"] = r2(apl["saldo"] + y)
            self.receitas["financeiras"] += y
            self.L.memo(ev, f"Rendimento {nome} ({(ate - apl['data']).days} dias a {fmt(apl['taxa'])}% a.m.)", y)
        apl["data"] = ate

    def _juros_garantida(self, ate: date, ev: str):
        g = self.garantida
        if g["saldo"] > 0 and g["data"] and ate > g["data"]:
            taxa = self.p("contrato", "C01", "taxa", 3.5)
            j = r2(g["saldo"] * ((1 + taxa / 100) ** ((ate - g["data"]).days / 30) - 1))
            if j:
                self.L.lanc(ate, ev, f"Juros da conta garantida até {ate:%d/%m}", [(pc.JUROS_GARANTIDA, j)],
                            [(pc.GARANTIDA, j)], {"P15"})
                self.L.memo(ev, f"Juros conta garantida ({(ate - g['data']).days} dias a {fmt(taxa)}% a.m.)", j)
                g["saldo"] = r2(g["saldo"] + j)
        g["data"] = ate

    def tesouraria(self, d: date):
        ev = "TES"
        banco = self.L.saldo(pc.BANCO)
        if banco < 0:
            falta = -banco
            inv = self.invest
            if inv and inv["saldo"] > 0:
                self._apropria(inv, pc.INVEST, d, ev, "INVEST LIQUID")
                prop_rend = max(0.0, (inv["saldo"] - inv["custo"]) / inv["saldo"])
                bruto = min(inv["saldo"], r2(falta / (1 - IR_APLICACAO * prop_rend)))
                ir = r2(bruto * prop_rend * IR_APLICACAO)
                self.L.lanc(d, ev, f"Resgate automático INVEST LIQUID em {d:%d/%m}", [(pc.BANCO, bruto - ir), (pc.IRRF_APLIC, ir)],
                            [(pc.INVEST, bruto)], {"P14", "P15"})
                self.L.memo(ev, f"{d:%d/%m} resgate INVEST LIQUID (IR {fmt(ir)})", bruto)
                inv["custo"] = r2(inv["custo"] * (1 - bruto / inv["saldo"])) if inv["saldo"] else 0
                inv["saldo"] = r2(inv["saldo"] - bruto)
                falta = -self.L.saldo(pc.BANCO)
            if falta > 0.004:
                self._juros_garantida(d, ev)
                self.L.lanc(d, ev, f"Uso da conta garantida em {d:%d/%m}", [(pc.BANCO, falta)], [(pc.GARANTIDA, falta)], {"P15"})
                self.L.memo(ev, f"{d:%d/%m} uso da conta garantida", falta)
                self.garantida["saldo"] = r2(self.garantida["saldo"] + falta)
                self.garantida["data"] = d
        elif self.garantida["saldo"] > 0:
            self._juros_garantida(d, ev)
            if self.L.saldo(pc.BANCO) >= self.garantida["saldo"]:
                g = self.garantida["saldo"]
                self.L.lanc(d, ev, f"Quitação da conta garantida em {d:%d/%m}", [(pc.GARANTIDA, g)], [(pc.BANCO, g)], {"P15"})
                self.L.memo(ev, f"{d:%d/%m} quitação da conta garantida", g)
                self.garantida["saldo"] = 0.0

    # ---------------- eventos
    def j01(self, d):
        lucro = 94923.97
        part_pct = self.p("empresa", "", "participação de empregados", 8.0)
        div_pct = self.p("empresa", "", "dividendos", 60.0)
        part = r2(lucro * part_pct / 100)
        ll = r2(lucro - part)
        rl = r2(ll * 0.05)
        div = r2((ll - rl) * div_pct / 100)
        est = r2(ll - rl - div)
        for t, v in (("Lucro de 2025 (antes das participações)", lucro), (f"Participações ({fmt(part_pct)}%)", part),
                     ("Lucro líquido ajustado", ll), ("Reserva legal (5%)", rl), (f"Dividendos ({fmt(div_pct)}%)", div),
                     ("Reserva estatutária (saldo)", est)):
            self.L.memo("J01", t, v)
        self.L.lanc(d, "J01", "Destinação do resultado de 2025", [(pc.LUCROS_ACUM, lucro)],
                    [(pc.PARTICIPACOES, part), (pc.RESERVA_LEGAL, rl), (pc.DIVIDENDOS, div), (pc.RESERVA_ESTAT, est)], {"P24"})

    def j02(self, d):
        tot = self.p("evento", "J02", "valor total")
        adm_pct = self.p("evento", "J02", "administrativa", 46.4)
        v_adm = round(tot * adm_pct / 100 / 10) * 10
        v_com = r2(tot - v_adm)
        pis, cof = r2(tot * PIS), r2(tot * COFINS)
        cred_adm = r2((pis + cof) * v_adm / tot)
        self.L.memo("J02", "Conta de energia (total)", tot)
        self.L.memo("J02", "Área administrativa", v_adm)
        self.L.memo("J02", "Área comercial", v_com)
        self.L.memo("J02", "Crédito de PIS 1,65% / COFINS 7,6%", pis + cof, "energia consumida no estabelecimento")
        self.L.lanc(d, "J02", "NF energia Luz do Sertão 987321 - janeiro",
                    [(pc.POR_AREA["energia"][0], v_adm - cred_adm), (pc.POR_AREA["energia"][1], v_com - (pis + cof - cred_adm)),
                     (pc.PIS_REC, pis), (pc.COFINS_REC, cof)], [(pc.ENERGIA_PAGAR, tot)], {"P05", "P19"})
        self.energia_jan = tot

    def j03(self, d):
        tot = self.p("evento", "J03", "valor total")
        self.L.memo("J03", "Fatura de água (área administrativa; industrial e não alocado vão para adm. em janeiro)", tot)
        self.L.lanc(d, "J03", "Fatura de água Águas do Litoral 321654 - janeiro", [(pc.AGUA, tot)], [(pc.AGUA_PAGAR, tot)], {"P19"})
        self.agua_jan = tot

    def j04(self, d):
        v = self.p("evento", "J04", "valor")
        taxa = self.p("contrato", "C02", "taxa", 1.6)
        self.invest = {"saldo": v, "custo": v, "data": d, "taxa": taxa}
        self.L.memo("J04", f"Aplicação INVEST LIQUID a {fmt(taxa)}% a.m.", v)
        self.L.lanc(d, "J04", "Aplicação no INVEST LIQUID", [(pc.INVEST, v)], [(pc.BANCO, v)], {"P14"})

    def j05(self, d):
        fixo = self.p("evento", "J05", "telefone")
        cel = self.p("contrato", "C08", "mensalidade", 480)
        net = self.p("contrato", "C07", "mensalidade", 350)
        tel = fixo + cel
        adm = r2(tel * 0.40 + net * 0.50)
        ven = r2(tel + net - adm)
        for t, val in (("Telefone fixo", fixo), ("Celulares (C08)", cel), ("Internet (C07)", net),
                       ("Administrativa: telefone 40% (20% + 20% ind.) + internet 50% (40% + 10% ind.)", adm), ("Vendas", ven)):
            self.L.memo("J05", t, val)
        self.L.lanc(d, "J05", "NFs de telefonia e internet - janeiro",
                    [(pc.POR_AREA["telefone"][0], adm), (pc.POR_AREA["telefone"][1], ven)],
                    [(pc.TEL_PAGAR, fixo), (pc.F_CELL, cel), (pc.F_INTERNET, net)], {"P19"})
        self.fixo_jan = fixo

    def pagar(self, d, ev, hist, contas: list[tuple[str, float]]):
        tot = r2(sum(v for _, v in contas))
        self.L.lanc(d, ev, hist, contas, [(pc.BANCO, tot)])
        for c, v in contas:
            self.L.memo(ev, pc.CONTAS[c]["nome"], v)

    def j06(self, d):
        self.pagar(d, "J06", "Pagamento de salários e pró-labores de 12/2025",
                   [(pc.SAL_PAGAR, 15760.64), (pc.PROLAB_PAGAR, 13008.92)])

    def j07(self, d):
        self.pagar(d, "J07", "Pagamento do FGTS e FGTS sobre 13º de 12/2025", [(pc.FGTS_REC, 1552.64), (pc.FGTS_13, 102.05)])

    def j08(self, d):
        q = self.p("evento", "J08", "quantidade")
        vu = self.p("evento", "J08", "unitário")
        ent = self.p("evento", "J08", "entrada", 20)
        valor = r2(q * vu)
        icms = r2(valor * ICMS_INTERESTADUAL["MA"])
        difal = r2(valor * (ICMS_INTERNO_CE - ICMS_INTERESTADUAL["MA"]))
        vista = r2(valor * ent / 100)
        for t, val in ((f"{int(q)} ar-condicionados × {fmt(vu)}", valor), ("ICMS destacado 12% (sem crédito)", icms),
                       ("DIFAL 20% − 12%", difal), (f"Entrada {fmt(ent)}%", vista), ("Saldo em 2 parcelas", valor - vista)):
            self.L.memo("J08", t, val)
        self.L.lanc(d, "J08", "NF 7.852 Ar Frio - ar-condicionados (adm.)", [(pc.MOVEIS, valor + difal)],
                    [(pc.BANCO, vista), (pc.F_ARFRIO, valor - vista), (pc.DIFAL, difal)], {"P02", "P04"})
        self.custo_ar = valor + difal

    def j09(self, d):
        f = self.p("evento", "J09", "frete")
        self.L.memo("J09", "Frete do imobilizado (incorporado ao custo)", f)
        self.L.lanc(d, "J09", "CT-e 322.123 - frete dos ar-condicionados", [(pc.MOVEIS, f)], [(pc.BANCO, f)], {"P04"})
        self.custo_ar += f

    def j10(self, d):
        self.pagar(d, "J10", "Pagamento Cell Telefonia - 12/2025", [(pc.F_CELL, 580.00)])

    def j11(self, d):
        self.pagar(d, "J11", "Pagamento Contador Formado - 12/2025", [(pc.F_CONTADOR, 5161.75)])

    def j12(self, d):
        self.pagar(d, "J12", "Pagamento do ISS de 12/2025", [(pc.ISS_RECOL, 7615.00)])

    def j13(self, d):
        self.pagar(d, "J13", "Pagamento Internet & Comunicação - 12/2025", [(pc.F_INTERNET, 410.00)])

    def j14(self, d):
        v = self.p("contrato", "C03", "valor")
        taxa = self.p("contrato", "C03", "taxa", 1.6)
        self.cdb = {"saldo": v, "custo": v, "data": d, "taxa": taxa}
        self.L.memo("J14", f"Aplicação CDB Renda Mais a {fmt(taxa)}% a.m.", v)
        self.L.lanc(d, "J14", "Aplicação no CDB Renda Mais (12 meses)", [(pc.CDB, v)], [(pc.BANCO, v)], {"P14"})

    def j15(self, d):
        q = self.p("evento", "J15", "quantidade")
        cu = self.p("evento", "J15", "custo")
        desc_pct = self.p("evento", "J15", "desconto", 5)
        frete = self.p("evento", "J15", "frete")
        bruto = r2(q * cu)
        desc = r2(bruto * desc_pct / 100)
        liq = r2(bruto - desc)
        al = ICMS_INTERESTADUAL["PB"]
        icms = r2(liq * al)
        pis, cof = r2((liq - icms) * PIS), r2((liq - icms) * COFINS)
        custo_m = r2(liq - icms - pis - cof)
        icms_f = r2(frete * al)
        pis_f, cof_f = r2((frete - icms_f) * PIS), r2((frete - icms_f) * COFINS)
        custo_f = r2(frete - icms_f - pis_f - cof_f)
        antec = r2(liq * (ICMS_INTERNO_CE - al))
        vista = r2(liq * 0.20)
        for t, val in ((f"{int(q)} un × {cu:.4f}".replace(".", ","), bruto), (f"(−) desconto incondicional {fmt(desc_pct)}%", desc),
                       ("= valor líquido da NF", liq), ("ICMS 12% (crédito)", icms), ("PIS 1,65% (crédito)", pis),
                       ("COFINS 7,6% (crédito)", cof), ("Custo das mercadorias", custo_m), ("Frete FOB (CT-e 423.765)", frete),
                       ("Créditos sobre o frete (ICMS 12%, PIS, COFINS)", icms_f + pis_f + cof_f), ("Custo do frete", custo_f),
                       ("Antecipação parcial do ICMS (20% − 12%)", antec), ("Pagamento à vista (20%)", vista)):
            self.L.memo("J15", t, val)
        self.L.lanc(d, "J15", "NF 3.369 Comercial Elegante - ALPHA",
                    [(pc.ALPHA, custo_m), (pc.ICMS_REC, icms), (pc.PIS_REC, pis), (pc.COFINS_REC, cof)],
                    [(pc.BANCO, vista), (pc.F_ELEGANTE, liq - vista)], {"P02", "P05"})
        self.L.lanc(d, "J15", "CT-e 423.765 - frete FOB da NF 3.369",
                    [(pc.ALPHA, custo_f), (pc.ICMS_REC, icms_f), (pc.PIS_REC, pis_f), (pc.COFINS_REC, cof_f)],
                    [(pc.F_FRETE, frete)], {"P02", "P05"})
        self.L.lanc(d, "J15", "Antecipação parcial do ICMS - NF 3.369", [(pc.ICMS_ANT_REC, antec)], [(pc.ICMS_ANT_RECOL, antec)], {"P03"})
        self.alpha_q += q
        self.alpha_v = r2(self.alpha_v + custo_m + custo_f)
        self.L.memo("J15", f"Estoque ALPHA após a compra: {int(self.alpha_q)} un; custo médio {self.alpha_v / self.alpha_q:.4f}".replace(".", ","), self.alpha_v)
        self.frete_j15 = frete

    def j16(self, d):
        v = self.p("evento", "J16", "comissão")
        iss, pis, cof, ir = r2(v * ISS_FORTALEZA), r2(v * PIS), r2(v * COFINS), r2(v * IRRF_SERVICOS)
        for t, val in (("Comissão (NFS-e 002)", v), ("ISS 5%", iss), ("PIS 1,65%", pis), ("COFINS 7,6%", cof),
                       ("IRRF 1,5% retido pelo tomador", ir), ("Valor a receber", v - ir)):
            self.L.memo("J16", t, val)
        self.L.lanc(d, "J16", "NFS-e 002 - comissão de representação", [(pc.COMISSOES_REC, v - ir), (pc.IRRF_REC, ir)],
                    [(pc.REC_SERVICOS, v)], {"P09"})
        self.L.lanc(d, "J16", "Tributos sobre a comissão", [(pc.DED_ISS, iss), (pc.DED_PIS, pis), (pc.DED_COFINS, cof)],
                    [(pc.ISS_RECOL, iss), (pc.PIS_RECOL, pis), (pc.COFINS_RECOL, cof)], {"P09"})
        self.receitas["servicos"] += v
        self.irrf_receitas += ir
        self.comissao_liq = r2(v - ir)

    def j17(self, d):
        self.pagar(d, "J17", "Pagamento de água, energia e telefone fixo de 01/2026",
                   [(pc.AGUA_PAGAR, self.agua_jan), (pc.ENERGIA_PAGAR, self.energia_jan), (pc.TEL_PAGAR, self.fixo_jan)])
        self.L.premissas_evento["J17"].add("P26")

    def j18(self, d):
        ev = "J18"
        func = [f for f in self.v.get("folha", []) if f.get("salario_jan")]
        n = len(func) or 1
        vt_ind, va_ind = r2(172.80 / n), r2(1773.00 / n)
        tot = defaultdict(float)
        deb = defaultdict(float)
        cred = defaultdict(float)
        linhas = []
        for f in func:
            a = area(f["setor"])
            sal, he, com = f["salario_jan"] or 0, f.get("he_jan") or 0, f.get("comissao_jan") or 0
            rem = r2(sal + he + com)
            inss = inss_empregado(min(rem, TETO_INSS))
            ids = idades(f.get("dependentes_jan"))
            deps = sum(1 for i in ids if i <= 21)
            ir, nota = irrf(rem, inss, deps)
            sf = r2(SALARIO_FAMILIA_COTA * sum(1 for i in ids if i <= 14)) if rem <= SALARIO_FAMILIA_LIMITE else 0.0
            dvt = r2(min(sal * 0.06, vt_ind))
            dva = r2(va_ind * 0.05)
            liq = r2(rem + sf - inss - ir - dvt - dva)
            linhas.append((f["nome"], rem, inss, ir, sf, dvt, dva, liq, nota))
            deb[pc.POR_AREA["salarios"][a]] += sal + he
            if com:
                deb[pc.COMISSOES] += com
            enc = r2(rem * ENCARGOS_INSS_FOLHA)
            fg = r2(rem * FGTS)
            deb[pc.POR_AREA["inss"][a]] += enc
            deb[pc.POR_AREA["fgts"][a]] += fg
            fer, dec = r2(rem / 12 * 4 / 3), r2(rem / 12)
            deb[pc.POR_AREA["ferias"][a]] += fer + r2(fer * ENCARGOS_INSS_FOLHA) + r2(fer * FGTS)
            deb[pc.POR_AREA["decimo"][a]] += dec + r2(dec * ENCARGOS_INSS_FOLHA) + r2(dec * FGTS)
            cred[pc.PROV_FERIAS] += fer
            cred[pc.INSS_FERIAS] += r2(fer * ENCARGOS_INSS_FOLHA)
            cred[pc.FGTS_FERIAS] += r2(fer * FGTS)
            cred[pc.PROV_13] += dec
            cred[pc.INSS_13] += r2(dec * ENCARGOS_INSS_FOLHA)
            cred[pc.FGTS_13] += r2(dec * FGTS)
            deb[pc.POR_AREA["vt"][a]] += vt_ind - dvt
            deb[pc.POR_AREA["va"][a]] += va_ind - dva
            cred[pc.INSS_REC] += inss + enc - sf
            cred[pc.FGTS_REC] += fg
            cred[pc.IRRF_RECOL] += ir
            cred[pc.SAL_PAGAR] += liq
            cred[pc.VT] += vt_ind - dvt
            cred[pc.VA] += va_ind - dva
            # VT/VA consumidos: parte descontada do empregado sai do adiantamento e reduz o líquido
            cred[pc.VT] += dvt
            cred[pc.VA] += dva
            deb["__desc__"] += dvt + dva
            for k, val in (("rem", rem), ("inss", inss), ("ir", ir), ("sf", sf), ("liq", liq), ("enc", enc), ("fgts", fg)):
                tot[k] += val
        # o desconto de VT/VA já reduziu o líquido; a contrapartida é o próprio adiantamento
        deb.pop("__desc__", None)
        # ajuste: crédito de INSS inclui encargos e salário-família compensado
        for nome, rem, inss, ir, sf, dvt, dva, liq, nota in linhas:
            self.L.memo(ev, f"{nome}: remuneração {fmt(rem)}; INSS {fmt(inss)}; IRRF {fmt(ir)} ({nota}); "
                            f"sal.-família {fmt(sf)}; desc. VT {fmt(dvt)} / VA {fmt(dva)}", liq, "líquido")
        self.L.memo(ev, "Encargos INSS 27,80% sobre a folha", tot["enc"])
        self.L.memo(ev, "FGTS 8%", tot["fgts"])
        # pró-labore
        pl_deb, pl_cred = defaultdict(float), defaultdict(float)
        for s in self.v.get("socios", []):
            pl = float(s.get("pro_labore_jan") or 0)
            if not pl:
                continue
            a = 1 if "comerc" in (s.get("funcao") or "").lower() else 0
            inss = r2(min(pl, TETO_INSS) * 0.11)
            soc = next((x for x in [s]), s)
            deps = sum(1 for i in idades(s.get("dependentes") or self._dep_socio(s["nome"])) if i <= 21)
            ir, nota = irrf(pl, inss, deps)
            pat = r2(pl * INSS_PATRONAL_CI)
            pl_deb[pc.POR_AREA["prolabore"][a]] += pl
            pl_deb[pc.POR_AREA["inss"][a]] += pat
            pl_cred[pc.PROLAB_PAGAR] += pl - inss - ir
            pl_cred[pc.INSS_REC] += inss + pat
            pl_cred[pc.IRRF_RECOL] += ir
            self.L.memo(ev, f"Pró-labore {soc['nome']}: {fmt(pl)}; INSS 11% {fmt(inss)}; IRRF {fmt(ir)} ({nota}); patronal 20% {fmt(pat)}",
                        pl - inss - ir, "líquido")
        self.L.lanc(d, ev, "Folha de pagamento de janeiro/2026", list(deb.items()), list(cred.items()), {"P01", "P16", "P17", "P18", "P19"})
        if pl_deb:
            self.L.lanc(d, ev, "Pró-labore de janeiro/2026", list(pl_deb.items()), list(pl_cred.items()), {"P01", "P16"})

    def _dep_socio(self, nome):
        for s in (self.v.get("socios_base") or []):
            if s.get("nome") == nome:
                return s.get("dependentes")
        return {"Adalberto Cantareira": "(2 e 8 anos)", "Marcela Soares": "(14 anos)", "Marconde Sobreira": "(7 anos)"}.get(nome, "")

    def j19(self, d):
        ev = "J19"
        deb, cred = defaultdict(float), defaultdict(float)
        itens = [
            ("Galpão", self.L.saldo(pc.GALPAO), 20, 80, (0.75, 0.25), pc.DEP_IMOVEIS),
            ("Máquinas industriais", self.L.saldo(pc.MAQUINAS), 8, 20, (1.0, 0.0), pc.DEP_MAQ),
            ("Veículo utilitário", self.L.saldo(pc.VEICULOS), 5, 40, (0.70, 0.30), pc.DEP_VEIC),
            ("Ar-condicionados (móveis e aparelhos)", self.L.saldo(pc.MOVEIS), 12, 10, (0.65, 0.35), pc.DEP_MOVEIS),
        ]
        for nome, valor, anos, resid, (pa, pv), conta in itens:
            if valor <= 0:
                continue
            q = r2(valor * (1 - resid / 100) / (anos * 12))
            va = r2(q * pa)
            deb[pc.POR_AREA["depreciacao"][0]] += va
            deb[pc.POR_AREA["depreciacao"][1]] += q - va
            cred[conta] += q
            self.L.memo(ev, f"{nome}: {fmt(valor)} × (1 − {resid}%) ÷ {anos * 12} meses; adm. {int(pa * 100)}% / vendas {int(pv * 100)}%", q)
        self.L.lanc(d, ev, "Depreciação de janeiro/2026", list(deb.items()), list(cred.items()), {"P19", "P20"})

    def integralizar(self, d, ev, nome):
        s = next((x for x in self.v.get("socios", []) if x["nome"] == nome), None)
        if not s:
            return
        v = float(s.get("a_integralizar") or 0)
        _, aint = pc.CAPITAL[nome]
        self.L.memo(ev, f"Integralização de {nome}", v)
        self.L.lanc(d, ev, f"Integralização de capital - {nome}", [(pc.BANCO, v)], [(aint, v)])

    def j20(self, d):
        self.integralizar(d, "J20", "Marcela Soares")

    def j21(self, d):
        self.pagar(d, "J21", "Pagamento da 4ª parcela do seguro", [(pc.F_SEGURO, 2100.00)])

    def j22(self, d):
        self.pagar(d, "J22", "Pagamento do CT-e 423.765", [(pc.F_FRETE, self.frete_j15)])

    def j23(self, d):
        ev = "J23"
        v = self.p("contrato", "C11", "valor")
        inss = r2(min(v, TETO_INSS) * 0.11)
        ir, nota = irrf(v, inss, 0)
        iss = r2(v * ISS_FORTALEZA)
        pat = r2(v * INSS_PATRONAL_CI)
        liq = r2(v - inss - ir - iss)
        for t, val in (("Valor bruto do RPA", v), ("INSS 11% retido (teto)", inss), (f"IRRF ({nota})", ir), ("ISS 5% retido", iss),
                       ("Líquido a pagar em 17/02", liq), ("INSS patronal 20% (capitalizado)", pat)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "RPA arquiteto - projeto da reforma do galpão", [(pc.OBRAS, v + pat)],
                    [(pc.F_RPA, liq), (pc.INSS_REC, inss + pat), (pc.IRRF_RECOL, ir), (pc.ISS_RET, iss)], {"P01", "P11"})

    def j24(self, d):
        ev = "J24"
        v = self.p("contrato", "C04", "valor")
        n = int(self.p("contrato", "C04", "prazo", 18))
        parcela = r2(v / n)
        cp = r2(v * min(12, n) / n)
        self.leasing = {"saldo": v, "data": d, "taxa": self.p("contrato", "C04", "taxa", 10)}
        for t, val in (("Valor das máquinas (arrendamento financeiro)", v), (f"Amortização SAC ({n} parcelas)", parcela),
                       ("Curto prazo (12 parcelas)", cp), ("Longo prazo", v - cp)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "Leasing financeiro - 2 máquinas industriais", [(pc.MAQ_LEASING, v)],
                    [(pc.LEASING_CP, cp), (pc.LEASING_LP, v - cp)], {"P13"})

    def j25(self, d):
        self.L.memo("J25", "Recebimento da comissão (líquida de IRRF)", self.comissao_liq)
        self.L.lanc(d, "J25", "Recebimento da NFS-e 002", [(pc.BANCO, self.comissao_liq)], [(pc.COMISSOES_REC, self.comissao_liq)])

    def j26(self, d):
        ev = "J26"
        tot = self.p("contrato", "C12", "valor")
        pm = self.p("contrato", "C12", "material", 40)
        parc = r2(tot * 0.5)
        mo = r2(parc * (1 - pm / 100))
        inss, iss = r2(mo * 0.11), r2(mo * ISS_FORTALEZA)
        for t, val in (("Contrato de reforma", tot), ("1ª parcela (50%)", parc), (f"Mão de obra ({fmt(100 - pm)}%)", mo),
                       ("INSS retido 11% (mão de obra)", inss), ("ISS retido 5% (mão de obra)", iss), ("Valor pago", parc - inss - iss)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "NFS-e 6.300 Construtor Express - 1ª parcela da reforma", [(pc.OBRAS, parc)],
                    [(pc.BANCO, parc - inss - iss), (pc.INSS_RET, inss), (pc.ISS_RET, iss)], {"P12"})

    def j27(self, d):
        ev = "J27"
        q = self.p("evento", "J27", "quantidade")
        mk = self.v.get("markup", {}) or {}
        margem = float(mk.get("margem_contribuicao") or 45)
        div = 1 - (ICMS_INTERNO_CE * 100 + PIS * 100 + COFINS * 100 + margem) / 100
        cm = self.alpha_v / self.alpha_q
        preco = r2(cm * (1 / div))
        rec = r2(q * preco)
        icms = r2(rec * ICMS_INTERNO_CE)
        pis, cof = r2((rec - icms) * PIS), r2((rec - icms) * COFINS)
        cmv = r2(q * cm)
        for t, val in (("Custo médio ALPHA", cm), (f"Mark-up divisor {div:.4f} → multiplicador {1 / div:.4f}".replace(".", ","), None),
                       ("Preço unitário", preco), (f"Receita ({int(q)} un)", rec), ("ICMS 20%", icms), ("PIS 1,65% (base sem ICMS)", pis),
                       ("COFINS 7,6% (base sem ICMS)", cof), ("CMV", cmv)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "NF 001 Comercial Caribe - venda de ALPHA", [(pc.CLIENTES, rec)], [(pc.REC_REVENDA, rec)], {"P06", "P07"})
        self.L.lanc(d, ev, "Tributos sobre a venda - NF 001", [(pc.DED_ICMS, icms), (pc.DED_PIS, pis), (pc.DED_COFINS, cof)],
                    [(pc.ICMS_RECOL, icms), (pc.PIS_RECOL, pis), (pc.COFINS_RECOL, cof)], {"P06"})
        self.L.lanc(d, ev, "Baixa do estoque - NF 001 (CMV)", [(pc.CMV, cmv)], [(pc.ALPHA, cmv)], {"P07"})
        self.alpha_q -= q
        self.alpha_v = r2(self.alpha_v - cmv)
        self.receitas["revenda"] += rec
        self.venda_j27 = rec

    def j28(self, d):
        self.pagar(d, "J28", "Pagamento da GPS (INSS) de 12/2025", [(pc.INSS_REC, 12822.74)])

    def j29(self, d):
        ev = "J29"
        b = self.p("evento", "J29", "base")
        aliq = self.p("evento", "J29", "alíquota", 18)
        icms = r2(b * aliq / 100)
        multa = r2(icms * 0.75)
        multa_red = r2(multa * 0.30)
        for t, val in (("Base de cálculo", b), (f"ICMS {fmt(aliq)}%", icms), ("Multa 75% do ICMS", multa),
                       ("Multa com redução de 70%", multa_red), ("Total a pagar em 05/02", icms + multa_red)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "Auto de infração SEFAZ-CE", [(pc.DESP_ICMS_AUTO, icms), (pc.MULTAS, multa_red)],
                    [(pc.AUTO, icms + multa_red)], {"P21"})

    def j30(self, d):
        ev = "J30"
        ins = self.x.insumo("MP-A")
        q = float(ins.get("compra") or self.p("evento", "J30", "quantidade"))
        cu = float(ins.get("custo_unit") or self.p("evento", "J30", "custo"))
        prod = r2(q * cu)
        ipi = r2(prod * ALIQ_IPI["9002.11.11"])
        total = r2(prod + ipi)
        icms = r2(prod * ICMS_INTERESTADUAL["MG"])
        pis, cof = r2((prod - icms) * PIS), r2((prod - icms) * COFINS)
        custo = r2(prod - icms - pis - cof)
        vista = r2(total * 0.25)
        for t, val in ((f"{int(q)} un × {cu:.4f}".replace(".", ","), prod), ("IPI 9,75% (recuperável)", ipi), ("Total da NF", total),
                       ("ICMS 7% (crédito)", icms), ("PIS (crédito)", pis), ("COFINS (crédito)", cof), ("Custo da MP-A", custo),
                       ("Pagamento à vista (25%)", vista)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "NF 23.456 Indústria Sofisticada - MP-A",
                    [(pc.MPA, custo), (pc.IPI_REC, ipi), (pc.ICMS_REC, icms), (pc.PIS_REC, pis), (pc.COFINS_REC, cof)],
                    [(pc.BANCO, vista), (pc.F_SOFISTICADA, total - vista)], {"P02", "P05", "P08"})

    def j31(self, d):
        self.pagar(d, "J31", "Pagamento de PIS e COFINS de 12/2025", [(pc.PIS_RECOL, 5045.29), (pc.COFINS_RECOL, 23238.90)])

    def j32(self, d):
        self.pagar(d, "J32", "Pagamento de telefone, energia e água de 12/2025",
                   [(pc.TEL_PAGAR, 350.00), (pc.ENERGIA_PAGAR, 1480.00), (pc.AGUA_PAGAR, 420.00)])

    def j33(self, d):
        self.L.memo("J33", "Recebimento NF 001", self.venda_j27)
        self.L.lanc(d, "J33", "Recebimento Comercial Caribe - NF 001", [(pc.BANCO, self.venda_j27)], [(pc.CLIENTES, self.venda_j27)])

    def j34(self, d):
        self.integralizar(d, "J34", "Cassilda Apedeuta")

    def j35(self, d):
        self.pagar(d, "J35", "Pagamento de ICMS normal e antecipado de 12/2025",
                   [(pc.ICMS_RECOL, 43361.81), (pc.ICMS_ANT_RECOL, 13258.52)])

    def _func_fev(self) -> int:
        return sum(1 for f in self.v.get("folha", []) if f.get("salario_fev") or f.get("pendente"))

    def j36(self, d):
        n = self._func_fev()
        v = r2(n * 18 * 2 * 5.40)
        self.L.memo("J36", f"VT fevereiro: {n} empregados × 18 dias × 2 × R$ 5,40", v)
        self.L.lanc(d, "J36", "Compra de vale-transporte para fevereiro", [(pc.VT, v)], [(pc.BANCO, v)], {"P17"})

    def j37(self, d):
        n = self._func_fev()
        v = r2(n * 18 * 1 * 26.00)
        self.L.memo("J37", f"VA fevereiro: {n} empregados × 18 dias × R$ 26,00", v)
        self.L.lanc(d, "J37", "Compra de vale-alimentação para fevereiro", [(pc.VA, v)], [(pc.BANCO, v)], {"P17"})

    def j38(self, d):
        self.pagar(d, "J38", "Pagamento de IRPJ e CSLL de 12/2025", [(pc.IRPJ_RECOL, 33198.47), (pc.CSLL_RECOL, 12671.45)])

    def j39(self, d):
        h = self.p("contrato", "C06", "honorário", 5500)
        ir, cs = r2(h * IRRF_SERVICOS), r2(h * CSRF)
        for t, val in (("Honorários de janeiro", h), ("IRRF 1,5%", ir), ("CSRF 4,65%", cs), ("Líquido a pagar em 10/02", h - ir - cs)):
            self.L.memo("J39", t, val)
        self.L.lanc(d, "J39", "NFS-e 023 Contador Formado - janeiro", [(pc.ASSESSORIA, h)],
                    [(pc.F_CONTADOR, h - ir - cs), (pc.IRRF_RECOL, ir), (pc.CSRF_RECOL, cs)], {"P10"})

    # ---------------- fim do mês
    def ajustes(self, d):
        ev = "AJ"
        premio = self.p("contrato", "C09", "prêmio", 6300)
        seg = r2(premio / 12)
        self.L.memo(ev, "Apropriação do seguro (1/12 do prêmio)", seg)
        self.L.lanc(d, ev, "Apropriação do seguro - janeiro", [(pc.SEGUROS, seg)], [(pc.SEGUROS_APROP, seg)], {"P25"})
        rec = self.p("contrato", "C05", "honor", 8800)
        self.L.memo(ev, "Recrutamento: metade dos honorários", r2(rec / 2))
        self.L.lanc(d, ev, "Apropriação do serviço de recrutamento - janeiro", [(pc.SERV_PJ, rec / 2)], [(pc.F_RECRUT, rec / 2)], {"P25"})
        if self.invest and self.invest["saldo"] > 0:
            self._apropria(self.invest, pc.INVEST, d, ev, "INVEST LIQUID")
        if self.cdb:
            self._apropria(self.cdb, pc.CDB, d, ev, "CDB Renda Mais")
        self._juros_garantida(d, ev)
        if self.leasing:
            ls = self.leasing
            j = r2(ls["saldo"] * ((1 + ls["taxa"] / 100) ** ((d - ls["data"]).days / 365) - 1))
            self.L.memo(ev, f"Juros do leasing ({(d - ls['data']).days} dias a {fmt(ls['taxa'])}% a.a.)", j)
            self.L.lanc(d, ev, "Juros do arrendamento financeiro - janeiro", [(pc.JUROS_LEASING, j)], [(pc.LEASING_CP, j)], {"P13"})

    def j40(self, d):
        ev = "J40"
        L = self.L
        # ICMS: crédito do antecipado de dezembro pago em 29/01
        ant = 13258.52
        L.lanc(d, ev, "Crédito do ICMS antecipado de 12/2025 (pago em 29/01)", [(pc.ICMS_REC, ant)], [(pc.ICMS_ANT_REC, ant)], {"P03"})
        for nome, deb_c, cred_c in (("ICMS", pc.ICMS_RECOL, pc.ICMS_REC), ("PIS", pc.PIS_RECOL, pc.PIS_REC),
                                    ("COFINS", pc.COFINS_RECOL, pc.COFINS_REC), ("IPI", pc.IPI_RECOL, pc.IPI_REC)):
            debitos = -L.saldo(deb_c)
            creditos = L.saldo(cred_c)
            comp = r2(min(debitos, creditos))
            L.memo(ev, f"{nome}: débitos {fmt(debitos)} − créditos {fmt(creditos)}",
                   debitos - creditos, "a recolher" if debitos > creditos else "saldo credor")
            if comp > 0:
                L.lanc(d, ev, f"Apuração do {nome} de janeiro", [(deb_c, comp)], [(cred_c, comp)], {"P23"})
        # IRPJ / CSLL por estimativa
        rv, rs, rf = (r2(self.receitas[k]) for k in ("revenda", "servicos", "financeiras"))
        b_ir = r2(rv * 0.08 + rs * 0.32 + rf)
        b_cs = r2(rv * 0.12 + rs * 0.32 + rf)
        irpj = r2(b_ir * 0.15 + max(0.0, b_ir - 20000) * 0.10)
        csll = r2(b_cs * 0.09)
        for t, val in (("Receita de revenda", rv), ("Receita de serviços", rs), ("Receitas financeiras", rf),
                       ("Base IRPJ (8% / 32% / 100%)", b_ir), ("IRPJ 15% + adicional 10%", irpj),
                       ("Base CSLL (12% / 32% / 100%)", b_cs), ("CSLL 9%", csll)):
            L.memo(ev, t, val)
        L.lanc(d, ev, "IRPJ e CSLL por estimativa - janeiro", [(pc.IRPJ_DESP, irpj), (pc.CSLL_DESP, csll)],
               [(pc.IRPJ_RECOL, irpj), (pc.CSLL_RECOL, csll)], {"P22"})
        comp = r2(min(irpj, L.saldo(pc.IRRF_REC) + L.saldo(pc.IRRF_APLIC)))
        if comp > 0:
            c1 = min(comp, L.saldo(pc.IRRF_REC))
            L.memo(ev, "IRRF retido compensado na estimativa", comp)
            L.lanc(d, ev, "Compensação do IRRF retido com o IRPJ", [(pc.IRPJ_RECOL, comp)],
                   [(pc.IRRF_REC, c1), (pc.IRRF_APLIC, comp - c1)], {"P22"})

    # ---------------- execução
    EVENTOS = {
        "J01": (2, "j01"), "J02": (2, "j02"), "J03": (5, "j03"), "J04": (5, "j04"), "J05": (6, "j05"), "J06": (6, "j06"),
        "J07": (7, "j07"), "J08": (8, "j08"), "J09": (8, "j09"), "J10": (9, "j10"), "J11": (9, "j11"), "J12": (9, "j12"),
        "J13": (9, "j13"), "J14": (12, "j14"), "J15": (12, "j15"), "J16": (13, "j16"), "J17": (14, "j17"),
        "J18": (15, "j18"), "J19": (15, "j19"), "J20": (16, "j20"), "J21": (19, "j21"), "J22": (19, "j22"),
        "J23": (20, "j23"), "J24": (20, "j24"), "J25": (21, "j25"), "J26": (22, "j26"), "J27": (23, "j27"),
        "J28": (23, "j28"), "J29": (26, "j29"), "J30": (26, "j30"), "J31": (27, "j31"), "J32": (27, "j32"),
        "J33": (28, "j33"), "J34": (28, "j34"), "J35": (29, "j35"), "J36": (30, "j36"), "J37": (30, "j37"),
        "J38": (30, "j38"), "J39": (30, "j39"),
    }

    def executar(self) -> dict:
        por_dia = defaultdict(list)
        for ev, (dia, metodo) in self.EVENTOS.items():
            por_dia[dia].append((ev, metodo))
        for dia in sorted(por_dia):
            d = date(ANO, 1, dia)
            for ev, metodo in sorted(por_dia[dia]):
                getattr(self, metodo)(d)
            self.tesouraria(d)
        self.ajustes(FIM_MES)
        self.j40(FIM_MES)
        self.tesouraria(FIM_MES)
        return self.resultado()

    def resultado(self) -> dict:
        L = self.L
        contas = []
        for c, info in pc.CONTAS.items():
            ini, mov_d, mov_c = L.ini.get(c, 0.0), 0.0, 0.0
            for l in L.lancs:
                mov_d += sum(p["valor"] for p in l["debitos"] if p["conta"] == c)
                mov_c += sum(p["valor"] for p in l["creditos"] if p["conta"] == c)
            fim = r2(ini + mov_d - mov_c)
            if abs(ini) < 0.005 and abs(mov_d) < 0.005 and abs(mov_c) < 0.005:
                continue
            contas.append({"conta": c, "nome": info["nome"], "inicial": r2(ini), "debitos": r2(mov_d),
                           "creditos": r2(mov_c), "final": fim})
        tot_d = r2(sum(x["final"] for x in contas if x["final"] > 0))
        tot_c = r2(-sum(x["final"] for x in contas if x["final"] < 0))
        ativo = r2(sum(x["final"] for x in contas if x["conta"].startswith("1")))
        passivo_pl = r2(-sum(x["final"] for x in contas if x["conta"].startswith("2")))
        resultado = r2(-sum(x["final"] for x in contas if x["conta"].startswith("3")))
        usadas = sorted({p for l in L.lancs for p in l["premissas"]})
        return {
            "formato": "labcont-gabarito/1", "mes": "2026-01",
            "lancamentos": L.lancs, "memoria": dict(L.memoria), "balancete": contas,
            "totais": {"devedor": tot_d, "credor": tot_c, "ativo": ativo, "passivo_pl": passivo_pl, "resultado": resultado,
                       # o balanço de 2025 tem R$ 0,01 de arredondamento (depreciação acumulada 10.408,33 x 10.408,34)
                       "diferenca": r2(tot_d - tot_c),
                       "fecha": abs(tot_d - tot_c) <= 0.015 and abs(ativo - passivo_pl - resultado) <= 0.015},
            "premissas": {k: PREMISSAS[k] for k in usadas},
            "premissas_evento": {k: sorted(v) for k, v in L.premissas_evento.items()},
        }


def gerar_gabarito(valores: dict) -> dict:
    return Gabarito(valores).executar()

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
ISS_CONSTRUCAO = 0.03  # CTM Fortaleza, art. 245, II: subitens 7.2, 7.4 e 7.5
IRRF_SERVICOS, CSRF = 0.015, 0.0465
IR_APLICACAO = 0.225  # até 180 dias
ALIQ_IPI = {"9002.11.11": 0.0975}  # TIPI - MP-A
# TIPI 2022 (ADE RFB nº 1/2026) por NCM: insumos e produtos de fevereiro
TIPI = {"9002.11.11": 0.0975, "9007.20.20": 0.13, "9002.20.10": 0.0975, "9008.50.00": 0.13, "9013.20.00": 0.0975,
        "9011.20.20": 0.0325, "3923.21.10": 0.0975, "9006.53.20": 0.0975, "9007.10.00": 0.195}
NCM = {"MP-A": "9002.11.11", "MP-B": "9007.20.20", "MS-Z": "9002.20.10", "MS-Q": "9008.50.00", "MS-R": "9013.20.00",
       "MS-K": "9011.20.20", "ME-H": "3923.21.10", "X": "9006.53.20", "Y": "9007.10.00"}
ICMS_UF = {"MA": 0.12, "PB": 0.12, "TO": 0.12, "AM": 0.12, "MG": 0.07, "RJ": 0.07, "PA": 0.12}
ICMS_INTERNO_MA = 0.23  # alíquota modal do Maranhão desde 23/02/2025

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
    "P12": "Reforma do galpão (empreitada com material): 1ª parcela de 50% paga na entrada da NFS-e; retenção de INSS 11% e ISS 3% (CTM Fortaleza, art. 245, II, subitem 7.2; materiais fora da base, art. 240, § 4º, I) sobre a parcela de mão de obra; sem IRRF/CSRF. Capitalizada em Imobilizado em andamento.",
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
    # ---------------- fevereiro (Etapa 8)
    "P27": "Obrigações da competência 01/2026 pagas em fevereiro pelos saldos do gabarito em 31/01 (folha, encargos, tributos e fornecedores). O IRRF (R$ 348,93) e a CSRF (R$ 255,75) de 12/2025 não têm evento de pagamento no exercício e continuam a recolher; os pagamentos de fevereiro recolhem só a competência 01/2026.",
    "P28": "Em fevereiro há produção: a parcela industrial das utilidades e dos itens do quadro de alocação é custo indireto de fabricação (CIF), acumulada em contas de CIF a apropriar e rateada entre X e Y pelo custo dos materiais diretos. A energia dos setores do Produto X e do Produto Y é tratada como CIF (não há medição por ordem de produção).",
    "P29": "Utilidades de fevereiro: energia pela fatura (comercial, Produto X e Produto Y; administrativa = diferença), com crédito de PIS 1,65% e COFINS 7,6% sobre o total, deduzido proporcionalmente de cada área; água sem crédito, administrativa e comercial pela fatura e industrial = diferença; telefone fixo e celulares 20/60/20 e internet 40/50/10 (adm./vendas/industrial).",
    "P30": "Ar Frio: pagamento de 45% do valor da NF 7.852 em 09/02, como descrito no evento (o contrato previa parcelas de 40%). Indústria Sofisticada: 30% do total da NF 23.456 (com IPI) em 25/02.",
    "P31": "Reforma: 2ª parcela (50%) com as mesmas retenções da 1ª (INSS 11% e ISS 3% sobre a mão de obra). Concluída em 23/02, o imobilizado em andamento (projeto, encargo e parcelas) é transferido para Edifícios e Construções; a depreciação começa em março (a de fevereiro é processada em 13/02).",
    "P32": "Leasing (SAC): 1ª parcela em 23/02 = amortização (valor ÷ prazo) + juros compostos pelo ano civil desde 20/01. Os juros de janeiro já apropriados saem do passivo e os de fevereiro até o pagamento vão para despesa; depois do pagamento, uma parcela passa do longo para o curto prazo (o circulante mantém as próximas 12).",
    "P33": "Mútuo à sócia (parte relacionada, sem vencimento): Realizável a Longo Prazo (Lei 6.404/76, art. 179, II), pelo valor do evento; juros compostos pela taxa do contrato, por fração diária (mês de 30 dias), apropriados no fim do mês como receita financeira. IOF desconsiderado.",
    "P34": "Recrutamento: a NFS-e 345 (26/02) reconhece a metade de fevereiro (a de janeiro já estava apropriada) e retém IRRF de 1,5% sobre o total (RIR/2018, art. 714); sem CSRF, porque o serviço não está na lista da Lei 10.833/2003, art. 30 (SC Disit/SRRF08 nº 8.048/2018). Não há evento de pagamento no exercício.",
    "P35": "Contabilidade de fevereiro: honorário reajustado pelo percentual do contrato (C06), arredondado a R$ 100, com IRRF 1,5% e CSRF 4,65%.",
    "P36": "Vale-transporte e vale-alimentação de março: 20 dias úteis × empregados de fevereiro (não há admissões previstas para março).",
    "P38": "IPI pela TIPI 2022 (ADE RFB nº 1/2026): MP-B 13% (NCM 9007.20.20). Só o fornecedor industrial (Indústria Zalego) destaca IPI; o Distribuidor Verde Oliva e a Embalagens Comerciais vendem como comerciantes (CFOP 6.102), sem IPI. O IPI destacado na compra de insumo é crédito do estabelecimento industrial (RIPI, art. 226, I) e não integra o custo.",
    "P39": "Insumos de outros estados: ICMS interestadual de 12% (TO e AM) e 7% (RJ), com crédito integral de ICMS, PIS e COFINS (base sem o ICMS). Não há antecipação parcial (exigida na entrada de mercadoria para comercialização) nem DIFAL (não é uso e consumo).",
    "P40": "Desconto financeiro condicional da NF 12.380: não reduz o custo da MP-B nem a base dos tributos (CPC 16, item 11, trata só dos descontos comerciais); é receita financeira quando obtido. Em 04/02 ele é obtido sobre a parcela paga à vista (35% do total da nota); o do saldo será reconhecido no pagamento de 03/03.",
    "P41": "Fretes FOB das compras de insumos (CT-e 424.110 e 425.130): integram o custo do insumo, com crédito de ICMS 12% e de PIS/COFINS; pagos em 18/02 e 24/02 pelo valor do CT-e (sem juros pelo atraso do 424.110, vencido em 13/02). Frete CIF da NF 9.147: sem lançamento.",
    "P42": "Estoques pelo custo médio ponderado móvel, um estoque por insumo. Devolução de compra (NF 004, CFOP 6.201) pelo custo da compra devolvida: baixa do estoque, estorno dos créditos de ICMS, IPI, PIS e COFINS e abatimento do saldo do fornecedor pelo valor da nota (produtos + IPI).",
    "P43": "Folha de fevereiro (processada em 13/02) pelos critérios de P16 a P18, com 15 empregados (os admitidos em 01/02 trabalham o mês inteiro). Vale-transporte e vale-alimentação consumidos = compras de 30/01 divididas igualmente. A mão de obra direta (setores dos Produtos X e Y), com encargos, provisões e benefícios, acumula em \"Mão de Obra Direta a Apropriar\" de cada produto; a mão de obra indireta vai para CIF. Renato Português (MOD do Produto X) não tem salário no exercício: o gabarito usa o salário mínimo até a decisão do professor.",
    "P44": "Pró-labore de fevereiro: Marconde Sobreira, sócio industrial, passa a receber; como dirige a produção, o pró-labore e o INSS patronal de 20% são CIF. Adalberto Cantareira (administração) e Marcela Soares (comercial) seguem como em janeiro.",
    "P45": "Depreciação de fevereiro (13/02): mesmos métodos de P20 e rateio do quadro de alocação (prédio 10/25/65, máquinas 100% industrial, veículo utilitário 70/30, móveis 45/35/20). As máquinas arrendadas depreciam desde fevereiro (100% industrial); a reforma, concluída em 23/02, deprecia a partir de março. A parcela industrial é CIF.",
    "P46": "Produção de fevereiro: começa em 19/02 (dia seguinte à compra do ME-H) e termina em 23/02 (três dias úteis: 19, 20 e 23/02). A requisição de 19/02 baixa os insumos pelo custo médio do dia, nas quantidades da ficha técnica × produção do mês. Todos os itens da ficha técnica (matérias-primas, materiais secundários e embalagem) são materiais diretos.",
    "P47": "CIF de fevereiro (energia, água e telefonia industriais, mão de obra indireta, pró-labore industrial e depreciação industrial) rateados entre X e Y na proporção do custo dos materiais diretos. Em 23/02, fim da produção, MOD e CIF são apropriados aos produtos em elaboração, que passam a produtos acabados; custo unitário = custo total ÷ unidades produzidas.",
    "P48": "Preço de venda (ALPHA, Produto X e Produto Y) pelo mark-up do exercício: custo médio na data × 1 ÷ [1 − (ICMS 20% + PIS 1,65% + COFINS 7,6% + margem de contribuição)], com esses percentuais mesmo quando a operação tem outra alíquota de ICMS; arredondado a centavos. A baixa do estoque (CMV ou CPV) é pelo custo médio da data.",
    "P49": "Venda a consumidor final não contribuinte em outro estado (NF 337, São Luís-MA): ICMS interestadual de 12% para o Ceará e DIFAL = valor da operação × (23% − 12%) para o Maranhão (EC 87/2015; LC 190/2022; alíquota modal do MA de 23% desde 23/02/2025), recolhido pelo remetente e registrado como dedução da receita. PIS e COFINS sobre a receita menos o ICMS destacado. Frete por conta do cliente.",
    "P50": "Venda de X e Y à Comercial Roma (PA, contribuinte, para revenda): IPI pela TIPI (X 9,75%; Y 19,5%, alíquota geral) sobre o valor dos produtos e cobrado à parte. Ele não é receita (Decreto-Lei 1.598/77, art. 12, § 4º, com redação da Lei 12.973/2014) e não integra a base do ICMS (CF, art. 155, § 2º, XI). ICMS interestadual de 12%; sem DIFAL (destinatário contribuinte).",
    "P51": "Desconto financeiro sobre o Produto Y: incide sobre o valor dos produtos Y, é concedido na emissão e abatido da parcela recebida (80% do total da nota). Não reduz a receita bruta nem a base dos tributos: é despesa financeira. O saldo (20%) vence em 22/03.",
    "P52": "Devolução de venda (NF 1.320 da Comercial Caribe, ALPHA): pelo preço da venda original, como dedução da receita (devoluções de vendas), com estorno de ICMS, PIS e COFINS (a recuperar) e retorno ao estoque pelo custo médio da saída; abatida do boleto. O recebimento de 27/02 é pelo valor líquido.",
    "P53": "Apuração de fevereiro (28/02) pelos critérios de P23: débitos e créditos de ICMS, IPI, PIS e COFINS compensados; saldo credor permanece a recuperar. O ICMS antecipado de 01/2026, pago em 26/02, vira crédito em fevereiro (P03). O DIFAL devido ao Maranhão é recolhido à parte (GNRE), sem compensação. Créditos de PIS/COFINS limitados a insumos, fretes, energia e devoluções, como em janeiro: sem créditos sobre depreciação de máquinas e contraprestações de leasing e sem PIS/COFINS sobre receitas financeiras (simplificação didática).",
    "P54": "IRPJ e CSLL por estimativa de fevereiro (P22): revenda (líquida de devoluções) e venda de produtos com presunção de 8% (IRPJ) e 12% (CSLL); serviços 32%; receitas financeiras integrais (rendimentos, juros do mútuo e descontos obtidos). IRPJ 15% + adicional de 10% sobre o que exceder R$ 20.000,00 no mês; CSLL 9%; IRRF retido sobre receitas compensado com o IRPJ.",
    "P55": "Conta garantida sem trava de limite: em fevereiro as compras de insumos (04/02 a 18/02) acontecem antes do recebimento da venda de X e Y (24/02), e o saldo devedor passa do limite contratado. O gabarito registra o uso necessário para o caixa não ficar negativo e sinaliza o excesso na memória de cálculo. Cabe ao professor decidir se mantém, se amplia o limite ou se muda as datas do caso.",
    "P37": "Aplicações em fevereiro: CDB apropriado até 05/02 (F07) e no fim do mês; o resgate de 27/02 retira só o rendimento acumulado do INVEST LIQUID (saldo menos o valor aplicado remanescente), com IR de 22,5% a recuperar.",
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


def qtd(v) -> str:
    return f"{int(round(v)):,}".replace(",", ".")


def f4(v) -> str:
    return f"{v:.4f}".replace(".", ",")


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

    def abrir_mes(self):
        """Saldos finais viram os saldos de abertura do mês seguinte; lançamentos e memória recomeçam."""
        contas = set(self.ini) | set(self.mov)
        self.ini = {c: self.saldo(c) for c in contas}
        self.mov = defaultdict(float)
        self.lancs = []
        self.memoria = defaultdict(list)
        self.premissas_evento = defaultdict(set)

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
                dias = (ate - g['data']).days
                self.L.memo(ev, f"Juros conta garantida ({dias} {'dia' if dias == 1 else 'dias'} a {fmt(taxa)}% a.m.)", j)
                g["saldo"] = r2(g["saldo"] + j)
        g["data"] = ate

    def tesouraria(self, d: date, ev: str = "TES"):
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
                limite = self.p("contrato", "C01", "limite", 970000)
                acima = r2(self.garantida["saldo"] + falta) > limite
                self.L.lanc(d, ev, f"Uso da conta garantida em {d:%d/%m}", [(pc.BANCO, falta)], [(pc.GARANTIDA, falta)],
                            {"P15", "P55"} if acima else {"P15"})
                self.L.memo(ev, f"{d:%d/%m} uso da conta garantida", falta)
                self.garantida["saldo"] = r2(self.garantida["saldo"] + falta)
                self.garantida["data"] = d
                if acima:
                    self.L.memo(ev, f"Atenção: saldo da conta garantida acima do limite contratado de {fmt(limite)} (P55)",
                                self.garantida["saldo"], "acima do limite")
                    self.L.premissas_evento[ev].add("P55")
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
        self.ar_valor = valor

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
        inss, iss = r2(mo * 0.11), r2(mo * ISS_CONSTRUCAO)
        for t, val in (("Contrato de reforma", tot), ("1ª parcela (50%)", parc), (f"Mão de obra ({fmt(100 - pm)}%)", mo),
                       ("INSS retido 11% (mão de obra)", inss), ("ISS retido 3% (mão de obra)", iss), ("Valor pago", parc - inss - iss)):
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
        self.sof_total = total
        self.est = {"MP-A": [q, custo]}
        self.sof_unit = {"cu": cu, "custo_un": custo / q if q else 0.0}
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
            ls["juros_apropriados"] = ls.get("juros_apropriados", 0.0) + j

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


    # ================================================================== fevereiro (Etapa 8)
    def ab(self, conta: str) -> float:
        """Saldo de abertura de fevereiro (31/01), positivo para o lado natural da conta."""
        v = self.L.ini.get(conta, 0.0)
        return r2(v if pc.CONTAS[conta]["natureza"] == "D" else -v)

    def pagar_ab(self, d, ev, hist, contas: list[str], menos: dict | None = None, premissas=("P27",)):
        itens = [(c, r2(self.ab(c) - (menos or {}).get(c, 0.0))) for c in contas]
        itens = [(c, v) for c, v in itens if v > 0.004]
        if not itens:
            self.L.memo(ev, "Não há saldo a pagar desta competência", 0.0)
            self.L.premissas_evento[ev].update(premissas)
            return
        tot = r2(sum(v for _, v in itens))
        self.L.lanc(d, ev, hist, itens, [(pc.BANCO, tot)], set(premissas))
        for c, v in itens:
            self.L.memo(ev, f"{pc.CONTAS[c]['nome']} (saldo de 31/01)", v)

    @staticmethod
    def _repartir(total: float, pesos: list[float]) -> list[float]:
        """Divide um valor por pesos, com o arredondamento na maior parte."""
        soma = sum(pesos) or 1
        partes = [r2(total * w / soma) for w in pesos]
        i = max(range(len(partes)), key=lambda k: partes[k])
        partes[i] = r2(partes[i] + total - sum(partes))
        return partes

    def f01(self, d):
        ev = "F01"
        tot = self.p("evento", "F01", "valor total", 3400)
        base = self.x.base("evento", "F01", "valor total") or 3400
        com, px, py = (round(vb * tot / base / 10) * 10 for vb in (590, 1070, 1210))
        adm = r2(tot - com - px - py)
        pis, cof = r2(tot * PIS), r2(tot * COFINS)
        liq = self._repartir(r2(tot - pis - cof), [adm, com, px + py])
        for t, val in (("Conta de energia (total)", tot), ("Área administrativa (diferença)", adm), ("Área comercial", com),
                       ("Setor do Produto X (CIF)", px), ("Setor do Produto Y (CIF)", py),
                       ("Crédito de PIS 1,65% + COFINS 7,6% (sobre o total)", pis + cof),
                       ("Custo líquido: adm. / vendas / CIF", None)):
            self.L.memo(ev, t, val)
        for rot, v in zip(("administrativa", "vendas", "CIF"), liq):
            self.L.memo(ev, f"  {rot}", v)
        self.L.lanc(d, ev, "NF energia Luz do Sertão 988.333 - fevereiro",
                    [(pc.POR_AREA["energia"][0], liq[0]), (pc.POR_AREA["energia"][1], liq[1]), (pc.CIF_ENERGIA, liq[2]),
                     (pc.PIS_REC, pis), (pc.COFINS_REC, cof)], [(pc.ENERGIA_PAGAR, tot)], {"P05", "P28", "P29"})
        self.energia_fev = tot

    def f02(self, d):
        ev = "F02"
        tot = self.p("evento", "F02", "valor total", 1780)
        base = self.x.base("evento", "F02", "valor total") or 1780
        adm, com = (round(vb * tot / base / 10) * 10 for vb in (280, 320))
        ind = r2(tot - adm - com)
        for t, val in (("Fatura de água (total)", tot), ("Área administrativa", adm), ("Área comercial", com),
                       ("Área industrial (diferença, CIF)", ind)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "Fatura de água Águas do Litoral 322.666 - fevereiro",
                    [(pc.POR_AREA["agua"][0], adm), (pc.POR_AREA["agua"][1], com), (pc.CIF_AGUA, ind)],
                    [(pc.AGUA_PAGAR, tot)], {"P28", "P29"})
        self.agua_fev = tot

    def f03(self, d):
        ev = "F03"
        fixo = self.p("evento", "F03", "telefone", 690)
        cel = self.p("contrato", "C08", "mensalidade", 480)
        net = self.p("contrato", "C07", "mensalidade", 350)
        tel = fixo + cel
        adm, ven, ind = r2(tel * 0.20 + net * 0.40), r2(tel * 0.60 + net * 0.50), r2(tel * 0.20 + net * 0.10)
        ind = r2(tel + net - adm - ven)
        for t, val in (("Telefone fixo", fixo), ("Celulares (C08)", cel), ("Internet (C07)", net),
                       ("Administrativa: telefone 20% + internet 40%", adm), ("Vendas: telefone 60% + internet 50%", ven),
                       ("Industrial (CIF): telefone 20% + internet 10%", ind)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "NFs de telefonia e internet - fevereiro",
                    [(pc.POR_AREA["telefone"][0], adm), (pc.POR_AREA["telefone"][1], ven), (pc.CIF_TELEFONE, ind)],
                    [(pc.TEL_PAGAR, fixo), (pc.F_CELL, cel), (pc.F_INTERNET, net)], {"P28", "P29"})
        self.fixo_fev = fixo

    def f06(self, d):
        self.pagar_ab(d, "F06", "Pagamento do auto de infração (ICMS e multa reduzida)", [pc.AUTO], premissas=("P21", "P27"))

    def f07(self, d):
        if self.cdb:
            self._apropria(self.cdb, pc.CDB, d, "F07", "CDB Renda Mais")
        self.L.premissas_evento["F07"].update({"P14", "P37"})
        for l in self.L.lancs:
            if l["evento"] == "F07":
                l["premissas"] = sorted(set(l["premissas"]) | {"P37"})

    def f08(self, d):
        ev = "F08"
        v = self.p("evento", "F08", "comissão", 82000)
        iss, pis, cof, ir = r2(v * ISS_FORTALEZA), r2(v * PIS), r2(v * COFINS), r2(v * IRRF_SERVICOS)
        for t, val in (("Comissão (NFS-e 003)", v), ("ISS 5%", iss), ("PIS 1,65%", pis), ("COFINS 7,6%", cof),
                       ("IRRF 1,5% retido pelo tomador", ir), ("Valor a receber", v - ir)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "NFS-e 003 - comissão de representação", [(pc.COMISSOES_REC, v - ir), (pc.IRRF_REC, ir)],
                    [(pc.REC_SERVICOS, v)], {"P09"})
        self.L.lanc(d, ev, "Tributos sobre a comissão", [(pc.DED_ISS, iss), (pc.DED_PIS, pis), (pc.DED_COFINS, cof)],
                    [(pc.ISS_RECOL, iss), (pc.PIS_RECOL, pis), (pc.COFINS_RECOL, cof)], {"P09"})
        self.receitas_fev["servicos"] += v
        self.irrf_receitas_fev += ir
        self.comissao_fev = r2(v - ir)

    def f09(self, d):
        self.pagar_ab(d, "F09", "Pagamento de salários e pró-labores de 01/2026", [pc.SAL_PAGAR, pc.PROLAB_PAGAR])

    def f11(self, d):
        ev = "F11"
        v = r2(getattr(self, "ar_valor", 0.0) * 0.45)
        self.L.memo(ev, "45% do valor da NF 7.852", v)
        self.L.lanc(d, ev, "Pagamento parcial (45%) da NF 7.852 - Ar Frio", [(pc.F_ARFRIO, v)], [(pc.BANCO, v)], {"P30"})

    def f12(self, d):
        self.pagar_ab(d, "F12", "Pagamento do FGTS de 01/2026", [pc.FGTS_REC])

    def f13(self, d):
        v = getattr(self, "comissao_fev", 0.0)
        self.L.memo("F13", "Recebimento da comissão (líquida de IRRF)", v)
        self.L.lanc(d, "F13", "Recebimento da NFS-e 003", [(pc.BANCO, v)], [(pc.COMISSOES_REC, v)])

    def f14(self, d):
        self.pagar_ab(d, "F14", "Pagamento Cell Telefonia - 01/2026", [pc.F_CELL])

    def f15(self, d):
        self.integralizar(d, "F15", "Marconde Sobreira")

    def f16(self, d):
        self.pagar_ab(d, "F16", "Pagamento do ISSQN de 01/2026 (próprio e retido)", [pc.ISS_RECOL, pc.ISS_RET])

    def f17(self, d):
        self.pagar_ab(d, "F17", "Pagamento Contador Formado - NFS-e 023 (01/2026)", [pc.F_CONTADOR])

    def f18(self, d):
        self.pagar_ab(d, "F18", "Pagamento Internet & Comunicação - 01/2026", [pc.F_INTERNET])

    def f19(self, d):
        ev = "F19"
        itens = [(pc.AGUA_PAGAR, getattr(self, "agua_fev", 0.0)), (pc.ENERGIA_PAGAR, getattr(self, "energia_fev", 0.0)),
                 (pc.TEL_PAGAR, getattr(self, "fixo_fev", 0.0))]
        self.pagar(d, ev, "Pagamento de água, energia e telefone fixo de 02/2026", [(c, v) for c, v in itens if v])
        self.L.premissas_evento[ev].add("P26")

    def f24(self, d):
        self.pagar_ab(d, "F24", "Pagamento do saldo da NF 3.369 - Comercial Elegante", [pc.F_ELEGANTE])

    def f25(self, d):
        self.integralizar(d, "F25", "Adalberto Cantareira")

    def f27(self, d):
        ev = "F27"
        v = self.p("evento", "F27", "valor") or 20000.0
        taxa = self.p("contrato", "C10", "taxa", 4.0)
        self.mutuo = {"saldo": v, "custo": v, "data": d, "taxa": taxa}
        self.L.memo(ev, f"Mútuo cedido à sócia Cassilda Apedeuta ({fmt(taxa)}% a.m.)", v)
        self.L.lanc(d, ev, "Mútuo cedido à sócia Cassilda Apedeuta", [(pc.MUTUO_SOCIA, v)], [(pc.BANCO, v)], {"P33"})

    def f29(self, d):
        self.pagar_ab(d, "F29", "Pagamento do IRRF de 01/2026", [pc.IRRF_RECOL], menos={pc.IRRF_RECOL: 348.93})

    def f30(self, d):
        self.pagar_ab(d, "F30", "Quitação do RPA do arquiteto", [pc.F_RPA])

    def f31(self, d):
        self.pagar_ab(d, "F31", "Pagamento da GPS (INSS) de 01/2026", [pc.INSS_REC, pc.INSS_RET])

    def f32(self, d):
        ev = "F32"
        tot = self.p("contrato", "C12", "valor", 228000)
        pm = self.p("contrato", "C12", "material", 40)
        parc = r2(tot - r2(tot * 0.5))
        mo = r2(parc * (1 - pm / 100))
        inss, iss = r2(mo * 0.11), r2(mo * ISS_CONSTRUCAO)
        for t, val in (("2ª parcela (50%)", parc), (f"Mão de obra ({fmt(100 - pm)}%)", mo), ("INSS retido 11% (mão de obra)", inss),
                       ("ISS retido 3% (mão de obra)", iss), ("Valor pago", parc - inss - iss)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "NFS-e 6.320 Construtor Express - 2ª parcela da reforma", [(pc.OBRAS, parc)],
                    [(pc.BANCO, parc - inss - iss), (pc.INSS_RET, inss), (pc.ISS_RET, iss)], {"P12", "P31"})
        obra = self.L.saldo(pc.OBRAS)
        self.L.memo(ev, "Reforma concluída: transferência para Edifícios e Construções", obra)
        self.L.lanc(d, ev, "Conclusão da reforma do galpão - transferência para o imobilizado em operação", [(pc.GALPAO, obra)],
                    [(pc.OBRAS, obra)], {"P31"})

    def f33(self, d):
        ev = "F33"
        ls = self.leasing
        if not ls:
            return
        n = int(self.p("contrato", "C04", "prazo", 18))
        v0 = self.p("contrato", "C04", "valor", 300000)
        amort = r2(v0 / n)
        j_tot = r2(ls["saldo"] * ((1 + ls["taxa"] / 100) ** ((d - ls["data"]).days / 365) - 1))
        j_jan = r2(ls.get("juros_apropriados", 0.0))
        j_fev = r2(j_tot - j_jan)
        for t, val in ((f"Amortização (SAC, {n} parcelas)", amort),
                       (f"Juros de {ls['data']:%d/%m} a {d:%d/%m} ({(d - ls['data']).days} dias a {fmt(ls['taxa'])}% a.a.)", j_tot),
                       ("  já apropriados em janeiro", j_jan), ("  de fevereiro (despesa)", j_fev), ("Parcela paga", amort + j_tot)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "Pagamento da 1ª parcela do leasing (SAC)", [(pc.LEASING_CP, amort + j_jan), (pc.JUROS_LEASING, j_fev)],
                    [(pc.BANCO, amort + j_tot)], {"P13", "P32"})
        ls["saldo"], ls["data"], ls["juros_apropriados"] = r2(ls["saldo"] - amort), d, 0.0
        if n > 12 and self.L.saldo(pc.LEASING_LP) < -0.004:
            self.L.memo(ev, "Transferência de uma parcela do longo para o curto prazo", amort)
            self.L.lanc(d, ev, "Leasing: parcela do longo prazo transferida para o curto prazo", [(pc.LEASING_LP, amort)],
                        [(pc.LEASING_CP, amort)], {"P13", "P32"})

    def f37(self, d):
        ev = "F37"
        v = r2(getattr(self, "sof_total", 0.0) * 0.30)
        self.L.memo(ev, "30% do total da NF 23.456", v)
        self.L.lanc(d, ev, "Pagamento de 30% da NF 23.456 - Indústria Sofisticada", [(pc.F_SOFISTICADA, v)], [(pc.BANCO, v)], {"P30"})

    def f38(self, d):
        n = self._func_fev()
        v = r2(n * 20 * 2 * 5.40)
        self.L.memo("F38", f"VT março: {n} empregados × 20 dias × 2 × R$ 5,40", v)
        self.L.lanc(d, "F38", "Compra de vale-transporte para março", [(pc.VT, v)], [(pc.BANCO, v)], {"P36"})

    def f39(self, d):
        n = self._func_fev()
        v = r2(n * 20 * 1 * 26.00)
        self.L.memo("F39", f"VA março: {n} empregados × 20 dias × R$ 26,00", v)
        self.L.lanc(d, "F39", "Compra de vale-alimentação para março", [(pc.VA, v)], [(pc.BANCO, v)], {"P36"})

    def f40(self, d):
        self.pagar_ab(d, "F40", "Pagamento do ICMS de 01/2026 (normal, antecipado e DIFAL)",
                      [pc.ICMS_RECOL, pc.ICMS_ANT_RECOL, pc.DIFAL])

    def f41(self, d):
        ev = "F41"
        h = self.p("contrato", "C05", "honor", 8800)
        metade = r2(h / 2)
        ir = r2(h * IRRF_SERVICOS)
        for t, val in (("Honorários totais (jan-fev)", h), ("Metade de fevereiro (despesa)", metade), ("IRRF 1,5% retido", ir),
                       ("Líquido a pagar", h - ir)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "NFS-e 345 Recrutamento S/S - seleção de pessoal (fevereiro)", [(pc.SERV_PJ, metade)],
                    [(pc.F_RECRUT, metade)], {"P25", "P34"})
        self.L.lanc(d, ev, "Retenção de IRRF - NFS-e 345", [(pc.F_RECRUT, ir)], [(pc.IRRF_RECOL, ir)], {"P34"})

    def f42(self, d):
        self.pagar_ab(d, "F42", "Pagamento de PIS e COFINS de 01/2026", [pc.PIS_RECOL, pc.COFINS_RECOL])

    def f43(self, d):
        self.pagar_ab(d, "F43", "Pagamento da CSRF de 01/2026", [pc.CSRF_RECOL], menos={pc.CSRF_RECOL: 255.75})

    def f45(self, d):
        ev = "F45"
        h0 = self.p("contrato", "C06", "honorário", 5500)
        reaj = self.p("contrato", "C06", "reajuste", 25.45)
        h = round(h0 * (1 + reaj / 100) / 100) * 100
        ir, cs = r2(h * IRRF_SERVICOS), r2(h * CSRF)
        for t, val in ((f"Honorário reajustado ({fmt(h0)} + {fmt(reaj)}%, arredondado a R$ 100)", h), ("IRRF 1,5%", ir),
                       ("CSRF 4,65%", cs), ("Líquido a pagar em 05/03", h - ir - cs)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "NFS-e 024 Contador Formado - fevereiro", [(pc.ASSESSORIA, h)],
                    [(pc.F_CONTADOR, h - ir - cs), (pc.IRRF_RECOL, ir), (pc.CSRF_RECOL, cs)], {"P10", "P35"})

    def f46(self, d):
        self.pagar_ab(d, "F46", "Pagamento de IRPJ e CSLL por estimativa de 01/2026", [pc.IRPJ_RECOL, pc.CSLL_RECOL])

    def f47(self, d):
        ev = "F47"
        inv = self.invest
        if not inv or inv["saldo"] <= 0:
            self.L.memo(ev, "INVEST LIQUID sem saldo: não há rendimento a resgatar", 0.0)
            return
        self._apropria(inv, pc.INVEST, d, ev, "INVEST LIQUID")
        rend = r2(inv["saldo"] - inv["custo"])
        if rend <= 0:
            return
        ir = r2(rend * IR_APLICACAO)
        self.L.memo(ev, "Rendimento acumulado resgatado", rend)
        self.L.memo(ev, "IR 22,5% (a recuperar)", ir)
        self.L.lanc(d, ev, "Resgate do rendimento do INVEST LIQUID", [(pc.BANCO, rend - ir), (pc.IRRF_APLIC, ir)],
                    [(pc.INVEST, rend)], {"P14", "P37"})
        inv["saldo"] = r2(inv["saldo"] - rend)
        for l in self.L.lancs:
            if l["evento"] == ev:
                l["premissas"] = sorted(set(l["premissas"]) | {"P37"})
        self.L.premissas_evento[ev].add("P37")

    # ---------------- 8b: compras de insumos e estoques (custo médio ponderado móvel)
    def _kardex(self, ev, cod, q, v, rot):
        e = self.est.setdefault(cod, [0.0, 0.0])
        e[0], e[1] = e[0] + q, r2(e[1] + v)
        cm = e[1] / e[0] if e[0] else 0.0
        self.L.memo(ev, f"Estoque {cod} após {rot}: {qtd(e[0])} un · custo médio {f4(cm)}", e[1])

    def _compra_insumos(self, d, ev, hist, itens, uf, ipi_destacado, conta_forn, vista_pct, premissas, desconto_pct=0.0):
        """itens: [(cod, q, custo_unit)]. Devolve o total da nota."""
        al = ICMS_UF[uf]
        deb, prod_t, ipi_t, custos = defaultdict(float), 0.0, 0.0, []
        for cod, q, cu in itens:
            prod = r2(q * cu)
            ipi = r2(prod * TIPI[NCM[cod]]) if ipi_destacado else 0.0
            icms = r2(prod * al)
            pis, cof = r2((prod - icms) * PIS), r2((prod - icms) * COFINS)
            custo = r2(prod - icms - pis - cof)
            custos.append((cod, q, custo))
            deb[pc.ESTOQUE[cod]] += custo
            deb[pc.IPI_REC] += ipi
            deb[pc.ICMS_REC] += icms
            deb[pc.PIS_REC] += pis
            deb[pc.COFINS_REC] += cof
            prod_t, ipi_t = prod_t + prod, ipi_t + ipi
            self.L.memo(ev, f"{cod}: {qtd(q)} un × {f4(cu)} = {fmt(prod)}"
                        + (f"; IPI {fmt(TIPI[NCM[cod]] * 100)}% {fmt(ipi)}" if ipi_destacado else "")
                        + f"; ICMS {fmt(al * 100)}% {fmt(icms)}; PIS {fmt(pis)}; COFINS {fmt(cof)}", custo, "custo do insumo")
        total = r2(prod_t + ipi_t)
        vista = r2(total * vista_pct / 100)
        desc = r2(vista * desconto_pct / 100)
        self.L.memo(ev, "Total da nota (produtos + IPI)", total)
        self.L.memo(ev, f"Pagamento à vista ({fmt(vista_pct)}%)", vista)
        cred = [(pc.BANCO, vista - desc), (conta_forn, total - vista)]
        if desc:
            self.L.memo(ev, f"Desconto financeiro condicional obtido ({fmt(desconto_pct)}% sobre a parcela à vista)", desc)
            cred.append((pc.DESC_OBTIDOS, desc))
            self.receitas_fev["financeiras"] += desc
        self.L.lanc(d, ev, hist, list(deb.items()), cred, premissas)
        for cod, q, custo in custos:
            self._kardex(ev, cod, q, custo, "a compra")
        return total

    def _frete_insumo(self, d, ev, cte, cod, frete, uf):
        al = ICMS_UF[uf]
        icms = r2(frete * al)
        pis, cof = r2((frete - icms) * PIS), r2((frete - icms) * COFINS)
        custo = r2(frete - icms - pis - cof)
        self.L.memo(ev, f"Frete FOB (CT-e {cte})", frete)
        self.L.memo(ev, f"Créditos sobre o frete (ICMS {fmt(al * 100)}%, PIS, COFINS)", icms + pis + cof)
        self.L.lanc(d, ev, f"CT-e {cte} - frete FOB da compra de {cod}",
                    [(pc.ESTOQUE[cod], custo), (pc.ICMS_REC, icms), (pc.PIS_REC, pis), (pc.COFINS_REC, cof)],
                    [(pc.F_FRETE, frete)], {"P05", "P41"})
        self._kardex(ev, cod, 0, custo, "o frete")

    def _insumo(self, cod):
        i = self.x.insumo(cod)
        return float(i.get("compra") or 0), float(i.get("custo_unit") or 0)

    def f05(self, d):
        ev = "F05"
        q, cu = self._insumo("MP-B")
        dp = self.p("evento", "F05", "desconto", 4)
        self._compra_insumos(d, ev, "NF 12.380 Indústria Zalego - MP-B", [("MP-B", q, cu)], "TO", True, pc.F_ZALEGO, 35,
                             {"P38", "P39", "P40", "P42", "P05"}, desconto_pct=dp)
        self.frete_f05 = self.p("evento", "F05", "frete", 1980)
        self._frete_insumo(d, ev, "424.110", "MP-B", self.frete_f05, "TO")

    def f10(self, d):
        ev = "F10"
        itens = [(cod, *self._insumo(cod)) for cod in ("MS-Z", "MS-Q", "MS-R", "MS-K")]
        total = self._compra_insumos(d, ev, "NF 9.147 Distribuidor Verde Oliva - materiais secundários",
                                     [i for i in itens if i[1]], "RJ", False, pc.F_VERDE_OLIVA, 15, {"P38", "P39", "P41", "P42", "P05"})
        self.L.memo(ev, "Saldo em 2 parcelas iguais (07/03 e 07/04)", r2(total * 0.85))

    def f22(self, d):
        ev = "F22"
        q, cu = self._insumo("ME-H")
        self._compra_insumos(d, ev, "NF 1.747 Embalagens Comerciais - ME-H", [("ME-H", q, cu)], "AM", False, pc.F_EMBALAGENS, 30,
                             {"P38", "P39", "P42", "P05"})
        self.frete_f22 = self.p("evento", "F22", "frete", 1410)
        self._frete_insumo(d, ev, "425.130", "ME-H", self.frete_f22, "AM")

    def f23(self, d):
        v = getattr(self, "frete_f05", 0.0)
        self.L.memo("F23", "CT-e 424.110 (vencido em 13/02)", v)
        self.L.lanc(d, "F23", "Pagamento do CT-e 424.110 - Frete Confiança", [(pc.F_FRETE, v)], [(pc.BANCO, v)], {"P41"})

    def f35(self, d):
        v = getattr(self, "frete_f22", 0.0)
        self.L.memo("F35", "CT-e 425.130", v)
        self.L.lanc(d, "F35", "Pagamento do CT-e 425.130 - Frete Confiança", [(pc.F_FRETE, v)], [(pc.BANCO, v)], {"P41"})

    def f28(self, d):
        ev = "F28"
        qd = self.p("evento", "F28", "devolvida") or float(self.x.insumo("MP-A").get("devolucao") or 320)
        cu = self.sof_unit["cu"]
        prod = r2(qd * cu)
        ipi = r2(prod * TIPI[NCM["MP-A"]])
        icms = r2(prod * ICMS_UF["MG"])
        pis, cof = r2((prod - icms) * PIS), r2((prod - icms) * COFINS)
        custo = r2(prod - icms - pis - cof)
        for t, val in ((f"{qtd(qd)} un de MP-A devolvidas × {f4(cu)}", prod), ("IPI 9,75% (estorno do crédito)", ipi),
                       ("ICMS 7% (estorno do crédito)", icms), ("PIS (estorno)", pis), ("COFINS (estorno)", cof),
                       ("Baixa do estoque pelo custo da compra", custo), ("Abatimento no saldo do fornecedor (produtos + IPI)", prod + ipi)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "NF 004 - devolução de MP-A à Indústria Sofisticada (CFOP 6.201)", [(pc.F_SOFISTICADA, prod + ipi)],
                    [(pc.ESTOQUE["MP-A"], custo), (pc.IPI_REC, ipi), (pc.ICMS_REC, icms), (pc.PIS_REC, pis), (pc.COFINS_REC, cof)],
                    {"P08", "P42"})
        self._kardex(ev, "MP-A", -qd, -custo, "a devolução")

    # ---------------- 8c: folha, depreciação e produção
    def _destino(self, setor: str) -> str:
        s = (setor or "").lower()
        if "industrial" in s:
            return "modx" if "produto x" in s else "mody" if "produto y" in s else "moi"
        return "vendas" if "comerc" in s else "adm"

    @staticmethod
    def _conta_area(chave: str, destino: str) -> str:
        if destino == "adm":
            return pc.POR_AREA[chave][0]
        if destino == "vendas":
            return pc.POR_AREA[chave][1]
        return {"modx": pc.MOD["X"], "mody": pc.MOD["Y"], "moi": pc.CIF_MOI}[destino]

    def f20(self, d):
        ev = "F20"
        func = [f for f in self.v.get("folha", []) if f.get("salario_fev") or f.get("pendente")]
        n = len(func) or 1
        vt_ind, va_ind = r2(self.ab(pc.VT) / n), r2(self.ab(pc.VA) / n)
        deb, cred, tot = defaultdict(float), defaultdict(float), defaultdict(float)
        por_dest = defaultdict(float)
        for f in func:
            dest = self._destino(f["setor"])
            sal = f.get("salario_fev") or (SALARIO_MINIMO if f.get("pendente") else 0)
            he, com = f.get("he_fev") or 0, f.get("comissao_fev") or 0
            rem = r2(sal + he + com)
            inss = inss_empregado(min(rem, TETO_INSS))
            ids = idades(f.get("dependentes_fev"))
            deps = sum(1 for i in ids if i <= 21)
            ir, nota = irrf(rem, inss, deps)
            sf = r2(SALARIO_FAMILIA_COTA * sum(1 for i in ids if i <= 14)) if rem <= SALARIO_FAMILIA_LIMITE else 0.0
            dvt = r2(min(sal * 0.06, vt_ind))
            dva = r2(va_ind * 0.05)
            liq = r2(rem + sf - inss - ir - dvt - dva)
            enc, fg = r2(rem * ENCARGOS_INSS_FOLHA), r2(rem * FGTS)
            fer, dec = r2(rem / 12 * 4 / 3), r2(rem / 12)
            enc_f, fg_f, enc_d, fg_d = r2(fer * ENCARGOS_INSS_FOLHA), r2(fer * FGTS), r2(dec * ENCARGOS_INSS_FOLHA), r2(dec * FGTS)
            custo = {"salarios": sal + he, "inss": enc, "fgts": fg, "ferias": fer + enc_f + fg_f, "decimo": dec + enc_d + fg_d,
                     "vt": vt_ind - dvt, "va": va_ind - dva}
            for k, val in custo.items():
                deb[self._conta_area(k, dest)] += val
                por_dest[dest] += val
            if com:
                deb[pc.COMISSOES] += com
                por_dest[dest] += com
            cred[pc.PROV_FERIAS] += fer
            cred[pc.INSS_FERIAS] += enc_f
            cred[pc.FGTS_FERIAS] += fg_f
            cred[pc.PROV_13] += dec
            cred[pc.INSS_13] += enc_d
            cred[pc.FGTS_13] += fg_d
            cred[pc.INSS_REC] += inss + enc - sf
            cred[pc.FGTS_REC] += fg
            cred[pc.IRRF_RECOL] += ir
            cred[pc.SAL_PAGAR] += liq
            cred[pc.VT] += vt_ind
            cred[pc.VA] += va_ind
            for k, val in (("rem", rem), ("enc", enc), ("fgts", fg)):
                tot[k] += val
            self.L.memo(ev, f"{f['nome']} ({f['setor']}{'; salário não informado no caso: mínimo' if f.get('pendente') else ''}): "
                            f"remuneração {fmt(rem)}; INSS {fmt(inss)}; IRRF {fmt(ir)} ({nota}); sal.-família {fmt(sf)}; "
                            f"desc. VT {fmt(dvt)} / VA {fmt(dva)}", liq, "líquido")
        self.L.memo(ev, f"VT e VA consumidos por empregado ({n} empregados)", vt_ind + va_ind)
        self.L.memo(ev, "Encargos INSS 27,80% sobre a folha", tot["enc"])
        self.L.memo(ev, "FGTS 8%", tot["fgts"])
        for dest, rot in (("adm", "Despesas administrativas"), ("vendas", "Despesas de vendas"), ("modx", "MOD a apropriar - Produto X"),
                          ("mody", "MOD a apropriar - Produto Y"), ("moi", "Mão de obra indireta (CIF)")):
            if por_dest.get(dest):
                self.L.memo(ev, f"Custo total da folha · {rot}", por_dest[dest])
        self.L.lanc(d, ev, "Folha de pagamento de fevereiro/2026", list(deb.items()), list(cred.items()),
                    {"P01", "P16", "P17", "P18", "P43"})
        pl_deb, pl_cred = defaultdict(float), defaultdict(float)
        for s_ in self.v.get("socios", []):
            pl = float(s_.get("pro_labore_fev") or 0)
            if not pl:
                continue
            fn = (s_.get("funcao") or "").lower()
            inss = r2(min(pl, TETO_INSS) * 0.11)
            deps = sum(1 for i in idades(s_.get("dependentes") or self._dep_socio(s_["nome"])) if i <= 21)
            ir, nota = irrf(pl, inss, deps)
            pat = r2(pl * INSS_PATRONAL_CI)
            if "industrial" in fn:
                pl_deb[pc.CIF_PROLAB] += pl + pat
            else:
                a = 1 if "comerc" in fn else 0
                pl_deb[pc.POR_AREA["prolabore"][a]] += pl
                pl_deb[pc.POR_AREA["inss"][a]] += pat
            pl_cred[pc.PROLAB_PAGAR] += pl - inss - ir
            pl_cred[pc.INSS_REC] += inss + pat
            pl_cred[pc.IRRF_RECOL] += ir
            self.L.memo(ev, f"Pró-labore {s_['nome']}: {fmt(pl)}; INSS 11% {fmt(inss)}; IRRF {fmt(ir)} ({nota}); patronal 20% {fmt(pat)}"
                        + (" · CIF" if "industrial" in fn else ""), pl - inss - ir, "líquido")
        if pl_deb:
            self.L.lanc(d, ev, "Pró-labore de fevereiro/2026", list(pl_deb.items()), list(pl_cred.items()), {"P01", "P16", "P44"})

    def f21(self, d):
        ev = "F21"
        deb, cred = defaultdict(float), defaultdict(float)
        itens = [
            ("Galpão (prédio)", self.L.saldo(pc.GALPAO), 20, 80, (0.10, 0.25, 0.65), pc.DEP_IMOVEIS),
            ("Máquinas industriais", self.L.saldo(pc.MAQUINAS), 8, 20, (0.0, 0.0, 1.0), pc.DEP_MAQ),
            ("Máquinas arrendadas (leasing)", self.L.saldo(pc.MAQ_LEASING), 8, 20, (0.0, 0.0, 1.0), pc.DEP_MAQ),
            ("Veículo utilitário", self.L.saldo(pc.VEICULOS), 5, 40, (0.70, 0.30, 0.0), pc.DEP_VEIC),
            ("Ar-condicionados (móveis e aparelhos)", self.L.saldo(pc.MOVEIS), 12, 10, (0.45, 0.35, 0.20), pc.DEP_MOVEIS),
        ]
        for nome, valor, anos, resid, (pa, pv, pi), conta in itens:
            if valor <= 0:
                continue
            q = r2(valor * (1 - resid / 100) / (anos * 12))
            va, vv = r2(q * pa), r2(q * pv)
            vi = r2(q - va - vv)
            deb[pc.POR_AREA["depreciacao"][0]] += va
            deb[pc.POR_AREA["depreciacao"][1]] += vv
            deb[pc.CIF_DEPREC] += vi
            cred[conta] += q
            self.L.memo(ev, f"{nome}: {fmt(valor)} × (1 − {resid}%) ÷ {anos * 12} meses; adm. {int(pa * 100)}% / vendas {int(pv * 100)}% "
                            f"/ industrial {int(pi * 100)}%", q)
        self.L.lanc(d, ev, "Depreciação de fevereiro/2026", [(c, v) for c, v in deb.items() if v], list(cred.items()), {"P20", "P45"})

    def _producao(self):
        prods = {p["codigo"]: float(p["quantidade"]) for p in self.v.get("producao", {}).get("produtos", [])}
        fichas = {i["codigo"]: i.get("por_produto", {}) for i in self.v.get("producao", {}).get("insumos", [])}
        return prods, fichas

    def fp1(self, d):
        ev = "FP1"
        prods, fichas = self._producao()
        deb, cred = defaultdict(float), defaultdict(float)
        self.md = {"X": 0.0, "Y": 0.0}
        for cod, por in fichas.items():
            e = self.est.get(cod)
            if not e or not e[0]:
                continue
            cm = e[1] / e[0]
            for prod, coef in por.items():
                q = coef * prods.get(prod, 0)
                if not q:
                    continue
                v = r2(q * cm)
                deb[pc.PEP[prod]] += v
                cred[pc.ESTOQUE[cod]] += v
                self.md[prod] += v
                self.L.memo(ev, f"{cod} → Produto {prod}: {fmt(coef).replace(',00', '')} × {qtd(prods[prod])} = {qtd(q)} un × "
                                f"custo médio {f4(cm)}", v)
                e[0], e[1] = e[0] - q, r2(e[1] - v)
        for cod in fichas:
            if cod in self.est:
                self.L.memo(ev, f"Estoque {cod} após a requisição: {qtd(self.est[cod][0])} un", self.est[cod][1])
        for prod in ("X", "Y"):
            self.L.memo(ev, f"Materiais diretos - Produto {prod}", self.md[prod])
        self.L.lanc(d, ev, "Requisição de materiais - início da produção de X e Y", list(deb.items()), list(cred.items()), {"P42", "P46"})

    def fp2(self, d):
        ev = "FP2"
        prods, _ = self._producao()
        md = getattr(self, "md", {"X": 0.0, "Y": 0.0})
        tot_md = (md["X"] + md["Y"]) or 1
        cif = {c: self.L.saldo(c) for c in pc.CIF_CONTAS if self.L.saldo(c) > 0.004}
        tot_cif = r2(sum(cif.values()))
        cif_x = r2(tot_cif * md["X"] / tot_md)
        cif_p = {"X": cif_x, "Y": r2(tot_cif - cif_x)}
        mod = {p: self.L.saldo(pc.MOD[p]) for p in ("X", "Y")}
        for c, v in cif.items():
            self.L.memo(ev, f"CIF · {pc.CONTAS[c]['nome']}", v)
        self.L.memo(ev, "Total do CIF", tot_cif)
        self.L.memo(ev, f"Rateio pelos materiais diretos: X {fmt(100 * md['X'] / tot_md)}% · Y {fmt(100 * md['Y'] / tot_md)}%", None)
        deb = [(pc.PEP[p], mod[p] + cif_p[p]) for p in ("X", "Y")]
        cred = [(pc.MOD[p], mod[p]) for p in ("X", "Y") if mod[p]] + list(cif.items())
        self.L.lanc(d, ev, "Apropriação da MOD e do CIF aos produtos em elaboração", deb, cred, {"P43", "P47"})
        acab = []
        for p in ("X", "Y"):
            total = self.L.saldo(pc.PEP[p])
            q = prods.get(p, 0)
            acab.append((p, total, q))
            for t, val in ((f"Produto {p} · materiais diretos", md[p]), (f"Produto {p} · mão de obra direta", mod[p]),
                           (f"Produto {p} · CIF rateado", cif_p[p]), (f"Produto {p} · custo total ({qtd(q)} un)", total)):
                self.L.memo(ev, t, val)
            self.L.memo(ev, f"Produto {p} · custo unitário {f4(total / q if q else 0)}", None)
            self.est[p] = [q, total]
        self.L.lanc(d, ev, "Término da produção - transferência para produtos acabados",
                    [(pc.PA[p], t) for p, t, _ in acab], [(pc.PEP[p], t) for p, t, _ in acab], {"P46", "P47"})

    # ---------------- 8d: vendas
    def _divisor(self):
        mk = self.v.get("markup", {}) or {}
        margem = float(mk.get("margem_contribuicao") or 45)
        return 1 - (ICMS_INTERNO_CE * 100 + PIS * 100 + COFINS * 100 + margem) / 100

    def _venda_alpha(self, d, ev, q, cliente_hist, al_icms, conta_rec, difal_pct=0.0, premissas=("P06", "P48")):
        div = self._divisor()
        cm = self.alpha_v / self.alpha_q
        preco = r2(cm * (1 / div))
        rec = r2(q * preco)
        icms = r2(rec * al_icms)
        difal = r2(rec * difal_pct)
        pis, cof = r2((rec - icms) * PIS), r2((rec - icms) * COFINS)
        cmv = r2(q * cm)
        for t, val in (("Custo médio ALPHA", cm), (f"Mark-up divisor {f4(div)} → multiplicador {f4(1 / div)}", None),
                       ("Preço unitário", preco), (f"Receita ({qtd(q)} un)", rec), (f"ICMS {fmt(al_icms * 100)}%", icms)) + \
                (((f"DIFAL {fmt(difal_pct * 100)}% (23% MA − 12%)", difal),) if difal else ()) + \
                (("PIS 1,65% (base sem ICMS)", pis), ("COFINS 7,6% (base sem ICMS)", cof), ("CMV", cmv)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, f"{cliente_hist} - venda de ALPHA", [(conta_rec, rec)], [(pc.REC_REVENDA, rec)], set(premissas))
        deb = [(pc.DED_ICMS, icms), (pc.DED_PIS, pis), (pc.DED_COFINS, cof)] + ([(pc.DED_DIFAL, difal)] if difal else [])
        cred = [(pc.ICMS_RECOL, icms), (pc.PIS_RECOL, pis), (pc.COFINS_RECOL, cof)] + ([(pc.DIFAL_MA, difal)] if difal else [])
        self.L.lanc(d, ev, f"Tributos sobre a venda - {cliente_hist}", deb, cred, set(premissas))
        self.L.lanc(d, ev, f"Baixa do estoque - {cliente_hist} (CMV)", [(pc.CMV, cmv)], [(pc.ALPHA, cmv)], {"P48"})
        self.alpha_q -= q
        self.alpha_v = r2(self.alpha_v - cmv)
        self.L.memo(ev, f"Estoque ALPHA após a venda: {qtd(self.alpha_q)} un", self.alpha_v)
        self.receitas_fev["revenda"] += rec
        return rec, preco, cm

    def f04(self, d):
        q = self.p("evento", "F04", "quantidade", 40)
        self._venda_alpha(d, "F04", q, "NF 337 consumidor final (São Luís-MA)", ICMS_UF["MA"], pc.BANCO,
                          difal_pct=ICMS_INTERNO_MA - ICMS_UF["MA"], premissas=("P06", "P48", "P49"))

    def f26(self, d):
        q = self.p("evento", "F26", "quantidade", 10400)
        rec, preco, cm = self._venda_alpha(d, "F26", q, "NF 003 Comercial Caribe", ICMS_INTERNO_CE, pc.CLIENTES)
        self.caribe = {"valor": rec, "preco": preco, "cm": cm}

    def f36(self, d):
        ev = "F36"
        cb = getattr(self, "caribe", None)
        if not cb:
            return
        q = self.p("evento", "F36", "devolvida", 70)
        v = r2(q * cb["preco"])
        icms = r2(v * ICMS_INTERNO_CE)
        pis, cof = r2((v - icms) * PIS), r2((v - icms) * COFINS)
        custo = r2(q * cb["cm"])
        for t, val in ((f"{qtd(q)} un devolvidas × preço da NF 003 {fmt(cb['preco'])}", v), ("Estorno do ICMS 20%", icms),
                       ("Estorno do PIS", pis), ("Estorno da COFINS", cof), ("Retorno ao estoque pelo custo da saída", custo)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "NF 1.320 Comercial Caribe - devolução de ALPHA", [(pc.DEVOLUCOES, v)], [(pc.CLIENTES, v)], {"P52"})
        self.L.lanc(d, ev, "Estorno dos tributos sobre a venda devolvida", [(pc.ICMS_REC, icms), (pc.PIS_REC, pis), (pc.COFINS_REC, cof)],
                    [(pc.DED_ICMS, icms), (pc.DED_PIS, pis), (pc.DED_COFINS, cof)], {"P52"})
        self.L.lanc(d, ev, "Retorno da mercadoria devolvida ao estoque", [(pc.ALPHA, custo)], [(pc.CMV, custo)], {"P52"})
        self.alpha_q += q
        self.alpha_v = r2(self.alpha_v + custo)
        self.receitas_fev["revenda"] -= v
        cb["devolucao"] = v
        self.L.memo(ev, f"Estoque ALPHA após a devolução: {qtd(self.alpha_q)} un", self.alpha_v)

    def f44(self, d):
        cb = getattr(self, "caribe", None)
        if not cb:
            return
        v = r2(cb["valor"] - cb.get("devolucao", 0.0))
        self.L.memo("F44", "Boleto da NF 003 menos a devolução (NF 1.320)", v)
        self.L.lanc(d, "F44", "Recebimento Comercial Caribe - NF 003 (líquido da devolução)", [(pc.BANCO, v)], [(pc.CLIENTES, v)], {"P52"})

    def f34(self, d):
        ev = "F34"
        div = self._divisor()
        vend = {p["codigo"]: float(p.get("vendido") or 0) for p in self.v.get("producao", {}).get("produtos", [])}
        dpct = self.p("evento", "F34", "desconto", 3)
        rpct = self.p("evento", "F34", "recebimento", 80)
        al = ICMS_UF["PA"]
        rec_t = ipi_t = icms_t = pis_t = cof_t = cpv_t = 0.0
        rec_p, cpv_p = {}, {}
        for p in ("X", "Y"):
            q = vend.get(p, 0)
            e = self.est.get(p)
            if not q or not e or not e[0]:
                continue
            cm = e[1] / e[0]
            preco = r2(cm * (1 / div))
            rec = r2(q * preco)
            ipi = r2(rec * TIPI[NCM[p]])
            icms = r2(rec * al)
            pis, cof = r2((rec - icms) * PIS), r2((rec - icms) * COFINS)
            cpv = r2(q * cm)
            rec_p[p], cpv_p[p] = rec, cpv
            rec_t, ipi_t, icms_t, pis_t, cof_t, cpv_t = rec_t + rec, ipi_t + ipi, icms_t + icms, pis_t + pis, cof_t + cof, cpv_t + cpv
            for t, val in ((f"Produto {p}: custo médio {f4(cm)} × {f4(1 / div)} = preço", preco), (f"Produto {p}: {qtd(q)} un", rec),
                           (f"Produto {p}: IPI {fmt(TIPI[NCM[p]] * 100)}%", ipi), (f"Produto {p}: ICMS 12%", icms),
                           (f"Produto {p}: PIS / COFINS", pis + cof), (f"Produto {p}: CPV", cpv)):
                self.L.memo(ev, t, val)
            e[0], e[1] = e[0] - q, r2(e[1] - cpv)
            self.L.memo(ev, f"Estoque do Produto {p} após a venda: {qtd(e[0])} un", e[1])
        if not rec_t:
            return
        total = r2(rec_t + ipi_t)
        desc = r2(rec_p.get("Y", 0) * dpct / 100)
        recebido = r2(total * rpct / 100)
        for t, val in (("Total da nota (produtos + IPI)", total), (f"Recebido na emissão ({fmt(rpct)}% do total) menos o desconto", recebido - desc),
                       (f"Desconto financeiro de {fmt(dpct)}% sobre o Produto Y (despesa financeira)", desc),
                       (f"Saldo a receber em 22/03 ({fmt(100 - rpct)}%)", total - recebido)):
            self.L.memo(ev, t, val)
        self.L.lanc(d, ev, "NF 005 Comercial Roma - venda dos Produtos X e Y",
                    [(pc.BANCO, recebido - desc), (pc.DESC_CONCEDIDOS, desc), (pc.CLIENTES, total - recebido)],
                    [(pc.REC_PRODUTOS, rec_t), (pc.IPI_RECOL, ipi_t)], {"P48", "P50", "P51"})
        self.L.lanc(d, ev, "Tributos sobre a venda - NF 005", [(pc.DED_ICMS, icms_t), (pc.DED_PIS, pis_t), (pc.DED_COFINS, cof_t)],
                    [(pc.ICMS_RECOL, icms_t), (pc.PIS_RECOL, pis_t), (pc.COFINS_RECOL, cof_t)], {"P06", "P50"})
        self.L.lanc(d, ev, "Baixa dos produtos vendidos - NF 005 (CPV)", [(pc.CPV, cpv_t)],
                    [(pc.PA[p], v) for p, v in cpv_p.items()], {"P48"})
        self.receitas_fev["producao"] = self.receitas_fev.get("producao", 0.0) + rec_t

    # ---------------- 8e: apuração de fevereiro
    def f48(self, d):
        ev = "F48"
        L = self.L
        ant = self.ab(pc.ICMS_ANT_RECOL)  # antecipado de 01/2026, pago em 26/02 (F40)
        if ant > 0.004:
            L.memo(ev, "ICMS antecipado de 01/2026 pago em 26/02: crédito em fevereiro", ant)
            L.lanc(d, ev, "Crédito do ICMS antecipado de 01/2026 (pago em 26/02)", [(pc.ICMS_REC, ant)], [(pc.ICMS_ANT_REC, ant)],
                   {"P03", "P53"})
        for nome, deb_c, cred_c in (("ICMS", pc.ICMS_RECOL, pc.ICMS_REC), ("IPI", pc.IPI_RECOL, pc.IPI_REC),
                                    ("PIS", pc.PIS_RECOL, pc.PIS_REC), ("COFINS", pc.COFINS_RECOL, pc.COFINS_REC)):
            debitos = -L.saldo(deb_c)
            creditos = L.saldo(cred_c)
            comp = r2(min(debitos, creditos))
            L.memo(ev, f"{nome}: débitos {fmt(debitos)} − créditos {fmt(creditos)}", debitos - creditos,
                   "a recolher" if debitos > creditos else "saldo credor")
            if comp > 0:
                L.lanc(d, ev, f"Apuração do {nome} de fevereiro", [(deb_c, comp)], [(cred_c, comp)], {"P23", "P53"})
        difal = -L.saldo(pc.DIFAL_MA)
        if difal > 0.004:
            L.memo(ev, "DIFAL devido ao Maranhão (recolhimento por GNRE, sem compensação)", difal)
        iss = -L.saldo(pc.ISS_RECOL)
        if iss > 0.004:
            L.memo(ev, "ISS próprio de fevereiro (NFS-e 003), a recolher ao município", iss)
        r = self.receitas
        rv, rp, rs, rf = (r2(r.get(k, 0.0)) for k in ("revenda", "producao", "servicos", "financeiras"))
        b_ir = r2((rv + rp) * 0.08 + rs * 0.32 + rf)
        b_cs = r2((rv + rp) * 0.12 + rs * 0.32 + rf)
        irpj = r2(b_ir * 0.15 + max(0.0, b_ir - 20000) * 0.10)
        csll = r2(b_cs * 0.09)
        for t, val in (("Receita de revenda (líquida de devoluções)", rv), ("Receita de venda de produtos", rp),
                       ("Receita de serviços", rs), ("Receitas financeiras", rf),
                       ("Base IRPJ (8% / 32% / 100%)", b_ir), ("IRPJ 15% + adicional 10%", irpj),
                       ("Base CSLL (12% / 32% / 100%)", b_cs), ("CSLL 9%", csll)):
            L.memo(ev, t, val)
        L.lanc(d, ev, "IRPJ e CSLL por estimativa - fevereiro", [(pc.IRPJ_DESP, irpj), (pc.CSLL_DESP, csll)],
               [(pc.IRPJ_RECOL, irpj), (pc.CSLL_RECOL, csll)], {"P22", "P54"})
        comp = r2(min(irpj, L.saldo(pc.IRRF_REC) + L.saldo(pc.IRRF_APLIC)))
        if comp > 0:
            c1 = min(comp, L.saldo(pc.IRRF_REC))
            L.memo(ev, "IRRF retido compensado na estimativa", comp)
            L.lanc(d, ev, "Compensação do IRRF retido com o IRPJ", [(pc.IRPJ_RECOL, comp)],
                   [(pc.IRRF_REC, c1), (pc.IRRF_APLIC, comp - c1)], {"P22", "P54"})

    def ajustes_fev(self, d):
        ev = "FAJ"
        premio = self.p("contrato", "C09", "prêmio", 6300)
        seg = r2(premio / 12)
        self.L.memo(ev, "Apropriação do seguro (1/12 do prêmio)", seg)
        self.L.lanc(d, ev, "Apropriação do seguro - fevereiro", [(pc.SEGUROS, seg)], [(pc.SEGUROS_APROP, seg)], {"P25"})
        if self.invest and self.invest["saldo"] > 0:
            self._apropria(self.invest, pc.INVEST, d, ev, "INVEST LIQUID")
        if self.cdb:
            self._apropria(self.cdb, pc.CDB, d, ev, "CDB Renda Mais")
        self._juros_garantida(d, ev)
        ls = self.leasing
        if ls and ls["saldo"] > 0:
            j = r2(ls["saldo"] * ((1 + ls["taxa"] / 100) ** ((d - ls["data"]).days / 365) - 1))
            if j:
                self.L.memo(ev, f"Juros do leasing ({(d - ls['data']).days} dias a {fmt(ls['taxa'])}% a.a.)", j)
                self.L.lanc(d, ev, "Juros do arrendamento financeiro - fevereiro", [(pc.JUROS_LEASING, j)], [(pc.LEASING_CP, j)], {"P13", "P32"})
                ls["juros_apropriados"] = ls.get("juros_apropriados", 0.0) + j
        m = getattr(self, "mutuo", None)
        if m:
            dias = (d - m["data"]).days
            j = r2(m["saldo"] * ((1 + m["taxa"] / 100) ** (dias / 30) - 1))
            if j:
                self.L.memo(ev, f"Juros do mútuo ({dias} dias a {fmt(m['taxa'])}% a.m.)", j)
                self.L.lanc(d, ev, "Juros do mútuo com a sócia - fevereiro", [(pc.MUTUO_SOCIA, j)], [(pc.JUROS_MUTUO, j)], {"P33"})
                m["saldo"], m["data"] = r2(m["saldo"] + j), d
                self.receitas_fev["financeiras"] += j

    # eventos de fevereiro: dia e método (None = gabarito em preparação nas etapas 8b a 8e)
    EVENTOS_FEV = {
        "F01": (2, "f01"), "F02": (2, "f02"), "F03": (2, "f03"), "F04": (3, "f04"), "F05": (4, "f05"), "F06": (4, "f06"),
        "F07": (5, "f07"), "F08": (6, "f08"), "F09": (6, "f09"), "F10": (9, "f10"), "F11": (9, "f11"), "F12": (10, "f12"),
        "F13": (10, "f13"), "F14": (11, "f14"), "F15": (11, "f15"), "F16": (12, "f16"), "F17": (12, "f17"),
        "F18": (13, "f18"), "F19": (13, "f19"), "F20": (13, "f20"), "F21": (13, "f21"), "F22": (18, "f22"), "F23": (18, "f23"),
        "F24": (18, "f24"), "F25": (19, "f25"), "F26": (19, "f26"), "F27": (20, "f27"), "F28": (20, "f28"), "F29": (20, "f29"),
        "F30": (23, "f30"), "F31": (23, "f31"), "F32": (23, "f32"), "F33": (23, "f33"), "F34": (24, "f34"), "F35": (24, "f35"),
        "F36": (24, "f36"), "F37": (25, "f37"), "F38": (25, "f38"), "F39": (25, "f39"), "F40": (26, "f40"), "F41": (26, "f41"),
        "F42": (26, "f42"), "F43": (27, "f43"), "F44": (27, "f44"), "F45": (27, "f45"), "F46": (27, "f46"), "F47": (27, "f47"),
        "F48": (28, "f48"), "FP1": (19, "fp1"), "FP2": (23, "fp2"),
    }
    # tesouraria e ajustes de fevereiro mudam conforme as etapas seguintes entram: ficam fora da correção até a 8e
    PROVISORIOS_FEV: set = set()  # fevereiro completo (8e): tesouraria e ajustes definitivos

    def _executar_fev(self):
        self.executados = set()
        self.receitas_fev = {"revenda": 0.0, "producao": 0.0, "servicos": 0.0, "financeiras": 0.0}
        self.irrf_receitas_fev = 0.0
        self.receitas = self.receitas_fev  # rendimentos apropriados em fevereiro entram na estimativa de fevereiro
        por_dia = defaultdict(list)
        for ev, (dia, metodo) in self.EVENTOS_FEV.items():
            if metodo and ev != "F48":  # a apuração roda depois dos ajustes de fim de mês
                por_dia[dia].append((ev, metodo))
        fim = date(ANO, 2, 28)
        for dia in range(1, 29):
            d = date(ANO, 2, dia)
            for ev, metodo in sorted(por_dia.get(dia, [])):
                getattr(self, metodo)(d)
                self.executados.add(ev)
            self.tesouraria(d, "FTES")
        self.ajustes_fev(fim)
        self.f48(fim)
        self.executados.add("F48")
        self.tesouraria(fim, "FTES")

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

    def executar(self, mes: str = "2026-01") -> dict:
        self._executar_jan()
        if mes != "2026-02":
            return self.resultado("2026-01")
        self.L.abrir_mes()
        self._executar_fev()
        return self.resultado("2026-02")

    def _executar_jan(self):
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

    def resultado(self, mes: str = "2026-01") -> dict:
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
            "formato": "labcont-gabarito/1", "mes": mes,
            "sem_gabarito": (sorted([e for e, (_, m) in self.EVENTOS_FEV.items() if not m] + sorted(self.PROVISORIOS_FEV))
                             if mes == "2026-02" else []),
            # eventos de fevereiro processados sem nada a lançar (ex.: aplicação sem saldo): corretos se a dupla não lançar
            "sem_efeito": (sorted(getattr(self, "executados", set()) - {l["evento"] for l in L.lancs})
                           if mes == "2026-02" else []),
            "lancamentos": L.lancs, "memoria": dict(L.memoria), "balancete": contas,
            "totais": {"devedor": tot_d, "credor": tot_c, "ativo": ativo, "passivo_pl": passivo_pl, "resultado": resultado,
                       # o balanço de 2025 tem R$ 0,01 de arredondamento (depreciação acumulada 10.408,33 x 10.408,34)
                       "diferenca": r2(tot_d - tot_c),
                       "fecha": abs(tot_d - tot_c) <= 0.015 and abs(ativo - passivo_pl - resultado) <= 0.015},
            "premissas": {k: PREMISSAS[k] for k in usadas},
            "premissas_evento": {k: sorted(v) for k, v in L.premissas_evento.items()},
        }


def gerar_gabarito(valores: dict, mes: str = "2026-01") -> dict:
    return Gabarito(valores).executar(mes)

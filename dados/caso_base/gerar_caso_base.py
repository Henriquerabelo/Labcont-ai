"""Caso-base da disciplina EH0012 (2026.2) estruturado para parametrização.

Fonte: "Exercício - Laboratório de Prática Contábil (EH-0012) - 2026.2.pdf" (versão revisada de 07/10/2026;
a primeira versão, de 04/09/2026, era um .docx).
Executar este arquivo gera:
  - dados/caso_base/eh0012_2026_2.json  (carga dos cadastros do sistema)
  - docs/PARAMETRIZACAO.md               (documento de análise para validação docente)

Convenções de cada parâmetro variável: base (valor do caso original), min, max,
passo (arredondamento) e, quando houver, regra de derivação ou restrição.
"""
from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def p(nome, base, mn=None, mx=None, passo=None, un="R$", regra=None):
    if un == "R$":  # unidade automática para quantidades, percentuais e tarifas
        n = nome.lower()
        if n.startswith("quantidade"):
            un = "un"
        elif n.startswith(("alíquota", "rateio")):
            un = "%"
        elif n.startswith("tarifa"):
            un = "R$/un"
    d = {"nome": nome, "base": base, "unidade": un}
    if mn is not None:
        d.update({"min": mn, "max": mx, "passo": passo})
    if regra:
        d["regra"] = regra
    return d


# ----------------------------------------------------------------------------
# 0. Empresa, sócios e saldos iniciais
# ----------------------------------------------------------------------------
EMPRESA = {
    "nome": "Empresa LAB",
    "cnae_principal": "2670-1/02 - Fabricação de equipamentos e instrumentos ópticos, fotográficos e cinematográficos",
    "cnae_secundarios": ["4789-0/08 - Comércio varejista de artigos fotográficos e para filmagem",
                         "4619-2/00 - Representantes comerciais e agentes do comércio de mercadorias em geral"],
    "uf": "CE", "municipio": "Fortaleza",
    "regime_federal": "Lucro Real Anual - estimativa mensal (balancete de suspensão/redução)",
    "pis_cofins": "Não cumulativo (1,65% / 7,60%)",
    "ipi": "Contribuinte - alíquotas da TIPI",
    "icms": "Regime normal - recolhimento no mês subsequente; crédito CIAP 1/48 só para imobilizado industrial",
    "iss": "Fortaleza - 5,00%",
    "centro_custo": "01 - Matriz",
    "estoques": "Custo médio ponderado móvel",
    "fpas": "507 - Indústria (encargos INSS+RAT+Terceiros 27,80%; FGTS 8,00%)",
    "destinacao_resultado": {
        "participacao_empregados_admin_pct": p("Participação de empregados e administradores (% do lucro após IR/CS)", 8.0, 5.0, 10.0, 0.5, "%"),
        "reserva_legal_pct": {"base": 5.0, "regra": "Lei 6.404/76, art. 193 - fixo (limite 20% do capital)"},
        "dividendos_pct": p("Dividendos (% do lucro líquido ajustado)", 50.0, 25.0, 50.0, 5.0, "%"),
        "reserva_estatutaria": "saldo remanescente",
    },
    "capital_social": p("Capital social subscrito", 1096000.00, 900000.00, 1300000.00, 1000.00,
                        regra="cotas de R$ 1,00; soma das cotas dos sócios"),
}

SOCIOS = [
    {"nome": "Adalberto Cantareira", "funcao": "Sócio administrador/financeiro", "cotas": 385000, "a_integralizar": 35000.00,
     "integralizacao_evento": "F25", "pro_labore_jan": 9600.00, "pro_labore_fev": 9600.00, "dependentes": "2 filhos (2 e 8 anos)"},
    {"nome": "Marconde Sobreira", "funcao": "Sócio industrial", "cotas": 166000, "a_integralizar": 31000.00,
     "integralizacao_evento": "F15", "pro_labore_jan": 0.00, "pro_labore_fev": 8600.00, "dependentes": "1 filho (7 anos)"},
    {"nome": "Marcela Soares", "funcao": "Sócia comercial", "cotas": 460000, "a_integralizar": 25000.00,
     "integralizacao_evento": "J20", "pro_labore_jan": 7700.00, "pro_labore_fev": 7700.00, "dependentes": "1 filho (14 anos)"},
    {"nome": "Cassilda Apedeuta", "funcao": "Sócia investidora", "cotas": 85000, "a_integralizar": 85000.00,
     "integralizacao_evento": "J34", "pro_labore_jan": 0.00, "pro_labore_fev": 0.00, "dependentes": "-"},
]
PARAM_SOCIOS = [
    p("Participação de cada sócio no capital", "35,13% / 15,15% / 41,97% / 7,76%", 5.0, 50.0, 0.01, "%",
      regra="soma = 100%; cotas inteiras"),
    p("Percentual a integralizar por sócio", "9,09% / 18,67% / 5,43% / 100%", 0.0, 100.0, 1000.0, "%",
      regra="valor a integralizar arredondado a R$ 1.000; ao menos 1 sócio com 100% a integralizar"),
    p("Pró-labore sócio administrador", 9600.00, 7000.00, 12000.00, 100.00),
    p("Pró-labore sócio comercial", 7700.00, 6000.00, 10000.00, 100.00),
    p("Pró-labore sócio industrial (a partir de fevereiro)", 8600.00, 6000.00, 11000.00, 100.00),
]

SALDOS_INICIAIS = {
    "data": "2025-12-31",
    "observacao": ("Balanço de abertura. Na geração por dupla, os saldos ligados a contratos e folha são recalculados "
                   "a partir dos parâmetros sorteados e o saldo bancário (Banco Rico) fecha a equação Ativo = Passivo + PL."),
    "ativo": {
        "Banco Rico - conta corrente": {"valor": 359250.65, "regra": "conta de fechamento (plug)"},
        "ICMS antecipado a recuperar": {"valor": 13258.52},
        "Vale-transporte (adiantamento)": {"valor": 172.80, "regra": "dias úteis × 2 × tarifa × empregados"},
        "Vale-alimentação (adiantamento)": {"valor": 1773.00},
        "Mercadoria ALPHA (620 un × R$ 14,00)": {"valor": 8680.00, "regra": "qtd 400–900 (passo 10); custo 12,00–16,00"},
        "Prêmios de seguros a apropriar": {"valor": 5250.00, "regra": "prêmio × 10/12"},
        "Terrenos": {"valor": 310000.00},
        "Edifícios e construções (galpão)": {"valor": 125000.00},
        "Máquinas e equipamentos industriais": {"valor": 262000.00},
        "Veículos": {"valor": 135000.00},
        "(-) Depreciação acumulada": {"valor": -10408.34},
    },
    "passivo": {
        "Fornecedores de serviços": {"Seguro Verdade": 2100.00, "Contador Formado": 5161.75,
                                      "Internet & Comunicação": 410.00, "Cell Telefonia": 580.00},
        "INSS a recolher": 12822.74, "FGTS a recolher": 1552.64, "Salários a pagar": 15760.64,
        "ICMS a recolher": 43361.80, "ISS a recolher": 7615.00, "PIS a recolher": 5045.29,
        "COFINS a recolher": 23238.90, "IRRF a recolher": 348.93, "CSRF a recolher": 255.75,
        "ICMS antecipado a recolher": 13258.52, "IRPJ estimativa": 33198.47, "CSLL estimativa": 12671.45,
        "Telefone a pagar": 350.00, "Energia a pagar": 1480.00, "Água a pagar": 420.00,
        "Pró-labores a pagar": 13008.92, "Provisões trabalhistas (férias, encargos)": 2411.86,
    },
    "patrimonio_liquido": {"Capital social": 1096000.00, "(-) Capital a integralizar": -176000.00,
                           "Lucros acumulados (resultado 2025)": 94923.97},
}

IMOBILIZADO = [
    {"bem": "Máquina de uso no parque industrial", "ncm": "9010", "aquisicao": "2025-11-05", "valor": 62000.00,
     "taxa_fiscal_aa": 10.0, "classe": "Máquinas e Equipamentos", "vida_util_anos": 8, "residual_pct": 20},
    {"bem": "Veículo utilitário 0 km", "ncm": "8704", "aquisicao": "2025-11-12", "valor": 135000.00,
     "taxa_fiscal_aa": 25.0, "classe": "Veículo - Utilitário", "vida_util_anos": 5, "residual_pct": 40},
    {"bem": "Terreno", "ncm": "", "aquisicao": "2025-11-18", "valor": 310000.00, "taxa_fiscal_aa": 0.0,
     "classe": "Terreno", "vida_util_anos": None, "residual_pct": None},
    {"bem": "Galpão", "ncm": "7610", "aquisicao": "2025-12-01", "valor": 125000.00, "taxa_fiscal_aa": 4.0,
     "classe": "Prédio / Imóvel / Galpão", "vida_util_anos": 20, "residual_pct": 80},
]
VIDA_UTIL = [
    ("Equipamentos de Informática", 3, 0), ("Móveis e Utensílios", 12, 10), ("Prédio / Imóvel / Galpão", 20, 80),
    ("Máquinas e Equipamentos", 8, 20), ("Veículo - Utilitário", 5, 40), ("Veículo - Caminhão", 6, 30),
    ("Veículo - Moto", 2, 50),
]
RATEIO_AREAS = [  # % Administração / Comercial / Industrial
    ("Depreciação - Equipamentos de Informática", 50, 17, 33), ("Depreciação - Móveis e Utensílios", 45, 35, 20),
    ("Depreciação - Prédio", 10, 25, 65), ("Depreciação - Máquinas e Equipamentos", 0, 0, 100),
    ("Depreciação - Veículo Utilitário", 70, 30, 0), ("Depreciação - Veículo Caminhão", 0, 0, 100),
    ("Depreciação - Veículo Moto", 40, 45, 15), ("Internet", 40, 50, 10), ("Telefone / Celular", 20, 60, 20),
    ("Material de Expediente", 60, 30, 10), ("Transporte de empregados", "nº de funcionários", "", ""),
    ("Alimentação", "nº de funcionários", "", ""),
]

# ----------------------------------------------------------------------------
# 1. Contratos
# ----------------------------------------------------------------------------
CONTRATOS = [
    {"id": "C01", "tipo": "Financeiro - Conta garantida", "parte": "Banco Rico S/A", "inicio": "2025-09-15",
     "descricao": "Limite rotativo para cobrir saldo negativo; juros compostos com capitalização diária a partir do dia seguinte ao uso; "
                  "amortização imediata quando houver saldo em conta ou aplicação.",
     "parametros": [p("Limite", 970000.00, 800000.00, 1200000.00, 10000.00),
                    p("Taxa de juros", 3.5, 3.0, 4.0, 0.1, "% a.m.")],
     "eventos": ["uso automático sempre que o caixa ficar negativo"]},
    {"id": "C02", "tipo": "Financeiro - Aplicação de liquidez imediata (INVEST LIQUID)", "parte": "Banco Rico S/A",
     "inicio": "2025-09-20",
     "descricao": "Rendimento prefixado com capitalização diária; resgate automático quando a conta corrente precisar; aplicação só por solicitação.",
     "parametros": [p("Taxa de rendimento", 1.6, 1.2, 2.0, 0.1, "% a.m.")], "eventos": ["J04", "F47"]},
    {"id": "C03", "tipo": "Financeiro - CDB Renda Mais", "parte": "Banco Rico S/A", "inicio": "2026-01-12",
     "descricao": "Título de renda fixa com vencimento em 12 meses (IR regressivo no resgate).",
     "parametros": [p("Valor aplicado", 9000.00, 6000.00, 12000.00, 500.00),
                    p("Taxa", 1.6, 1.2, 2.0, 0.1, "% a.m.")], "eventos": ["J14", "F07"]},
    {"id": "C04", "tipo": "Financeiro - Leasing financeiro (SAC)", "parte": "Banco Rico S/A", "inicio": "2026-01-19",
     "descricao": "Arrendamento de 2 máquinas do parque industrial, com opção de compra (CPC 06 R2). Juros compostos, ano civil.",
     "parametros": [p("Valor das máquinas", 300000.00, 250000.00, 400000.00, 5000.00),
                    p("Taxa de juros", 10.0, 8.0, 14.0, 0.5, "% a.a."),
                    p("Prazo", 18, 12, 24, 6, "meses", regra="valores admitidos: 12, 18 ou 24")],
     "eventos": ["J24", "F33"]},
    {"id": "C05", "tipo": "Serviço - Recrutamento e seleção", "parte": "Recrutamento S/S", "inicio": "2026-01-04",
     "descricao": "Vigência jan-fev/2026; apropriação de 50% por mês; pagamento único em 26/02/2026, na emissão da NFS-e 345 (com retenção de IRRF).",
     "parametros": [p("Honorários brutos", 8800.00, 6000.00, 12000.00, 100.00)], "eventos": ["F41"]},
    {"id": "C06", "tipo": "Serviço - Assessoria contábil", "parte": "Contador Formado S/A (Fortaleza)", "inicio": "2025-09-01",
     "descricao": "Honorários mensais pagos no dia 10 do mês seguinte, com retenções (IRRF 1,5% + CSRF 4,65%). Reajuste a partir de 01/02/2026.",
     "parametros": [p("Honorário mensal", 5500.00, 4500.00, 7000.00, 100.00),
                    p("Reajuste a partir de fevereiro", 25.45, 10.0, 30.0, 0.5, "%", regra="novo valor arredondado a R$ 100")],
     "eventos": ["J11", "J39", "F17", "F45"]},
    {"id": "C07", "tipo": "Comodato - Internet (cable modem)", "parte": "Internet & Comunicação Ltda.", "inicio": "2025-10-10",
     "descricao": "Mensalidade paga no dia 10 do mês seguinte.",
     "parametros": [p("Mensalidade", 410.00, 300.00, 550.00, 10.00)], "eventos": ["J05", "J13", "F03", "F18"]},
    {"id": "C08", "tipo": "Comodato - 5 aparelhos celulares", "parte": "Cell Telefonia Ltda.", "inicio": "2025-10-09",
     "descricao": "Mensalidade paga no dia 9 do mês seguinte.",
     "parametros": [p("Mensalidade", 580.00, 400.00, 750.00, 10.00),
                    p("Quantidade de aparelhos", 5, 3, 8, 1, "un")], "eventos": ["J05", "J10", "F03", "F14"]},
    {"id": "C09", "tipo": "Seguro contra incêndio", "parte": "Seguro Verdade Ltda.", "inicio": "2025-10-16",
     "descricao": "Cobertura de 12 meses a partir de 16/10/2025; prêmio em 3 parcelas (16/11/2025, 16/12/2025 e 17/01/2026); apropriação mensal pro rata.",
     "parametros": [p("Prêmio total", 6300.00, 4800.00, 8400.00, 100.00),
                    p("Número de parcelas", 3, un="un")], "eventos": ["J21"]},
    {"id": "C10", "tipo": "Mútuo cedido a sócia (parte relacionada)", "parte": "Cassilda Apedeuta", "inicio": "2026-02-18",
     "descricao": "Empréstimo da empresa à sócia; juros compostos apropriados por fração diária; sem vencimento; juros compensados com dividendos.",
     "parametros": [p("Valor do mútuo", 30000.00, 20000.00, 45000.00, 1000.00),
                    p("Taxa de juros", 4.0, 2.0, 5.0, 0.5, "% a.m.")], "eventos": ["F27"]},
    {"id": "C11", "tipo": "Serviço - Projeto de arquitetura (autônomo, RPA)", "parte": "Arquiteto autônomo (contribuinte de Fortaleza)",
     "inicio": "2026-01-20",
     "descricao": "Pagamento em 17/02/2026; retenções de INSS, IRRF e ISS do autônomo; encargo patronal de 20%.",
     "parametros": [p("Valor bruto", 10600.00, 8000.00, 14000.00, 100.00)], "eventos": ["J23", "F30"]},
    {"id": "C12", "tipo": "Serviço - Reforma do galpão industrial", "parte": "Construtor Express Ltda.", "inicio": "2026-01-22",
     "descricao": "Contrato em 2 parcelas de 50% (22/01 e 22/02); parte material e parte mão de obra (base de ISS/retenções).",
     "parametros": [p("Valor total", 228000.00, 180000.00, 300000.00, 1000.00),
                    p("Parcela de material", 40.0, 30.0, 50.0, 5.0, "%")], "eventos": ["J26", "F32"]},
]

# ----------------------------------------------------------------------------
# 2. Folha de pagamento
# ----------------------------------------------------------------------------
FOLHA_REGRAS = {
    "processamento": {"jan": "2026-01-15", "fev": "2026-02-13"},
    "pagamento": "dia 05 do mês subsequente",
    "admissoes": "somente no 1º dia do mês",
    "vale_transporte": {"tarifa": 5.40, "por_dia": 2, "desconto": "6% do salário-base (limitado ao benefício recebido)"},
    "vale_alimentacao": {"valor_dia": 26.00, "por_dia": 1, "desconto": "5% do benefício"},
    "dias_uteis": {"fev/2026": 18, "mar/2026": 20},
    "encargos": "INSS patronal + RAT + Terceiros 28,80% (FPAS 507, RAT 3%); FGTS 8,00% (sobre folha, férias e 13º)",
    "provisoes": "Férias + 1/3 e 13º salário (1/12 por mês), com encargos",
    "tabelas": "INSS, IRRF e salário-família vigentes em 2026",
}
PARAM_FOLHA = [
    p("Salário-base de cada empregado", "conforme tabela", -20.0, 20.0, 10.00, "% sobre a base",
      regra="arredondar a R$ 10; nunca abaixo do salário mínimo vigente; manter a hierarquia entre cargos"),
    p("Horas extras (valor)", "conforme tabela", 0.0, 10.0, 1.00, "% do salário", regra="pelo menos 1/3 dos empregados com HE"),
    p("Comissões (área comercial)", "conforme tabela", 0.0, 15.0, 1.00, "% do salário"),
    p("Número de dependentes (filhos)", "conforme tabela", 0, 3, 1, "un", regra="idades coerentes entre jan e fev"),
    p("Dias úteis para VT/VA", 18, None, None, None, "dias", regra="fixo pelo calendário (fev/2026 = 18; mar/2026 = 20)"),
]
FUNCIONARIOS = [
    # setor, nome, admissão, salário jan, HE jan, comissão jan, dependentes jan, salário fev, HE fev, comissão fev, dependentes fev
    ("Administração", "Alves Africano", "anterior", 5920.00, 280.00, None, "2 (20 e 16 anos)", 5920.00, 458.00, None, "2 (20 e 16 anos)"),
    ("Administração", "Venâncio Australiano", "anterior", 1621.00, 45.00, None, "1 (9 anos)", 1621.00, None, None, "1 (9 anos)"),
    ("Administração", "Tiago Espanhol", "anterior", 4100.00, None, None, "1 (7 anos)", 4100.00, 373.00, None, "1 (7 anos)"),
    ("Comercial", "Ângela Peruana", "anterior", 2100.00, 100.00, 400.00, "2 (10 e 14 anos)", 1621.00, None, 77.00, "2 (10 e 14 anos)"),
    ("Comercial", "Marena Russa", "anterior", 2500.00, 200.00, 500.00, "1 (9 anos)", 5700.00, 389.00, 285.00, "1 (9 anos)"),
    ("Comercial", "Vitor Canadense", "2026-02-01", None, None, None, None, 4000.00, 273.00, None, "1 (16 anos)"),
    ("Industrial - MOD Produto X", "Eurico Canadense", "2026-02-01", None, None, None, None, 3600.00, 246.00, None, "1 (3 anos)"),
    ("Industrial - MOD Produto X", "Pedro Algarve", "2026-02-01", None, None, None, None, 6200.00, None, None, "2 (12 e 9 anos)"),
    ("Industrial - MOD Produto X", "Regina Italiana", "2026-02-01", None, None, None, None, 1680.00, 115.00, None, "2 (7 e 8 anos)"),
    ("Industrial - MOD Produto X", "Renato Português", "2026-02-01", None, None, None, None, 2120.00, None, None, "2 (8 e 10 anos)"),
    ("Industrial - MOD Produto Y", "Gustavo Equatoriano", "2026-02-01", None, None, None, None, 5450.00, 372.00, None, "1 (5 anos)"),
    ("Industrial - MOD Produto Y", "Rubens Irlandês", "2026-02-01", None, None, None, None, 1720.00, None, None, "1 (3 anos)"),
    ("Industrial - MOD Produto Y", "Vitor Veneza", "2026-02-01", None, None, None, None, 2500.00, 171.00, None, "0"),
    ("Industrial - MOI", "Breno Alemão", "2026-02-01", None, None, None, None, 5300.00, 362.00, None, "0"),
    ("Industrial - MOI", "Cleide Ucraniana", "2026-02-01", None, None, None, None, 1830.00, None, None, "3 (5, 8 e 14 anos)"),
]

# ----------------------------------------------------------------------------
# 3. Produção: itens, ficha técnica e plano
# ----------------------------------------------------------------------------
ITENS = [
    # código, descrição, tipo, NCM, custo unitário base (compra), faixa de custo
    ("MP-A", "Matéria-prima A", "Matéria-prima", "9002.11.11", 9.0867112, (7.70, 10.50)),
    ("MP-B", "Matéria-prima B", "Matéria-prima", "9007.20.20", 11.2986347, (9.60, 13.00)),
    ("MS-Z", "Material secundário Z", "Material secundário", "9002.20.10", 10.0600459, (8.50, 11.60)),
    ("MS-Q", "Material secundário Q", "Material secundário", "9008.50.00", 11.553644, (9.80, 13.30)),
    ("MS-R", "Material secundário R", "Material secundário", "9013.20.00", 12.5750572, (10.70, 14.50)),
    ("MS-K", "Material secundário K", "Material secundário", "9011.20.20", 13.28943795, (11.30, 15.30)),
    ("ME-H", "Material de embalagem H", "Embalagem", "3923.21.10", 5.65893, (4.80, 6.50)),
    ("X", "Produto X", "Produto acabado", "9006.53.20", None, None),
    ("Y", "Produto Y", "Produto acabado", "9007.10.00", None, None),
    ("ALPHA", "Mercadoria para revenda ALPHA", "Mercadoria", "9032.10.10", 19.6703463, (17.50, 22.00)),
]
FICHA_TECNICA = {
    "X": {"MP-A": 4, "MP-B": 2, "MS-Z": 5, "MS-Q": 1, "MS-K": 3, "ME-H": 1},
    "Y": {"MP-A": 3, "MP-B": 5, "MS-Z": 2, "MS-R": 2, "MS-K": 4, "ME-H": 1},
}
PLANO_PRODUCAO = {"mes": "2026-02", "X": 19300, "Y": 18700,
                  "inicio": "dia útil seguinte à compra do ME-H (19/02/2026)", "duracao": "3 dias úteis (término 23/02/2026)"}
PARAM_PRODUCAO = [
    p("Quantidade produzida - Produto X", 19300, 15000, 25000, 100, "un"),
    p("Quantidade produzida - Produto Y", 18700, 15000, 25000, 100, "un"),
    p("Coeficientes da ficha técnica", "conforme ficha", -1, 1, 1, "un/produto",
      regra="variação de ±1 unidade por insumo, mínimo 1; ME-H sempre 1 por produto"),
    p("Sobra de compra sobre a necessidade", "140 a 280 un", 100, 300, 10, "un",
      regra="quantidade comprada = necessidade da ficha técnica + sobra (MP-A: + devolução)"),
    p("Custo unitário de compra de cada insumo", "ver itens", -15.0, 15.0, 0.0001, "%"),
    p("Percentual vendido da produção", "99,4% (X) / 99,0% (Y)", 98.5, 99.8, 0.1, "%",
      regra="quantidade vendida inteira, menor que a produzida"),
]
MARKUP = {"ICMS": 20.00, "PIS": 1.65, "COFINS": 7.60, "margem_contribuicao": 45.00,
          "divisor": 0.2575, "multiplicador": 3.8835,
          "parametro": p("Margem de contribuição", 45.0, 40.0, 50.0, 1.0, "%",
                         regra="ICMS, PIS e COFINS seguem a legislação (não variam)")}

# ----------------------------------------------------------------------------
# 4. Eventos
#   natureza: V = valores variáveis (parametrizados) | D = derivado (calculado pelo
#   sistema a partir de saldos, contratos, folha ou produção) | F = fixo
# ----------------------------------------------------------------------------
def ev(id_, data, grupo, desc, natureza, parametros=None, contrato=None, obs=None):
    d = {"id": id_, "data": data, "grupo": grupo, "descricao": desc, "natureza": natureza}
    if parametros:
        d["parametros"] = parametros
    if contrato:
        d["contrato"] = contrato
    if obs:
        d["obs"] = obs
    return d


EVENTOS = [
    # ------------------------------ JANEIRO -------------------------------
    ev("J01", "2026-01-02", "Societário", "Destinação do resultado do exercício de 2025 (participações, reserva legal, dividendos, reserva estatutária)", "D"),
    ev("J02", "2026-01-02", "Utilidades", "NF Energia Luz do Sertão n.º 987321 - consumo jan; vencimento 14/01", "V",
       [p("Valor total", 2520.00, 2200.00, 2900.00, 10.00), p("Parcela da área administrativa", 46.4, 40.0, 55.0, 0.1, "%"),
        p("Tarifa", 1.4316, regra="fixa; consumo (kWh) = valor ÷ tarifa")]),
    ev("J03", "2026-01-05", "Utilidades", "Fatura de água Águas do Litoral n.º 321654 - consumo jan; vencimento 14/01", "V",
       [p("Valor total", 590.00, 500.00, 700.00, 10.00), p("Tarifa", 23.62, regra="fixa; m³ = valor ÷ tarifa")],
       obs="Rateio da fatura: área administrativa R$ 210,00 e comercial R$ 380,00."),
    ev("J04", "2026-01-05", "Financeiro", "Aplicação no INVEST LIQUID (Banco Rico)", "V",
       [p("Valor aplicado", 18000.00, 15000.00, 25000.00, 500.00)], "C02"),
    ev("J05", "2026-01-06", "Utilidades", "NFs de telefonia fixa, celular e internet - competência jan", "V",
       [p("Telefone fixo", 687.00, 600.00, 800.00, 1.00)], "C07/C08",
       obs="Celular e internet seguem os contratos C08 e C07."),
    ev("J06", "2026-01-06", "Pagamento", "Pagamento da folha e do pró-labore de 12/2025", "D"),
    ev("J07", "2026-01-07", "Pagamento", "Pagamento do FGTS e FGTS sobre 13º de 12/2025", "D"),
    ev("J08", "2026-01-08", "Compra - imobilizado", "NF 7.852 Ar Frio Ltda. (MA, CFOP 6.102) - ar-condicionados para a administração; 20% à vista e 2 parcelas (07/02 e 07/03)", "V",
       [p("Quantidade", 5, 3, 8, 1, "un"), p("Valor unitário", 4400.00, 3800.00, 5200.00, 50.00),
        p("Entrada à vista", 20.0, 10.0, 30.0, 5.0, "%")], obs="Gera DIFAL e crédito/estorno conforme destinação (uso administrativo)."),
    ev("J09", "2026-01-08", "Compra - frete", "CT-e 322.123 Rodovia Transportes - frete da NF 7.852, à vista", "V",
       [p("Valor do frete", 1050.00, 800.00, 1300.00, 10.00)]),
    ev("J10", "2026-01-09", "Pagamento", "Pagamento Cell Telefonia - competência 12/2025", "D", contrato="C08"),
    ev("J11", "2026-01-09", "Pagamento", "Pagamento Contador Formado - dezembro/2025", "D", contrato="C06"),
    ev("J12", "2026-01-09", "Tributos", "Pagamento do ISS de 12/2025", "D"),
    ev("J13", "2026-01-09", "Pagamento", "Pagamento Internet & Comunicação - 12/2025", "D", contrato="C07"),
    ev("J14", "2026-01-12", "Financeiro", "Aplicação no CDB Renda Mais (12 meses)", "V", contrato="C03"),
    ev("J15", "2026-01-12", "Compra - mercadoria", "NF 3.369 Comercial Elegante (PB, CFOP 6.102) - mercadoria ALPHA, desconto incondicional, 20% à vista e saldo em 14/02; CT-e 423.765 frete FOB (venc. 18/01)", "V",
       [p("Quantidade", 18075, 15000, 21000, 25, "un"), p("Custo unitário", 19.6703463, 17.50, 22.00, 0.0001),
        p("Desconto incondicional", 5.0, 3.0, 7.0, 0.5, "%"), p("Frete", 1720.00, 1400.00, 2100.00, 10.00)]),
    ev("J16", "2026-01-13", "Receita - serviço", "NFS-e 002 para Algodão Doce - comissão de representação (Beta); recebimento 20/01", "V",
       [p("Valor da comissão", 98000.00, 80000.00, 115000.00, 500.00)]),
    ev("J17", "2026-01-14", "Pagamento", "Pagamento de água, energia e telefone - competência 01/2026", "D"),
    ev("J18", "2026-01-15", "Folha", "Processamento da folha e pró-labore de janeiro + provisões", "D"),
    ev("J19", "2026-01-15", "Depreciação", "Depreciação de janeiro", "D"),
    ev("J20", "2026-01-16", "Societário", "Integralização de capital - Marcela Soares", "D"),
    ev("J21", "2026-01-19", "Pagamento", "Pagamento da 3ª e última parcela do seguro (Seguro Verdade)", "D", contrato="C09"),
    ev("J22", "2026-01-19", "Pagamento", "Pagamento do CT-e 423.765", "D"),
    ev("J23", "2026-01-20", "Serviço tomado", "Contratação de arquiteto autônomo (RPA) - pagamento em 17/02", "V", contrato="C11"),
    ev("J24", "2026-01-19", "Financeiro", "Liberação do leasing para aquisição de 2 máquinas industriais", "V", contrato="C04"),
    ev("J25", "2026-01-21", "Recebimento", "Recebimento da comissão (NFS-e 002)", "D"),
    ev("J26", "2026-01-22", "Serviço tomado", "NFS-e 6.300 Construtor Express - 1ª parcela (50%) da reforma do galpão", "V", contrato="C12"),
    ev("J27", "2026-01-23", "Venda - mercadoria", "NF 001 Comercial Caribe (CE, CFOP 5.102) - venda de ALPHA, preço pelo mark-up, boleto em 28/01", "V",
       [p("Quantidade vendida", 8200, 7000, 9500, 50, "un", regra="não pode superar o estoque disponível")]),
    ev("J28", "2026-01-23", "Tributos", "Pagamento da GPS (INSS) de 12/2025", "D"),
    ev("J29", "2026-01-26", "Tributos - infração", "Auto de infração SEFAZ-CE (mercadorias sem nota) - pagamento em 05/02 com redução de multa", "V",
       [p("Base de cálculo", 70000.00, 50000.00, 90000.00, 1000.00),
        p("Alíquota aplicada", 18.0, regra="ICMS = base × alíquota; multa = 75% do ICMS (conforme o caso)")]),
    ev("J30", "2026-01-26", "Compra - insumo", "NF 23.456 Indústria Sofisticada (MG, CFOP 6.101) - MP-A; 25% à vista, 30% em 26/02 e 45% em 24/03; CT-e 423.951 frete CIF", "V",
       [p("Quantidade", 133900, regra="derivada: necessidade de MP-A + sobra + devolução (F28)"),
        p("Custo unitário", 9.0867112, 7.70, 10.50, 0.0001), p("Frete", 2050.00, 1700.00, 2400.00, 10.00)]),
    ev("J31", "2026-01-27", "Tributos", "Pagamento de PIS e COFINS de 12/2025", "D"),
    ev("J32", "2026-01-27", "Pagamento", "Pagamento de telefone fixo, energia e água de 12/2025", "D"),
    ev("J33", "2026-01-28", "Recebimento", "Recebimento de Comercial Caribe (NF 001)", "D"),
    ev("J34", "2026-01-28", "Societário", "Integralização de capital - Cassilda Apedeuta", "D"),
    ev("J35", "2026-01-29", "Tributos", "Pagamento de ICMS (normal, antecipado, DIFAL) de 12/2025", "D"),
    ev("J36", "2026-01-30", "Folha - benefício", "Compra de vale-transporte para fevereiro (Sindiônibus 14.320)", "D"),
    ev("J37", "2026-01-30", "Folha - benefício", "Compra de vale-alimentação para fevereiro (Ticket 4.310)", "D"),
    ev("J38", "2026-01-30", "Tributos", "Pagamento de IRPJ e CSLL de 12/2025", "D"),
    ev("J39", "2026-01-30", "Serviço tomado", "NFS-e 023 Contador Formado - janeiro, pagamento em 10/02", "D", contrato="C06"),
    ev("J40", "2026-01-30", "Apuração", "Apuração de ICMS, ISS, PIS, COFINS, IPI, IRPJ e CSLL de janeiro", "D"),
    # ------------------------------ FEVEREIRO -----------------------------
    ev("F01", "2026-02-02", "Utilidades", "NF Energia Luz do Sertão n.º 988.333 - consumo fev; vencimento 12/02", "V",
       [p("Valor total", 3400.00, 3000.00, 3900.00, 10.00),
        p("Rateio Adm/Com/Ind X/Ind Y", "15,6/17,4/31,5/35,6", regra="percentuais sorteados ±5 p.p., soma 100%"),
        p("Tarifa", 1.432, regra="fixa")], obs="Rateio da fatura: administrativa R$ 530,00, comercial R$ 590,00, Produto X R$ 1.070,00 e Produto Y R$ 1.210,00."),
    ev("F02", "2026-02-02", "Utilidades", "Fatura de água Águas do Litoral n.º 322.666 - consumo fev; vencimento 12/02", "V",
       [p("Valor total", 1780.00, 1500.00, 2100.00, 10.00), p("Tarifa", 23.62, regra="fixa")],
       obs="Rateio da fatura: administrativa R$ 280,00, comercial R$ 320,00, Produto X R$ 610,00 e Produto Y R$ 570,00."),
    ev("F03", "2026-02-02", "Utilidades", "NFs de telefonia fixa, celular e internet - competência fev", "V",
       [p("Telefone fixo", 690.00, 600.00, 800.00, 1.00)], "C07/C08"),
    ev("F04", "2026-02-03", "Venda - mercadoria", "NF 337 - venda de ALPHA a consumidor final em São Luís-MA, PIX, preço pelo mark-up (DIFAL)", "V",
       [p("Quantidade", 40, 20, 80, 5, "un")]),
    ev("F05", "2026-02-04", "Compra - insumo", "NF 12.380 Indústria Zalego (TO) - MP-B; 35% à vista, saldo em 03/03; desconto financeiro condicional; CT-e 424.110 (venc. 13/02)", "V",
       [p("Quantidade", 132310, regra="derivada: necessidade de MP-B + sobra"),
        p("Custo unitário", 11.2986347, 9.60, 13.00, 0.0001), p("Desconto financeiro condicional", 4.0, 3.0, 5.0, 0.5, "%"),
        p("Frete", 1980.00, 1600.00, 2300.00, 10.00)]),
    ev("F06", "2026-02-05", "Tributos - infração", "Pagamento do auto de infração (com redução de 70% da multa)", "D"),
    ev("F07", "2026-02-05", "Financeiro", "Apropriação do rendimento do CDB Renda Mais", "D", contrato="C03"),
    ev("F08", "2026-02-06", "Receita - serviço", "NFS-e 003 para Algodão Doce - comissão de representação (Beta); recebimento 08/02", "V",
       [p("Valor da comissão", 82000.00, 70000.00, 100000.00, 500.00)]),
    ev("F09", "2026-02-06", "Pagamento", "Pagamento da folha e pró-labore de 01/2026", "D"),
    ev("F10", "2026-02-09", "Compra - insumo", "NF 9.147 Distribuidor Verde Oliva (RJ) - materiais secundários Z, Q, R e K; 15% à vista e 2 parcelas (07/03, 07/04); frete CIF", "V",
       [p("Quantidades", "134.130 / 19.440 / 37.560 / 132.870", regra="derivadas: necessidade + sobra"),
        p("Custos unitários", "10,06 / 11,55 / 12,58 / 13,29", regra="faixas na tabela de itens")]),
    ev("F11", "2026-02-09", "Pagamento", "Pagamento parcial (40%) da NF 7.852 (Ar Frio)", "D"),
    ev("F12", "2026-02-10", "Tributos", "Pagamento do FGTS de 01/2026", "D"),
    ev("F13", "2026-02-10", "Recebimento", "Recebimento da comissão (NFS-e 003)", "D"),
    ev("F14", "2026-02-11", "Pagamento", "Pagamento Cell Telefonia - janeiro", "D", contrato="C08"),
    ev("F15", "2026-02-11", "Societário", "Integralização de capital - Marconde Sobreira", "D"),
    ev("F16", "2026-02-12", "Tributos", "Pagamento do ISSQN de 01/2026", "D"),
    ev("F17", "2026-02-10", "Pagamento", "Pagamento da NFS-e 023 (contabilidade de janeiro)", "D", contrato="C06"),
    ev("F18", "2026-02-13", "Pagamento", "Pagamento Internet & Comunicação - janeiro", "D", contrato="C07"),
    ev("F19", "2026-02-13", "Pagamento", "Pagamento de água, energia e telefone - competência 02/2026", "D"),
    ev("F20", "2026-02-13", "Folha", "Processamento da folha e pró-labore de fevereiro + provisões", "D"),
    ev("F21", "2026-02-13", "Depreciação", "Depreciação de fevereiro", "D"),
    ev("F22", "2026-02-18", "Compra - insumo", "NF 1.747 Embalagens Comerciais (AM) - ME-H; 30% à vista, saldo em 13/03; CT-e 425.130 (venc. 22/02)", "V",
       [p("Quantidade", 38150, regra="derivada: produção X + Y + sobra"), p("Custo unitário", 5.65893, 4.80, 6.50, 0.0001),
        p("Frete", 1410.00, 1100.00, 1700.00, 10.00)]),
    ev("F23", "2026-02-18", "Pagamento", "Pagamento do CT-e 424.110", "D"),
    ev("F24", "2026-02-18", "Pagamento", "Pagamento do saldo da NF 3.369 (Comercial Elegante)", "D"),
    ev("F25", "2026-02-19", "Societário", "Integralização de capital - Adalberto Cantareira", "D"),
    ev("F26", "2026-02-19", "Venda - mercadoria", "NF 003 Comercial Caribe (CE, CFOP 5.102) - venda de ALPHA pelo mark-up; boleto em 27/02", "V",
       [p("Quantidade vendida", 10400, 9000, 11000, 50, "un", regra="não pode superar o estoque disponível")]),
    ev("F27", "2026-02-20", "Financeiro", "Cessão de mútuo à sócia Cassilda Apedeuta (valor disponibilizado à sócia, conforme o contrato C10)", "V", contrato="C10"),
    ev("F28", "2026-02-20", "Devolução de compra", "NF 004 (CFOP 6.201) - devolução de MP-A com defeito à Indústria Sofisticada", "V",
       [p("Quantidade devolvida", 320, 150, 500, 10, "un")]),
    ev("F29", "2026-02-20", "Tributos", "Pagamento do IRRF de 01/2026", "D"),
    ev("F30", "2026-02-23", "Pagamento", "Quitação do arquiteto (RPA)", "D", contrato="C11"),
    ev("F31", "2026-02-23", "Tributos", "Pagamento da GPS (INSS) de 01/2026", "D"),
    ev("F32", "2026-02-23", "Serviço tomado", "NFS-e 6.320 Construtor Express - 2ª parcela da reforma", "D", contrato="C12"),
    ev("F33", "2026-02-23", "Financeiro", "Pagamento da 1ª parcela do leasing (SAC)", "D", contrato="C04"),
    ev("P01", "2026-02-19", "Produção", "Requisição de materiais e início da produção de X e Y (dia útil seguinte à compra do ME-H)", "D",
       obs="Evento implícito nas regras do caso; não aparece na lista original."),
    ev("P02", "2026-02-23", "Produção", "Término da produção (3 dias úteis) e transferência para produtos acabados", "D",
       obs="Evento implícito nas regras do caso."),
    ev("F34", "2026-02-24", "Venda - produção", "NF 005 Comercial Roma (PA, CFOP 6.101) - Produtos X e Y pelo mark-up; 80% na emissão e 20% em 22/03; desconto financeiro sobre Y", "V",
       [p("Quantidade vendida X", 19190, regra="produção de X × percentual vendido"),
        p("Quantidade vendida Y", 18520, regra="produção de Y × percentual vendido"),
        p("Desconto financeiro sobre Y", 3.0, 2.0, 4.0, 0.5, "%"), p("Recebimento na emissão", 80.0, 70.0, 90.0, 5.0, "%")]),
    ev("F35", "2026-02-24", "Pagamento", "Pagamento do CT-e 425.130", "D"),
    ev("F36", "2026-02-24", "Devolução de venda", "NF 1.320 Comercial Caribe - devolução de ALPHA (abate o boleto)", "V",
       [p("Quantidade devolvida", 70, 40, 120, 5, "un")]),
    ev("F37", "2026-02-25", "Pagamento", "Pagamento de 30% da NF 23.456 (Indústria Sofisticada)", "D"),
    ev("F38", "2026-02-25", "Folha - benefício", "Compra de vale-transporte para março (Sindiônibus 15.520)", "D"),
    ev("F39", "2026-02-25", "Folha - benefício", "Compra de vale-alimentação para março (Ticket 5.410)", "D"),
    ev("F40", "2026-02-26", "Tributos", "Pagamento de ICMS (normal, antecipado, DIFAL) de 01/2026", "D"),
    ev("F41", "2026-02-26", "Serviço tomado", "NFS-e 345 Recrutamento S/S - seleção de pessoal (jan-fev); pagamento na emissão", "D", contrato="C05"),
    ev("F42", "2026-02-26", "Tributos", "Pagamento de PIS e COFINS de 01/2026", "D"),
    ev("F43", "2026-02-27", "Tributos", "Pagamento das CSRF de 01/2026", "D"),
    ev("F44", "2026-02-27", "Recebimento", "Recebimento de Comercial Caribe (NF 003, líquido da devolução)", "D"),
    ev("F45", "2026-02-27", "Serviço tomado", "NFS-e 024 Contador Formado - fevereiro (valor reajustado)", "D", contrato="C06"),
    ev("F46", "2026-02-27", "Tributos", "Pagamento de IRPJ e CSLL por estimativa de 01/2026", "D"),
    ev("F47", "2026-02-27", "Financeiro", "Resgate do rendimento da aplicação, líquido de IR", "D", contrato="C02"),
    ev("F48", "2026-02-27", "Apuração", "Apuração de ICMS, ISS, PIS, COFINS, IPI, IRPJ e CSLL de fevereiro", "D"),
]

# ----------------------------------------------------------------------------
# Inconsistências encontradas no caso original (para revisão docente)
# ----------------------------------------------------------------------------
INCONSISTENCIAS = [
    # onde, descrição, status, decisão (correções do professor de 07/10 e 11/10/2026)
    ("Conta garantida (C01)", "Limite escrito como \"R$ 970.000,00 (novecentos mil reais)\"; número e extenso divergem.", "RESOLVIDA", "Decisão do professor (11/10/2026): novecentos e setenta mil reais."),
    ("Leasing (C04, J24, F33)", "Contrato \"assinado e liberado em 19/01\"; o evento de liberação era 20/01.", "RESOLVIDA", "Decisão do professor (11/10/2026): liberação em 19/01, data do contrato."),
    ("Arquiteto (C11, J23, F30)", "Contratado em 20/01; a quitação (23/02) diz \"contratado em 19/01\".", "RESOLVIDA", "Decisão do professor (11/10/2026): contratação em 20/01."),
    ("Recrutamento (C05, F41)", "Honorários pagos em 24/02, mas a NFS-e 345 só é emitida em 26/02; não havia evento de pagamento.", "RESOLVIDA", "Decisão do professor (11/10/2026): pagamento somente em 26/02, na emissão da NFS-e 345."),
    ("Mútuo (C10, F27)", "Contrato de R$ 30.000,00; o evento cedia R$ 20.000,00. O título diz \"com os sócios\".", "RESOLVIDA", "Decisão do professor (11/10/2026): cessão de R$ 30.000,00 no caso-base (o valor da dupla está no contrato C10); texto do contrato mantido."),
    ("Seguro (C09, J21)", "Última parcela vence em 17/01 (sábado) e o pagamento ocorre em 19/01.", "RESOLVIDA", "Decisão do professor (11/10/2026): 3ª e última parcela; vencimento em fim de semana é pago no próximo dia útil (19/01)."),
    ("Contabilidade (C06)", "Razão social \"S/S\" e \"S/A\"; contrato prevê pagamento no dia 10, mas a NFS-e 024 indicava 05/03 e o pagamento da NFS-e 023 era em 12/02.", "RESOLVIDA", "Decisão do professor (11/10/2026): Contador Formado S/A; pagamento no dia 10 do mês seguinte (NFS-e 023 em 10/02; NFS-e 024 em 10/03)."),
    ("Comodatos (C07, C08)", "Contratos de R$ 350,00 e R$ 480,00, mas o balanço registra R$ 410,00 (internet) e R$ 580,00 (celular) a pagar.", "RESOLVIDA", "Decisão do professor (11/10/2026): contratos de R$ 410,00 (internet) e R$ 580,00 (celulares); as notas de telefonia de janeiro e fevereiro acompanham."),
    ("Frete MP-A (J30)", "Frete CIF, mas há CT-e na NF 23.456; vencimento \"24.02.2025\".", "MANTIDA", "Decisão do professor (11/10/2026): frete CIF, a cargo do fornecedor; o CT-e não tem evento de pagamento (sem lançamento). Correção de 11/10/2026 (análise completa): texto sem o vencimento do CT-e."),
    ("NF 23.456 (J30, F37)", "Evento em 26/01; o pagamento de 25/02 diz \"emitida em 24/01/2026\".", "MANTIDA", "Decisão do professor (11/10/2026): emissão em 24/01 e entrada em 26/01."),
    ("Auto de infração (J29, F06)", "TIF n.º 20230001/00 e 20220001/00; pagamento previsto em 05/02 e evento em 04/02; multa \"9,450,00\"; ICMS de 18%; redução de 70%.", "RESOLVIDA", "Decisão do professor (11/10/2026): pagamento em 05/02; redução de 70% da multa por pagamento no prazo, sem recurso; alíquota de 18%. Correção de 11/10/2026 (análise completa): TIF n.º 20260001/00, de 12/01/2026, nos dois eventos."),
    ("Aplicações (J14, F07)", "CDB \"realizado em 11/01\" (domingo) e evento em 12/01.", "RESOLVIDA", "Decisão do professor (11/10/2026): renda fixa (05/01) e CDB são aplicações diferentes; data em fim de semana vai para o próximo dia útil (12/01). Correção de 11/10/2026 (análise completa): o texto de 05/02 passa a \"realizada no dia 12/01/2026\"."),
    ("Ar Frio (J08, F11)", "Pagamento de 09/02 cita NF \"emitida em 05/01\" e pagava 45%, enquanto o contrato prevê 2 parcelas iguais de 40%.", "RESOLVIDA", "Decisão do professor (11/10/2026): emissão em 05/01 e entrada em 08/01; pagamento de 40% em 09/02."),
    ("Vendas ALPHA (J27, J33, F26, F36, F44)", "Boleto da NF 001 em 25/01 e recebimento em 28/01; NF 003 emitida em 19/02 mas citada como \"de 15/02\"; vencimento 28/02 vs. \"27/02\".", "RESOLVIDA", "Correção de 11/10/2026 (análise completa): boleto da NF 001 com vencimento em 28/01 (data do recebimento); NF 003 citada como de 19/02; boleto da NF 003 com vencimento em 27/02 (28/02 é sábado), data do recebimento."),
    ("Comissões (J16, J25, F08, F13)", "Recebimentos previstos em 20/01 e 08/02; eventos de recebimento em 21/01 e 10/02.", "MANTIDA", "Decisão do professor (11/10/2026): recebimentos em atraso, sem juros e multa."),
    ("Folha (funcionários)", "Idades dos dependentes diminuíam de janeiro para fevereiro; salários de Ângela (2.100 → 1.530) e Marena (2.500 → 5.700) mudam sem evento; valor digitado \"2.500.00\".", "RESOLVIDA", "Decisão do professor (11/10/2026): idades de fevereiro iguais às de janeiro; salário de R$ 2.500,00 em janeiro (Marena). Correção de 11/10/2026 (análise completa): salário de fevereiro da Ângela igual ao salário mínimo de 2026 (R$ 1.621,00)."),
    ("Telefonia (J05, F03)", "Celular com vencimento em 08/02 e 08/03 (contrato: dia 9); telefone fixo com vencimento em 24/02 e 24/03, mas pago em 14/01 e 13/02.", "RESOLVIDA", "Correção de 11/10/2026 (análise completa): celular com vencimento em 09/02 e 09/03; telefone fixo com vencimento na data do pagamento (14/01 e 13/02)."),
    ("CT-e 424.110 (F05, F23)", "O pagamento de 18/02 diz CT-e \"emitido em 05.02.2026\"; a NF 12.380 e o CT-e são de 04/02.", "RESOLVIDA", "Correção de 11/10/2026 (análise completa): CT-e emitido em 04/02/2026."),
    ("Quadro de prazos", "Turma 01A – 15/11/2026 marcada como sexta (é domingo e feriado); \"Janeiro / 2026.1\" e \"Fevereiro / 2026.1\".", "RESOLVIDA", "Correção de 11/10/2026 (análise completa): 2ª parte da Turma 01A em 06/11/2026 (sexta, uma semana antes da prova); períodos Janeiro/2026 e Fevereiro/2026."),
    ("Energia e água (J03, F01, F02)", "Tabelas de rateio incompletas: água/jan sem R$ 380,00; energia/fev sem a área administrativa (R$ 530,00); água/fev sem R$ 1.180,00 (área industrial).", "RESOLVIDA", "Corrigido pelo professor no exercício revisado de 07/10/2026."),
    ("Encargos (FPAS)", "Texto usa 27,80%; a planilha de apoio traz FPAS 507 com RAT 3% (= 28,80%).", "RESOLVIDA", "Decisão do professor (11/10/2026): encargos de 28,80% (INSS + RAT 3% + Terceiros)."),
    ("Imobilizado", "Balanço: Máquinas R$ 262.000,00; tabela de bens: máquina de R$ 62.000,00.", "RESOLVIDA", "Corrigido pelo professor no exercício revisado de 07/10/2026."),
    ("Materiais secundários (F10)", "Planilha de apoio cita \"MP-Z\" e \"MS-W\", inexistentes na ficha técnica. (Corrigido em 07/10: total da NF 9.147 = R$ 3.812.043,57.)", "PENDENTE", None),
    ("Balanço de 31/12/2025 (versão de 07/10)", "Após o ajuste de centavos, os subtotais Obrigações Fiscais (138.994,12; soma 138.994,11) e Ativo não Circulante/Imobilizado (821.591,67; correto 821.591,66) não foram atualizados; a despesa de depreciação na DRE de 2025 segue 10.408,33.", "MANTIDA", "Decisão do professor (11/10/2026): ajustar os subtotais do Balanço; manter a depreciação de 10.408,33 na DRE."),
]


# ----------------------------------------------------------------------------
def gerar():
    dados = {
        "caso": "EH0012 - Laboratório de Prática Contábil - 2026.2", "fonte": "Exercício EH-0012 2026.2 (PDF revisado de 07/10/2026)",
        "empresa": EMPRESA, "socios": SOCIOS, "parametros_socios": PARAM_SOCIOS, "saldos_iniciais": SALDOS_INICIAIS,
        "imobilizado": IMOBILIZADO, "vida_util": [{"classe": c, "anos": a, "residual_pct": r} for c, a, r in VIDA_UTIL],
        "rateio_areas": [{"item": i, "adm": a, "com": c, "ind": n} for i, a, c, n in RATEIO_AREAS],
        "contratos": CONTRATOS, "folha_regras": FOLHA_REGRAS, "parametros_folha": PARAM_FOLHA,
        "funcionarios": [dict(zip(["setor", "nome", "admissao", "salario_jan", "he_jan", "comissao_jan", "dependentes_jan",
                                   "salario_fev", "he_fev", "comissao_fev", "dependentes_fev"], f)) for f in FUNCIONARIOS],
        "itens": [{"codigo": c, "descricao": d, "tipo": t, "ncm": n, "custo_base": cb,
                   "custo_min": (f[0] if f else None), "custo_max": (f[1] if f else None)} for c, d, t, n, cb, f in ITENS],
        "ficha_tecnica": FICHA_TECNICA, "plano_producao": PLANO_PRODUCAO, "parametros_producao": PARAM_PRODUCAO,
        "markup": MARKUP, "eventos": EVENTOS,
        "inconsistencias": [{"onde": x[0], "descricao": x[1], **({"status": x[2], "decisao": x[3]} if len(x) > 2 and x[3] else {"status": x[2]} if len(x) > 2 else {})}
                            for x in INCONSISTENCIAS],
    }
    saida = RAIZ / "dados" / "caso_base" / "eh0012_2026_2.json"
    saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return dados


if __name__ == "__main__":
    d = gerar()
    nv = sum(1 for e in EVENTOS if e["natureza"] == "V")
    print(f"{len(EVENTOS)} eventos ({nv} variáveis), {len(CONTRATOS)} contratos, {len(FUNCIONARIOS)} funcionários")

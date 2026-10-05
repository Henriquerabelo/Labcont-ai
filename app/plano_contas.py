"""Plano de contas do exercício EH0012.

Parte das contas do Balanço Patrimonial e da DRE de 31/12/2025 (com os mesmos códigos) e acrescenta,
no mesmo padrão, as contas exigidas pelos eventos de 2026. Contas novas não têm dígito verificador.
Natureza: D (devedora) ou C (credora). Saldo-base = saldo de 31/12/2025 do exercício original.
"""
from __future__ import annotations

# código: nome (contas sintéticas, só para agrupar o balancete)
SINTETICAS = {
    "1": "ATIVO",
    "1.01": "Ativo Circulante",
    "1.01.01": "Disponibilidades",
    "1.01.01.02": "Bancos",
    "1.01.01.02.01": "Contas Correntes",
    "1.01.01.03": "Aplicações de Liquidez Imediata",
    "1.01.03": "Aplicações Financeiras",
    "1.01.05": "Créditos",
    "1.01.05.01": "Créditos com Terceiros",
    "1.01.05.01.01": "Clientes",
    "1.01.05.01.05": "Impostos e Contribuições a Recuperar",
    "1.01.05.01.07": "Antecipações a Recuperar",
    "1.01.15": "Estoques",
    "1.01.15.01.01": "Estoque de Mercadorias",
    "1.01.15.01.02": "Estoque de Matérias-Primas e Materiais",
    "1.01.17": "Despesas Antecipadas do Exercício Vigente",
    "1.01.17.01.01": "Despesas Antecipadas",
    "1.07": "Ativo não Circulante",
    "1.07.04": "Imobilizado",
    "1.07.04.01": "Bens em Operação",
    "1.07.04.01.01": "Bens Utilizados na Produção e/ou Prestação de Serviços",
    "1.07.04.05": "Imobilizado em Andamento",
    "1.07.04.12": "(-) Depreciações, Amortizações e Quotas de Exaustão",
    "1.07.04.12.01": "(-) Depreciações Acumuladas",
    "2": "PASSIVO",
    "2.01": "Passivo Circulante",
    "2.01.01": "Obrigações de Curto Prazo",
    "2.01.01.01": "Fornecedores",
    "2.01.01.01.01": "Fornecedores de Mercadorias, Insumos e Bens",
    "2.01.01.01.02": "Fornecedores de Serviços",
    "2.01.01.03": "Obrigações Trabalhistas, Previdenciárias e Fiscais",
    "2.01.01.03.01": "Obrigações Trabalhistas e Previdenciárias",
    "2.01.01.03.03": "Obrigações Fiscais",
    "2.01.01.05": "Empréstimos e Financiamentos",
    "2.01.01.17": "Outras Contas",
    "2.01.01.17.01": "Outras Obrigações",
    "2.01.01.21": "Provisões",
    "2.01.01.21.02": "Provisões de Natureza Trabalhista",
    "2.03": "Passivo não Circulante",
    "2.03.01": "Empréstimos e Financiamentos de Longo Prazo",
    "2.07": "Patrimônio Líquido",
    "2.07.01": "Capital Realizado",
    "2.07.01.01": "Capital Social",
    "2.07.01.01.01": "Capital Social Subscrito",
    "2.07.01.01.03": "(-) Capital Social a Integralizar",
    "2.07.04": "Reservas de Lucros",
    "2.07.07": "Outras Contas",
    "2.07.07.01.01": "Lucros Acumulados",
    "3": "RESULTADO",
    "3.01": "Resultado Antes do IRPJ e da CSLL",
    "3.01.01.01": "Receita Líquida",
    "3.01.01.01.01": "Receita Bruta",
    "3.01.01.01.03": "(-) Deduções da Receita Bruta",
    "3.01.01.03": "Custo dos Bens e Serviços Vendidos",
    "3.01.01.07": "Despesas Operacionais",
    "3.01.01.07.01": "Despesas Administrativas",
    "3.01.01.07.02": "Despesas de Vendas",
    "3.01.01.07.03": "Despesas Tributárias",
    "3.01.01.09": "Resultado Financeiro",
    "3.01.01.09.01": "Receitas Financeiras",
    "3.01.01.09.02": "Despesas Financeiras",
    "3.02.01.01": "Provisão para CSLL e IRPJ",
}

# (código, nome, natureza, saldo-base 31/12/2025)
ANALITICAS: list[tuple[str, str, str, float]] = [
    # ----- Ativo circulante
    ("1.01.01.02.01.0001-8", "Banco Rico", "D", 359250.65),
    ("1.01.01.03.0001", "Aplicação INVEST LIQUID - Banco Rico", "D", 0),
    ("1.01.03.0001", "CDB Renda Mais - Banco Rico", "D", 0),
    ("1.01.05.01.01.0001", "Clientes - Mercado Interno", "D", 0),
    ("1.01.05.01.01.0002", "Comissões a Receber", "D", 0),
    ("1.01.05.01.05.0001", "ICMS a Recuperar", "D", 0),
    ("1.01.05.01.05.0002", "IPI a Recuperar", "D", 0),
    ("1.01.05.01.05.0003", "PIS a Recuperar", "D", 0),
    ("1.01.05.01.05.0004", "COFINS a Recuperar", "D", 0),
    ("1.01.05.01.05.0005", "IRRF a Recuperar", "D", 0),
    ("1.01.05.01.05.0006", "IRRF s/ Aplicações Financeiras a Recuperar", "D", 0),
    ("1.01.05.01.05.0013-0", "ICMS Antecipado a Recuperar", "D", 13258.52),
    ("1.01.05.01.07.0003-1", "Vale-Transporte", "D", 172.80),
    ("1.01.05.01.07.0004-0", "Vale-Alimentação", "D", 1773.00),
    ("1.01.15.01.01.0001-5", "Mercadorias para Revenda - ALPHA", "D", 8680.00),
    ("1.01.15.01.02.0001", "Matéria-Prima A (MP-A)", "D", 0),
    ("1.01.17.01.01.0001-1", "Prêmios de Seguros a Apropriar", "D", 5250.00),
    # ----- Imobilizado
    ("1.07.04.01.01.0001-8", "Terrenos", "D", 310000.00),
    ("1.07.04.01.01.0002-6", "Edifícios e Construções", "D", 125000.00),
    ("1.07.04.01.01.0003-4", "Equipamentos, Máquinas e Instalações Industriais", "D", 262000.00),
    ("1.07.04.01.01.0004-2", "Veículos", "D", 135000.00),
    ("1.07.04.01.01.0005", "Móveis, Utensílios e Aparelhos", "D", 0),
    ("1.07.04.01.01.0006", "Máquinas Industriais - Arrendamento Financeiro", "D", 0),
    ("1.07.04.05.0001", "Reforma do Galpão Industrial (em andamento)", "D", 0),
    ("1.07.04.12.01.0001-2", "(-) Dep. Acumulada - Imóveis", "C", 416.67),
    ("1.07.04.12.01.0002-0", "(-) Dep. Acumulada - Máquinas e Equips.", "C", 4366.67),
    ("1.07.04.12.01.0003", "(-) Dep. Acumulada - Móveis, Utensílios e Aparelhos", "C", 0),
    ("1.07.04.12.01.0004-7", "(-) Dep. Acumulada - Veículos", "C", 5625.00),
    # ----- Passivo circulante
    ("2.01.01.01.01.0001", "Comercial Elegante Ltda.", "C", 0),
    ("2.01.01.01.01.0002", "Indústria Sofisticada Ltda.", "C", 0),
    ("2.01.01.01.01.0003", "Ar Frio Ltda.", "C", 0),
    ("2.01.01.01.02.0003-0", "Seguro Verdade Ltda.", "C", 2100.00),
    ("2.01.01.01.02.0005-6", "Contador Formado S/S", "C", 5161.75),
    ("2.01.01.01.02.0006-7", "Internet & Comunicação Ltda.", "C", 410.00),
    ("2.01.01.01.02.0007-8", "Cell Telefonia Ltda.", "C", 580.00),
    ("2.01.01.01.02.0008", "Frete Confiança Ltda.", "C", 0),
    ("2.01.01.01.02.0009", "Recrutamento S/S (serviços a faturar)", "C", 0),
    ("2.01.01.01.02.0010", "Serviços de Autônomos a Pagar (RPA)", "C", 0),
    ("2.01.01.03.01.0001-5", "INSS a Recolher", "C", 12822.74),
    ("2.01.01.03.01.0002-3", "FGTS a Recolher", "C", 1552.64),
    ("2.01.01.03.01.0003", "INSS Retido de Terceiros a Recolher", "C", 0),
    ("2.01.01.03.01.0010-4", "Salários a Pagar", "C", 15760.64),
    ("2.01.01.03.03.0001-4", "ICMS a Recolher", "C", 43361.81),
    ("2.01.01.03.03.0002", "ICMS DIFAL a Recolher", "C", 0),
    ("2.01.01.03.03.0003-0", "ISS a Recolher", "C", 7615.00),
    ("2.01.01.03.03.0004-9", "PIS a Recolher", "C", 5045.29),
    ("2.01.01.03.03.0005-7", "COFINS a Recolher", "C", 23238.90),
    ("2.01.01.03.03.0006", "IPI a Recolher", "C", 0),
    ("2.01.01.03.03.0007", "ISS Retido a Recolher", "C", 0),
    ("2.01.01.03.03.0008-1", "IRRF a Recolher", "C", 348.93),
    ("2.01.01.03.03.0009-0", "CSRF a Recolher", "C", 255.75),
    ("2.01.01.03.03.0013-8", "ICMS Antecipado a Recolher", "C", 13258.52),
    ("2.01.01.03.03.0014-6", "IRPJ por Estimativa a Recolher", "C", 33198.47),
    ("2.01.01.03.03.0015-4", "CSLL por Estimativa a Recolher", "C", 12671.45),
    ("2.01.01.03.03.0016", "Auto de Infração ICMS a Pagar", "C", 0),
    ("2.01.01.05.0001", "Conta Garantida - Banco Rico", "C", 0),
    ("2.01.01.05.0002", "Arrendamento Financeiro a Pagar - Curto Prazo", "C", 0),
    ("2.01.01.17.01.0002-6", "Telefone a Pagar", "C", 350.00),
    ("2.01.01.17.01.0003-4", "Energia a Pagar", "C", 1480.00),
    ("2.01.01.17.01.0004-2", "Consumo Água a Pagar", "C", 420.00),
    ("2.01.01.17.01.0007-7", "Pró-labores a Pagar", "C", 13008.92),
    ("2.01.01.17.01.0008", "Dividendos a Pagar", "C", 0),
    ("2.01.01.17.01.0009", "Participações de Empregados e Administradores a Pagar", "C", 0),
    ("2.01.01.21.02.0002-6", "Provisão de Férias", "C", 1700.89),
    ("2.01.01.21.02.0003", "Provisão de 13º Salário", "C", 0),
    ("2.01.01.21.02.0004-2", "FGTS sobre 13º Salário", "C", 102.05),
    ("2.01.01.21.02.0005-0", "INSS sobre Férias", "C", 472.85),
    ("2.01.01.21.02.0006-9", "FGTS sobre Férias", "C", 136.07),
    ("2.01.01.21.02.0007", "INSS sobre 13º Salário", "C", 0),
    ("2.03.01.0001", "Arrendamento Financeiro a Pagar - Longo Prazo", "C", 0),
    # ----- Patrimônio líquido
    ("2.07.01.01.01.0001-8", "Capital - Adalberto Cantareira", "C", 385000.00),
    ("2.07.01.01.01.0002-6", "Capital - Marconde Sobreira", "C", 166000.00),
    ("2.07.01.01.01.0003-4", "Capital - Marcela Soares", "C", 460000.00),
    ("2.07.01.01.01.0004-2", "Capital - Cassilda Apedeuta", "C", 85000.00),
    ("2.07.01.01.03.0001-7", "(-) A integralizar - Adalberto Cantareira", "D", 35000.00),
    ("2.07.01.01.03.0002-5", "(-) A integralizar - Marconde Sobreira", "D", 31000.00),
    ("2.07.01.01.03.0003-3", "(-) A integralizar - Marcela Soares", "D", 25000.00),
    ("2.07.01.01.03.0004-1", "(-) A integralizar - Cassilda Apedeuta", "D", 85000.00),
    ("2.07.04.0001", "Reserva Legal", "C", 0),
    ("2.07.04.0002", "Reserva Estatutária", "C", 0),
    ("2.07.07.01.01.0001-7", "Lucros Acumulados", "C", 94923.97),
    # ----- Resultado
    ("3.01.01.01.01.0005-7", "Receita da Revenda de Mercadorias - Mercado Interno", "C", 0),
    ("3.01.01.01.01.0006-5", "Receita da Prestação de Serviços - Mercado Interno", "C", 0),
    ("3.01.01.01.03.0002-1", "(-) ICMS sobre Vendas", "D", 0),
    ("3.01.01.01.03.0003-0", "(-) COFINS", "D", 0),
    ("3.01.01.01.03.0004-8", "(-) PIS/PASEP", "D", 0),
    ("3.01.01.01.03.0005-6", "(-) ISS", "D", 0),
    ("3.01.01.03.03.0001-9", "Custo das Mercadorias Revendidas", "D", 0),
    ("3.01.01.07.01.0003-7", "Ordenados, Salários e Horas Extras - Adm.", "D", 0),
    ("3.01.01.07.01.0009-6", "Serviços Prestados por Pessoa Jurídica", "D", 0),
    ("3.01.01.07.01.0012-6", "INSS - Previdência Social - Adm.", "D", 0),
    ("3.01.01.07.01.0013-4", "FGTS - Adm.", "D", 0),
    ("3.01.01.07.01.0030-4", "Depreciação - Adm.", "D", 0),
    ("3.01.01.07.01.0043-6", "Férias - Adm.", "D", 0),
    ("3.01.01.07.01.0044-4", "13º Salário - Adm.", "D", 0),
    ("3.01.01.07.01.0048-7", "Energia Elétrica - Adm.", "D", 0),
    ("3.01.01.07.01.0049-5", "Água e Esgoto - Adm.", "D", 0),
    ("3.01.01.07.01.0050-9", "Telefones e Internet - Adm.", "D", 0),
    ("3.01.01.07.01.0055-0", "Pró-labores - Adm.", "D", 0),
    ("3.01.01.07.01.0056-8", "Seguros", "D", 0),
    ("3.01.01.07.01.0068-1", "Assessoria Contábil", "D", 0),
    ("3.01.01.07.01.0070", "Vale-Transporte - Adm.", "D", 0),
    ("3.01.01.07.01.0071", "Vale-Alimentação - Adm.", "D", 0),
    ("3.01.01.07.02.0009-0", "Ordenados, Salários e Horas Extras - Vendas", "D", 0),
    ("3.01.01.07.02.0010-4", "INSS - Previdência Social - Vendas", "D", 0),
    ("3.01.01.07.02.0011-2", "FGTS - Vendas", "D", 0),
    ("3.01.01.07.02.0012-0", "13º Salário - Vendas", "D", 0),
    ("3.01.01.07.02.0013-9", "Férias - Vendas", "D", 0),
    ("3.01.01.07.02.0014-7", "Pró-labores - Vendas", "D", 0),
    ("3.01.01.07.02.0015", "Comissões sobre Vendas", "D", 0),
    ("3.01.01.07.02.0016", "Vale-Transporte - Vendas", "D", 0),
    ("3.01.01.07.02.0017", "Vale-Alimentação - Vendas", "D", 0),
    ("3.01.01.07.02.0018", "Energia Elétrica - Vendas", "D", 0),
    ("3.01.01.07.02.0019", "Telefones e Internet - Vendas", "D", 0),
    ("3.01.01.07.02.0020", "Depreciação - Vendas", "D", 0),
    ("3.01.01.07.03.0001", "ICMS - Auto de Infração", "D", 0),
    ("3.01.01.07.03.0002", "Multas Fiscais (indedutíveis)", "D", 0),
    ("3.01.01.09.01.0001", "Rendimentos de Aplicações Financeiras", "C", 0),
    ("3.01.01.09.02.0001", "Juros - Conta Garantida", "D", 0),
    ("3.01.01.09.02.0002", "Juros - Arrendamento Financeiro", "D", 0),
    ("3.02.01.01.01.0001-0", "Contribuição Social sobre o Lucro Líquido", "D", 0),
    ("3.02.01.01.01.0002-9", "Imposto de Renda - Pessoa Jurídica", "D", 0),
]

CONTAS = {c: {"codigo": c, "nome": n, "natureza": nat, "base": b} for c, n, nat, b in ANALITICAS}

# atalhos usados pelo gabarito
BANCO = "1.01.01.02.01.0001-8"
INVEST = "1.01.01.03.0001"
CDB = "1.01.03.0001"
CLIENTES = "1.01.05.01.01.0001"
COMISSOES_REC = "1.01.05.01.01.0002"
ICMS_REC, IPI_REC, PIS_REC, COFINS_REC = "1.01.05.01.05.0001", "1.01.05.01.05.0002", "1.01.05.01.05.0003", "1.01.05.01.05.0004"
IRRF_REC, IRRF_APLIC = "1.01.05.01.05.0005", "1.01.05.01.05.0006"
ICMS_ANT_REC = "1.01.05.01.05.0013-0"
VT, VA = "1.01.05.01.07.0003-1", "1.01.05.01.07.0004-0"
ALPHA, MPA = "1.01.15.01.01.0001-5", "1.01.15.01.02.0001"
SEGUROS_APROP = "1.01.17.01.01.0001-1"
GALPAO, MAQUINAS, VEICULOS, MOVEIS, MAQ_LEASING, OBRAS = (
    "1.07.04.01.01.0002-6", "1.07.04.01.01.0003-4", "1.07.04.01.01.0004-2", "1.07.04.01.01.0005",
    "1.07.04.01.01.0006", "1.07.04.05.0001")
DEP_IMOVEIS, DEP_MAQ, DEP_MOVEIS, DEP_VEIC = (
    "1.07.04.12.01.0001-2", "1.07.04.12.01.0002-0", "1.07.04.12.01.0003", "1.07.04.12.01.0004-7")
F_ELEGANTE, F_SOFISTICADA, F_ARFRIO = "2.01.01.01.01.0001", "2.01.01.01.01.0002", "2.01.01.01.01.0003"
F_SEGURO, F_CONTADOR, F_INTERNET, F_CELL = (
    "2.01.01.01.02.0003-0", "2.01.01.01.02.0005-6", "2.01.01.01.02.0006-7", "2.01.01.01.02.0007-8")
F_FRETE, F_RECRUT, F_RPA = "2.01.01.01.02.0008", "2.01.01.01.02.0009", "2.01.01.01.02.0010"
INSS_REC, FGTS_REC, INSS_RET, SAL_PAGAR = (
    "2.01.01.03.01.0001-5", "2.01.01.03.01.0002-3", "2.01.01.03.01.0003", "2.01.01.03.01.0010-4")
ICMS_RECOL, DIFAL, ISS_RECOL, PIS_RECOL, COFINS_RECOL, IPI_RECOL, ISS_RET = (
    "2.01.01.03.03.0001-4", "2.01.01.03.03.0002", "2.01.01.03.03.0003-0", "2.01.01.03.03.0004-9",
    "2.01.01.03.03.0005-7", "2.01.01.03.03.0006", "2.01.01.03.03.0007")
IRRF_RECOL, CSRF_RECOL, ICMS_ANT_RECOL, IRPJ_RECOL, CSLL_RECOL, AUTO = (
    "2.01.01.03.03.0008-1", "2.01.01.03.03.0009-0", "2.01.01.03.03.0013-8", "2.01.01.03.03.0014-6",
    "2.01.01.03.03.0015-4", "2.01.01.03.03.0016")
GARANTIDA, LEASING_CP, LEASING_LP = "2.01.01.05.0001", "2.01.01.05.0002", "2.03.01.0001"
TEL_PAGAR, ENERGIA_PAGAR, AGUA_PAGAR, PROLAB_PAGAR, DIVIDENDOS, PARTICIPACOES = (
    "2.01.01.17.01.0002-6", "2.01.01.17.01.0003-4", "2.01.01.17.01.0004-2", "2.01.01.17.01.0007-7",
    "2.01.01.17.01.0008", "2.01.01.17.01.0009")
PROV_FERIAS, PROV_13, FGTS_13, INSS_FERIAS, FGTS_FERIAS, INSS_13 = (
    "2.01.01.21.02.0002-6", "2.01.01.21.02.0003", "2.01.01.21.02.0004-2", "2.01.01.21.02.0005-0",
    "2.01.01.21.02.0006-9", "2.01.01.21.02.0007")
RESERVA_LEGAL, RESERVA_ESTAT, LUCROS_ACUM = "2.07.04.0001", "2.07.04.0002", "2.07.07.01.01.0001-7"
REC_REVENDA, REC_SERVICOS = "3.01.01.01.01.0005-7", "3.01.01.01.01.0006-5"
DED_ICMS, DED_COFINS, DED_PIS, DED_ISS = (
    "3.01.01.01.03.0002-1", "3.01.01.01.03.0003-0", "3.01.01.01.03.0004-8", "3.01.01.01.03.0005-6")
CMV = "3.01.01.03.03.0001-9"
SERV_PJ, SEGUROS, ASSESSORIA = "3.01.01.07.01.0009-6", "3.01.01.07.01.0056-8", "3.01.01.07.01.0068-1"
AGUA = "3.01.01.07.01.0049-5"
DESP_ICMS_AUTO, MULTAS = "3.01.01.07.03.0001", "3.01.01.07.03.0002"
REND_APLIC, JUROS_GARANTIDA, JUROS_LEASING = "3.01.01.09.01.0001", "3.01.01.09.02.0001", "3.01.01.09.02.0002"
CSLL_DESP, IRPJ_DESP = "3.02.01.01.01.0001-0", "3.02.01.01.01.0002-9"

# despesas por área: chave -> (adm, vendas)
POR_AREA = {
    "salarios": ("3.01.01.07.01.0003-7", "3.01.01.07.02.0009-0"),
    "inss": ("3.01.01.07.01.0012-6", "3.01.01.07.02.0010-4"),
    "fgts": ("3.01.01.07.01.0013-4", "3.01.01.07.02.0011-2"),
    "ferias": ("3.01.01.07.01.0043-6", "3.01.01.07.02.0013-9"),
    "decimo": ("3.01.01.07.01.0044-4", "3.01.01.07.02.0012-0"),
    "prolabore": ("3.01.01.07.01.0055-0", "3.01.01.07.02.0014-7"),
    "vt": ("3.01.01.07.01.0070", "3.01.01.07.02.0016"),
    "va": ("3.01.01.07.01.0071", "3.01.01.07.02.0017"),
    "energia": ("3.01.01.07.01.0048-7", "3.01.01.07.02.0018"),
    "telefone": ("3.01.01.07.01.0050-9", "3.01.01.07.02.0019"),
    "depreciacao": ("3.01.01.07.01.0030-4", "3.01.01.07.02.0020"),
}
COMISSOES = "3.01.01.07.02.0015"
CAPITAL = {  # sócio -> (capital subscrito, a integralizar)
    "Adalberto Cantareira": ("2.07.01.01.01.0001-8", "2.07.01.01.03.0001-7"),
    "Marconde Sobreira": ("2.07.01.01.01.0002-6", "2.07.01.01.03.0002-5"),
    "Marcela Soares": ("2.07.01.01.01.0003-4", "2.07.01.01.03.0003-3"),
    "Cassilda Apedeuta": ("2.07.01.01.01.0004-2", "2.07.01.01.03.0004-1"),
}


def sinteticas_de(codigo: str) -> list[str]:
    """Contas sintéticas (agrupadoras) de uma conta analítica, da mais geral para a mais específica."""
    base = codigo.split("-")[0]
    partes = base.split(".")
    out = []
    for i in range(1, len(partes)):
        c = ".".join(partes[:i])
        if c in SINTETICAS:
            out.append(c)
    return out

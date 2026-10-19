# Parametrização do caso EH0012 (2026.2)

> Documento gerado a partir de `dados/caso_base/eh0012_2026_2.json` (rode `python dados/caso_base/gerar_caso_base.py` e depois `gerar_doc.py`). As faixas são **propostas** para validação pelos professores da disciplina.

## Como ler

- **Base:** valor do caso original (empresa LAB).
- **Faixa:** intervalo em que o valor de cada dupla será sorteado, com o passo de arredondamento.
- **Derivado:** valor calculado pelo sistema a partir de outros parâmetros (saldos, contratos, folha, produção). Não é sorteado, mas muda junto com eles.
- **Datas:** permanecem fixas em todas as duplas, para preservar o calendário de vencimentos e apurações.

## Resumo

| Elemento | Itens | Parâmetros variáveis |
|---|---|---|
| Contratos | 12 | 21 |
| Funcionários (folha) | 15 empregados + 3 sócios com pró-labore | salário, HE, comissão, dependentes, pró-labore |
| Produção | 2 produtos, 7 insumos, 1 mercadoria | quantidades, coeficientes, custos, margem |
| Eventos | 90 (28 com valores variáveis, 62 derivados) | ver seção 4 |

## 1. Contratos

### C01 · Financeiro - Conta garantida
**Parte:** Banco Rico S/A · **Início:** 2025-09-15  
Limite rotativo para cobrir saldo negativo; juros compostos com capitalização diária a partir do dia seguinte ao uso; amortização imediata quando houver saldo em conta ou aplicação.

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Limite | 970.000,00  | R$ 800.000,00 a R$ 1.200.000,00 (passo 10.000,00) |
| Taxa de juros | 3,50 % a.m. | 3,00 a 4,00 % a.m. (passo 0,10) |

Eventos ligados: uso automático sempre que o caixa ficar negativo

### C02 · Financeiro - Aplicação de liquidez imediata (INVEST LIQUID)
**Parte:** Banco Rico S/A · **Início:** 2025-09-20  
Rendimento prefixado com capitalização diária; resgate automático quando a conta corrente precisar; aplicação só por solicitação.

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Taxa de rendimento | 1,60 % a.m. | 1,20 a 2,00 % a.m. (passo 0,10) |

Eventos ligados: J04, F47

### C03 · Financeiro - CDB Renda Mais
**Parte:** Banco Rico S/A · **Início:** 2026-01-12  
Título de renda fixa com vencimento em 12 meses (IR regressivo no resgate).

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Valor aplicado | 9.000,00  | R$ 6.000,00 a R$ 12.000,00 (passo 500,00) |
| Taxa | 1,60 % a.m. | 1,20 a 2,00 % a.m. (passo 0,10) |

Eventos ligados: J14, F07

### C04 · Financeiro - Leasing financeiro (SAC)
**Parte:** Banco Rico S/A · **Início:** 2026-01-19  
Arrendamento de 2 máquinas do parque industrial, com opção de compra (CPC 06 R2). Juros compostos, ano civil.

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Valor das máquinas | 300.000,00  | R$ 250.000,00 a R$ 400.000,00 (passo 5.000,00) |
| Taxa de juros | 10,00 % a.a. | 8,00 a 14,00 % a.a. (passo 0,50) |
| Prazo | 18 meses | 12 a 24 meses (passo 6) — valores admitidos: 12, 18 ou 24 |

Eventos ligados: J24, F33

### C05 · Serviço - Recrutamento e seleção
**Parte:** Recrutamento S/S · **Início:** 2026-01-04  
Vigência jan-fev/2026; apropriação de 50% por mês; pagamento único em 26/02/2026, na emissão da NFS-e 345 (com retenção de IRRF).

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Honorários brutos | 8.800,00  | R$ 6.000,00 a R$ 12.000,00 (passo 100,00) |

Eventos ligados: F41

### C06 · Serviço - Assessoria contábil
**Parte:** Contador Formado S/A (Fortaleza) · **Início:** 2025-09-01  
Honorários mensais pagos no dia 10 do mês seguinte, com retenções (IRRF 1,5% + CSRF 4,65%). Reajuste a partir de 01/02/2026.

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Honorário mensal | 5.500,00  | R$ 4.500,00 a R$ 7.000,00 (passo 100,00) |
| Reajuste a partir de fevereiro | 25,45 % | 10,00 a 30,00 % (passo 0,50) — novo valor arredondado a R$ 100 |

Eventos ligados: J11, J39, F17, F45

### C07 · Comodato - Internet (cable modem)
**Parte:** Internet & Comunicação Ltda. · **Início:** 2025-10-10  
Mensalidade paga no dia 10 do mês seguinte.

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Mensalidade | 410,00  | R$ 300,00 a R$ 550,00 (passo 10,00) |

Eventos ligados: J05, J13, F03, F18

### C08 · Comodato - 5 aparelhos celulares
**Parte:** Cell Telefonia Ltda. · **Início:** 2025-10-09  
Mensalidade paga no dia 9 do mês seguinte.

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Mensalidade | 580,00  | R$ 400,00 a R$ 750,00 (passo 10,00) |
| Quantidade de aparelhos | 5 un | 3 a 8 un (passo 1) |

Eventos ligados: J05, J10, F03, F14

### C09 · Seguro contra incêndio
**Parte:** Seguro Verdade Ltda. · **Início:** 2025-10-16  
Cobertura de 12 meses a partir de 16/10/2025; prêmio em 3 parcelas (16/11/2025, 16/12/2025 e 17/01/2026); apropriação mensal pro rata.

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Prêmio total | 6.300,00  | R$ 4.800,00 a R$ 8.400,00 (passo 100,00) |
| Número de parcelas | 3 un | — |

Eventos ligados: J21

### C10 · Mútuo cedido a sócia (parte relacionada)
**Parte:** Cassilda Apedeuta · **Início:** 2026-02-18  
Empréstimo da empresa à sócia; juros compostos apropriados por fração diária; sem vencimento; juros compensados com dividendos.

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Valor do mútuo | 30.000,00  | R$ 20.000,00 a R$ 45.000,00 (passo 1.000,00) |
| Taxa de juros | 4,00 % a.m. | 2,00 a 5,00 % a.m. (passo 0,50) |

Eventos ligados: F27

### C11 · Serviço - Projeto de arquitetura (autônomo, RPA)
**Parte:** Arquiteto autônomo (contribuinte de Fortaleza) · **Início:** 2026-01-20  
Pagamento em 17/02/2026; retenções de INSS, IRRF e ISS do autônomo; encargo patronal de 20%.

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Valor bruto | 10.600,00  | R$ 8.000,00 a R$ 14.000,00 (passo 100,00) |

Eventos ligados: J23, F30

### C12 · Serviço - Reforma do galpão industrial
**Parte:** Construtor Express Ltda. · **Início:** 2026-01-22  
Contrato em 2 parcelas de 50% (22/01 e 22/02); parte material e parte mão de obra (base de ISS/retenções).

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Valor total | 228.000,00  | R$ 180.000,00 a R$ 300.000,00 (passo 1.000,00) |
| Parcela de material | 40,00 % | 30,00 a 50,00 % (passo 5,00) |

Eventos ligados: J26, F32

## 2. Folha de pagamento e funcionários

**Regras fixas do caso:**

- **processamento:** jan: 2026-01-15; fev: 2026-02-13
- **pagamento:** dia 05 do mês subsequente
- **admissoes:** somente no 1º dia do mês
- **vale transporte:** tarifa: 5.4; por_dia: 2; desconto: 6% do salário-base (limitado ao benefício recebido)
- **vale alimentacao:** valor_dia: 26.0; por_dia: 1; desconto: 5% do benefício
- **dias uteis:** fev/2026: 18; mar/2026: 20
- **encargos:** INSS patronal + RAT + Terceiros 28,80% (FPAS 507, RAT 3%); FGTS 8,00% (sobre folha, férias e 13º)
- **provisoes:** Férias + 1/3 e 13º salário (1/12 por mês), com encargos
- **tabelas:** INSS, IRRF e salário-família vigentes em 2026

**Quadro de pessoal:** janeiro 5 empregados (3 Adm, 2 Com); fevereiro 15 (3 Adm, 3 Com, 7 MOD - 4 em X e 3 em Y, 2 MOI). Admissões em 01/02.

| Setor | Empregado | Admissão | Salário jan | Salário fev | HE fev | Comissão fev | Dependentes fev |
|---|---|---|---|---|---|---|---|
| Administração | Alves Africano | anterior | 5.920,00 | 5.920,00 | 458,00 | — | 2 (20 e 16 anos) |
| Administração | Venâncio Australiano | anterior | 1.621,00 | 1.621,00 | — | — | 1 (9 anos) |
| Administração | Tiago Espanhol | anterior | 4.100,00 | 4.100,00 | 373,00 | — | 1 (7 anos) |
| Comercial | Ângela Peruana | anterior | 2.100,00 | 1.621,00 | — | 77,00 | 2 (10 e 14 anos) |
| Comercial | Marena Russa | anterior | 2.500,00 | 5.700,00 | 389,00 | 285,00 | 1 (9 anos) |
| Comercial | Vitor Canadense | 2026-02-01 | — | 4.000,00 | 273,00 | — | 1 (16 anos) |
| Industrial - MOD Produto X | Eurico Canadense | 2026-02-01 | — | 3.600,00 | 246,00 | — | 1 (3 anos) |
| Industrial - MOD Produto X | Pedro Algarve | 2026-02-01 | — | 6.200,00 | — | — | 2 (12 e 9 anos) |
| Industrial - MOD Produto X | Regina Italiana | 2026-02-01 | — | 1.680,00 | 115,00 | — | 2 (7 e 8 anos) |
| Industrial - MOD Produto X | Renato Português | 2026-02-01 | — | 2.120,00 | — | — | 2 (8 e 10 anos) |
| Industrial - MOD Produto Y | Gustavo Equatoriano | 2026-02-01 | — | 5.450,00 | 372,00 | — | 1 (5 anos) |
| Industrial - MOD Produto Y | Rubens Irlandês | 2026-02-01 | — | 1.720,00 | — | — | 1 (3 anos) |
| Industrial - MOD Produto Y | Vitor Veneza | 2026-02-01 | — | 2.500,00 | 171,00 | — | 0 |
| Industrial - MOI | Breno Alemão | 2026-02-01 | — | 5.300,00 | 362,00 | — | 0 |
| Industrial - MOI | Cleide Ucraniana | 2026-02-01 | — | 1.830,00 | — | — | 3 (5, 8 e 14 anos) |

**Sócios (pró-labore):**

| Sócio | Função | Cotas | A integralizar | Pró-labore jan | Pró-labore fev |
|---|---|---|---|---|---|
| Adalberto Cantareira | Sócio administrador/financeiro | 385.000 | 35.000,00 | 9.600,00 | 9.600,00 |
| Marconde Sobreira | Sócio industrial | 166.000 | 31.000,00 | 0,00 | 8.600,00 |
| Marcela Soares | Sócia comercial | 460.000 | 25.000,00 | 7.700,00 | 7.700,00 |
| Cassilda Apedeuta | Sócia investidora | 85.000 | 85.000,00 | 0,00 | 0,00 |

| Parâmetro | Base | Faixa proposta |
|---|---|---|
| Salário-base de cada empregado | conforme tabela | -20,00 a 20,00 % sobre a base (passo 10,00) — arredondar a R$ 10; nunca abaixo do salário mínimo vigente; manter a hierarquia entre cargos |
| Horas extras (valor) | conforme tabela | 0,00 a 10,00 % do salário (passo 1,00) — pelo menos 1/3 dos empregados com HE |
| Comissões (área comercial) | conforme tabela | 0,00 a 15,00 % do salário (passo 1,00) |
| Número de dependentes (filhos) | conforme tabela | 0 a 3 un (passo 1) — idades coerentes entre jan e fev |
| Dias úteis para VT/VA | 18 | fixo pelo calendário (fev/2026 = 18; mar/2026 = 20) |
| Participação de cada sócio no capital | 35,13% / 15,15% / 41,97% / 7,76% | 5,00 a 50,00 % (passo 0,01) — soma = 100%; cotas inteiras |
| Percentual a integralizar por sócio | 9,09% / 18,67% / 5,43% / 100% | 0,00 a 100,00 % (passo 1.000,00) — valor a integralizar arredondado a R$ 1.000; ao menos 1 sócio com 100% a integralizar |
| Pró-labore sócio administrador | 9.600,00 | R$ 7.000,00 a R$ 12.000,00 (passo 100,00) |
| Pró-labore sócio comercial | 7.700,00 | R$ 6.000,00 a R$ 10.000,00 (passo 100,00) |
| Pró-labore sócio industrial (a partir de fevereiro) | 8.600,00 | R$ 6.000,00 a R$ 11.000,00 (passo 100,00) |

## 3. Produção, ficha técnica e mercadoria

| Código | Item | Tipo | NCM | Custo unitário base | Faixa |
|---|---|---|---|---|---|
| MP-A | Matéria-prima A | Matéria-prima | 9002.11.11 | 9,0867 | R$ 7,70 a R$ 10,50 |
| MP-B | Matéria-prima B | Matéria-prima | 9007.20.20 | 11,2986 | R$ 9,60 a R$ 13,00 |
| MS-Z | Material secundário Z | Material secundário | 9002.20.10 | 10,0600 | R$ 8,50 a R$ 11,60 |
| MS-Q | Material secundário Q | Material secundário | 9008.50.00 | 11,5536 | R$ 9,80 a R$ 13,30 |
| MS-R | Material secundário R | Material secundário | 9013.20.00 | 12,5751 | R$ 10,70 a R$ 14,50 |
| MS-K | Material secundário K | Material secundário | 9011.20.20 | 13,2894 | R$ 11,30 a R$ 15,30 |
| ME-H | Material de embalagem H | Embalagem | 3923.21.10 | 5,6589 | R$ 4,80 a R$ 6,50 |
| X | Produto X | Produto acabado | 9006.53.20 | — | apurado pelo custeio |
| Y | Produto Y | Produto acabado | 9007.10.00 | — | apurado pelo custeio |
| ALPHA | Mercadoria para revenda ALPHA | Mercadoria | 9032.10.10 | 19,6703 | R$ 17,50 a R$ 22,00 |

**Ficha técnica (unidades de insumo por unidade de produto):**

| Produto | MP-A | MP-B | MS-Z | MS-Q | MS-R | MS-K | ME-H |
|---|---|---|---|---|---|---|---|
| X | 4 | 2 | 5 | 1 | — | 3 | 1 |
| Y | 3 | 5 | 2 | — | 2 | 4 | 1 |

**Plano de produção (2026-02):** X = 19.300 un; Y = 18.700 un. Início: dia útil seguinte à compra do ME-H (19/02/2026); duração: 3 dias úteis (término 23/02/2026).

**Coerência verificada no caso original:** cada compra cobre a necessidade da ficha técnica com uma sobra de 140 a 280 unidades (MP-A: necessidade 133.300; compra 133.900 − devolução 320 = 133.580). As vendas de X (19.190) e Y (18.520) correspondem a 99,4% e 99,0% da produção. A mercadoria ALPHA fecha fevereiro com 125 unidades (620 + 18.075 − 8.200 − 40 − 10.400 + 70).

**Mark-up:** ICMS 20.0% + PIS 1.65% + COFINS 7.6% + margem de contribuição 45.0% → divisor 0.2575 (multiplicador 3.8835). Margem variável: 40,00 a 50,00 % (passo 1,00).

| Parâmetro de produção | Base | Faixa proposta |
|---|---|---|
| Quantidade produzida - Produto X | 19.300 | 15.000 a 25.000 un (passo 100) |
| Quantidade produzida - Produto Y | 18.700 | 15.000 a 25.000 un (passo 100) |
| Coeficientes da ficha técnica | conforme ficha | -1 a 1 un/produto (passo 1) — variação de ±1 unidade por insumo, mínimo 1; ME-H sempre 1 por produto |
| Sobra de compra sobre a necessidade | 140 a 280 un | 100 a 300 un (passo 10) — quantidade comprada = necessidade da ficha técnica + sobra (MP-A: + devolução) |
| Custo unitário de compra de cada insumo | ver itens | -15,00 a 15,00 % (passo 0,0001) |
| Percentual vendido da produção | 99,4% (X) / 99,0% (Y) | 98,50 a 99,80 % (passo 0,10) — quantidade vendida inteira, menor que a produzida |

## 4. Eventos

Natureza: **V** = possui valores sorteados por dupla; **D** = derivado (calculado pelo sistema); P01/P02 são eventos de produção implícitos nas regras do caso.

### Janeiro/2026

| ID | Data | Grupo | Evento | Nat. | Parâmetros variáveis (base → faixa) |
|---|---|---|---|---|---|
| J01 | 02/01 | Societário | Destinação do resultado do exercício de 2025 (participações, reserva legal, dividendos, reserva estatutária) | D | — |
| J02 | 02/01 | Utilidades | NF Energia Luz do Sertão n.º 987321 - consumo jan; vencimento 14/01 | V | Valor total: 2.520,00 → R$ 2.200,00 a R$ 2.900,00 (passo 10,00); Parcela da área administrativa: 46,40 → 40,00 a 55,00 % (passo 0,10); Tarifa: 1,4316 → fixa; consumo (kWh) = valor ÷ tarifa |
| J03 | 05/01 | Utilidades | Fatura de água Águas do Litoral n.º 321654 - consumo jan; vencimento 14/01 | V | Valor total: 590,00 → R$ 500,00 a R$ 700,00 (passo 10,00); Tarifa: 23,62 → fixa; m³ = valor ÷ tarifa · *Rateio da fatura: área administrativa R$ 210,00 e comercial R$ 380,00.* |
| J04 | 05/01 | Financeiro | Aplicação no INVEST LIQUID (Banco Rico) | V | Valor aplicado: 18.000,00 → R$ 15.000,00 a R$ 25.000,00 (passo 500,00) |
| J05 | 06/01 | Utilidades | NFs de telefonia fixa, celular e internet - competência jan | V | Telefone fixo: 687,00 → R$ 600,00 a R$ 800,00 (passo 1,00) · *Celular e internet seguem os contratos C08 e C07.* |
| J06 | 06/01 | Pagamento | Pagamento da folha e do pró-labore de 12/2025 | D | — |
| J07 | 07/01 | Pagamento | Pagamento do FGTS e FGTS sobre 13º de 12/2025 | D | — |
| J08 | 08/01 | Compra - imobilizado | NF 7.852 Ar Frio Ltda. (MA, CFOP 6.102) - ar-condicionados para a administração; 20% à vista e 2 parcelas (07/02 e 07/03) | V | Quantidade: 5 → 3 a 8 un (passo 1); Valor unitário: 4.400,00 → R$ 3.800,00 a R$ 5.200,00 (passo 50,00); Entrada à vista: 20,00 → 10,00 a 30,00 % (passo 5,00) · *Gera DIFAL e crédito/estorno conforme destinação (uso administrativo).* |
| J09 | 08/01 | Compra - frete | CT-e 322.123 Rodovia Transportes - frete da NF 7.852, à vista | V | Valor do frete: 1.050,00 → R$ 800,00 a R$ 1.300,00 (passo 10,00) |
| J10 | 09/01 | Pagamento | Pagamento Cell Telefonia - competência 12/2025 | D | ver contrato C08 |
| J11 | 09/01 | Pagamento | Pagamento Contador Formado - dezembro/2025 | D | ver contrato C06 |
| J12 | 09/01 | Tributos | Pagamento do ISS de 12/2025 | D | — |
| J13 | 09/01 | Pagamento | Pagamento Internet & Comunicação - 12/2025 | D | ver contrato C07 |
| J14 | 12/01 | Financeiro | Aplicação no CDB Renda Mais (12 meses) | V | ver contrato C03 |
| J15 | 12/01 | Compra - mercadoria | NF 3.369 Comercial Elegante (PB, CFOP 6.102) - mercadoria ALPHA, desconto incondicional, 20% à vista e saldo em 14/02; CT-e 423.765 frete FOB (venc. 18/01) | V | Quantidade: 18.075 → 15.000 a 21.000 un (passo 25); Custo unitário: 19,6703 → R$ 17,50 a R$ 22,00 (passo 0,0001); Desconto incondicional: 5,00 → 3,00 a 7,00 % (passo 0,50); Frete: 1.720,00 → R$ 1.400,00 a R$ 2.100,00 (passo 10,00) |
| J16 | 13/01 | Receita - serviço | NFS-e 002 para Algodão Doce - comissão de representação (Beta); recebimento 20/01 | V | Valor da comissão: 98.000,00 → R$ 80.000,00 a R$ 115.000,00 (passo 500,00) |
| J17 | 14/01 | Pagamento | Pagamento de água, energia e telefone - competência 01/2026 | D | — |
| J18 | 15/01 | Folha | Processamento da folha e pró-labore de janeiro + provisões | D | — |
| J19 | 15/01 | Depreciação | Depreciação de janeiro | D | — |
| J20 | 16/01 | Societário | Integralização de capital - Marcela Soares | D | — |
| J21 | 19/01 | Pagamento | Pagamento da 3ª e última parcela do seguro (Seguro Verdade) | D | ver contrato C09 |
| J22 | 19/01 | Pagamento | Pagamento do CT-e 423.765 | D | — |
| J24 | 19/01 | Financeiro | Liberação do leasing para aquisição de 2 máquinas industriais | V | ver contrato C04 |
| J23 | 20/01 | Serviço tomado | Contratação de arquiteto autônomo (RPA) - pagamento em 17/02 | V | ver contrato C11 |
| J25 | 21/01 | Recebimento | Recebimento da comissão (NFS-e 002) | D | — |
| J26 | 22/01 | Serviço tomado | NFS-e 6.300 Construtor Express - 1ª parcela (50%) da reforma do galpão | V | ver contrato C12 |
| J27 | 23/01 | Venda - mercadoria | NF 001 Comercial Caribe (CE, CFOP 5.102) - venda de ALPHA, preço pelo mark-up, boleto em 28/01 | V | Quantidade vendida: 8.200 → 7.000 a 9.500 un (passo 50) |
| J28 | 23/01 | Tributos | Pagamento da GPS (INSS) de 12/2025 | D | — |
| J29 | 26/01 | Tributos - infração | Auto de infração SEFAZ-CE (mercadorias sem nota) - pagamento em 05/02 com redução de multa | V | Base de cálculo: 70.000,00 → R$ 50.000,00 a R$ 90.000,00 (passo 1.000,00); Alíquota aplicada: 18,00 → ICMS = base × alíquota; multa = 75% do ICMS (conforme o caso) |
| J30 | 26/01 | Compra - insumo | NF 23.456 Indústria Sofisticada (MG, CFOP 6.101) - MP-A; 25% à vista, 30% em 26/02 e 45% em 24/03; CT-e 423.951 frete CIF | V | Quantidade: 133.900 → derivada: necessidade de MP-A + sobra + devolução (F28); Custo unitário: 9,0867 → R$ 7,70 a R$ 10,50 (passo 0,0001); Frete: 2.050,00 → R$ 1.700,00 a R$ 2.400,00 (passo 10,00) |
| J31 | 27/01 | Tributos | Pagamento de PIS e COFINS de 12/2025 | D | — |
| J32 | 27/01 | Pagamento | Pagamento de telefone fixo, energia e água de 12/2025 | D | — |
| J33 | 28/01 | Recebimento | Recebimento de Comercial Caribe (NF 001) | D | — |
| J34 | 28/01 | Societário | Integralização de capital - Cassilda Apedeuta | D | — |
| J35 | 29/01 | Tributos | Pagamento de ICMS (normal, antecipado, DIFAL) de 12/2025 | D | — |
| J36 | 30/01 | Folha - benefício | Compra de vale-transporte para fevereiro (Sindiônibus 14.320) | D | — |
| J37 | 30/01 | Folha - benefício | Compra de vale-alimentação para fevereiro (Ticket 4.310) | D | — |
| J38 | 30/01 | Tributos | Pagamento de IRPJ e CSLL de 12/2025 | D | — |
| J39 | 30/01 | Serviço tomado | NFS-e 023 Contador Formado - janeiro, pagamento em 10/02 | D | ver contrato C06 |
| J40 | 30/01 | Apuração | Apuração de ICMS, ISS, PIS, COFINS, IPI, IRPJ e CSLL de janeiro | D | — |

### Fevereiro/2026

| ID | Data | Grupo | Evento | Nat. | Parâmetros variáveis (base → faixa) |
|---|---|---|---|---|---|
| F01 | 02/02 | Utilidades | NF Energia Luz do Sertão n.º 988.333 - consumo fev; vencimento 12/02 | V | Valor total: 3.400,00 → R$ 3.000,00 a R$ 3.900,00 (passo 10,00); Rateio Adm/Com/Ind X/Ind Y: 15,6/17,4/31,5/35,6 → percentuais sorteados ±5 p.p., soma 100%; Tarifa: 1,4320 → fixa · *Rateio da fatura: administrativa R$ 530,00, comercial R$ 590,00, Produto X R$ 1.070,00 e Produto Y R$ 1.210,00.* |
| F02 | 02/02 | Utilidades | Fatura de água Águas do Litoral n.º 322.666 - consumo fev; vencimento 12/02 | V | Valor total: 1.780,00 → R$ 1.500,00 a R$ 2.100,00 (passo 10,00); Tarifa: 23,62 → fixa · *Rateio da fatura: administrativa R$ 280,00, comercial R$ 320,00, Produto X R$ 610,00 e Produto Y R$ 570,00.* |
| F03 | 02/02 | Utilidades | NFs de telefonia fixa, celular e internet - competência fev | V | Telefone fixo: 690,00 → R$ 600,00 a R$ 800,00 (passo 1,00) |
| F04 | 03/02 | Venda - mercadoria | NF 337 - venda de ALPHA a consumidor final em São Luís-MA, PIX, preço pelo mark-up (DIFAL) | V | Quantidade: 40 → 20 a 80 un (passo 5) |
| F05 | 04/02 | Compra - insumo | NF 12.380 Indústria Zalego (TO) - MP-B; 35% à vista, saldo em 03/03; desconto financeiro condicional; CT-e 424.110 (venc. 13/02) | V | Quantidade: 132.310 → derivada: necessidade de MP-B + sobra; Custo unitário: 11,2986 → R$ 9,60 a R$ 13,00 (passo 0,0001); Desconto financeiro condicional: 4,00 → 3,00 a 5,00 % (passo 0,50); Frete: 1.980,00 → R$ 1.600,00 a R$ 2.300,00 (passo 10,00) |
| F06 | 05/02 | Tributos - infração | Pagamento do auto de infração (com redução de 70% da multa) | D | — |
| F07 | 05/02 | Financeiro | Apropriação do rendimento do CDB Renda Mais | D | ver contrato C03 |
| F08 | 06/02 | Receita - serviço | NFS-e 003 para Algodão Doce - comissão de representação (Beta); recebimento 08/02 | V | Valor da comissão: 82.000,00 → R$ 70.000,00 a R$ 100.000,00 (passo 500,00) |
| F09 | 06/02 | Pagamento | Pagamento da folha e pró-labore de 01/2026 | D | — |
| F10 | 09/02 | Compra - insumo | NF 9.147 Distribuidor Verde Oliva (RJ) - materiais secundários Z, Q, R e K; 15% à vista e 2 parcelas (07/03, 07/04); frete CIF | V | Quantidades: 134.130 / 19.440 / 37.560 / 132.870 → derivadas: necessidade + sobra; Custos unitários: 10,06 / 11,55 / 12,58 / 13,29 → faixas na tabela de itens |
| F11 | 09/02 | Pagamento | Pagamento parcial (40%) da NF 7.852 (Ar Frio) | D | — |
| F12 | 10/02 | Tributos | Pagamento do FGTS de 01/2026 | D | — |
| F13 | 10/02 | Recebimento | Recebimento da comissão (NFS-e 003) | D | — |
| F17 | 10/02 | Pagamento | Pagamento da NFS-e 023 (contabilidade de janeiro) | D | ver contrato C06 |
| F14 | 11/02 | Pagamento | Pagamento Cell Telefonia - janeiro | D | ver contrato C08 |
| F15 | 11/02 | Societário | Integralização de capital - Marconde Sobreira | D | — |
| F16 | 12/02 | Tributos | Pagamento do ISSQN de 01/2026 | D | — |
| F18 | 13/02 | Pagamento | Pagamento Internet & Comunicação - janeiro | D | ver contrato C07 |
| F19 | 13/02 | Pagamento | Pagamento de água, energia e telefone - competência 02/2026 | D | — |
| F20 | 13/02 | Folha | Processamento da folha e pró-labore de fevereiro + provisões | D | — |
| F21 | 13/02 | Depreciação | Depreciação de fevereiro | D | — |
| F22 | 18/02 | Compra - insumo | NF 1.747 Embalagens Comerciais (AM) - ME-H; 30% à vista, saldo em 13/03; CT-e 425.130 (venc. 22/02) | V | Quantidade: 38.150 → derivada: produção X + Y + sobra; Custo unitário: 5,6589 → R$ 4,80 a R$ 6,50 (passo 0,0001); Frete: 1.410,00 → R$ 1.100,00 a R$ 1.700,00 (passo 10,00) |
| F23 | 18/02 | Pagamento | Pagamento do CT-e 424.110 | D | — |
| F24 | 18/02 | Pagamento | Pagamento do saldo da NF 3.369 (Comercial Elegante) | D | — |
| F25 | 19/02 | Societário | Integralização de capital - Adalberto Cantareira | D | — |
| F26 | 19/02 | Venda - mercadoria | NF 003 Comercial Caribe (CE, CFOP 5.102) - venda de ALPHA pelo mark-up; boleto em 27/02 | V | Quantidade vendida: 10.400 → 9.000 a 11.000 un (passo 50) |
| P01 | 19/02 | Produção | Requisição de materiais e início da produção de X e Y (dia útil seguinte à compra do ME-H) | D | *Evento implícito nas regras do caso; não aparece na lista original.* |
| F27 | 20/02 | Financeiro | Cessão de mútuo à sócia Cassilda Apedeuta (valor disponibilizado à sócia, conforme o contrato C10) | V | ver contrato C10 |
| F28 | 20/02 | Devolução de compra | NF 004 (CFOP 6.201) - devolução de MP-A com defeito à Indústria Sofisticada | V | Quantidade devolvida: 320 → 150 a 500 un (passo 10) |
| F29 | 20/02 | Tributos | Pagamento do IRRF de 01/2026 | D | — |
| F30 | 23/02 | Pagamento | Quitação do arquiteto (RPA) | D | ver contrato C11 |
| F31 | 23/02 | Tributos | Pagamento da GPS (INSS) de 01/2026 | D | — |
| F32 | 23/02 | Serviço tomado | NFS-e 6.320 Construtor Express - 2ª parcela da reforma | D | ver contrato C12 |
| F33 | 23/02 | Financeiro | Pagamento da 1ª parcela do leasing (SAC) | D | ver contrato C04 |
| P02 | 23/02 | Produção | Término da produção (3 dias úteis) e transferência para produtos acabados | D | *Evento implícito nas regras do caso.* |
| F34 | 24/02 | Venda - produção | NF 005 Comercial Roma (PA, CFOP 6.101) - Produtos X e Y pelo mark-up; 80% na emissão e 20% em 22/03; desconto financeiro sobre Y | V | Quantidade vendida X: 19.190 → produção de X × percentual vendido; Quantidade vendida Y: 18.520 → produção de Y × percentual vendido; Desconto financeiro sobre Y: 3,00 → 2,00 a 4,00 % (passo 0,50); Recebimento na emissão: 80,00 → 70,00 a 90,00 % (passo 5,00) |
| F35 | 24/02 | Pagamento | Pagamento do CT-e 425.130 | D | — |
| F36 | 24/02 | Devolução de venda | NF 1.320 Comercial Caribe - devolução de ALPHA (abate o boleto) | V | Quantidade devolvida: 70 → 40 a 120 un (passo 5) |
| F37 | 25/02 | Pagamento | Pagamento de 30% da NF 23.456 (Indústria Sofisticada) | D | — |
| F38 | 25/02 | Folha - benefício | Compra de vale-transporte para março (Sindiônibus 15.520) | D | — |
| F39 | 25/02 | Folha - benefício | Compra de vale-alimentação para março (Ticket 5.410) | D | — |
| F40 | 26/02 | Tributos | Pagamento de ICMS (normal, antecipado, DIFAL) de 01/2026 | D | — |
| F41 | 26/02 | Serviço tomado | NFS-e 345 Recrutamento S/S - seleção de pessoal (jan-fev); pagamento na emissão | D | ver contrato C05 |
| F42 | 26/02 | Tributos | Pagamento de PIS e COFINS de 01/2026 | D | — |
| F43 | 27/02 | Tributos | Pagamento das CSRF de 01/2026 | D | — |
| F44 | 27/02 | Recebimento | Recebimento de Comercial Caribe (NF 003, líquido da devolução) | D | — |
| F45 | 27/02 | Serviço tomado | NFS-e 024 Contador Formado - fevereiro (valor reajustado) | D | ver contrato C06 |
| F46 | 27/02 | Tributos | Pagamento de IRPJ e CSLL por estimativa de 01/2026 | D | — |
| F47 | 27/02 | Financeiro | Resgate do rendimento da aplicação, líquido de IR | D | ver contrato C02 |
| F48 | 27/02 | Apuração | Apuração de ICMS, ISS, PIS, COFINS, IPI, IRPJ e CSLL de fevereiro | D | — |

## 5. Regras de coerência para a geração por dupla

- Quantidades compradas de insumos = necessidade da ficha técnica × produção + sobra (100 a 300 un). Para MP-A, soma-se a quantidade devolvida.
- Vendas de mercadoria e de produtos nunca superam o estoque disponível na data (custo médio ponderado móvel).
- Saldos iniciais ligados a contratos (seguro a apropriar, fornecedores de comodato e contabilidade) e à folha são recalculados; a conta Banco Rico fecha o balanço.
- Valores monetários arredondados ao passo indicado; custos unitários com 4 casas decimais e total da nota em centavos.
- Datas, CFOPs, UFs de origem e destino e regras tributárias ficam fixos: a variação é numérica, e a dificuldade técnica é a mesma para todas as duplas.
- Cada dupla recebe uma semente de sorteio registrada. Com ela o caso pode ser regerado e o gabarito recalculado a qualquer momento.
- Equivalência: os sorteios usam faixas próximas da base (cerca de ±15% a ±20%), mantendo o porte da empresa e o volume de lançamentos.

## 6. Inconsistências encontradas no caso original

Foram encontradas no texto do exercício. Precisam de decisão docente antes de virarem regra no sistema.

| # | Onde | Descrição |
|---|---|---|
| 1 | Conta garantida (C01) | Limite escrito como "R$ 970.000,00 (novecentos mil reais)"; número e extenso divergem. |
| 2 | Leasing (C04, J24, F33) | Contrato "assinado e liberado em 19/01"; o evento de liberação era 20/01. |
| 3 | Arquiteto (C11, J23, F30) | Contratado em 20/01; a quitação (23/02) diz "contratado em 19/01". |
| 4 | Recrutamento (C05, F41) | Honorários pagos em 24/02, mas a NFS-e 345 só é emitida em 26/02; não havia evento de pagamento. |
| 5 | Mútuo (C10, F27) | Contrato de R$ 30.000,00; o evento cedia R$ 20.000,00. O título diz "com os sócios". |
| 6 | Seguro (C09, J21) | Última parcela vence em 17/01 (sábado) e o pagamento ocorre em 19/01. |
| 7 | Contabilidade (C06) | Razão social "S/S" e "S/A"; contrato prevê pagamento no dia 10, mas a NFS-e 024 indicava 05/03 e o pagamento da NFS-e 023 era em 12/02. |
| 8 | Comodatos (C07, C08) | Contratos de R$ 350,00 e R$ 480,00, mas o balanço registra R$ 410,00 (internet) e R$ 580,00 (celular) a pagar. |
| 9 | Frete MP-A (J30) | Frete CIF, mas há CT-e na NF 23.456; vencimento "24.02.2025". |
| 10 | NF 23.456 (J30, F37) | Evento em 26/01; o pagamento de 25/02 diz "emitida em 24/01/2026". |
| 11 | Auto de infração (J29, F06) | TIF n.º 20230001/00 e 20220001/00; pagamento previsto em 05/02 e evento em 04/02; multa "9,450,00"; ICMS de 18%; redução de 70%. |
| 12 | Aplicações (J14, F07) | CDB "realizado em 11/01" (domingo) e evento em 12/01. |
| 13 | Ar Frio (J08, F11) | Pagamento de 09/02 cita NF "emitida em 05/01" e pagava 45%, enquanto o contrato prevê 2 parcelas iguais de 40%. |
| 14 | Vendas ALPHA (J27, J33, F26, F36, F44) | Boleto da NF 001 em 25/01 e recebimento em 28/01; NF 003 emitida em 19/02 mas citada como "de 15/02"; vencimento 28/02 vs. "27/02". |
| 15 | Comissões (J16, J25, F08, F13) | Recebimentos previstos em 20/01 e 08/02; eventos de recebimento em 21/01 e 10/02. |
| 16 | Folha (funcionários) | Idades dos dependentes diminuíam de janeiro para fevereiro; salários de Ângela (2.100 → 1.530) e Marena (2.500 → 5.700) mudam sem evento; valor digitado "2.500.00". |
| 17 | Telefonia (J05, F03) | Celular com vencimento em 08/02 e 08/03 (contrato: dia 9); telefone fixo com vencimento em 24/02 e 24/03, mas pago em 14/01 e 13/02. |
| 18 | CT-e 424.110 (F05, F23) | O pagamento de 18/02 diz CT-e "emitido em 05.02.2026"; a NF 12.380 e o CT-e são de 04/02. |
| 19 | Quadro de prazos | Turma 01A – 15/11/2026 marcada como sexta (é domingo e feriado); "Janeiro / 2026.1" e "Fevereiro / 2026.1". |
| 20 | Energia e água (J03, F01, F02) | Tabelas de rateio incompletas: água/jan sem R$ 380,00; energia/fev sem a área administrativa (R$ 530,00); água/fev sem R$ 1.180,00 (área industrial). |
| 21 | Encargos (FPAS) | Texto usa 27,80%; a planilha de apoio traz FPAS 507 com RAT 3% (= 28,80%). |
| 22 | Imobilizado | Balanço: Máquinas R$ 262.000,00; tabela de bens: máquina de R$ 62.000,00. |
| 23 | Materiais secundários (F10) | Planilha de apoio cita "MP-Z" e "MS-W", inexistentes na ficha técnica. (Corrigido em 07/10: total da NF 9.147 = R$ 3.812.043,57.) |
| 24 | Balanço de 31/12/2025 (versão de 07/10) | Após o ajuste de centavos, os subtotais Obrigações Fiscais (138.994,12; soma 138.994,11) e Ativo não Circulante/Imobilizado (821.591,67; correto 821.591,66) não foram atualizados; a despesa de depreciação na DRE de 2025 segue 10.408,33. |

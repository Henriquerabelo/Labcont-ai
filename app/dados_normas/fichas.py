"""Base normativa padrão do tutor (Etapa 6).

Resumos próprios, curtos e didáticos, com a fonte indicada. Trazem só a norma geral: as decisões do caso
(premissas P01–P26) ficam no gabarito e só chegam ao tutor depois de validadas pelo professor.
Campos: codigo, titulo, fonte, texto, palavras (termos extras de busca), eventos (códigos de janeiro relacionados).
"""

FICHAS = [
    # ---------------------------------------------------------------- escrituração e estrutura
    dict(codigo="ESC-01", titulo="Elementos do lançamento contábil", fonte="ITG 2000 (R1) – Escrituração Contábil, item 13",
         texto="Todo lançamento deve conter data, conta(s) devedora(s), conta(s) credora(s), histórico que identifique a "
               "operação e o documento de suporte, e valor. Pelo método das partidas dobradas, a soma dos débitos é sempre "
               "igual à soma dos créditos; um mesmo fato pode ser registrado em um lançamento composto ou em vários simples.",
         palavras="partidas dobradas debito credito historico documento composto", eventos=""),
    dict(codigo="ESC-02", titulo="Regime de competência", fonte="Lei 6.404/76, art. 177; CPC 00 (R2) – Estrutura Conceitual",
         texto="Os efeitos das transações são reconhecidos no período em que ocorrem, e não quando o dinheiro entra ou sai. "
               "Despesas pagas antecipadamente ficam no ativo e são apropriadas ao resultado conforme o tempo passa; despesas "
               "incorridas e ainda não pagas são reconhecidas com a obrigação no passivo.",
         palavras="competencia apropriacao antecipada provisao periodo caixa", eventos="J17,J21,J32,AJ,J39,FAJ"),
    dict(codigo="ESC-03", titulo="Grupos do balanço e natureza das contas",
         fonte="Lei 6.404/76, arts. 178 a 182",
         texto="Ativo: circulante e não circulante (realizável a longo prazo, investimentos, imobilizado e intangível). "
               "Passivo: circulante e não circulante. Patrimônio líquido: capital social, reservas de capital, ajustes de avaliação "
               "patrimonial, reservas de lucros, ações/quotas em tesouraria e prejuízos acumulados. Contas do ativo e de despesa têm "
               "natureza devedora (aumentam a débito); passivo, PL e receitas têm natureza credora (aumentam a crédito).",
         palavras="ativo passivo patrimonio liquido natureza devedora credora grupo circulante", eventos=""),
    dict(codigo="ESC-04", titulo="Pagamento de obrigação já registrada",
         fonte="CPC 00 (R2); Lei 6.404/76, art. 180",
         texto="Quando a despesa ou a compra já foi reconhecida em período anterior (por exemplo, no balanço de 31/12), o "
               "pagamento apenas baixa o passivo (fornecedores, salários, tributos ou encargos a pagar) contra o banco. "
               "Não se reconhece a despesa de novo. Diferenças entre o valor pago e o registrado indicam juros, multa ou desconto.",
         palavras="pagamento baixa obrigacao passivo quitacao dezembro balanco fornecedor",
         eventos="J06,J07,J10,J11,J12,J13,J22,J28,J31,J32,J35,J38"),
    dict(codigo="ESC-05", titulo="Recebimento de direito já registrado", fonte="CPC 00 (R2); Lei 6.404/76, art. 179",
         texto="Se a receita foi reconhecida quando o serviço foi prestado ou a mercadoria entregue, o recebimento só baixa o "
               "direito (clientes ou contas a receber) contra o banco. Retenções sofridas na fonte reduzem o valor recebido e "
               "ficam registradas como tributo a recuperar ou a compensar.",
         palavras="recebimento clientes contas receber baixa direito retencao", eventos="J25,J33"),
    # ---------------------------------------------------------------- A3: corpus citado no memorial (3.5)
    dict(codigo="CPC26-01", titulo="Balanço patrimonial: circulante e não circulante", fonte="CPC 26 (R1) – Apresentação das Demonstrações Contábeis, itens 54, 66 e 69",
         texto="O balanço apresenta, no mínimo, caixa e equivalentes, clientes, estoques, imobilizado, fornecedores, tributos, "
               "provisões, empréstimos e o patrimônio líquido. Um ativo é circulante quando se espera realizá-lo no ciclo "
               "operacional ou em até 12 meses; um passivo é circulante quando deve ser liquidado nesse prazo. O restante é não "
               "circulante — por isso as parcelas de um financiamento são separadas entre curto e longo prazo.",
         palavras="balanco patrimonial circulante nao circulante 12 meses classificacao apresentacao curto longo prazo",
         eventos="J24,J14"),
    dict(codigo="CPC26-02", titulo="Demonstração do resultado", fonte="CPC 26 (R1), itens 82, 99 e 103; Lei 6.404/76, art. 187",
         texto="A DRE parte da receita bruta, deduz tributos sobre vendas e devoluções (receita líquida), o custo das "
               "mercadorias e serviços vendidos (lucro bruto), as despesas operacionais por função (vendas, administrativas) "
               "e o resultado financeiro, chegando ao resultado antes do IRPJ e da CSLL e ao resultado líquido do período.",
         palavras="dre demonstracao resultado receita liquida lucro bruto despesas operacionais resultado financeiro",
         eventos="J27,J40,F48"),
    dict(codigo="ICMS-08", titulo="Alíquota interna do ICMS no Ceará", fonte="Lei estadual 12.670/1996 (Ceará), alterada pela Lei 18.305/2023",
         texto="Desde 1º de janeiro de 2024 a alíquota interna geral (modal) do ICMS no Ceará é de 20%; alguns produtos têm "
               "alíquotas específicas. É essa alíquota que se compara com a interestadual no diferencial de alíquotas e na "
               "antecipação parcial das entradas de outros estados.",
         palavras="aliquota interna ceara 20 modal icms geral",
         eventos="J08,J15,J27,J35"),
    dict(codigo="ISS-FOR", titulo="ISS em Fortaleza: fato gerador, contribuinte, base e alíquotas",
         fonte="Código Tributário do Município de Fortaleza (LC municipal 159/2013, atualizado até a LC 452/2025), arts. 223, § 2º, III, 229, 240 e 245; LC 116/2003",
         texto="O ISS incide sobre a prestação dos serviços da lista do Anexo I do CTM e o fato gerador independe do "
               "recebimento do preço (art. 223, § 2º, III): o imposto é reconhecido na competência em que a nota de serviço é "
               "emitida. O contribuinte é o prestador (art. 229) e a base de cálculo é o preço do serviço (art. 240). As alíquotas "
               "(art. 245) são 2% para alguns subitens (ex.: 8.1, 16.1), 3% para os itens 4 e 5 e os subitens 7.2, 7.4 e 7.5 "
               "(construção civil e afins) e 5% para os demais serviços, como representação comercial (subitem 10.9). Para quem "
               "presta o serviço, o ISS é dedução da receita bruta contra ISS a recolher; o pagamento segue os prazos do regulamento (art. 255).",
         palavras="iss issqn fortaleza ctm codigo tributario municipal aliquota 5 3 2 lista servicos anexo representacao comissao nfse prestador competencia deducao",
         eventos="J12,J16,J40,F48"),
    dict(codigo="ISS-FOR-02", titulo="Retenção do ISS na fonte pelo tomador (Fortaleza)",
         fonte="Código Tributário do Município de Fortaleza (LC municipal 159/2013, atualizado até a LC 452/2025), arts. 230, 232, 233, 236, 237 e 239",
         texto="Em certos casos quem contrata o serviço retém o ISS do valor pago e o recolhe ao município. São substitutos "
               "tributários (art. 230, II) pessoas jurídicas de alguns ramos, entre elas construtoras e indústrias de transformação; "
               "o art. 232 dispensa a retenção quando o prestador é, por exemplo, autônomo inscrito e em dia com o imposto, "
               "sociedade de profissionais em dia com o valor fixo, MEI ou concessionária de serviço público. Também é "
               "responsável (art. 233) quem toma serviço de autônomo sem inscrição ou sem prova de quitação (inciso IV) e de "
               "prestador de fora que não emite documento fiscal (inciso VI). O tomador responde pelo imposto mesmo que não o "
               "tenha retido (art. 236), e quem não é substituto nem responsável não pode reter (art. 239). Contabilmente o valor "
               "retido sai do valor pago ao prestador e vira obrigação (ISS retido a recolher) do tomador.",
         palavras="retencao retido fonte tomador substituto responsavel tributario iss issqn recolher autonomo rpa construtora industria dispensa",
         eventos="J23,J26,J39"),
    dict(codigo="ISS-FOR-03", titulo="ISS na construção civil: materiais, alíquota e local",
         fonte="Código Tributário do Município de Fortaleza (LC municipal 159/2013, atualizado até a LC 452/2025), arts. 224, § 1º, III, 240, §§ 4º, I, e 5º, e 245, II",
         texto="Nas obras de construção civil e reformas (subitens 7.2 e 7.5 da lista), o valor dos materiais fornecidos pelo "
               "prestador não entra na base de cálculo do ISS (art. 240, § 4º, I): o imposto incide sobre a parcela de serviço "
               "(mão de obra). A alíquota desses subitens em Fortaleza é de 3% (art. 245, II), e o imposto é devido no local da "
               "obra (art. 224, § 1º, III). Nenhuma dedução pode levar a carga abaixo de 2% do preço (art. 240, § 5º).",
         palavras="construcao civil obra reforma empreitada material materiais mao obra galpao 3 base deducao local execucao",
         eventos="J26"),
    dict(codigo="ISS-FOR-04", titulo="ISS do profissional autônomo",
         fonte="Código Tributário do Município de Fortaleza (LC municipal 159/2013, atualizado até a LC 452/2025), arts. 233, IV, e 246 a 248",
         texto="O autônomo inscrito no cadastro municipal e em dia paga o ISS por valor fixo anual (art. 246; R$ 600 quando a "
               "profissão exige nível superior) e, nesse caso, o tomador não retém. Se não for inscrito, ou se inscrito não "
               "comprovar a quitação do valor fixo, o tomador retém o ISS sobre o preço do serviço pela alíquota da atividade "
               "(arts. 233, IV, e 246, § 3º), e essa retenção é tributação definitiva (art. 246, § 4º). Pessoa física não inscrita "
               "é equiparada à pessoa jurídica para fins do imposto (art. 247, § 2º).",
         palavras="autonomo rpa recibo pagamento pessoa fisica valor fixo anual inscricao cadastro quitacao arquiteto profissional liberal retencao",
         eventos="J23"),
    dict(codigo="ICMS-09", titulo="Como consultar o Regulamento do ICMS do Ceará (RICMS-CE)",
         fonte="Decretos estaduais 33.327/2019, 35.061/2022, 34.605/2022 e 24.569/1997; portal Sefaz Legis (sefazlegis.sefaz.ce.gov.br)",
         texto="O RICMS-CE não está mais em um arquivo único: foi dividido em livros, cada um em um decreto. Livro I, parte geral "
               "(fato gerador, base de cálculo, alíquotas, isenções, créditos): Decreto 33.327/2019. Livro II, obrigações acessórias "
               "(cadastro CGF, documentos fiscais, escrituração digital): Decreto 35.061/2022. Livro IV, fiscalização, infrações, "
               "penalidades e consulta: Decreto 34.605/2022. Procedimentos especiais, como substituição tributária e regimes "
               "especiais, seguem nos dispositivos e anexos remanescentes do Decreto 24.569/1997. Os textos oficiais e "
               "atualizados ficam no portal de legislação da Sefaz-CE (Sefaz Legis); a lei do imposto é a Lei estadual 12.670/1996.",
         palavras="ricms regulamento icms ceara decreto consultar onde legislacao sefaz livro cgf substituicao tributaria penalidade",
         eventos="J15,J29,J35,J40,F48"),
    # ---------------------------------------------------------------- PL e destinação
    dict(codigo="PL-01", titulo="Capital subscrito e capital a integralizar", fonte="Lei 6.404/76, art. 182; Código Civil, arts. 1.052 e 1.055",
         texto="O capital social é apresentado pelo valor subscrito e, por dedução, a parcela ainda não realizada (capital a "
               "integralizar, conta retificadora do PL). Quando o sócio integraliza em dinheiro ou bens, debita-se o ativo recebido "
               "e baixa-se a parcela a integralizar daquele sócio.",
         palavras="capital social subscrito integralizar integralizacao socio quotas realizado", eventos="J20,J34"),
    dict(codigo="PL-02", titulo="Ordem de cálculo do lucro líquido e participações", fonte="Lei 6.404/76, arts. 189 a 191",
         texto="Do resultado do exercício deduzem-se, antes de qualquer participação, os prejuízos acumulados e a provisão para "
               "IR e CSLL. As participações estatutárias (debêntures, empregados, administradores e partes beneficiárias) são "
               "calculadas sucessivamente, nessa ordem, cada uma sobre o lucro que remanescer após a anterior. Lucro líquido é o "
               "resultado que sobra depois das participações.",
         palavras="participacoes empregados administradores lucro liquido destinacao resultado ordem", eventos="J01"),
    dict(codigo="PL-03", titulo="Reserva legal", fonte="Lei 6.404/76, art. 193",
         texto="Do lucro líquido, 5% são aplicados na constituição da reserva legal, antes de qualquer outra destinação. "
               "A reserva legal não pode exceder 20% do capital social; a companhia pode deixar de constituí-la quando o saldo "
               "dela somado às reservas de capital exceder 30% do capital.",
         palavras="reserva legal cinco por cento limite capital destinacao", eventos="J01"),
    dict(codigo="PL-04", titulo="Dividendo mínimo obrigatório", fonte="Lei 6.404/76, art. 202",
         texto="Os sócios têm direito ao dividendo fixado no estatuto ou contrato; se omisso, metade do lucro líquido ajustado. "
               "O lucro ajustado é o lucro líquido diminuído da reserva legal e ajustado pelas reservas para contingências. "
               "Dividendos declarados e não pagos vão para o passivo (dividendos a pagar).",
         palavras="dividendos minimo obrigatorio lucro ajustado estatuto contrato socios", eventos="J01"),
    dict(codigo="PL-05", titulo="Reservas estatutárias e lucros acumulados", fonte="Lei 6.404/76, arts. 194 e 202, § 6º",
         texto="O estatuto ou contrato pode criar reservas com finalidade, critério de cálculo e limite definidos. "
               "Os lucros não destinados às reservas devem ser distribuídos como dividendos; por isso a conta de lucros "
               "acumulados é transitória e fica zerada depois da destinação.",
         palavras="reserva estatutaria lucros acumulados saldo zerado destinacao", eventos="J01"),
    # ---------------------------------------------------------------- estoques e compras
    dict(codigo="EST-01", titulo="Custo de aquisição de estoques", fonte="CPC 16 (R1) – Estoques, itens 10 e 11",
         texto="O custo de aquisição compreende o preço de compra, os impostos não recuperáveis, o transporte, o seguro e o "
               "manuseio para trazer o item até o estoque. Tributos recuperáveis (que geram crédito) não entram no custo. "
               "Descontos comerciais e abatimentos reduzem o custo.",
         palavras="custo aquisicao estoque mercadoria materia prima frete tributos recuperaveis desconto",
         eventos="J15,J30,J09,F05,F10,F22"),
    dict(codigo="EST-02", titulo="Custo médio ponderado", fonte="CPC 16 (R1), itens 25 e 27",
         texto="Pelo custo médio ponderado, o custo de cada unidade é a média entre o saldo em estoque e as compras do período "
               "(no método móvel, recalculada a cada entrada). As saídas são baixadas pelo custo médio vigente na data, gerando o "
               "custo das mercadorias vendidas (CMV).",
         palavras="requisicao saida producao baixa custo medio ponderado movel cmv baixa estoque saida kardex", eventos="J27,F05,F10,F22,F28,FP1,F04,F26,F34,F36"),
    dict(codigo="EST-03", titulo="Desconto incondicional e condicional", fonte="LC 87/96, art. 13, § 1º, II, a; CPC 16 (R1), item 11",
         texto="Desconto incondicional (destacado na nota, sem depender de evento futuro) reduz o preço e não integra a base do "
               "ICMS. Desconto condicional (ex.: por pagamento antecipado) integra a base do ICMS e, se obtido, é receita "
               "financeira de quem compra; para quem vende e concede, é despesa financeira, sem reduzir a receita bruta.",
         palavras="desconto incondicional condicional base icms nota", eventos="J15,F05,F34"),
    dict(codigo="EST-04", titulo="Frete na compra: CIF e FOB", fonte="CPC 16 (R1), item 11; CPC 27, item 16",
         texto="No frete CIF o fornecedor contrata e paga o transporte (o custo já está no preço). No FOB o comprador contrata o "
               "transporte e o valor do frete integra o custo do bem ou da mercadoria adquirida, descontados os tributos "
               "recuperáveis sobre o frete.",
         palavras="frete cif fob transporte conhecimento cte custo", eventos="J09,J22,J30,F05,F10,F22"),
    dict(codigo="EST-06", titulo="Devolução de compra", fonte="CPC 16 (R1), item 11; RIPI (Decreto 7.212/2010), art. 229; LC 87/96, art. 21",
         texto="Na devolução de compra o comprador emite nota fiscal de devolução (CFOP 5.201/6.201 para insumos de industrialização) "
               "com os mesmos valores e alíquotas da entrada. Contabilmente, desfaz a parte devolvida da compra: baixa o estoque pelo "
               "custo da compra devolvida, estorna os créditos de ICMS, IPI, PIS e COFINS e abate o valor da nota (produtos + IPI) "
               "do saldo devido ao fornecedor ou registra o valor a receber dele.",
         palavras="devolucao compra defeito nota devolucao estorno credito fornecedor abatimento 6201 5201",
         eventos="F28"),
    dict(codigo="EST-05", titulo="CFOP: leitura da nota fiscal", fonte="Convênio s/nº de 1970 (tabela CFOP), Ajuste SINIEF 07/01",
         texto="O primeiro dígito indica o tipo e a origem: 1/2/3 entradas (estadual, interestadual, exterior) e 5/6/7 saídas. "
               "O CFOP impresso na nota é do emitente: 5.101/6.101 venda de produção própria; 5.102/6.102 venda de mercadoria "
               "adquirida de terceiros. Na entrada, o destinatário classifica conforme o uso: 2.101 industrialização, 2.102 "
               "comercialização, 2.551 ativo imobilizado, 2.556 uso e consumo.",
         palavras="cfop nota fiscal entrada saida interestadual uso consumo ativo revenda industrializacao",
         eventos="J08,J15,J27,J30,F05,F10,F22,F28"),
    # ---------------------------------------------------------------- ICMS
    dict(codigo="ICMS-01", titulo="Não cumulatividade do ICMS", fonte="LC 87/96, arts. 19, 20, 24 e 25",
         texto="O ICMS devido em cada operação é compensado com o cobrado nas anteriores. O imposto destacado na compra de "
               "mercadoria para revenda ou de insumo para industrialização gera crédito (ICMS a recuperar). Na apuração mensal, "
               "débitos das saídas e créditos das entradas são compensados; saldo credor é transportado para o mês seguinte.",
         palavras="icms credito debito nao cumulatividade recuperar recuperavel tributos impostos apuracao saldo credor", eventos="J15,J30,J40,F05,F10,F22,F28,F48"),
    dict(codigo="ICMS-02", titulo="Uso e consumo e bens alheios à atividade", fonte="LC 87/96, arts. 20, §§ 1º e 5º, e 33, I",
         texto="Material de uso e consumo só dará crédito de ICMS a partir da data fixada na LC 87/96 (art. 33, I). Bens do ativo "
               "imobilizado ligados à atividade geram crédito em 1/48 por mês; bens alheios à atividade do estabelecimento não "
               "geram crédito. Sem crédito, o imposto pago integra o custo do bem.",
         palavras="uso consumo ativo imobilizado credito 48 alheio administrativo aparelho equipamento ar-condicionado recuperar", eventos="J08,J09"),
    dict(codigo="ICMS-03", titulo="Alíquotas interestaduais", fonte="Resolução do Senado Federal nº 22/1989",
         texto="Nas operações interestaduais a alíquota geral é 12%. Nas saídas das regiões Sul e Sudeste (exceto Espírito "
               "Santo) para Norte, Nordeste, Centro-Oeste e Espírito Santo, a alíquota é 7%. A alíquota interna é fixada pela "
               "lei de cada estado.",
         palavras="aliquota interestadual 12 7 sudeste nordeste origem", eventos="J08,J15,J30,F05,F10,F22"),
    dict(codigo="ICMS-04", titulo="Diferencial de alíquotas (DIFAL)", fonte="CF, art. 155, § 2º, VII e VIII (EC 87/2015); LC 190/2022",
         texto="Na compra interestadual de bem para uso, consumo ou ativo imobilizado por contribuinte do ICMS, cabe ao estado "
               "de destino a diferença entre a sua alíquota interna e a interestadual. O DIFAL é recolhido pelo adquirente e, "
               "quando não há crédito, integra o custo do bem.",
         palavras="difal diferencial aliquota uso consumo ativo destino adquirente", eventos="J08,J35,F04"),
    dict(codigo="ICMS-05", titulo="Antecipação parcial do ICMS", fonte="Lei estadual 12.670/1996 e RICMS-CE, Livro I (Decreto 33.327/2019)",
         texto="Na entrada interestadual de mercadoria para revenda, o Ceará exige o recolhimento antecipado de parte do imposto: "
               "a diferença entre a alíquota interna e a interestadual sobre a base da operação. O valor recolhido não é custo: "
               "é crédito aproveitado na apuração do ICMS.",
         palavras="antecipacao parcial icms revenda interestadual ceara credito recuperar tributos", eventos="J15,J35"),
    dict(codigo="ICMS-06", titulo="ICMS na venda", fonte="LC 87/96, arts. 12 e 13; CPC 47, item 47",
         texto="Na saída da mercadoria ocorre o fato gerador do ICMS, calculado sobre o valor da operação. Na DRE, a receita "
               "bruta é apresentada com o ICMS e o imposto aparece como dedução (ICMS sobre vendas) contra ICMS a recolher.",
         palavras="icms venda saida receita bruta deducao recolher", eventos="J27,J40,F04,F26,F34,F48"),
    dict(codigo="ICMS-07", titulo="Auto de infração e multa fiscal", fonte="CPC 25, item 14; Lei 8.981/95, art. 41, § 5º",
         texto="Um auto de infração gera obrigação presente: o imposto, os juros e a multa prováveis são provisionados como "
               "despesa quando a empresa reconhece o débito. Multas punitivas por infração fiscal são indedutíveis para IRPJ e CSLL. "
               "Reduções previstas em lei para pagamento antecipado diminuem a multa a pagar.",
         palavras="auto infracao multa provisao indedutivel reducao sefaz", eventos="J29"),
    # ---------------------------------------------------------------- IPI
    dict(codigo="ICMS-10", titulo="DIFAL na venda a consumidor final de outro estado", fonte="CF, art. 155, § 2º, VII, b, e VIII, b (EC 87/2015); LC 190/2022",
         texto="Na venda interestadual a consumidor final não contribuinte do ICMS, o remetente destaca o ICMS pela alíquota "
               "interestadual (12% do Nordeste para o Nordeste) e recolhe ao estado de destino o diferencial entre a alíquota interna "
               "do destino e a interestadual. No Maranhão a alíquota modal é 23% desde 23/02/2025. Para quem vende, o DIFAL é tributo "
               "sobre a venda (dedução da receita) e uma obrigação a recolher à UF de destino.",
         palavras="difal consumidor final nao contribuinte pessoa fisica outro estado destino maranhao 23 interestadual 12 remetente venda",
         eventos="F04"),
    dict(codigo="IPI-02", titulo="IPI na venda de produção própria", fonte="RIPI (Decreto 7.212/2010), arts. 35 e 190; CF, art. 155, § 2º, XI; Decreto-Lei 1.598/77, art. 12, § 4º",
         texto="Na saída do produto industrializado, o IPI é calculado pela alíquota da TIPI sobre o valor da operação e cobrado do "
               "comprador por fora, somado ao total da nota. Ele não compõe a receita bruta (o vendedor é mero depositário) e vai "
               "para IPI a recolher. Quando a venda é para contribuinte do ICMS, para revenda ou industrialização, o IPI não integra a "
               "base de cálculo do ICMS.",
         palavras="ipi saida venda producao propria por fora tipi recolher receita bruta base icms contribuinte revenda",
         eventos="F34"),
    dict(codigo="VEN-01", titulo="Devolução de venda", fonte="Lei 6.404/76, art. 187, I; CPC 47, item 47; LC 87/96, art. 21",
         texto="Quando o cliente devolve a mercadoria, a devolução é deduzida da receita bruta (conta de devoluções de vendas) "
               "pelo valor da venda, e o valor sai do saldo a receber. Os tributos debitados na venda são estornados (crédito de ICMS, "
               "PIS e COFINS pela nota de devolução) e a mercadoria volta ao estoque pelo custo com que saiu, revertendo o CMV.",
         palavras="devolucao venda cliente deducao receita estorno cmv retorno estoque abatimento boleto",
         eventos="F36,F44"),
    dict(codigo="IPI-01", titulo="Crédito de IPI do estabelecimento industrial", fonte="RIPI (Decreto 7.212/2010), art. 226, I",
         texto="O estabelecimento industrial credita-se do IPI destacado na compra de matéria-prima, produto intermediário e "
               "material de embalagem para industrialização (IPI a recuperar). Para mercadoria de revenda ou bem de uso, sem "
               "crédito, o IPI integra o custo. O IPI é calculado por fora, sobre o valor dos produtos, pela alíquota da TIPI.",
         palavras="ipi credito industrial materia prima tipi recuperar tributos por fora", eventos="J30,J40,F05,F28,F48"),
    # ---------------------------------------------------------------- PIS/COFINS
    dict(codigo="PC-01", titulo="PIS e COFINS não cumulativos: alíquotas e créditos", fonte="Lei 10.637/2002 e Lei 10.833/2003, arts. 2º e 3º",
         texto="No lucro real, PIS (1,65%) e COFINS (7,6%) incidem sobre a receita, com créditos sobre bens para revenda, insumos, "
               "energia elétrica consumida no estabelecimento, aluguéis, depreciação de máquinas e fretes pagos. Bens e "
               "serviços de uso administrativo, em regra, não geram crédito.",
         palavras="pis cofins nao cumulativo credito recuperar tributos insumo revenda energia frete 1,65 7,6", eventos="J02,J15,J30,J40,F48"),
    dict(codigo="PC-02", titulo="ICMS fora da base de PIS e COFINS", fonte="STF, RE 574.706 (Tema 69); Lei 14.592/2023",
         texto="O ICMS destacado não compõe a base de cálculo do PIS e da COFINS sobre a receita (Tema 69/STF). Em simetria, "
               "desde a Lei 14.592/2023 o crédito de PIS e COFINS na compra é calculado sem o ICMS destacado na nota.",
         palavras="tema 69 exclusao icms base pis cofins credito compra", eventos="J15,J27,J30,J40,F48"),
    # ---------------------------------------------------------------- serviços e retenções
    dict(codigo="RET-01", titulo="IRRF sobre serviços profissionais e comissões", fonte="RIR/2018 (Decreto 9.580), arts. 714 e 718",
         texto="A pessoa jurídica que paga a outra PJ por serviços profissionais (ex.: contabilidade) ou por comissões e "
               "representação retém IRRF de 1,5% sobre o valor bruto. Quem retém registra IRRF a recolher; quem sofre a retenção "
               "registra IRRF a recuperar, compensável no IRPJ.",
         palavras="irrf retencao 1,5 servicos profissionais comissao representacao recuperar", eventos="J11,J16,J25,J39"),
    dict(codigo="RET-02", titulo="Retenção de CSLL, PIS e COFINS (CSRF)", fonte="Lei 10.833/2003, art. 30",
         texto="Nos pagamentos de PJ a PJ por serviços profissionais, de limpeza, manutenção e outros listados, retêm-se CSLL 1%, "
               "COFINS 3% e PIS 0,65% (total 4,65%). O valor retido é obrigação de quem paga até o recolhimento.",
         palavras="csrf retencao 4,65 csll pis cofins servicos", eventos="J11,J39"),
    dict(codigo="RET-03", titulo="Retenção de INSS em empreitada e cessão de mão de obra", fonte="Lei 8.212/91, art. 31",
         texto="A contratante de serviços por empreitada ou cessão de mão de obra retém 11% do valor da mão de obra da nota "
               "e recolhe em nome da prestadora. Material discriminado na nota fica fora da base.",
         palavras="inss retencao 11 empreitada mao obra construcao", eventos="J26"),
    dict(codigo="RET-04", titulo="ISS e sua retenção", fonte="LC 116/2003, arts. 3º, 6º e 8º",
         texto="O ISS incide sobre serviços da lista anexa, com alíquota municipal entre 2% e 5%. Em vários casos (como "
               "construção civil e serviços prestados por autônomos sem inscrição) o tomador é responsável e retém o imposto. "
               "Para quem presta o serviço, o ISS é dedução da receita.",
         palavras="iss imposto servicos retencao tomador municipal 5", eventos="J12,J16,J23,J26"),
    dict(codigo="RET-05", titulo="Contratação de autônomo (RPA)", fonte="Lei 10.666/2003, art. 4º; Lei 8.212/91, art. 22, III",
         texto="Ao pagar contribuinte individual (autônomo), a empresa retém 11% de INSS (limitado ao teto), retém o IRRF pela "
               "tabela progressiva e, se aplicável, o ISS. Além disso, paga a contribuição patronal de 20% sobre a remuneração, "
               "que é custo da empresa.",
         palavras="rpa autonomo contribuinte individual inss 11 20 patronal irrf tabela arquiteto engenheiro profissional liberal pessoa fisica", eventos="J23"),
    # ---------------------------------------------------------------- folha
    dict(codigo="CUS-01", titulo="Custo de produção: materiais, mão de obra direta e custos indiretos", fonte="CPC 16 (R1) – Estoques, itens 10, 12 e 13",
         texto="O custo dos produtos fabricados reúne o custo de aquisição dos materiais consumidos e os custos de transformação: "
               "mão de obra direta e custos indiretos de fabricação (CIF), como energia da fábrica, mão de obra indireta, depreciação "
               "das máquinas e do prédio industrial. Os custos indiretos são alocados aos produtos por um critério sistemático e "
               "racional. Despesas administrativas e de vendas não entram no custo dos produtos.",
         palavras="custo producao fabricacao materiais diretos mao obra direta mod cif indireto transformacao fabrica",
         eventos="F20,F21,FP1,FP2"),
    dict(codigo="CUS-02", titulo="Custeio por absorção", fonte="Decreto 9.580/2018 (RIR/2018), art. 302; CPC 16 (R1), item 12",
         texto="Pela legislação do IR e pelo CPC 16, os estoques de produtos são avaliados pelo custeio por absorção: integram o "
               "custo de produção o custo dos insumos consumidos, a mão de obra (inclusive supervisão e encargos), os encargos de "
               "depreciação dos bens aplicados na produção e os demais custos indiretos ligados à fabricação. O custo só vai para o "
               "resultado (CPV) quando o produto é vendido.",
         palavras="absorcao custeio cpv custo produtos vendidos estoque produtos acabados depreciacao fabrica",
         eventos="FP2,F34,F04"),
    dict(codigo="CUS-03", titulo="Rateio do CIF e produtos em elaboração", fonte="CPC 16 (R1), itens 12 a 14",
         texto="Os custos indiretos acumulados no período são distribuídos entre os produtos por uma base de rateio (por exemplo, "
               "o custo dos materiais diretos de cada produto): CIF do produto = CIF total × (base do produto ÷ base total). Durante a "
               "fabricação os custos ficam em Produtos em Elaboração; ao término, o custo total é transferido para Produtos "
               "Acabados e o custo unitário é o custo total dividido pelas unidades produzidas.",
         palavras="rateio cif base materiais diretos produtos elaboracao acabados custo unitario requisicao ordem producao",
         eventos="FP1,FP2"),
    dict(codigo="FOL-01", titulo="Folha de pagamento: proventos e descontos", fonte="CLT; Lei 8.212/91, art. 20; Decreto 9.580/2018 (IRRF)",
         texto="Proventos: salário, horas extras, comissões, salário-família. Descontos do empregado: INSS pela tabela "
               "progressiva, IRRF pela tabela mensal (base = proventos − INSS − dependentes), vale-transporte e outros. "
               "O líquido vai para salários a pagar; INSS e IRRF retidos vão para obrigações a recolher.",
         palavras="folha salario inss irrf desconto proventos liquido dependentes hora extra", eventos="J06,J18,F20"),
    dict(codigo="FOL-02", titulo="Encargos patronais e FGTS", fonte="Lei 8.212/91, art. 22, I e II; Lei 8.036/90, art. 15",
         texto="Sobre a folha, a empresa paga INSS patronal (20%), RAT/GILRAT e contribuições a terceiros (Sistema S, salário-"
               "educação), além do FGTS de 8% depositado em favor do empregado. São despesas da empresa com contrapartida em "
               "encargos a recolher.",
         palavras="encargos patronal inss rat terceiros fgts 8 20 despesa", eventos="J07,J18,J28,F20"),
    dict(codigo="FOL-03", titulo="Salário-família", fonte="Lei 8.213/91, arts. 65 e 66",
         texto="Pago ao empregado de baixa renda por filho de até 14 anos. A empresa paga junto com o salário e deduz o valor "
               "do INSS a recolher (não é despesa da empresa).",
         palavras="salario familia filho 14 anos baixa renda deducao inss", eventos="J18,F20"),
    dict(codigo="FOL-04", titulo="Pró-labore dos sócios", fonte="Lei 8.212/91, arts. 21 e 22, III",
         texto="Pró-labore é a remuneração do sócio que trabalha na empresa. O sócio contribui com 11% de INSS (limitado ao teto), "
               "retido pela empresa, e a empresa paga 20% patronal. Há retenção de IRRF pela tabela mensal.",
         palavras="pro labore socio inss 11 20 irrf", eventos="J06,J18,F20"),
    dict(codigo="FOL-05", titulo="Provisões de férias e 13º salário", fonte="CPC 33 (R1), itens 11 e 13; CF, art. 7º, VIII e XVII",
         texto="Férias (com o terço constitucional) e 13º salário são benefícios de curto prazo reconhecidos mês a mês, "
               "conforme o empregado presta serviço: a cada mês provisiona-se 1/12 do 13º e 1/12 das férias mais 1/3, com os "
               "encargos e o FGTS incidentes.",
         palavras="provisao ferias 13 decimo terceiro terco encargos mensal", eventos="J18,F20"),
    dict(codigo="FOL-06", titulo="Vale-transporte e vale-alimentação", fonte="Lei 7.418/85, art. 4º, parágrafo único; Lei 6.321/76 (PAT)",
         texto="O vale-transporte pode ser descontado do empregado até 6% do salário-base; o que exceder é despesa da empresa. "
               "Vales comprados para o mês seguinte são adiantamento (ativo) e viram despesa no mês de uso.",
         palavras="vale transporte alimentacao 6 desconto adiantamento beneficio pat", eventos="J18,J36,J37,F20"),
    # ---------------------------------------------------------------- imobilizado, arrendamento
    dict(codigo="IMO-01", titulo="Custo do imobilizado", fonte="CPC 27 – Ativo Imobilizado, itens 16 e 17",
         texto="O custo inclui o preço de compra, tributos não recuperáveis (como ICMS sem crédito e DIFAL), frete, instalação e "
               "demais custos diretamente atribuíveis para colocar o bem em condição de uso, menos descontos.",
         palavras="imobilizado custo aquisicao frete instalacao difal nao recuperavel", eventos="J08,J09,J24"),
    dict(codigo="IMO-02", titulo="Depreciação", fonte="CPC 27, itens 50, 53 e 55",
         texto="O valor depreciável (custo − valor residual) é distribuído de forma sistemática ao longo da vida útil. A "
               "depreciação começa quando o bem está disponível para uso. No método linear, a quota mensal é o valor "
               "depreciável dividido pelo número de meses de vida útil, registrada em despesa contra depreciação acumulada.",
         palavras="depreciacao vida util residual linear acumulada quota mensal", eventos="J19,F21"),
    dict(codigo="IMO-03", titulo="Reformas e obras em andamento", fonte="CPC 27, itens 7, 12 e 13",
         texto="Gastos que aumentam a vida útil ou os benefícios do ativo (reforma, ampliação) são capitalizados; manutenção "
               "periódica é despesa. Enquanto a obra não termina, os custos ficam em imobilizado em andamento, sem depreciação.",
         palavras="reforma obra andamento capitalizar manutencao galpao construcao", eventos="J23,J26,F32"),
    dict(codigo="IMO-04", titulo="Arrendamento (leasing) no arrendatário", fonte="CPC 06 (R2) – Arrendamentos, itens 22 a 26",
         texto="O arrendatário reconhece o bem arrendado no ativo e, em contrapartida, o passivo de arrendamento pelo valor "
               "presente das contraprestações. O passivo é separado em circulante (parcelas dos próximos 12 meses) e não "
               "circulante; os juros são apropriados como despesa financeira ao longo do tempo.",
         palavras="leasing arrendamento financeiro passivo curto longo prazo juros direito uso maquinas", eventos="J24,AJ,FAJ"),
    # ---------------------------------------------------------------- financeiro
    dict(codigo="FIN-01", titulo="Aplicações financeiras e rendimentos", fonte="CPC 48 – Instrumentos Financeiros; CPC 00 (R2)",
         texto="A aplicação é transferida do banco para a conta de aplicação (ativo). Os rendimentos são receita financeira "
               "reconhecida por competência, mesmo antes do resgate. Aplicações com liquidez imediata são equivalentes de caixa; "
               "as de prazo maior ficam em aplicações financeiras.",
         palavras="aplicacao cdb invest rendimento receita financeira resgate juros competencia", eventos="J04,J14,TES,AJ,FTES,FAJ"),
    dict(codigo="FIN-02", titulo="IR sobre rendimentos de aplicações", fonte="Lei 11.033/2004, art. 1º",
         texto="Rendimentos de renda fixa sofrem IRRF regressivo: 22,5% até 180 dias, 20% de 181 a 360, 17,5% de 361 a 720 e 15% "
               "acima de 720 dias. Para a pessoa jurídica no lucro real, o IR retido é antecipação: vai para IRRF a recuperar.",
         palavras="ir rendimento aplicacao 22,5 regressivo resgate irrf recuperar", eventos="TES,J14,J04,FTES"),
    dict(codigo="FIN-03", titulo="Conta garantida e juros bancários", fonte="CPC 00 (R2); CPC 48",
         texto="Conta garantida é um limite de crédito: o saldo negativo coberto pelo banco é um empréstimo no passivo "
               "circulante. Os juros incorridos são despesa financeira do período, mesmo que cobrados depois.",
         palavras="conta garantida cheque especial juros despesa financeira saldo negativo emprestimo", eventos="TES,AJ,FTES,FAJ"),
    dict(codigo="FIN-04", titulo="Seguros pagos antecipadamente", fonte="CPC 00 (R2) – regime de competência",
         texto="O prêmio de seguro cobre um período futuro: é registrado como despesa antecipada (ativo) e apropriado ao "
               "resultado mês a mês, conforme a vigência. O pagamento de parcela de prêmio já registrado baixa a obrigação.",
         palavras="seguro premio despesa antecipada apropriacao vigencia parcela", eventos="J21,AJ,FAJ"),
    # ---------------------------------------------------------------- receita, preço, resultado
    dict(codigo="REC-01", titulo="Reconhecimento da receita", fonte="CPC 47 – Receita de Contrato com Cliente, itens 31 e 38",
         texto="A receita é reconhecida quando a empresa satisfaz a obrigação de desempenho, isto é, quando transfere o controle "
               "da mercadoria ou conclui o serviço. Junto com a receita de venda, baixa-se o estoque vendido como custo (CMV).",
         palavras="receita reconhecimento venda servico controle cmv obrigacao desempenho", eventos="J16,J27"),
    dict(codigo="REC-02", titulo="Formação do preço pelo mark-up divisor", fonte="Contabilidade de custos (método do mark-up)",
         texto="O mark-up divisor é 1 − (soma dos percentuais sobre o preço: tributos sobre a venda + margem desejada). "
               "O preço é o custo dividido por esse divisor; o multiplicador equivalente é 1 ÷ divisor. Os percentuais devem "
               "incidir sobre o preço de venda, não sobre o custo.",
         palavras="mark-up markup preco venda margem divisor multiplicador custo", eventos="J27,F04,F26,F34"),
    dict(codigo="IR-01", titulo="IRPJ e CSLL por estimativa mensal", fonte="Lei 9.430/96, art. 2º; Lei 9.249/95, arts. 3º, 15 e 20; Lei 7.689/88",
         texto="No lucro real anual, a empresa recolhe mensalmente por estimativa: aplica percentuais de presunção sobre a "
               "receita bruta (IRPJ: 8% revenda, 32% serviços; CSLL: 12% revenda, 32% serviços) e soma integralmente as demais "
               "receitas, como as financeiras. IRPJ de 15% mais adicional de 10% sobre a parcela que exceder R$ 20.000,00 no mês; "
               "CSLL de 9%. Retenções sofridas são deduzidas.",
         palavras="irpj csll estimativa presuncao 8 12 32 adicional 10 15 9 receita bruta", eventos="J38,J40,F48"),
    dict(codigo="AP-01", titulo="Apuração mensal dos tributos", fonte="LC 87/96, art. 24; Lei 10.637/2002 e Lei 10.833/2003; Lei 9.430/96",
         texto="No fim do mês, os débitos (tributos sobre vendas e serviços) são compensados com os créditos registrados nas "
               "entradas. Se os débitos forem maiores, o saldo vai para tributo a recolher; se os créditos forem maiores, o saldo "
               "credor permanece como tributo a recuperar para os meses seguintes.",
         palavras="apuracao mensal compensacao debitos creditos recolher recuperar saldo", eventos="J40,F48"),
    dict(codigo="SRV-01", titulo="Serviços tomados: competência e retenções", fonte="CPC 00 (R2); LC 116/2003; Lei 10.833/2003",
         texto="Ao receber a nota de serviço tomado, reconhece-se a despesa (ou o ativo, se capitalizável) na competência, "
               "com o valor bruto. Retenções feitas pela empresa (IRRF, CSRF, INSS, ISS) reduzem o valor a pagar ao prestador e "
               "viram obrigação a recolher.",
         palavras="servico tomado nota despesa bruto retencao fornecedor pagar", eventos="J02,J03,J05,J39"),
    dict(codigo="SRV-02", titulo="Contas de consumo (energia, água, telecomunicações)", fonte="CPC 00 (R2); Lei 10.833/2003, art. 3º, III",
         texto="Faturas de energia, água e telecomunicações são despesas do mês de consumo, rateadas entre as áreas da empresa "
               "quando houver critério. Energia consumida na produção gera crédito de PIS e COFINS no lucro real; em despesas "
               "administrativas, não.",
         palavras="energia agua telefone internet fatura consumo rateio despesa", eventos="J02,J03,J05,J17,J32"),
]

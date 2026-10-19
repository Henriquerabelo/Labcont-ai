# LABCONT-AI · Etapas do protótipo

Este é o plano de desenvolvimento do protótipo funcional (MVP), que será o Documento 8 do Edital nº 1/2026 da Cátedra Luíza de Teodoro.
A inscrição termina em **31/10/2026**. A meta é ter a versão de demonstração publicada até **24/10** e submeter até **29/10**.

| Etapa | Período | Entrega | Situação |
|---|---|---|---|
| 1. Cadastros acadêmicos | 03–07/10 | Disciplinas, turmas, docentes e discentes, com importação dos PDFs do SIGAA | **Em validação** |
| 2. Publicação | 03/10 | Repositório privado no GitHub, publicação automática no VPS Hostinger (https://labcont.io), HTTPS e senha de acesso | **Concluída** |
| 2b. Caso da empresa | 04/10 | Cadastro editável do caso-base EH0012: empresa e sócios, contratos, folha, produção (ficha técnica), eventos, faixas por parâmetro e inconsistências; cópia por professor; exportar/importar JSON | **Em validação** |
| 3. Duplas e motor paramétrico | 04–08/10 | Registro das duplas; empresa exclusiva por dupla; orientação .docx; gabarito de janeiro | **3a e 3b (janeiro) em validação** · fevereiro a fazer |
| 4. Central de documentos | 04/10 | Documentos de janeiro por dupla (NF-e, CT-e, NFS-e, faturas, RPA, contrato, auto), no site | **Janeiro em validação** |
| 5. Escrituração e auditoria | 04/10 | Área da dupla (código + matrícula), lançamentos, Diário, Razão, balancete e auditoria em 3 níveis contra o gabarito | **Janeiro em validação** |
| 6. Tutor e painel docente | 04–05/10 | Tutor socrático com IA local e base normativa (RAG), com bloqueio de respostas prontas; painel da turma com progresso e alertas | **Em validação** |
| 7. Fechamento para o Edital | 05–28/10 | Login com perfis, dados de demonstração, vídeo de 3–5 min, links públicos e congelamento da versão | **Login com perfis, Painel de Gestão/Learning Analytics e turma de demonstração em validação** · vídeo e congelamento a fazer |

> As datas são uma proposta e podem ser ajustadas. As etapas 3 a 6 entregam a versão mínima de cada módulo descrito no memorial (Seções 3.2 a 3.6), suficiente para demonstrar o fluxo completo de uma dupla.

---

## Etapa 1 — Cadastros acadêmicos (escopo)

### Incluído
1. **Disciplinas:** código, nome, nível, carga horária, departamento e observações. Permite incluir, alterar, excluir e buscar.
2. **Turmas** (de cada disciplina): período letivo, código, tipo, situação, horário, vigência, local, capacidade e número de matriculados informado pelo SIGAA. Permite incluir, alterar e excluir.
3. **Docentes:** nome, e-mail, SIAPE, departamento, formação e situação (ativo/inativo). Permite vincular e desvincular de turmas, informando a carga horária.
4. **Discentes:** matrícula (única), nome, e-mail, curso, turno e situação (ativo/inativo). Permite incluir em turmas e retirar delas. A situação na turma pode ser ATIVO, TRANCADO, CANCELADO ou DESISTENTE.
5. **Importação dos PDFs do SIGAA**, com prévia antes de gravar e histórico das importações:
   - *Consulta Geral de Turmas* → cria disciplinas, turmas e docentes;
   - *Lista de participantes (Turma Virtual)* → cria a turma, os docentes (com e-mail) e os discentes, inclusive os trancados.
   - A importação pode ser repetida sem duplicar registros: o sistema reconhece cada item pela matrícula, pelo código ou pelo nome.
6. **Painel inicial** com os totais e as últimas importações.
7. Estilo visual baseado no sistema *Monad* (refero.design): fundo pergaminho, títulos em serifa, interface em fonte monoespaçada e um único azul para a ação principal de cada tela.

### Fora desta etapa
- Login e perfis de acesso (previsto para a Etapa 7; até lá, a versão publicada fica protegida por usuário e senha únicos).
- Importação por planilha CSV/Excel.
- Edição em lote.

### Critérios de aceite
- [x] Importar `Turmas 2026.2.pdf` → 69 turmas e 49 disciplinas, sem avisos.
- [x] Importar as duas listas de participantes → 29 + 50 discentes, com os trancados identificados.
- [x] Reimportar o mesmo PDF não duplica nada.
- [x] Incluir, alterar e excluir em todos os cadastros, com confirmação antes de excluir.
- [ ] Validação pelo professor/equipe no servidor local.

### Observação sobre os dados
A lista de participantes da EH0012 se refere à **turma 03A de 2026.1**. A Consulta de Turmas é de 2026.2. Por isso, o sistema cria duas turmas 03A distintas, uma por período. Esse comportamento está correto.

---

## Etapa 3a — Duplas e geração das empresas (escopo)

Acesso: página da turma → **Duplas e empresas** (`/turmas/{id}/duplas`).

### Duplas (formação voluntária)
- Os discentes formam as duplas por conta própria e o professor as registra. Só aparecem discentes **ATIVOS** na turma.
- Duas formas de registrar: marcar 2 nomes na lista **Sem dupla**, ou colar várias duplas de uma vez (uma por linha, com matrículas ou nomes separados por `;` `,` `/` ou “ e ”).
- Cada discente participa de no máximo uma dupla por turma. Trio ou integrante sozinho são aceitos como exceção (máximo 3) e ficam sinalizados.
- O professor pode dar nome à dupla, incluir ou retirar integrantes e desfazer a dupla. A numeração reaproveita o primeiro número livre.
- A lista pode ser exportada em CSV (com a empresa e os totais de cada dupla).

### Geração das empresas
- O professor escolhe o **caso** (o caso-base ou a sua cópia) e o modo: só as duplas sem empresa; todas, mantendo o sorteio (para aplicar alterações feitas no caso); ou todas, com novo sorteio.
- Cada dupla recebe uma **semente**. Cada parâmetro é sorteado com uma chave própria (semente + parâmetro), dentro de [mínimo, máximo] e no passo definido. Com a mesma semente e o mesmo caso, os valores se repetem. Incluir um parâmetro não altera os demais.
- Regras de coerência já aplicadas:
  - produção de X e Y sorteada; coeficientes da ficha técnica com variação de ±1 (mínimo 1; a embalagem fica fixa);
  - compra de cada insumo = necessidade (ficha × produção) + sobra de 100 a 300 un; custo unitário sorteado na faixa do item;
  - venda = percentual sorteado da produção, sempre menor que a produção;
  - salários com variação por empregado, arredondados a R$ 10 e nunca abaixo do salário mínimo (R$ 1.621,00); HE e comissão só para quem já as tinha no caso;
  - pró-labore por função do sócio; mark-up recalculado com a margem sorteada.
- Página da empresa da dupla: resumo, produção e compras, folha, sócios e todos os parâmetros sorteados (base × faixa × valor da dupla). Ações: recalcular, novo sorteio, exportar JSON e excluir.

### Documento de orientação da dupla (.docx)
- Botão **Orientação (.docx)** na página da empresa e em cada dupla; **Baixar orientações (.zip)** gera os arquivos de todas as duplas da turma.
- O modelo é o próprio exercício-base (`dados/caso_base/modelo_orientacao_eh0012.docx`): mesma capa, índice, cabeçalho, tabelas e formatação. Na capa entram a empresa, a turma, a dupla e os integrantes.
- São trocados pelos valores da dupla: capital social (por extenso) e quadro de sócios; destinação do resultado (percentuais e quadro recalculado); balanço de abertura (capital e Banco Rico como conta de fechamento, Ativo = Passivo + PL); produção, ficha técnica e mark-up; pró-labore e folha de janeiro e fevereiro; contratos (C01 a C12, exceto o seguro C09, preso ao saldo de 2025); e os eventos com valores variáveis, com totais, consumos (kWh/m³), ICMS e multa do auto recalculados.
- Coerência: a compra de cada insumo é a necessidade da ficha técnica + sobra (MP-A também + devolução) ao custo sorteado no evento de compra; as vendas de ALPHA nunca superam estoque inicial + compras (a venda F26 é reduzida quando necessário e aparece como "ajustado").

## Etapa 3b — Gabarito de janeiro (entregue em 04/10, em validação)

- `app/gabarito.py` calcula os lançamentos dos 39 eventos de janeiro (J01–J39), a tesouraria diária (resgate automático do INVEST LIQUID e conta garantida com juros diários), os ajustes de fim de mês (seguro, recrutamento, rendimentos, juros do leasing) e a apuração (J40: ICMS, PIS, COFINS, IPI, IRPJ/CSLL por estimativa).
- `app/plano_contas.py`: plano do balanço/DRE de 2025 ampliado no mesmo padrão (contas novas sem dígito verificador).
- Telas: **Gabarito de janeiro** na empresa de cada dupla e aba **Gabarito de janeiro** no caso (valores do caso-base, para conferência). Planilha .xlsx com Diário, Balancete, Memória de cálculo e Premissas (com coluna "Validada?").
- 26 premissas (P01–P26) registram as decisões que o exercício não define; cada lançamento indica as premissas usadas.
- Testes: partidas dobradas, valores de referência do caso-base, fechamento do balancete em 15 sementes.

### Fica para depois
- Balanço de abertura por dupla (o Banco Rico fecha a equação patrimonial) e valores derivados dos 62 eventos.
- Gabarito contábil por dupla, que será usado na auditoria (Etapa 5).

### Critérios de aceite
- [x] Registrar duplas por seleção e em lote; recusar discente repetido, não ativo ou grupo com mais de 3.
- [x] Gerar empresas com valores dentro das faixas e reproduzíveis pela semente.
- [x] Recalcular aplica as alterações do caso sem mudar o sorteio.
- [ ] Validação pelo professor com a turma real.

---

## Etapa 4 — Central de documentos (janeiro, entregue em 04/10)

Onde fica: **Duplas** → turma → botão **Documentos** de cada dupla (ou **Documentos** na página da empresa da dupla).

- 17 documentos de janeiro gerados com os valores da dupla: contas de energia e água, faturas de telefonia/internet, NF-e de compra (ar-condicionados, ALPHA, MP-A), CT-e, NFS-e (comissão emitida pela empresa, reforma, contador), RPA, resumo do contrato de leasing e auto de infração.
- Os documentos mostram só dados de origem; o que o exercício manda a dupla calcular aparece como "a calcular pela dupla" (preço da NF-e 001 pelo mark-up, retenções do RPA e da reforma).
- Didáticos: emitentes e CNPJs fictícios (dígitos válidos), concessionárias sem marca real, marca d'água "sem valor fiscal". Navegação anterior/próximo e impressão pelo navegador.
- Os totais conferem com o gabarito (teste automático).

---

## Etapa 5 — Escrituração e auditoria (janeiro, entregue em 04/10)

**Professor:** Duplas → turma → seção **Acesso das duplas** → "Gerar códigos que faltam". Entregue a cada dupla o código e o endereço `https://labcont.io/aluno`. Em cada dupla aparecem o código, o percentual de eventos corretos e o botão **Escrituração** (auditoria detalhada: gabarito × dupla por conta, e a mensagem exibida à dupla).

**Dupla (área do aluno, `/aluno`, sem a senha do professor):** entra com o código da dupla + matrícula de um integrante. Menu: Painel (situação de cada evento), Documentos, Novo lançamento, Diário, Razão, Balancete, orientação (.docx).

- Lançamento: evento, data, histórico e quantas partidas forem necessárias (conta por código ou nome, débito/crédito, valor em formato brasileiro); só grava se débitos = créditos. Pode editar e excluir.
- **Correção só no fechamento do mês:** enquanto a dupla escritura, o painel mostra apenas "Lançado" ou "Pendente". A dupla envia o **Fechamento de janeiro** (com confirmação se houver eventos pendentes); só então vê a correção. Após o envio, a escrituração do mês fica bloqueada e a nota fica registrada. O professor pode **reabrir** o mês (o envio anterior fica no histórico) e vê a prévia da correção a qualquer momento.
- Auditoria por evento, comparando o efeito líquido por conta (débitos − créditos) com o gabarito — a dupla pode usar lançamentos compostos ou simples. Tolerância de R$ 0,05 por conta.
  - **Correto**; **Valor divergente** (contas certas, valor errado — mostra as contas); **Conta errada** (conta a mais ou no lado trocado — mostra quais; contas faltantes — só a quantidade, para não entregar a resposta); **Pendente**.
- Segurança: cookie assinado; cada dupla só vê e altera os próprios lançamentos; gabarito e telas do professor continuam atrás da senha.

---

## Etapa 6 — Tutor com IA local e painel da turma (entregue em 04/10)

**Dupla:** menu **Tutor** da área do aluno (também pelo botão "Tutor" de cada evento no Painel e "Perguntar ao tutor" em cada documento). Escolhe o evento (ou "Dúvida geral") e conversa.

- A IA roda **no próprio VPS** (Ollama ou servidor compatível com OpenAI); nenhum dado de aluno sai do servidor.
- Contexto enviado à IA: o evento, os documentos da dupla, os lançamentos da própria dupla e as regras do caso **já validadas** pelo professor. **O gabarito nunca é enviado.**
- Antes do fechamento o tutor não diz se o lançamento está certo nem entrega lançamento pronto (perguntas socráticas, ≤150 palavras). Depois do fechamento recebe só a mensagem de correção do evento e ajuda a dupla a entender o erro.
- Sem IA configurada (ou se ela falhar), responde com **roteiro** de perguntas-guia por tipo de evento — o site nunca fica sem tutor.
- Limite de 40 perguntas por dupla por dia; todas as mensagens ficam registradas com a matrícula de quem perguntou.

**Professor:** Duplas → turma → **Painel da turma** (também em Duplas → "Painel" e na página da turma).

- Situação da IA (ativa / modo roteiro e por quê), duplas com empresa, janeiros enviados, média dos enviados, total de perguntas.
- Tabela por dupla: eventos lançados, situação de janeiro, % correto (ou prévia), perguntas ao tutor, último acesso, botões Escrituração e Tutor.
- **Eventos com mais erros** (pelas correções dos fechamentos enviados) cruzados com o número de perguntas ao tutor — indica o que retomar em aula.
- Perguntas recentes e, por dupla, a conversa completa com o tutor (`/duplas/{id}/tutor`).

**Base normativa (RAG local):** menu **Normas** (professor e dupla).

- 50 fichas curtas, em texto próprio, com a fonte: Lei 6.404/76 (estrutura, PL, destinação do resultado), CPC 00, 06, 16, 25, 27, 33, 47 e 48, ITG 2000, LC 87/96 e alíquotas interestaduais (ICMS, DIFAL, antecipação parcial), RIPI, PIS/COFINS não cumulativos e Tema 69, retenções (IRRF, CSRF, INSS, ISS, RPA), folha, IRPJ/CSLL por estimativa.
- A cada pergunta, o servidor busca as 3 fichas mais relevantes (busca lexical BM25 com bônus para as fichas ligadas ao evento), envia ao tutor e acrescenta à resposta a linha **"Para consultar:"** com as fontes — a citação não depende do modelo.
- O professor testa a busca ("que fichas o tutor receberia para esta pergunta?"), edita, inclui e desativa fichas. Fichas padrão editadas não são sobrescritas nas atualizações; fichas novas do sistema entram automaticamente.
- As fichas trazem só a norma geral; as decisões do caso (premissas) continuam no gabarito e só chegam ao tutor depois de validadas.
- Proteções do tutor: antes do fechamento a IA não recebe os valores lançados pela dupla; um filtro no código bloqueia respostas com valores fora dos documentos ou com julgamento "certo/errado" (uma nova tentativa e, se falhar, pergunta-guia); o painel conta as respostas bloqueadas.

**Ligar a IA no VPS:** `bash /opt/labcont/app/deploy/configurar-ia.sh` — detecta o Ollama (container ou host), lista os modelos, grava `TUTOR_LLM_URL`/`TUTOR_LLM_MODEL` no `/opt/labcont/.env`, recria o app e testa de dentro do container. Chave, se houver, só no `.env`.

### Critérios de aceite
- [x] Tutor responde com IA local ou roteiro; histórico por evento; limite diário.
- [x] Contexto sem gabarito; comportamento diferente antes/depois do fechamento (testes).
- [x] Cada dupla vê só as próprias conversas; painel e conversas atrás da senha do professor.
- [x] IA local ligada no VPS (qwen2.5:3b) e testada com perguntas reais.
- [x] Base normativa com fontes citadas nas respostas.
- [ ] Revisão pedagógica das fichas e de uma amostra de respostas pelo professor.


---

## Etapa 7a — Login com perfis (entregue em 05/10)

Entrada da equipe em **/entrar** (login + senha); alunos em **/aluno** (matrícula + senha). A senha do HTTP Basic deixou de existir: o `APP_USUARIO`/`APP_SENHA` do `.env` criam só o primeiro administrador.

| Perfil | O que acessa |
|---|---|
| **Administrador** | Tudo, inclusive **Gestão → Operações em lote** (excluir lançamentos ou conversas de grupos, reabrir fechamentos, apagar senhas ou excluir discentes, sempre com prévia e confirmação) e **Histórico de ações**; reabre turma encerrada; marca turma de demonstração. |
| **Coordenador** | Disciplinas, docentes, discentes, turmas, importação do SIGAA, grupos de todas as turmas, caso-base, base normativa; cria usuários professor/monitor/visitante; encerra turmas. |
| **Professor** | Só as turmas em que está vinculado como docente: grupos, empresas, códigos, escrituração, tutor, painel; apaga a senha de aluno da turma. Consulta o caso-base e altera a **própria cópia** (inclusive validação das premissas). |
| **Monitor** | Turmas atribuídas, somente leitura, sem gabarito e sem e-mails. |
| **Visitante** | Avaliadores: somente leitura, apenas em turmas marcadas como **demonstração**; pode "ver como aluno". |
| **Aluno** | Área do próprio grupo. Primeiro acesso: matrícula + código do grupo + nova senha. Esqueceu a senha: o professor apaga e o aluno refaz o primeiro acesso. |

- Senhas com PBKDF2; usuários criados recebem **senha provisória** (troca obrigatória no primeiro acesso); bloqueio de 5 minutos após 5 tentativas erradas.
- **Ver como aluno**: equipe abre a área do grupo em modo somente leitura (botão em cada grupo e na escrituração).
- **Turma encerrada**: somente leitura para professor e alunos; só o administrador altera ou reabre.
- **Histórico**: toda gravação (inclusive entradas, lançamentos dos alunos e lotes) com quem, quando e onde.
- Perdeu a senha do único administrador: `docker exec labcont-app python -m app.redefinir_senha admin`.

### Critérios de aceite
- [x] Regras por perfil e por turma testadas (professor, coordenador, monitor, visitante, aluno, turma encerrada, lote, histórico).
- [ ] Cadastrar os usuários reais (professores) e testar com o próprio login.


---

## Etapa 7b — Painel de Gestão e Learning Analytics (Módulo 5 do memorial, entregue em 05/10)

**Painel de Gestão** (menu **Painel**, página inicial da equipe): todas as turmas do escopo do usuário com adesão (alunos com senha), progresso de janeiro, envios, acerto médio, perguntas ao tutor, notas homologadas, última atividade e aviso de turma parada (> 7 dias). Coordenação e admin veem também usuários ativos por perfil, cadastros, importações e (admin) ações recentes.

**Painel da turma** (`/turmas/{id}/painel`), calculado a partir dos dados do sistema:
- **Visão geral** por grupo, ordenada por risco: eventos lançados, % correto (oficial após o envio ou prévia), situação de janeiro, última atividade, perguntas e alertas.
- **Alertas precoces** (Rigo et al., 2014): sem acesso; inativo há 7+ dias; abaixo da metade da mediana da turma; travado em evento crítico (J18, J24, J27, J30, J40, TES) com 3+ perguntas ao tutor; prévia abaixo de 50%; busca de respostas prontas (3+ respostas bloqueadas); participação desigual (90%+ dos lançamentos de um integrante).
- **Matriz de calor** evento × grupo (✓ correto, ≈ valor, ✗ conta errada, · pendente) com perguntas ao tutor por célula; **dificuldades por tema** (% de erro, perguntas e bloqueios) e **contas com mais divergências** (faltou, sobrou, lado trocado, valor).
- **Engajamento** em 30 dias (lançamentos e perguntas por dia) e participação de cada integrante.
- Monitor vê o painel sem a correção antecipada (prévia) e sem as contas divergentes.

**Notas de janeiro** (`/turmas/{id}/notas`): nota proposta pelo sistema após o envio — 10 × (corretos × 1 + valor divergente × 0,5) ÷ eventos do mês —, ajuste de participação qualitativa e observação por aluno, homologação em lote (e desfazer), exportação CSV. O aluno vê a nota no painel dele só depois de homologada.

### Critérios de aceite
- [x] Alertas, matriz, temas, engajamento, notas e homologação testados.
- [ ] Revisar com o professor os limites dos alertas e o critério da nota.


---

## Etapa 7c — Turma de demonstração (entregue em 05/10)

**Gestão → Turma de demonstração** (admin) ou, no servidor, `docker exec labcont-app python -m app.demo`.

- Turma **EH0012 · DEMO** com 20 alunos e 10 grupos **fictícios** (matrículas 9000xx, nenhum dado real), marcada como demonstração, com docente fictício.
- Cada grupo em um estágio, para o painel mostrar tudo: 01 completo e correto (enviado, nota homologada); 02 completo com erros (enviado); 03 quase completo; 04 travado no leasing (J24); 05 um integrante faz tudo; 06 parou há 12 dias; 07 muitos erros de conta; 08 insiste em respostas prontas; 09 nunca entrou; 10 completo com poucos erros (enviado, homologado).
- Lançamentos e conversas distribuídos nos últimos dias (gráfico de engajamento); conversas geradas pelo roteiro do próprio sistema, com as fontes da base normativa.
- Acessos criados com senha gerada na hora (mostrada uma vez): **avaliador** (visitante, somente leitura), **professor.demo** (professor da turma) e um aluno do grupo 03. Recriar apaga tudo da turma DEMO e gera senhas novas.

### Critérios de aceite
- [x] Criação, recriação e exclusão testadas; visitante entra e não altera; aluno de demonstração entra.
- [ ] Criar a demonstração no servidor e registrar o acesso do avaliador no formulário do edital.

---

## Ajustes rápidos da verificação (item 7.1 do relatório de 05/10)

- **A1 · DRE, Balanço e encerramento:** menu **DRE e BP** na área do aluno (a partir dos lançamentos da dupla) e botão **DRE e Balanço** na escrituração do professor (dupla × gabarito). Estrutura do CPC 26; prévia da ARE (não gravada, pois no Lucro Real anual o resultado de janeiro fica em balancete de suspensão).
- **A2 · Conferência imediata (Informativo / Aviso / Erro estrutural):** datas fora de janeiro, data diferente da do evento, histórico curto, lançamento repetido, conta patrimonial com saldo invertido, banco negativo em algum dia. Não compara com o gabarito. Aparece no painel do aluno, na mensagem após gravar e na escrituração do professor.
- **A3 · Base normativa:** fichas novas CPC26-01 (balanço), CPC26-02 (DRE), ICMS-08 (alíquota interna de 20% no Ceará, Lei 12.670/1996 alterada pela Lei 18.305/2023) e ISS-FOR (Código Tributário de Fortaleza, LC 159/2013). Fichas padrão não editadas passam a ser atualizadas automaticamente.
- **A4 · Tempo até o envio:** do primeiro lançamento ao fechamento, por grupo, por turma e no Painel de Gestão.
- **A5 · Privacidade (LGPD):** página `/privacidade`, link no rodapé e ciência obrigatória no primeiro acesso do aluno (registrada no histórico). Contato configurável em `APP_CONTATO_PRIVACIDADE` no `.env`.
- **A6 · Sem marcas reais:** Enel e Cagece substituídas por concessionárias fictícias nos eventos do caso (inclusive nos casos já cadastrados), nos documentos, nos históricos do gabarito e no modelo da orientação .docx.
- **A7 · Repositório público:** `python deploy/exportar_publico.py` atualiza https://github.com/Henriquerabelo/labcont-ai-ai a partir da pasta `LABCONT-AI Publico`, sem dados pessoais, sem arquivos internos e sem o IP do servidor.

### Base normativa com artigos (05/10)

- **CTM de Fortaleza (LC 159/2013, atualizado até a LC 452/2025)**, conferido no texto consolidado:
  - **ISS-FOR**: fato gerador independe do recebimento (art. 223, § 2º, III), contribuinte (229), base (240), alíquotas 2/3/5% (245).
  - **ISS-FOR-02**: retenção pelo tomador (arts. 230, 232, 233, 236, 237, 239).
  - **ISS-FOR-03**: construção civil, materiais fora da base, alíquota de 3% e local da obra (arts. 224, § 1º, III; 240, §§ 4º e 5º; 245, II).
  - **ISS-FOR-04**: autônomo, valor fixo anual ou retenção (arts. 233, IV; 246 a 248).
- **ICMS-09 · Como consultar o RICMS-CE:**
  - Livro I: Decreto 33.327/2019;
  - Livro II: Decreto 35.061/2022;
  - Livro IV: Decreto 34.605/2022;
  - remanescentes do Decreto 24.569/1997;
  - portal Sefaz Legis.
- **P12 corrigida:** a premissa P12 (reforma do galpão, J26) passou de ISS 5% para **3%** sobre a mão de obra (art. 245, II, do CTM, subitem 7.2; materiais fora da base pelo art. 240, § 4º, I). O exercício manda consultar a alíquota específica do serviço. A NFS-e da Construtor Express também mostra 3%. No caso-base o ISS retido da 1ª parcela cai de R$ 3.420,00 para R$ 2.052,00. Como o gabarito é calculado na hora, todas as duplas já veem o valor novo.

---

## Etapa 8 · Fevereiro (em 5 partes)

Decisões do professor (05/10): fevereiro completo, em etapas; **os dois meses livres desde o início**, cada um com o seu fechamento; a escrituração de fevereiro **continua a do próprio grupo**: os saldos de abertura vêm dos lançamentos de janeiro da dupla, e a correção continua sendo feita por evento.

### 8a · Mês no sistema e eventos sem produção

- **Meses:**
  - `app/periodos.py`: o mês sai do código do evento (J.., TES, AJ = janeiro; F.., FTES, FAJ = fevereiro).
  - Na área do aluno, o seletor **Jan | Fev** fica no menu e o mês escolhido é lembrado.
  - Painel, lançar, diário, balancete (abertura = 31/12/2025 + janeiro do grupo), DRE e BP (acumulado), documentos, tutor e conferência imediata funcionam por mês.
  - A data do lançamento precisa estar no mês do evento.
- **Fechamento por mês:**
  - O envio de fevereiro é independente do de janeiro.
  - Enviar um mês bloqueia só esse mês.
  - O professor reabre cada mês separadamente.
  - A operação em lote "Reabrir" vale para os dois meses.
- **Equipe (abas Janeiro/2026 | Fevereiro/2026):**
  - Escrituração do grupo, gabarito (tela e .xlsx), DRE e Balanço, painel da turma (Learning Analytics) e notas (homologação por mês).
  - A tela de grupos mostra o andamento de fevereiro; o Painel de Gestão mostra o progresso dos dois meses e os envios de janeiro e de fevereiro.
- **Gabarito de fevereiro** (`gerar_gabarito(valores, "2026-02")`):
  - Roda janeiro e continua dos saldos de 31/01.
  - Eventos prontos: F01–F03, F06–F09, F11–F19, F24, F25, F27, F29–F33, F37–F43, F45–F47.
  - Os demais ficam "em preparação": podem ser lançados, mas ficam fora da correção.
  - FTES e FAJ ficam provisórios até a 8e.
  - Um evento sem nada a lançar (ex.: aplicação sem saldo) conta como correto se o grupo não lançar nada.
- **Premissas novas P27–P37** (a validar):
  - pagamentos da competência 01 pelos saldos de 31/01; IRRF e CSRF de 12/2025 sem evento de pagamento;
  - CIF e utilidades com área industrial;
  - Ar Frio 45% e NF 23.456 30%;
  - reforma concluída e transferida para Edifícios;
  - parcela SAC do leasing com juros desde 20/01 e reclassificação longo → curto prazo;
  - mútuo à sócia no Realizável a Longo Prazo, com juros por fração diária;
  - recrutamento com IRRF 1,5% e sem CSRF (SC Disit/SRRF08 8.048/2018);
  - contador reajustado;
  - VT e VA de março;
  - rendimentos e resgate.
- **Plano de contas:**
  - CIF a apropriar (energia, água, telefones e internet);
  - Água e Esgoto - Vendas;
  - Mútuo a Receber - sócia (Realizável a Longo Prazo);
  - Juros Ativos - Mútuo.
- **Documentos de fevereiro:** energia, água, telefonia, NFS-e 003 (comissão), contrato de mútuo, NFS-e 6.320 (reforma), NFS-e 345 (recrutamento), NFS-e 024 (contador).
- **Turma de demonstração:** os grupos que enviaram janeiro já têm parte de fevereiro lançada.
- **Testes:** `tests/test_fevereiro.py`; 63 passando.

### 8b · Compras de insumos, devolução e estoques (custo médio ponderado móvel)

- **Eventos com gabarito:**
  - F05: NF 12.380, MP-B, Tocantins. IPI de 13%, ICMS de 12%, desconto financeiro condicional e CT-e 424.110.
  - F10: NF 9.147, materiais secundários Z, Q, R e K, Rio de Janeiro. Fornecedor distribuidor, sem IPI, ICMS de 7% e frete CIF.
  - F22: NF 1.747, ME-H, Amazonas. ICMS de 12% e CT-e 425.130.
  - F23 e F35: pagamento dos CT-e.
  - F28: NF 004, devolução de MP-A (CFOP 6.201).
- **IPI pela TIPI 2022 (ADE RFB nº 1/2026):**
  - MP-A 9,75%; MP-B 13%; MS-Z 9,75%; MS-Q 13%; MS-R 9,75%; MS-K 3,25%; ME-H 9,75%;
  - Produto X 9,75% e Produto Y 19,5%, para as vendas da 8d.
- **Estoques:**
  - uma conta por insumo;
  - a memória de cálculo mostra a ficha de cada item (quantidade, saldo e custo médio) depois de cada entrada, frete ou devolução.
- **Contas novas:**
  - estoques de MP-B, MS-Z, MS-Q, MS-R, MS-K e ME-H;
  - fornecedores Indústria Zalego, Distribuidor Verde Oliva e Embalagens Comerciais;
  - Descontos Financeiros Obtidos.
- **Premissas P38–P42** (a validar):
  - quem destaca o IPI;
  - ICMS interestadual de 12% ou 7%, sem antecipação parcial nem DIFAL para insumos;
  - desconto condicional como receita financeira, obtido sobre a parcela à vista;
  - fretes FOB no custo (pagamento do CT-e 424.110 sem juros);
  - custo médio e devolução pelo custo da compra.
- **Documentos:** NF-e 12.380 com CT-e 424.110, NF-e 9.147, NF-e 1.747 com CT-e 425.130 e NF-e 004 de devolução, que a dupla emite e na qual calcula os impostos.
- **Base normativa:** ficha EST-06 (devolução de compra) e fichas de estoque, ICMS e IPI ligadas aos eventos de fevereiro (59 fichas).
- **Testes:** 65 passando. Janeiro conferido sem alterações.

### 8c · Folha, depreciação e produção de X e Y

A folha (F20) e a depreciação (F21) passaram para esta etapa porque são processadas em 13/02, antes da produção, e compõem o custo de X e Y.

- **F20 · Folha de fevereiro:**
  - 15 empregados e pró-labores; mesmos critérios de janeiro.
  - A mão de obra direta dos setores X e Y, com encargos, provisões e VT/VA, vai para "Mão de Obra Direta a Apropriar" de cada produto.
  - A mão de obra indireta e o pró-labore do sócio industrial (Marconde Sobreira) vão para o CIF.
  - Renato Português está sem salário no caso: o gabarito usa o salário mínimo até a decisão do professor.
- **F21 · Depreciação de fevereiro:**
  - Rateio do quadro de alocação: prédio 10/25/65, máquinas 100% industrial, utilitário 70/30, móveis 45/35/20.
  - As máquinas do leasing depreciam desde fevereiro.
  - A parcela industrial vai para o CIF.
- **FP1 · 19/02 · Requisição de materiais:**
  - Ficha técnica × produção do mês, pelo custo médio de cada insumo.
  - Os insumos vão para Produtos em Elaboração X e Y.
- **FP2 · 23/02 · Fim da produção (19, 20 e 23/02, três dias úteis):**
  - MOD e CIF apropriados aos produtos em elaboração; o CIF é rateado pelo custo dos materiais diretos.
  - Transferência para Produtos Acabados.
  - A memória de cálculo mostra o custo total e o unitário de cada produto.
- **Contas novas:**
  - CIF (mão de obra indireta, pró-labore industrial, depreciação);
  - MOD a apropriar (X e Y);
  - Produtos em Elaboração (X e Y);
  - Produtos Acabados (X e Y).
- **Premissas P43–P47** (a validar).
- **Documentos:**
  - requisição de materiais (OP 001/2026), com as quantidades por insumo e produto;
  - boletim de produção (novo tipo "Produção").
- **Base normativa:** fichas CUS-01 (custo de produção), CUS-02 (custeio por absorção, RIR/2018, art. 302) e CUS-03 (rateio do CIF e produtos em elaboração); 62 fichas.
- **Tutor:** roteiro de produção.
- **Turma de demonstração:** sorteio próprio para fevereiro (não altera o janeiro dos grupos).
- **Testes:** 67 passando; janeiro inalterado.

### 8d · Vendas, devolução e recebimento

- **F04 · NF 337 — ALPHA a consumidor final em São Luís-MA, PIX:**
  - preço pelo mark-up;
  - ICMS interestadual de 12% e DIFAL de 11% (alíquota modal do MA de 23% desde 23/02/2025) como dedução da receita, a recolher ao MA;
  - CMV pelo custo médio.
- **F26 · NF 003 — ALPHA à Comercial Caribe (CE):** ICMS de 20%, boleto em 28/02.
- **F36 · NF 1.320 — devolução de ALPHA:**
  - pelo preço da NF 003, como dedução da receita (devoluções de vendas);
  - estorno de ICMS, PIS e COFINS;
  - retorno ao estoque pelo custo da saída;
  - abatida do boleto.
- **F44 · Recebimento da Caribe:** valor líquido da devolução.
- **F34 · NF 005 — Produtos X e Y à Comercial Roma (PA):**
  - preço pelo mark-up sobre o custo de produção;
  - IPI por fora (X 9,75%, Y 19,5%), fora da receita e da base do ICMS;
  - ICMS de 12%;
  - desconto financeiro de 3% sobre o Y como despesa financeira;
  - 80% recebidos na emissão e 20% em 22/03;
  - CPV pelo custo médio dos produtos acabados.
- **Contas novas:**
  - Receita da Venda de Produtos de Fabricação Própria;
  - (−) Devoluções de Vendas;
  - (−) ICMS DIFAL sobre Vendas;
  - ICMS DIFAL a Recolher - MA;
  - Custo dos Produtos Vendidos;
  - Descontos Financeiros Concedidos.
- **Premissas P48–P52** (a validar).
- **Documentos:** NF-e 337, 003 e 005, que a dupla emite e na qual calcula preço e impostos, e NF-e 1.320 de devolução, emitida pelo cliente.
- **Base normativa:**
  - fichas ICMS-10 (DIFAL na venda a consumidor final), IPI-02 (IPI na venda de produção própria) e VEN-01 (devolução de venda);
  - EST-03 passa a tratar também do desconto concedido;
  - 65 fichas.
- **Falta (8e):** F48 (apuração de fevereiro), FTES e FAJ.
- **Testes:** 68 passando; janeiro inalterado.

### 8e · Apuração de fevereiro e mês completo

- **F48 · Apuração (28/02, depois dos ajustes de fim de mês):**
  - crédito do ICMS antecipado de 01/2026, pago em 26/02;
  - compensação de débitos e créditos de ICMS, IPI, PIS e COFINS; saldo credor fica a recuperar;
  - DIFAL do MA e ISS próprio informados à parte;
  - IRPJ e CSLL por estimativa: revenda líquida de devoluções e venda de produtos a 8%/12%, serviços a 32%, receitas financeiras integrais, adicional de 10% acima de R$ 20.000,00;
  - compensação do IRRF retido.
- **Tesouraria (FTES) e ajustes (FAJ) definitivos:** fevereiro não tem mais eventos "em preparação", e todos os 52 entram na correção.
- **Conta garantida acima do limite:**
  - Entre as compras de insumos (a partir de 04/02) e o recebimento da venda de X e Y (24/02), o saldo devedor passa do limite contratado (R$ 970 mil).
  - A memória de cálculo sinaliza o excesso, conforme a premissa P55: decisão do professor.
- **Premissas P53–P55** (a validar).
- **Base normativa:** fichas de apuração, tesouraria e ajustes ligadas aos eventos F48, FTES e FAJ.
- **Testes:** 69 passando. Janeiro conferido sem alterações nos 6 cenários; fevereiro fecha em todos.

---

## Exercício revisado pelo professor (PDF de 07/10/2026)

Conferência completa em `Inconsistencias do Exercicio EH0012 - conferencia 07-10.docx`. Das 20 inconsistências, 3 foram corrigidas, 3 em parte, 13 seguem e 1 depende da planilha de apoio. O protótipo foi alinhado ao que foi corrigido:

- **Dividendos:** 50% do lucro líquido ajustado; antes eram 60%. A faixa de sorteio vai de 25% a 50%. Afeta a J01 (P24).
- **Balanço de abertura:**
  - ICMS a recolher passa a 43.361,80 e a depreciação acumulada a 10.408,34;
  - o gabarito deixa de ter a diferença de R$ 0,01 e fecha em zero nos dois meses (caso-base e 20 sementes).
- **Seguro:** 3 parcelas (16/11, 16/12 e 17/01). A J21 passa a "3ª e última parcela"; o valor não muda (R$ 2.100,00).
- **Renato Português:** salário de R$ 2.120,00 em fevereiro, no lugar do salário mínimo provisório (P43). Muda a folha (F20), a MOD e o custo do Produto X.
- **Água e energia:**
  - água de janeiro rateada entre administrativa (210) e comercial (380); antes ia toda para a administrativa;
  - energia de fevereiro com a área administrativa (530);
  - água de fevereiro com a industrial: Produto X 610 e Produto Y 570 (P19, P29).
- **Orientação .docx (modelo):**
  - tabelas de água e energia completas;
  - tabela de bens com R$ 262.000,00;
  - total da NF 9.147, seguro em 3 parcelas, resgate da aplicação de 05/01 e salário do Renato;
  - Balanço com os subtotais acertados (o PDF ainda traz dois subtotais com R$ 0,01 de diferença).
- **Inconsistências do caso:** "Energia e água" e "Imobilizado" ficam como RESOLVIDA. "Seguro", "Aplicações", "Folha" e "Materiais secundários" são atualizadas. Entra a nova "Balanço de 31/12/2025 (versão de 07/10)".
- **Bancos já existentes** (`app/ajuste_exercicio.py`):
  - na primeira subida, os casos cadastrados recebem as mesmas correções, só onde o valor ainda é o antigo;
  - as empresas das duplas desses casos são recalculadas com a mesma semente;
  - a turma de demonstração deve ser recriada.
- **Testes:** 76 passando (novo `tests/test_exercicio_revisado.py`).

---

## Página inicial de apresentação (07/10/2026)

- **Quem vê:**
  - quem chega a `/` sem login vê a apresentação do sistema (`app/templates/apresentacao.html`), também disponível em `/apresentacao`;
  - a equipe logada continua indo ao Painel de Gestão, e o aluno à área do grupo.
- **Conteúdo, aprovado a partir do memorial:**
  - o problema pedagógico (cinco limitações do formato tradicional);
  - benefícios para aluno, professor e curso;
  - como as soluções foram criadas (problema → solução → como funciona);
  - como o sistema foi desenvolvido;
  - telas de exemplo.
- **Acesso:** apenas o botão **Entrar**, no canto superior direito, que leva à tela de entrada (Equipe / Sou aluno).
- **Telas:** capturas reais da turma de demonstração em `app/static/img/apresentacao/` (área do grupo, documento, tutor, painel da turma; .webp). O aviso de "tutor em modo roteiro" do ambiente de testes foi retirado da captura do painel.
- **Estilo:** bloco "Página inicial" no fim do `style.css` (classes `ap-*`, paleta Rubelita). Funciona no celular, sem rolagem lateral.

---

## Decisões do professor sobre as inconsistências (11/10/2026)

Aplicadas a partir da coluna "Correção" da conferência e das respostas aos pontos em aberto.

- **Caso-base (JSON, `gerar_caso_base.py`):**
  - comodatos: internet R$ 410,00 e celulares R$ 580,00 (C07, C08);
  - mútuo à sócia de R$ 30.000,00, faixa de 20.000 a 45.000 (C10, F27);
  - Contador Formado **S/A**, honorários pagos no dia 10;
  - recrutamento com pagamento único em 26/02, na emissão da NFS-e 345;
  - datas dos eventos: leasing 19/01 (J24), auto de infração 05/02 com redução de 70% da multa (F06), contabilidade 10/02 (F17);
  - eventos em fim de semana passam para o dia útil seguinte (seguro 19/01; CDB 12/01, já assim no caso);
  - Ar Frio: pagamento de 40% (F11);
  - encargos de 28,80% (FPAS 507, RAT 3%);
  - dependentes de fevereiro iguais aos de janeiro;
  - 21 inconsistências: 15 RESOLVIDA, 4 MANTIDA (frete MP-A, NF 23.456, comissões, Balanço) e 2 PENDENTE (vendas ALPHA, materiais secundários).
- **Gabarito:**
  - encargos 28,80% (P16, P18);
  - F11 com 40% (P30);
  - F27 pelo valor do contrato C10;
  - F41 paga a NFS-e 345 na emissão (janeiro + fevereiro − IRRF; P34);
  - NFS-e 024 com vencimento em 10/03;
  - nova premissa P56: comissões recebidas com atraso, sem juros nem multa (J25, F13).
- **Documentos:**
  - NF 7.852 emitida em 05/01 (entrada em 08/01);
  - NF 23.456 emitida em 24/01 (entrada em 26/01);
  - NFS-e 345 com vencimento em 26/02;
  - Contador S/A;
  - leasing liberado em 19/01.
- **Orientação .docx (modelo):** as mesmas correções. As linhas do leasing, do auto e da NFS-e 023 foram movidas para a nova data.
- **Bancos existentes:**
  - `ajuste_exercicio.aplicar_1110` roda uma vez e só troca valores ainda antigos;
  - inconsistências em PENDENTE recebem a decisão;
  - as decisões que o professor já tenha registrado no sistema são mantidas;
  - as empresas das duplas são recalculadas.
- **Conferência:**
  - caso-base e 20 duplas sorteadas fecham em janeiro e fevereiro com diferença 0;
  - resultado do caso-base em jan–fev: R$ 11.255.742,78.
- **Testes:** 80 passando (novo `tests/test_correcoes_1110.py`).

---

## Correções da análise completa do exercício (11/10/2026)

Itens 5 e 6 do relatório "Analise Completa do Exercicio EH0012 - 11-10.docx".

- **Sistema (item 5):**
  - **S1:** a orientação passa a atualizar a tabela de telefonia de fevereiro com os valores da dupla. A âncora antiga pegava a linha do vale-transporte de 30/01.
  - **S2:** o contrato de leasing (documento J24-1) fica datado de 19/01.
  - **S3:** custos unitários do caso-base com a precisão do exercício (até 8 casas). As NF 3.369, 23.456, 12.380, 9.147 e 1.747 reproduzem os totais do PDF. Nas notas, o valor unitário aparece com 4 a 8 casas (filtro `nu`).
  - **S4:** salário de fevereiro da Ângela igual ao salário mínimo de 2026 (R$ 1.621,00).
  - **S5:** valor do mútuo formatado nos casos atualizados.
- **Texto do exercício (item 6, modelo da orientação e caso):**
  - **T1:** CDB realizado em 12/01.
  - **T2:** TIF n.º 20260001/00 nos dois eventos.
  - **T3:** CT-e 423.951 sem vencimento (frete CIF pago pelo fornecedor).
  - **T4:** CT-e 424.110 emitido em 04/02.
  - **T5:** celular com vencimento em 09/02 e 09/03.
  - **T6:** telefone fixo com vencimento em 14/01 e 13/02, as datas de pagamento (P26).
  - **T7:** um parágrafo por evento em 27/02.
  - **T8:** quadro de prazos com a Turma 01A em 06/11/2026 e períodos "Janeiro/2026" e "Fevereiro/2026".
  - **T9:** boleto da NF 001 em 28/01; NF 003 citada como de 19/02, com boleto em 27/02.
- **Inconsistências:** 24 itens: 19 RESOLVIDA, 4 MANTIDA e 1 PENDENTE (materiais secundários). Entraram três itens novos: Telefonia, CT-e 424.110 e Quadro de prazos.
- **Bancos existentes:** `ajuste_exercicio.aplicar_1110b` roda uma vez, só troca valores ainda antigos e recalcula as empresas.
- **Conferência:**
  - 51 empresas fecham com diferença 0;
  - a turma de demonstração mantém os perfis;
  - 86 testes passando (novo `tests/test_analise_1110.py`).

---

## Fechamento: três turmas de demonstração (19/10/2026)

- **Turmas:** a demonstração passa a ter três turmas da EH0012, uma por professor da disciplina em 2026.2 (horários do SIGAA):
  - DEMO-01A, Danival Sousa Cavalcante;
  - DEMO-02A, Eduardo Rodrigues Linhares;
  - DEMO-03A, Rosângela Venâncio Nunes.
- **Grupos:** cada turma tem 20 alunos fictícios (matrículas 9000101 a 9000320) em 10 grupos, com os mesmos perfis de antes. A DEMO-01A reproduz a turma anterior (sementes 900–909).
- **Acessos:**
  - visitante `avaliador`, que vê as três turmas;
  - professores `danival.demo`, `eduardo.demo` e `rosangela.demo`, cada um com a sua turma;
  - um aluno por turma (grupo 03).
- **Docentes:** se o professor já está cadastrado, a turma usa o cadastro existente.
- **Onde fica:** Gestão → Demonstração, ou `python -m app.demo` no servidor.
- **Limpeza dos dados atuais:** fica para quando o responsável confirmar o que será apagado.
- **Testes:** 87 passando.

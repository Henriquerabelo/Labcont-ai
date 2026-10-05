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
- **A7 · Repositório público anônimo:** `python deploy/exportar_publico.py` gera a pasta `LABCONT-AI Publico` sem dados pessoais, sem arquivos internos, sem o nome do repositório privado nem o IP do servidor e com metadados dos .docx limpos.

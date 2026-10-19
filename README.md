# LABCONT-AI

Protótipo funcional apresentado ao **Prêmio Inteligência Artificial e Formação Universitária** (Cátedra Luíza de
Teodoro/UFC, Edital nº 1/2026, Categoria III – Soluções Tecnológicas), para a disciplina **Laboratório de Prática
Contábil (EH0012)** da FEAAC/UFC.

- **Site de demonstração:** https://labcont.io (acesso de avaliador informado na proposta; três turmas com dados fictícios)
- **Módulos:** empresa exclusiva por dupla (motor paramétrico) · central de documentos · escrituração (Diário, Razão,
  balancete, DRE e Balanço) · auditoria contra o gabarito da dupla, com conferência imediata e correção no
  fechamento mensal · tutor socrático com IA executada localmente e base normativa com fontes · Painel de Gestão e
  Learning Analytics · login com perfis

Este repositório contém o código. Nenhum dado pessoal é versionado: listas de alunos e configurações do servidor
ficam fora do Git (LGPD).

## Executar localmente

```
cp .env.example .env
docker compose up -d --build
```
Abra http://localhost:8000. Sem usuários cadastrados, o sistema abre em modo local de testes.
Turmas de demonstração: `docker compose exec app python -m app.demo`.

## Testes

```
pip install -r requirements.txt
pytest
```
(requer um PostgreSQL de testes; veja `deploy/ci.yml`).

## Estrutura
- `app/` aplicação FastAPI (rotas em `app/routers`, telas em `app/templates`)
- `app/geracao.py` motor paramétrico · `app/gabarito.py` gabarito por dupla · `app/auditoria.py` e `app/consistencia.py` auditoria
- `app/demonstracoes.py` DRE e Balanço · `app/tutor.py` tutor e filtro pedagógico · `app/normas.py` base normativa
- `app/analytics.py` Learning Analytics · `app/acesso.py` perfis e histórico
- `dados/caso_base/` caso-base do exercício (empresa fictícia) · `tests/` testes automáticos
- `ETAPAS.md` registro das etapas do desenvolvimento

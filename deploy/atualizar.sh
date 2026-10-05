#!/usr/bin/env bash
# Atualiza o LABCONT-AI no VPS quando houver versão nova aprovada nos testes.
# Executado a cada minuto pelo systemd (labcont-atualizar.timer).
# Use "atualizar.sh --forcar" para reconstruir mesmo sem mudanças.
set -euo pipefail
BASE=/opt/labcont
SRC=$BASE/app
cd "$SRC"

# A branch "producao" só recebe commits que passaram nos testes do GitHub Actions.
# Sem ela (testes ainda não configurados), usa a branch principal do repositório (main ou master).
RAMO=producao
if ! git ls-remote --exit-code --heads origin producao >/dev/null 2>&1; then
  RAMO=$(git ls-remote --symref origin HEAD | awk '/^ref:/ {sub("refs/heads/", "", $2); print $2}')
  RAMO=${RAMO:-main}
fi

git fetch -q origin "$RAMO"
ATUAL=$(git rev-parse HEAD)
NOVO=$(git rev-parse "origin/$RAMO")
if [[ "$ATUAL" == "$NOVO" && "${1:-}" != "--forcar" ]]; then
  exit 0
fi

echo "[$(date '+%F %T')] Atualizando $ATUAL -> $NOVO ($RAMO)"
git reset -q --hard "origin/$RAMO"
# Traefik em "network_mode: host" alcança o app pela rede interna do LABCONT-AI;
# nos demais casos, o app também entra na rede do Traefik.
TRAEFIK_NETWORK=$(grep -E '^TRAEFIK_NETWORK=' "$BASE/.env" | cut -d= -f2- || true)
ARQUIVOS=(-f deploy/docker-compose.prod.yml)
if [[ -n "$TRAEFIK_NETWORK" && "$TRAEFIK_NETWORK" != "host" ]]; then
  ARQUIVOS+=(-f deploy/compose.rede-traefik.yml)
  export TRAEFIK_DOCKER_NETWORK="$TRAEFIK_NETWORK"
else
  export TRAEFIK_DOCKER_NETWORK=labcont_interna
fi
# IA local em outra rede Docker (ex.: container do Ollama): o app também entra nessa rede.
IA_NETWORK=$(grep -E '^IA_NETWORK=' "$BASE/.env" | cut -d= -f2- || true)
if [[ -n "$IA_NETWORK" ]]; then
  ARQUIVOS+=(-f deploy/compose.rede-ia.yml)
  export IA_NETWORK
fi
docker compose -p labcont --env-file "$BASE/.env" "${ARQUIVOS[@]}" up -d --build --remove-orphans
docker image prune -f >/dev/null
echo "[$(date '+%F %T')] Publicado: $(git log -1 --format='%h %s')"

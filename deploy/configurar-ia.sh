#!/usr/bin/env bash
# Liga o Tutor do LABCONT-AI à IA local do VPS (Etapa 6).
#
# Uso (no VPS, como root):
#   bash /opt/labcont/app/deploy/configurar-ia.sh            # detecta a IA e pergunta o modelo
#   bash /opt/labcont/app/deploy/configurar-ia.sh qwen2.5:7b # já informando o modelo
#
# O que faz:
#   1. procura a IA local: container do Ollama ou serviço no próprio host (portas 11434, 1234, 8080);
#   2. lista os modelos instalados e escolhe um;
#   3. grava TUTOR_LLM_URL, TUTOR_LLM_MODEL (e IA_NETWORK, se preciso) em /opt/labcont/.env;
#   4. recria o app e testa a conexão de dentro do container.
# Nada é enviado para fora do servidor. Se a IA exigir chave, edite TUTOR_LLM_KEY direto no .env
# (nunca cole a chave em chats ou no GitHub).
set -euo pipefail
BASE=/opt/labcont
ENV="$BASE/.env"
MODELO="${1:-}"
[[ -f "$ENV" ]] || { echo "Não encontrei $ENV. Rode antes o setup-vps.sh."; exit 1; }

def_env() {  # def_env CHAVE VALOR  -> grava/substitui no .env
  if grep -qE "^$1=" "$ENV"; then sed -i "s|^$1=.*|$1=$2|" "$ENV"; else echo "$1=$2" >> "$ENV"; fi
}

URL=""; REDE=""; TIPO=""
echo "== Procurando a IA local"
# 1) container do Ollama
CONT=$(docker ps --format '{{.Names}} {{.Image}}' | awk 'tolower($2) ~ /ollama/ && tolower($2) !~ /webui/ {print $1; exit}')
if [[ -n "$CONT" ]]; then
  MODO=$(docker inspect -f '{{.HostConfig.NetworkMode}}' "$CONT")
  echo "   container Ollama: $CONT (rede: $MODO)"
  TIPO=ollama
  if [[ "$MODO" == "host" ]]; then
    URL="http://host.docker.internal:11434"
  else
    REDE=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' "$CONT" | awk '{print $1}')
    URL="http://$CONT:11434"
  fi
fi
# 2) serviço no host (Ollama instalado direto, LM Studio, llama.cpp…)
if [[ -z "$URL" ]]; then
  if curl -fsS -m 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    TIPO=ollama; URL="http://host.docker.internal:11434"; echo "   Ollama no host (porta 11434)"
  else
    for P in 1234 8080; do
      if curl -fsS -m 3 "http://127.0.0.1:$P/v1/models" >/dev/null 2>&1; then
        TIPO=openai; URL="http://host.docker.internal:$P/v1"; echo "   servidor compatível com OpenAI na porta $P"; break
      fi
    done
  fi
fi
[[ -n "$URL" ]] || { echo "Não encontrei a IA local. Rode 'docker ps' e 'ss -ltnp' e me diga o nome do container ou a porta."; exit 1; }

echo "== Modelos instalados"
if [[ "$TIPO" == ollama ]]; then
  if [[ -n "$CONT" ]]; then LISTA=$(docker exec "$CONT" ollama list 2>/dev/null | awk 'NR>1 {print $1}')
  else LISTA=$(curl -fsS http://127.0.0.1:11434/api/tags | python3 -c 'import json,sys;[print(m["name"]) for m in json.load(sys.stdin)["models"]]'); fi
else
  P=$(echo "$URL" | sed -E 's|.*:([0-9]+)/v1|\1|')
  LISTA=$(curl -fsS "http://127.0.0.1:$P/v1/models" | python3 -c 'import json,sys;[print(m["id"]) for m in json.load(sys.stdin)["data"]]')
fi
[[ -n "$LISTA" ]] || { echo "A IA não tem modelos instalados (ex.: docker exec $CONT ollama pull qwen2.5:7b)."; exit 1; }
nl -w2 -s'. ' <<< "$LISTA"
if [[ -z "$MODELO" ]]; then
  read -rp "Número do modelo para o tutor [1]: " N
  MODELO=$(sed -n "${N:-1}p" <<< "$LISTA")
fi
echo "   modelo escolhido: $MODELO"

def_env TUTOR_LLM_URL "$URL"
def_env TUTOR_LLM_MODEL "$MODELO"
grep -qE '^TUTOR_LLM_KEY=' "$ENV" || echo "TUTOR_LLM_KEY=" >> "$ENV"
if [[ -n "$REDE" && "$REDE" != "labcont_interna" ]]; then def_env IA_NETWORK "$REDE"; else sed -i '/^IA_NETWORK=/d' "$ENV"; fi

echo "== Recriando o app"
bash "$BASE/app/deploy/atualizar.sh" --forcar
sleep 5

echo "== Testando de dentro do container labcont-app"
docker exec -i labcont-app python - <<'PY'
import asyncio
from app import tutor
st = asyncio.run(tutor.status_ia())
print("   OK: tutor ligado à IA local." if st["ok"] else f"   FALHOU: {st['motivo']}. Modelos vistos: {st.get('modelos')}")
if st["ok"]:
    r = asyncio.run(tutor.chamar_ia([{"role": "user", "content": "Responda só: pronto"}], timeout=180))
    print("   resposta de teste:", (r or "(vazia)")[:80])
PY
echo "Se falhou com Ollama instalado direto no host: ele escuta só em 127.0.0.1."
echo "Ajuste com: systemctl edit ollama  ->  [Service] Environment=OLLAMA_HOST=0.0.0.0  -> systemctl restart ollama"
echo "(e mantenha a porta 11434 fechada no firewall para a internet)."

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

ENV_TEMPLATE_DIRS=(. gateway ms_data ms_dijkstra ms_mcp ms_metier ms_predictive)
OLLAMA_URL="http://localhost:11435"
OLLAMA_MODEL="qwen2.5:7b"

BOLD="\033[1m"; DIM="\033[2m"; GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; RESET="\033[0m"

step()  { printf "\n${BOLD}==> %s${RESET}\n" "$1"; }
ok()    { printf "  ${GREEN}[OK]${RESET}       %s\n" "$1"; }
skip()  { printf "  ${DIM}[IGNORÉ]${RESET}   %s\n" "$1"; }
create(){ printf "  ${YELLOW}[NOUVEAU]${RESET}  %s\n" "$1"; }
fail()  { printf "  ${RED}[ÉCHEC]${RESET}    %s\n" "$1"; }

# Check des prérequis (docker, git)
step "Vérification des prérequis"
for bin in docker git curl; do
  if command -v "$bin" >/dev/null 2>&1; then
    ok "$bin trouvé"
  else
    fail "$bin est requis mais n'est pas installé"
    exit 1
  fi
done
if docker compose version >/dev/null 2>&1; then
  ok "plugin docker compose trouvé"
else
  fail "docker compose (plugin v2) est requis"
  exit 1
fi

# Copie colle .env.example dans .env dans les dossier où ils ne sont pas présents
step "Configuration des fichiers d'environnement"
for dir in "${ENV_TEMPLATE_DIRS[@]}"; do
  example="$dir/.env.example"
  target="$dir/.env"
  [ -f "$example" ] || continue
  if [ -f "$target" ]; then
    skip "$target existe déjà"
  else
    cp "$example" "$target"
    create "$target créé à partir de .env.example"
  fi
done

# démarrage des conteneurs
step "Démarrage de la stack Docker"
docker compose up -d --build
ok "docker compose up terminé"

# Pull du modèle Ollama via l'API HTTP (skip si déjà présent) : plus fiable que `docker exec ... ollama`, dont le binaire ne se trouve pas toujours
# dans $PATH selon l'image utilisée (ex. la variante Intel iGPU en local).
step "Vérification du modèle Ollama ($OLLAMA_MODEL)"
ollama_ready=false
for _ in $(seq 1 30); do
  if curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
    ollama_ready=true
    break
  fi
  sleep 2
done

if [ "$ollama_ready" = false ]; then
  fail "l'API Ollama ($OLLAMA_URL) ne répond pas"
elif curl -s "$OLLAMA_URL/api/tags" | grep -qF "\"$OLLAMA_MODEL\""; then
  skip "$OLLAMA_MODEL déjà téléchargé"
else
  create "téléchargement de $OLLAMA_MODEL (cela peut prendre du temps)..."
  if curl -s -X POST "$OLLAMA_URL/api/pull" -d "{\"name\":\"$OLLAMA_MODEL\"}" | tail -n1 | grep -qF '"status":"success"'; then
    ok "$OLLAMA_MODEL téléchargé"
  else
    fail "échec du téléchargement de $OLLAMA_MODEL"
  fi
fi

# sommaire & affichage des ports des apis
get_var() {
  local file="$1" key="$2" default="$3"
  [ -f "$file" ] && grep -E "^${key}=" "$file" | tail -n1 | cut -d= -f2- || true
  [ -f "$file" ] || echo "$default"
}
val() {
  local v
  v="$(get_var "$1" "$2" "")"
  echo "${v:-$3}"
}

GATEWAY_PORT="$(val .env GATEWAY_PORT 3000)"
API_PORT="$(val .env API_PORT 8080)"
METIER_PORT="$(val .env METIER_PORT 8007)"
DATA_PORT="$(val .env PORT 8004)"
PREDICTIVE_PORT="$(val .env PREDICTIVE_PORT 8005)"
POSTGRES_PORT="$(val .env POSTGRES_PORT 5434)"
POSTGRES_PREDICTIVE_PORT="$(val .env POSTGRES_PREDICTIVE_PORT 5435)"

step "Installation terminée — adresses des services"
printf "  %-28s http://localhost:%s\n" "Gateway (point d'entrée)" "$GATEWAY_PORT"
printf "  %-28s http://localhost:%s/docs\n" "ms_dijkstra (energia-api)" "$API_PORT"
printf "  %-28s http://localhost:%s/docs\n" "ms_metier" "$METIER_PORT"
printf "  %-28s http://localhost:8003/docs\n" "ms_mcp"
printf "  %-28s http://localhost:%s/docs\n" "ms_data" "$DATA_PORT"
printf "  %-28s http://localhost:%s/docs\n" "ms_predictive" "$PREDICTIVE_PORT"
printf "  %-28s http://localhost:8081\n" "frontend"
printf "  %-28s http://localhost:11435\n" "Ollama"
printf "  %-28s localhost:%s\n" "postgres (ms_data)" "$POSTGRES_PORT"
printf "  %-28s localhost:%s\n" "postgres (predictive)" "$POSTGRES_PREDICTIVE_PORT"
printf "\n${DIM}En utilisation normale, envoyer les requêtes uniquement à la Gateway.${RESET}\n"

#!/usr/bin/env bash
# run_dashboard.sh — arranca el dashboard con recarga automática y caché limpia.
#
# Cada arranque:
#   1. carga las variables de `.env`
#   2. limpia la caché de Python (__pycache__ / *.pyc) del proyecto
#   3. levanta uvicorn con `--reload` (recarga al editar el código)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

PORT="${APP_PORT:-8100}"
HOST="${APP_HOST:-0.0.0.0}"
RELOAD="${APP_RELOAD:-true}"

if [ ! -x ./venv/bin/uvicorn ]; then
  echo "ERROR: falta ./venv. Ejecuta: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

# --- Limpiar caché de Python (excepto el venv) ---
echo "[run_dashboard] Limpiando caché de Python…"
find "$SCRIPT_DIR" -path "$SCRIPT_DIR/venv" -prune -o -type d -name "__pycache__" -print0 \
  | xargs -0 -r rm -rf
find "$SCRIPT_DIR" -path "$SCRIPT_DIR/venv" -prune -o -type f -name "*.pyc" -print0 \
  | xargs -0 -r rm -f

# --- Flags de recarga (por defecto activados) ---
RELOAD_FLAGS=()
if [ "$RELOAD" = "true" ]; then
  RELOAD_FLAGS=(--reload --reload-dir "$SCRIPT_DIR" --reload-exclude "venv/*" --reload-exclude "logs/*" --reload-exclude "*.pyc")
  echo "[run_dashboard] Recarga automática ACTIVADA (APP_RELOAD=true)"
else
  echo "[run_dashboard] Recarga automática desactivada (APP_RELOAD=false)"
fi

echo "[run_dashboard] http://localhost:${PORT}"
exec ./venv/bin/uvicorn web.app:app \
  --host "$HOST" --port "$PORT" \
  ${RELOAD_FLAGS[@]+"${RELOAD_FLAGS[@]}"}

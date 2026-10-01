#!/usr/bin/env bash
# run_check_score_freshness.sh — watchdog de frescura del score de mercado (cron H).
#
# Comprueba que fact_market_score_agg reciba ciclos: si el último es más antiguo
# que el umbral, sale con 5 para que el cron avise. Detecta un persist_score
# caído en ~10 min en lugar de en horas.
#
# Uso: ./run_check_score_freshness.sh [--max-edad-min N] [--dry-run]
#
# Salidas: 0 fresco · 1 error · 2 argumentos · 3 BD no configurada
#          4 precondición local (falta .env / venv / logs no escribible) · 5 rancio
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Precondiciones ruidosas -------------------------------------------------
# Un fallo aquí NO debe pasar en silencio: es justo el modo de fallo que dejó
# el score 16 h sin actualizarse sin que nadie se enterara.
if [ ! -f .env ]; then
  echo "ERROR: falta .env en $SCRIPT_DIR — el job no puede leer la configuracion de BD." >&2
  exit 4
fi

set -a
. ./.env
set +a

if [ ! -x ./venv/bin/python ]; then
  echo "ERROR: falta ./venv/bin/python. Ejecuta: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 4
fi

LOG_DIR="${FILE_PATH_LOG:-./logs}"
mkdir -p "$LOG_DIR"
if [ ! -w "$LOG_DIR" ]; then
  echo "ERROR: $LOG_DIR no es escribible por $(id -un). Revisa dueno y permisos." >&2
  exit 4
fi

exec ./venv/bin/python jobs/check_score_freshness.py "$@"

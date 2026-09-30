#!/usr/bin/env bash
# run_persist_score.sh — lanza el job de persistencia del score (cron H).
# Uso: ./run_persist_score.sh [--cycle|--backfill --since <ISO>|--dry-run]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

if [ ! -x ./venv/bin/python ]; then
  echo "ERROR: falta ./venv. Ejecuta: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

ARGS=("$@")
if [ ${#ARGS[@]} -eq 0 ]; then
  ARGS=(--cycle)
fi

exec ./venv/bin/python jobs/persist_score.py "${ARGS[@]}"

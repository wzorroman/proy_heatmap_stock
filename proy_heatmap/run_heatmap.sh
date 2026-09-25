#!/bin/bash

# run_heatmap.sh - v1.2 (F3.9)
# Script para ejecutar el scraper del heatmap con gate de NYSE.
#
# F3.9: cron cada 15 min alineado a :00/:15/:30/:45 + ~20 s -> 28 snapshots por sesión.
# NO está registrado en crontab todavía (se ejecuta manualmente con el venv).
# Para activarlo luego:
#   */15 * * * 1-4 /home/wilson/CODE_MAIN/.../proy_heatmap/run_heatmap.sh
#   Ajustar también --delay-start para alinear a :00/:15/:30/:45 [+20s].

# ============================================
# CONFIGURACIÓN INICIAL Y CARGA DE ENTORNO
# ============================================

# Auto-detectar PROJECT_DIR (directorio donde está este script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"

ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

SERVER_ID="${SERVER_ID:-WZ-PC}"

HEATMAP_SCRIPT="$PROJECT_DIR/scrapper_heatmap_v1.py"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
LOG_DIR="$PROJECT_DIR/logs_ejecucion"
DELAY_START=20   # F3.9: +20 s para alinear a :00/:15/:30/:45

mkdir -p "$LOG_DIR"
EXEC_LOG="$LOG_DIR/heatmap_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$EXEC_LOG"
}

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === HEATMAP SCRAPER (gate NYSE) ===" | tee -a "$EXEC_LOG"

# F3.9: pausa inicial para alinear el ciclo al cuarto de hora +20 s.
log "Pausa inicial de ${DELAY_START}s para alinear a :00/:15/:30/:45..."
sleep "$DELAY_START"

if [ ! -f "$VENV_PYTHON" ]; then
    log "ERROR: no se encontró $VENV_PYTHON"
    exit 1
fi
if [ ! -f "$HEATMAP_SCRIPT" ]; then
    log "ERROR: no se encontró $HEATMAP_SCRIPT"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1
log "Ejecutando: $VENV_PYTHON $HEATMAP_SCRIPT (DB_WRITE_ENABLED=$DB_WRITE_ENABLED)"
"$VENV_PYTHON" "$HEATMAP_SCRIPT" >> "$EXEC_LOG" 2>&1
EXIT_CODE=$?
log "Finalizado con código $EXIT_CODE"

# Limpieza: conservar 7 archivos de log como máximo (F3.6 analogía al calendario)
ls -1t "$LOG_DIR"/heatmap_*.log 2>/dev/null | tail -n +8 | xargs -r rm -f

exit $EXIT_CODE
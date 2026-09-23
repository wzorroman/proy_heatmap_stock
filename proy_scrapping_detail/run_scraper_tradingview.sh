#!/bin/bash

# run_scraper_tradingview.sh - v3.1.0
# Script para ejecutar el scraper de TradingView V5
# Cambios: apunta a scraper_live_tradingview_v5.py, verificación BD, seed de dim_asset

# ============================================
# CONFIGURACIÓN INICIAL Y CARGA DE ENTORNO
# ============================================

# Auto-detectar PROJECT_DIR (directorio donde está este script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"

ENV_FILE="./.env"

# Cargar variables del archivo .env si existe
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

SERVER_ID="${SERVER_ID:-WZ-PC}"

# ============================================
# CONFIGURACIÓN
# ============================================

SCRAPER_SCRIPT="$PROJECT_DIR/scraper_live_tradingview_v5.py"
SEED_SCRIPT="$PROJECT_DIR/seed_symbols.py"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
ENV_FILE="$PROJECT_DIR/.env"
LOG_DIR="$PROJECT_DIR/logs_ejecucion"
EXEC_LOG="$LOG_DIR/scraper_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

# ============================================
# FUNCIONES
# ============================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$EXEC_LOG"
}

get_python_cmd() {
    # Esta función SOLO devuelve el path de Python, sin logs
    if [ -f "$VENV_PYTHON" ]; then
        echo "$VENV_PYTHON"
        return 0
    elif [ -f "/usr/bin/python3" ]; then
        echo "/usr/bin/python3"
        return 0
    else
        return 1
    fi
}

check_directories() {
    log "🔍 Verificando directorios y archivos..."

    if [ ! -d "$PROJECT_DIR" ]; then
        log "❌ ERROR: Directorio no encontrado: $PROJECT_DIR"
        exit 1
    fi

    if [ ! -f "$SCRAPER_SCRIPT" ]; then
        log "❌ ERROR: Script no encontrado: $SCRAPER_SCRIPT"
        exit 1
    fi

    local PYTHON_CMD=$(get_python_cmd)
    if [ -z "$PYTHON_CMD" ]; then
        log "❌ ERROR: No se encontró Python"
        exit 1
    fi

    log "✅ Usando Python: $PYTHON_CMD"
    echo "$PYTHON_CMD"
}

load_env_vars() {
    if [ -f "$ENV_FILE" ]; then
        log "📁 Cargando variables de entorno desde: $ENV_FILE"
        set -a
        source "$ENV_FILE"
        set +a
    fi
}

check_db_connection() {
    if [ "$DB_WRITE_ENABLED" = "true" ]; then
        log "🗄️ Modo BD activo — verificando conexión a $BD_HEATMAP_DATABASE"

        "$PYTHON_CMD" -c "
from db.postgresql_connection import PostgreSQLConnector
import config
db = PostgreSQLConnector(config.PG_HOST, config.PG_PORT, config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD)
if db.connect():
    print('✅ Conexión BD exitosa')
    db.disconnect()
else:
    print('❌ Error conectando a BD')
    exit(1)
" >> "$EXEC_LOG" 2>&1

        if [ $? -ne 0 ]; then
            log "⚠️ BD no disponible — continuando en modo CSV legacy"
            export DB_WRITE_ENABLED=false
        fi
    else
        log "📁 Modo legacy: solo CSV (DB_WRITE_ENABLED=false)"
    fi
}

run_seed_symbols() {
    if [ "$DB_WRITE_ENABLED" = "true" ]; then
        log "🌱 Ejecutando seed_symbols (solo altas nuevas en dim_asset)..."
        "$PYTHON_CMD" "$SEED_SCRIPT" >> "$EXEC_LOG" 2>&1
        if [ $? -ne 0 ]; then
            log "⚠️ seed_symbols falló — continuando (el pipeline BD omitirá símbolos ausentes)"
        else
            log "✅ seed_symbols OK (idempotente: cubre solo símbolos nuevos)"
        fi
    fi
}

check_directorios_datos() {
    local DATOS_DIR="$PROJECT_DIR/DATOS_LIVE"

    # Verificar que existen los directorios críticos
    local DIRS_CRITICOS=(
        "$DATOS_DIR/NASDAQ-QQQ"
        "$DATOS_DIR/OANDA-XAUUSD"
        "$DATOS_DIR/OANDA-EURUSD"
    )

    for dir in "${DIRS_CRITICOS[@]}"; do
        if [ ! -d "$dir" ]; then
            log "📁 Creando directorio: $(basename $dir)"
            mkdir -p "$dir"
        fi
    done

    log "✅ Directorios de datos verificados"
}

run_scraper() {
    local PYTHON_CMD=$1

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 [$SERVER_ID] Ejecutando TRADINGVIEW SCRAPER V5..." | tee -a "$EXEC_LOG"
    echo "=======================================" | tee -a "$EXEC_LOG"
    log "   Script: $(basename $SCRAPER_SCRIPT)"
    log "   BD_WRITE_ENABLED: $DB_WRITE_ENABLED"

    cd "$PROJECT_DIR" || {
        log "❌ ERROR: No se puede acceder a $PROJECT_DIR"
        return 1
    }

    log "   Inicio: $(date '+%H:%M:%S')"

    # Ejecutar scraper
    "$PYTHON_CMD" "$SCRAPER_SCRIPT" >> "$EXEC_LOG" 2>&1
    EXIT_CODE=$?

    log "   Fin: $(date '+%H:%M:%S') - Código: $EXIT_CODE"

    if [ $EXIT_CODE -eq 0 ]; then
        log "✅ Scraper completado exitosamente"
    else
        log "❌ Scraper falló con código: $EXIT_CODE"
        log "   Revisa el log completo para más detalles"
    fi

    return $EXIT_CODE
}

check_resultados() {
    local DATOS_DIR="$PROJECT_DIR/DATOS_LIVE"

    log "📊 Verificando archivos generados..."

    local ARCHIVOS_CRITICOS=(
        "$DATOS_DIR/NASDAQ-QQQ/NASDAQ-QQQ.csv"
        "$DATOS_DIR/OANDA-XAUUSD/OANDA-XAUUSD.csv"
        "$DATOS_DIR/OANDA-EURUSD/OANDA-EURUSD.csv"
    )

    local OK_COUNT=0
    for archivo in "${ARCHIVOS_CRITICOS[@]}"; do
        if [ -f "$archivo" ]; then
            local LINEAS=$(wc -l < "$archivo" | tr -d ' ')
            if [ "$LINEAS" -gt 1 ]; then
                log "   ✅ $(basename $archivo): $LINEAS líneas"
                OK_COUNT=$((OK_COUNT + 1))
            else
                log "   ⚠️  $(basename $archivo): archivo vacío"
            fi
        else
            log "   ❌ $(basename $archivo): NO ENCONTRADO"
        fi
    done

    log "   📈 Archivos críticos OK: $OK_COUNT/3"

    local TOTAL_CSVS=$(find "$DATOS_DIR" -name "*.csv" -not -path "*/calendario_economico/*" 2>/dev/null | wc -l)
    log "   📊 Total archivos CSV (excluyendo calendario): $TOTAL_CSVS"
}

cleanup_old_logs() {
    local DIAS_MANTENER=2
    log "🧹 Limpiando logs antiguos (más de $DIAS_MANTENER días)..."

    find "$LOG_DIR" -name "scraper_*.log" -type f -mtime +$DIAS_MANTENER -delete 2>/dev/null
    log "   Limpieza completada"
}

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

main() {
    echo "======================================="
    echo "📊 TRADINGVIEW SCRAPER V5 - LIVE DATA"
    echo "======================================="

    log "📝 Log: $(basename $EXEC_LOG)"

    # Obtener Python cmd
    PYTHON_CMD=$(get_python_cmd)
    if [ -z "$PYTHON_CMD" ]; then
        log "❌ ERROR: No se encontró Python"
        exit 1
    fi

    # Verificar todo
    check_directories >/dev/null

    # Cargar variables
    load_env_vars

    # Verificar conexión BD (degrada a legacy si no está disponible)
    check_db_connection

    # Seed de dim_asset (solo altas nuevas; no-op si ya están cubiertos)
    run_seed_symbols

    # Verificar directorios de datos
    check_directorios_datos

    # Ejecutar scraper
    echo ""
    run_scraper "$PYTHON_CMD"
    EXIT_CODE=$?

    # Verificar resultados
    echo ""
    check_resultados

    # Limpiar logs
    echo ""
    cleanup_old_logs

    # Resumen
    echo ""
    log "📋 RESUMEN: Código $EXIT_CODE"
    echo "======================================="

    exit $EXIT_CODE
}

# Ejecutar
main "$@"
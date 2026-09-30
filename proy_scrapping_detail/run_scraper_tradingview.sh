#!/bin/bash

# run_scraper_tradingview.sh - v3.1.1
# Script para ejecutar el scraper de TradingView V5
# Cambios: apunta a scraper_live_tradingview_v5.py, verificación BD, seed de dim_asset
# v3.1.1: raíz de datos vía FILES_OUTPUT_SCRAPPING (mismo fallback que config.py)

# ============================================
# CONFIGURACIÓN INICIAL Y CARGA DE ENTORNO
# ============================================

# Auto-detectar el directorio donde está este script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Cargar el .env del propio proyecto (no "./.env", relativo al CWD)
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# PROJECT_DIR se reafirma DESPUÉS del .env a propósito: el .env de este repo
# trae PROJECT_DIR apuntando al repo padre, que no contiene ni el script ni el
# venv (check_directories abortaba ahí). Override explícito: PROJECT_DIR_OVERRIDE.
PROJECT_DIR="${PROJECT_DIR_OVERRIDE:-$SCRIPT_DIR}"

SERVER_ID="${SERVER_ID:-WZ-PC}"

# ============================================
# CONFIGURACIÓN
# ============================================

SCRAPER_SCRIPT="$PROJECT_DIR/scraper_live_tradingview_v5.py"
SEED_SCRIPT="$PROJECT_DIR/seed_symbols.py"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
LOG_DIR="$PROJECT_DIR/logs_ejecucion"
EXEC_LOG="$LOG_DIR/scraper_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

# ============================================
# RUTAS DE DATOS
# ============================================

# Raíz de las series del radar. Misma fuente que scraper_live_tradingview_v5.py:
# env var FILES_OUTPUT_SCRAPPING y, si falta, dentro de la carpeta del proyecto.
init_rutas() {
    DATOS_DIR="${FILES_OUTPUT_SCRAPPING:-$PROJECT_DIR/DATOS_LIVE}"
}

init_rutas

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
        # El .env trae PROJECT_DIR apuntando al repo padre (no contiene ni el
        # script ni el venv): reafirmarlo para que el venv, los imports locales
        # (db, config) y el fallback de rutas resuelvan en este proyecto.
        PROJECT_DIR="${PROJECT_DIR_OVERRIDE:-$SCRIPT_DIR}"
        # El .env puede traer FILES_OUTPUT_SCRAPPING: recalcular la raíz.
        init_rutas
    fi
    # Normalizar el flag de BD: config.py acepta 'True'/'TRUE' (.lower() == 'true'),
    # pero aquí se compara literalmente contra "true". Sin esto, un 'True' del
    # .env deja la verificación de BD desactivada mientras Python SÍ escribe en BD.
    DB_WRITE_ENABLED="$(printf '%s' "${DB_WRITE_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')"
    export DB_WRITE_ENABLED
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
    log "📁 Raíz de datos: $DATOS_DIR"

    # La raíz debe existir y ser escribible por el usuario que corre el scraper.
    # Sin esto, el ciclo muerde en el primer símbolo con PermissionError.
    if [ ! -d "$DATOS_DIR" ]; then
        log "📁 Creando raíz de datos: $DATOS_DIR"
        if ! mkdir -p "$DATOS_DIR"; then
            log "❌ ERROR: no se pudo crear $DATOS_DIR (¿permisos en $(dirname "$DATOS_DIR")?)"
            return 1
        fi
    fi

    if [ ! -w "$DATOS_DIR" ]; then
        log "❌ ERROR: $DATOS_DIR no es escribible por $(id -un)"
        log "   Archivos con dueño/permisos:"
        log "   $(ls -ld "$DATOS_DIR" 2>&1)"
        log "   Sustituye el dueño o ajusta permisos, p.ej.:"
        log "   sudo chown -R $(id -un):$(id -gn) \"$DATOS_DIR\""
        return 1
    fi

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

    # `heatmap/` (universo del heatmap) y `calendario_economico/` no son series del radar.
    local TOTAL_CSVS=$(find "$DATOS_DIR" -name "*.csv" -not -path "*/calendario_economico/*" -not -path "*/heatmap/*" 2>/dev/null | wc -l)
    log "   📊 Total archivos CSV (series del radar): $TOTAL_CSVS"
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

    # Situarse en el proyecto ANTES de cualquier import local (db, config).
    # check_db_connection ejecuta `python -c`, y en ese modo sys.path[0] es el
    # CWD: si cron arranca el script desde otro directorio, `import db` falla y
    # la BD se marca falsamente como no disponible (DB_WRITE_ENABLED=false).
    cd "$PROJECT_DIR" || {
        log "❌ ERROR: No se puede acceder a $PROJECT_DIR"
        exit 1
    }

    # Cargar variables
    load_env_vars

    # Verificar conexión BD (degrada a legacy si no está disponible)
    check_db_connection

    # Seed de dim_asset (solo altas nuevas; no-op si ya están cubiertos)
    run_seed_symbols

    # Verificar directorios de datos (aborta si la raíz no es escribible)
    if ! check_directorios_datos; then
        log "❌ No se puede escribir en la raíz de datos — se omite el ciclo"
        log "📋 RESUMEN: Código 1"
        exit 1
    fi

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
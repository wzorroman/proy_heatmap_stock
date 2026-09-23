#!/bin/bash

# run_calendario_tradingview.sh - v3.1.0
# Script para ejecutar el calendario económico de TradingView
# Correcciones: rutas DATOS_LIVE_CALENDARIO, verificación BD, PROJECT_DIR auto-detectado

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

CALENDARIO_SCRIPT="$PROJECT_DIR/calendario_tradingview_live_v5.py"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
ENV_FILE="$PROJECT_DIR/.env"
LOG_DIR="$PROJECT_DIR/logs_ejecucion"
EXEC_LOG="$LOG_DIR/calendario_$(date +%Y%m%d_%H%M%S).log"

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

    if [ ! -f "$CALENDARIO_SCRIPT" ]; then
        log "❌ ERROR: Script no encontrado: $CALENDARIO_SCRIPT"
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

check_directorio_calendario() {
    # CORRECCIÓN v3.1.0: DATOS_LIVE_CALENDARIO (no DATOS_LIVE)
    local CALENDARIO_DIR="$PROJECT_DIR/DATOS_LIVE_CALENDARIO/calendario_economico"

    if [ ! -d "$CALENDARIO_DIR" ]; then
        log "📁 Creando directorio calendario_economico..."
        mkdir -p "$CALENDARIO_DIR"
    fi

    if [ ! -d "$CALENDARIO_DIR/logs" ]; then
        mkdir -p "$CALENDARIO_DIR/logs"
        log "📁 Creando directorio de logs del calendario"
    fi

    log "✅ Directorios del calendario verificados ($CALENDARIO_DIR)"
}

run_calendario() {
    local PYTHON_CMD=$1

    log "🚀 Ejecutando CALENDARIO ECONÓMICO TRADINGVIEW..."
    log "   Script: $(basename $CALENDARIO_SCRIPT)"

    cd "$PROJECT_DIR" || {
        log "❌ ERROR: No se puede acceder a $PROJECT_DIR"
        return 1
    }

    log "   Inicio: $(date '+%H:%M:%S')"

    "$PYTHON_CMD" "$CALENDARIO_SCRIPT" >> "$EXEC_LOG" 2>&1
    EXIT_CODE=$?

    log "   Fin: $(date '+%H:%M:%S') - Código: $EXIT_CODE"

    if [ $EXIT_CODE -eq 0 ]; then
        log "✅ Calendario completado exitosamente"
    else
        log "❌ Calendario falló con código: $EXIT_CODE"
        log "   Revisa el log completo para más detalles"
    fi

    return $EXIT_CODE
}

check_resultados() {
    # CORRECCIÓN v3.1.0: DATOS_LIVE_CALENDARIO
    local CALENDARIO_DIR="$PROJECT_DIR/DATOS_LIVE_CALENDARIO/calendario_economico"
    local EVENTOS_FILE="$CALENDARIO_DIR/eventos_calendario.csv"

    log "📊 Verificando archivos generados..."

    if [ -f "$EVENTOS_FILE" ]; then
        local LINEAS=$(wc -l < "$EVENTOS_FILE" | tr -d ' ')
        local EVENTOS=$((LINEAS - 1))
        [ $EVENTOS -lt 0 ] && EVENTOS=0
        log "   ✅ eventos_calendario.csv: $EVENTOS eventos"
    else
        log "   ❌ eventos_calendario.csv: NO ENCONTRADO"
    fi

    if [ -f "$CALENDARIO_DIR/checkpoint.json" ]; then
        log "   ✅ checkpoint.json: presente"
    fi

    if [ -d "$CALENDARIO_DIR/logs" ]; then
        local LOGS_COUNT=$(ls -1 "$CALENDARIO_DIR/logs"/calendario_*.log 2>/dev/null | wc -l)
        if [ "$LOGS_COUNT" -gt 0 ]; then
            log "   📋 Logs disponibles: $LOGS_COUNT archivos"
        fi
    fi
}

cleanup_old_logs() {
    local DIAS_MANTENER=2
    log "🧹 Limpiando logs antiguos (más de $DIAS_MANTENER días)..."

    # Logs de ejecución
    find "$LOG_DIR" -name "calendario_*.log" -type f -mtime +$DIAS_MANTENER -delete 2>/dev/null

    # Logs del calendario
    local CALENDARIO_LOG_DIR="$PROJECT_DIR/DATOS_LIVE_CALENDARIO/calendario_economico/logs"
    if [ -d "$CALENDARIO_LOG_DIR" ]; then
        find "$CALENDARIO_LOG_DIR" -name "calendario_*.log" -type f -mtime +$DIAS_MANTENER -delete 2>/dev/null
    fi

    log "   Limpieza completada"
}

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

main() {
    echo "=======================================" | tee -a "$EXEC_LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 📅 [$SERVER_ID] CALENDARIO ECONÓMICO TRADINGVIEW v3.1.0" | tee -a "$EXEC_LOG"
    echo "=======================================" | tee -a "$EXEC_LOG"

    log "📝 Log: $(basename $EXEC_LOG)"

    # Obtener Python cmd (SIN LOGS)
    PYTHON_CMD=$(get_python_cmd)
    if [ -z "$PYTHON_CMD" ]; then
        log "❌ ERROR: No se encontró Python"
        exit 1
    fi

    # Verificar todo
    check_directories >/dev/null

    # Cargar variables
    load_env_vars

    # Verificar conexión BD (si está habilitado)
    check_db_connection

    # Verificar directorios del calendario
    check_directorio_calendario

    # Ejecutar calendario
    echo ""
    run_calendario "$PYTHON_CMD"
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
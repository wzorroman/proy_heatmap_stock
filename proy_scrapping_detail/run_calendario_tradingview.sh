#!/bin/bash

# run_calendario_tradingview.sh - v3.1.1
# Script para ejecutar el calendario económico de TradingView
# Correcciones: rutas DATOS_LIVE_CALENDARIO, verificación BD, PROJECT_DIR auto-detectado
# v3.1.1: raíz del calendario vía FILES_OUTPUT_CALENDAR (mismo fallback que config.py)

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

CALENDARIO_SCRIPT="$PROJECT_DIR/calendario_tradingview_live_v5.py"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
LOG_DIR="$PROJECT_DIR/logs_ejecucion"
EXEC_LOG="$LOG_DIR/calendario_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

# ============================================
# RUTAS DE DATOS
# ============================================

# Raíz del calendario. Misma fuente que calendario_tradingview_live_v5.py:
# env var FILES_OUTPUT_CALENDAR y, si falta, dentro de la carpeta del proyecto.
init_rutas() {
    CALENDARIO_DATA_DIR="${FILES_OUTPUT_CALENDAR:-$PROJECT_DIR/DATOS_LIVE_CALENDARIO}"
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
        # El .env trae PROJECT_DIR apuntando al repo padre (no contiene ni el
        # script ni el venv): reafirmarlo para que el venv, los imports locales
        # (db, config) y el fallback de rutas resuelvan en este proyecto.
        PROJECT_DIR="${PROJECT_DIR_OVERRIDE:-$SCRIPT_DIR}"
        # El .env puede traer FILES_OUTPUT_CALENDAR: recalcular la raíz.
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

fix_permissions_calendario() {
    # Si un proceso root dejó el CSV/checkpoint con dueño root, el cron como
    # appuser falla con PermissionError al intentar hacer overwrite. Normalizar
    # la propiedad del árbol del calendario antes de la captura.
    local CALENDARIO_DIR="$CALENDARIO_DATA_DIR/calendario_economico"
    local EVENTOS_FILE="$CALENDARIO_DIR/eventos_calendario.csv"
    local CHECKPOINT_FILE="$CALENDARIO_DIR/checkpoint.json"

    if [ "$(id -un)" = "appuser" ] && [ -d "$CALENDARIO_DIR" ]; then
        if [ -f "$EVENTOS_FILE" ] || [ -f "$CHECKPOINT_FILE" ]; then
            if [ ! -w "$EVENTOS_FILE" ] || [ ! -w "$CHECKPOINT_FILE" ]; then
                log "🔐 Corrigiendo permisos del calendario para appuser..."
                chown -R appuser:appuser "$CALENDARIO_DIR" 2>/dev/null || true
                chmod -R u+rwX,go+rX "$CALENDARIO_DIR" 2>/dev/null || true
            fi
        fi
    fi
}

check_directorio_calendario() {
    # Raíz vía FILES_OUTPUT_CALENDAR (ver init_rutas)
    local CALENDARIO_DIR="$CALENDARIO_DATA_DIR/calendario_economico"

    if [ ! -d "$CALENDARIO_DIR" ]; then
        log "📁 Creando directorio calendario_economico..."
        mkdir -p "$CALENDARIO_DIR"
    fi

    if [ ! -d "$CALENDARIO_DIR/logs" ]; then
        mkdir -p "$CALENDARIO_DIR/logs"
        log "📁 Creando directorio de logs del calendario"
    fi

    fix_permissions_calendario

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
    # Raíz vía FILES_OUTPUT_CALENDAR (ver init_rutas)
    local CALENDARIO_DIR="$CALENDARIO_DATA_DIR/calendario_economico"
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
    local CALENDARIO_LOG_DIR="$CALENDARIO_DATA_DIR/calendario_economico/logs"
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
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 📅 [$SERVER_ID] CALENDARIO ECONÓMICO TRADINGVIEW v3.1.1" | tee -a "$EXEC_LOG"
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
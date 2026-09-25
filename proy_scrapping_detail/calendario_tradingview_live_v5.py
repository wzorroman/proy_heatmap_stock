#!/usr/bin/env python3
"""
CALENDARIO ECONOMICO TRADINGVIEW - CAPTURA RAW V5
===================================================
Script: calendario_tradingview_live_v5.py
Author: Wilson Zauma
Date: 2026-09-13
Version: 3.1.0

DESCRIPCION:
    Captura eventos economicos de TradingView y guarda TODOS los campos
    tal cual vienen de la API, sin filtrar ni transformar nada.
    La normalizacion se hara en un script separado.

    Estructura de carpetas:
    - DATOS_LIVE_CALENDARIO/calendario_economico/eventos_calendario.csv (ultimos 7 dias)
    - DATOS_LIVE_CALENDARIO/calendario_economico/YYYY-MM/historico_YYYYMM.csv (historico mensual)
    - BD: heatmap_stock.fact_economic_event (29 columnas, UPSERT)
    - BD: heatmap_stock.audit_sync_run (1 fila por ejecucion)
    - BD: heatmap_stock.sync_checkpoint (resumen de checkpoint)

FRECUENCIA RECOMENDADA:
    - Cada 15-30 minutos via cron

DIFERENCIAS CON V3:
    - NO filtra por importancia (guarda todo)
    - NO normaliza campos (guarda todos los campos originales)
    - Dedup por 'id' del evento (campo unico de la API)
    - Todos los campos se guardan tal cual: id, title, country, indicator,
      ticker, comment, category, period, referenceDate, source, source_url,
      actual, previous, forecast, actualRaw, previousRaw, forecastRaw,
      currency, unit, importance, date
    - v3.1.0: Añade escritura a PostgreSQL heatmap_stock (si DB_WRITE_ENABLED=true)

USO:
    # Captura normal (ejecutar cada 15-30 minutos via cron)
    python3 calendario_tradingview_live_v5.py

    # Con paises especificos
    python3 calendario_tradingview_live_v5.py --paises "US,GB,DE,FR"

    # Sin rotacion automatica
    python3 calendario_tradingview_live_v5.py --no-rotate

    # Forzar rotacion manual
    python3 calendario_tradingview_live_v5.py --rotate-now --dias-mantener 14

    # Ver estado actual
    python3 calendario_tradingview_live_v5.py --status

    # Re-iniciar el mes (borrar historico del mes actual y empezar de cero)
    python3 calendario_tradingview_live_v5.py --reset-month
"""

import os
import sys
import json
import time
import argparse
import logging
from logging.handlers import RotatingFileHandler
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Tuple
import config  # NUEVO: config para BD

# ==============================================================================
# 1. CONFIGURACION
# ==============================================================================

CALENDAR_API = "https://economic-calendar.tradingview.com/events"

PAISES_POR_DEFECTO = "US,GB,DE,FR,IT,ES,CN,JP,AU,CA,CH"

HEADERS = {
    "Origin": "https://es.tradingview.com",
    "Referer": "https://es.tradingview.com/",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

BASE_DIR = Path("DATOS_LIVE_CALENDARIO")
CALENDARIO_DIR = BASE_DIR / "calendario_economico"

EVENTOS_RECIENTES = CALENDARIO_DIR / "eventos_calendario.csv"
CHECKPOINT_FILE = CALENDARIO_DIR / "checkpoint.json"

LOG_DIR = CALENDARIO_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DIAS_MANTENER_DEFAULT = 7

# Campos que vienen de la API (los guardamos todos)
CAMPOS_API = [
    'id', 'title', 'country', 'indicator', 'ticker', 'comment',
    'category', 'period', 'referenceDate', 'source', 'source_url',
    'actual', 'previous', 'forecast', 'actualRaw', 'previousRaw',
    'forecastRaw', 'currency', 'unit', 'importance', 'date'
]

# ==============================================================================
# 2. LOGGING (F3.6: RotatingFileHandler 10MB x 7, buste en vez de 1 log por ejecución)
# ==============================================================================

def setup_logging():
    # RotatingFileHandler (F3.6, E-CAL-04): no acumula más de 7 archivos.
    log_file = LOG_DIR / "calendario.log"
    rotating = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=7, encoding='utf-8'
    )
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            rotating,
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Adjuntar explícitamente al logger del módulo: basicConfig es no-op si el
    # root ya tiene handlers (p.ej. bajo pytest), así el handler queda garantizado.
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        if len(logger.handlers) == 0:
            logger.handlers = [rotating, logging.StreamHandler(sys.stdout)]
        else:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            rotating.setFormatter(formatter)
            logger.addHandler(rotating)
    return logger

logger = setup_logging()

# ==============================================================================
# 3. EXTRACCION - RAW, SIN TRANSFORMACION
# ==============================================================================

# F3.6 · Reintento con backoff exponencial (E-CAL-01, E-CAL-03)
MAX_REINTENTOS_API = 3
BACKOFF_BASE_S = 5


class ApiSinEventos(Exception):
    """Distinto de error de API: no hay eventos en el rango (checkpoint intacto)."""
    pass


class ErrorApi(Exception):
    """Error real de red/HTTP/429: se debe reintentar."""
    pass


def fetch_calendar_events(desde: datetime, hasta: datetime, paises: str) -> List[Dict]:
    """Consulta la API con reintento con backoff (F3.6).

    - Sin eventos en rango -> retorna [] (estado PARTIAL_FAIL, checkpoint intacto
      lo maneja el caller, NO se reinicia a cero).
    - Error de API/429 -> reintenta hasta MAX_REINTENTOS_API con backoff.
    """
    desde_str = desde.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    hasta_str = hasta.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    params = {
        "from": desde_str,
        "to": hasta_str,
        "countries": paises
    }

    intento = 0
    while intento < MAX_REINTENTOS_API:
        intento += 1
        try:
            logger.debug(f"Consultando API: {desde_str[:10]} a {hasta_str[:10]} (intento {intento})")
            response = requests.get(CALENDAR_API, params=params, headers=HEADERS, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    eventos = data.get('result', [])
                    logger.info(f"Eventos obtenidos de API: {len(eventos)}")
                    return eventos
                else:
                    logger.warning(f"Estado API: {data.get('status')}")
                    # API respondió pero sin status 'ok' -> no hay eventos nuevos
                    raise ApiSinEventos(f"status={data.get('status')}")
            elif response.status_code == 429:
                logger.error(f"RATE LIMIT (429) intento {intento}/{MAX_REINTENTOS_API}.")
                if intento < MAX_REINTENTOS_API:
                    espera = BACKOFF_BASE_S * (2 ** (intento - 1))
                    logger.warning(f"Backoff {espera}s antes de reintentar...")
                    time.sleep(espera)
                continue
            else:
                logger.error(f"Error HTTP {response.status_code} (intento {intento}).")
                if intento < MAX_REINTENTOS_API:
                    espera = BACKOFF_BASE_S * (2 ** (intento - 1))
                    logger.warning(f"Backoff {espera}s antes de reintentar...")
                    time.sleep(espera)
                continue

        except ApiSinEventos:
            return []  # no hay eventos (PARTIAL_FAIL; checkpoint intacto via caller)
        except requests.exceptions.Timeout:
            logger.error(f"Timeout en la solicitud (intento {intento}).")
        except requests.exceptions.ConnectionError:
            logger.error(f"Error de conexion (intento {intento}).")
        except Exception as e:
            logger.error(f"Error inesperado: {e} (intento {intento}).")

    # Se agotaron los reintentos por error de API (no por falta de eventos)
    raise ErrorApi(f"API calendario agotó {MAX_REINTENTOS_API} reintentos")


def evento_a_dict(evento_raw: Dict) -> Dict:
    """
    Convierte un evento crudo de la API a diccionario plano para CSV.
    Guarda TODOS los campos tal cual vienen, sin transformar.
    Agrega timestamp_captura para saber cuando se grabo.
    """
    registro = {}
    for campo in CAMPOS_API:
        valor = evento_raw.get(campo)
        # Convertir None a string vacio para CSV
        registro[campo] = '' if valor is None else valor

    # Campo de captura
    registro['timestamp_captura'] = datetime.now(timezone.utc).isoformat()
    return registro

# ==============================================================================
# 4. GESTION DE ARCHIVOS
# ==============================================================================

def asegurar_directorios():
    CALENDARIO_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

def cargar_checkpoint() -> Dict:
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                checkpoint = json.load(f)
            logger.info(f"Checkpoint cargado - Ultima revision: {checkpoint.get('fecha_ultima_revision', 'N/A')}")
            return checkpoint
        except Exception as e:
            logger.warning(f"No se pudo cargar checkpoint: {e}")

    return {
        'ultimo_timestamp': 0,
        'ultima_fecha': '',
        'eventos_acumulados': 0,
        'eventos_encontrados': 0,
        'fecha_ultima_revision': ''
    }

def guardar_checkpoint(ultimo_timestamp: int, eventos_acumulados: int, eventos_encontrados: int = 0):
    ahora = datetime.now(timezone.utc)
    checkpoint = {
        'ultimo_timestamp': ultimo_timestamp,
        'ultima_fecha': datetime.fromtimestamp(ultimo_timestamp, timezone.utc).isoformat() if ultimo_timestamp else '',
        'eventos_acumulados': eventos_acumulados,
        'eventos_encontrados': eventos_encontrados,
        'fecha_ultima_revision': ahora.isoformat()
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    logger.info(f"Checkpoint guardado - Revision: {ahora.strftime('%Y-%m-%d %H:%M:%S UTC')}, "
                f"Encontrados: {eventos_encontrados}, Nuevos: {eventos_acumulados}")


def rotar_eventos_recientes(force_rotate: bool = False, dias_mantener: int = DIAS_MANTENER_DEFAULT):
    """
    Mantiene solo eventos de los ultimos N dias en eventos_calendario.csv
    Los eventos antiguos se mueven a historico mensual.
    """
    if not EVENTOS_RECIENTES.exists():
        logger.info("No hay archivo de eventos para rotar")
        return 0

    try:
        df = pd.read_csv(EVENTOS_RECIENTES)
        if df.empty:
            logger.info("Archivo de eventos vacio")
            return 0

        # Parsear fecha del evento (campo 'date' de la API)
        df['_fecha_dt'] = pd.to_datetime(df['date'], errors='coerce', utc=True)
        ahora = datetime.now(timezone.utc)
        limite_dias = ahora - timedelta(days=dias_mantener)

        df_recientes = df[df['_fecha_dt'] >= limite_dias].copy()
        df_historicos = df[df['_fecha_dt'] < limite_dias].copy()

        # Force rotate: si no hay historicos pero hay datos viejos cerca del limite
        if df_historicos.empty and force_rotate and not df_recientes.empty:
            limite_cercano = ahora - timedelta(days=dias_mantener * 2)
            df_historicos = df[df['_fecha_dt'] < limite_cercano].copy()
            df_recientes = df[df['_fecha_dt'] >= limite_cercano].copy()

        if df_historicos.empty:
            logger.info(f"No hay eventos antiguos para rotar (todos dentro de ultimos {dias_mantener} dias)")
            df.drop(columns=['_fecha_dt'], inplace=True, errors='ignore')
            return 0

        # Guardar recientes (sin columna auxiliar)
        df_recientes.drop(columns=['_fecha_dt'], inplace=True, errors='ignore')
        df_recientes.to_csv(EVENTOS_RECIENTES, index=False)
        logger.info(f"Archivo principal actualizado: {len(df_recientes)} eventos recientes")

        # Mover a historico mensual
        df_historicos['_anio_mes'] = df_historicos['_fecha_dt'].dt.strftime('%Y-%m')

        eventos_movidos = {}
        for anio_mes, grupo in df_historicos.groupby('_anio_mes'):
            anio, mes = anio_mes.split('-')
            historico_dir = CALENDARIO_DIR / anio_mes
            historico_dir.mkdir(exist_ok=True)
            historico_file = historico_dir / f"historico_{anio}{mes}.csv"

            grupo_save = grupo.drop(columns=['_fecha_dt', '_anio_mes'], errors='ignore')

            if historico_file.exists():
                df_existente = pd.read_csv(historico_file)
                df_combinado = pd.concat([df_existente, grupo_save], ignore_index=True)
                antes = len(df_combinado)
                df_combinado.drop_duplicates(subset=['id'], keep='last', inplace=True)
                despues = len(df_combinado)
                df_combinado.to_csv(historico_file, index=False)
                eventos_movidos[anio_mes] = len(grupo)
                logger.info(f"  {anio_mes}: {len(grupo)} eventos (antes: {antes}, ahora: {despues})")
            else:
                grupo_save.to_csv(historico_file, index=False)
                eventos_movidos[anio_mes] = len(grupo)
                logger.info(f"  {anio_mes}: nuevo historico con {len(grupo)} eventos")

        logger.info(f"Rotacion completada: {len(df_historicos)} eventos movidos -> {eventos_movidos}")
        return len(df_historicos)

    except Exception as e:
        logger.error(f"Error en rotacion: {e}")
        return 0


def guardar_eventos(eventos: List[Dict], auto_rotate: bool = True, dias_mantener: int = DIAS_MANTENER_DEFAULT):
    """
    Guarda eventos en CSV. Dedup por campo 'id' de la API.
    """
    if not eventos:
        return

    df_nuevo = pd.DataFrame(eventos)
    df_nuevo.drop_duplicates(subset=['id'], keep='last', inplace=True)

    if EVENTOS_RECIENTES.exists():
        try:
            df_existente = pd.read_csv(EVENTOS_RECIENTES)
        except pd.errors.EmptyDataError:
            df_existente = None

        if df_existente is not None and not df_existente.empty:
            df_combinado = pd.concat([df_existente, df_nuevo], ignore_index=True)
            antes = len(df_combinado)
            df_combinado.drop_duplicates(subset=['id'], keep='last', inplace=True)
            despues = len(df_combinado)
            if antes != despues:
                logger.info(f"Duplicados eliminados: {antes - despues}")
            df_combinado.to_csv(EVENTOS_RECIENTES, index=False)
            logger.info(f"Archivo principal: {len(df_combinado)} eventos totales")
        else:
            df_nuevo.to_csv(EVENTOS_RECIENTES, index=False)
            logger.info(f"Archivo principal creado: {len(df_nuevo)} eventos")
    else:
        df_nuevo.to_csv(EVENTOS_RECIENTES, index=False)
        logger.info(f"Archivo principal creado: {len(df_nuevo)} eventos")

    if auto_rotate:
        rotar_eventos_recientes(dias_mantener=dias_mantener)


def mostrar_estado():
    if not EVENTOS_RECIENTES.exists():
        print("No existe archivo de eventos")
        return
    try:
        df = pd.read_csv(EVENTOS_RECIENTES)
        if df.empty:
            print("Archivo vacio")
            return
        total = len(df)
        print(f"\nESTADO DEL ARCHIVO PRINCIPAL:")
        print(f"  Archivo: {EVENTOS_RECIENTES}")
        print(f"  Total eventos: {total}")
        print(f"  Columnas: {list(df.columns)}")
        if 'importance' in df.columns:
            print(f"  Distribucion importancia:")
            for imp in sorted(df['importance'].unique()):
                print(f"    importance={imp}: {len(df[df['importance']==imp])} eventos")
    except Exception as e:
        print(f"Error leyendo archivo: {e}")


def reset_mes():
    """
    Borra el historico del mes actual y el archivo reciente para empezar de cero.
    """
    ahora = datetime.now(timezone.utc)
    mes_actual = ahora.strftime('%Y-%m')
    anio = ahora.strftime('%Y')
    mes = ahora.strftime('%m')

    historico_dir = CALENDARIO_DIR / mes_actual
    historico_file = historico_dir / f"historico_{anio}{mes}.csv"

    archivos_borrados = []

    if EVENTOS_RECIENTES.exists():
        EVENTOS_RECIENTES.unlink()
        archivos_borrados.append(str(EVENTOS_RECIENTES))

    if historico_file.exists():
        historico_file.unlink()
        archivos_borrados.append(str(historico_file))

    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        archivos_borrados.append(str(CHECKPOINT_FILE))

    if archivos_borrados:
        logger.info(f"Mes reiniciado. Archivos borrados:")
        for f in archivos_borrados:
            logger.info(f"  - {f}")
    else:
        logger.info("No hay archivos que borrar para reiniciar el mes")


# ==============================================================================
# 5. CAPTURA PRINCIPAL
# ==============================================================================

def capturar_eventos(paises: str = PAISES_POR_DEFECTO,
                     dias_adelante: int = 2,
                     incluir_pasado: int = 1,
                     auto_rotate: bool = True,
                     dias_mantener: int = DIAS_MANTENER_DEFAULT) -> Tuple[int, int]:
    """
    Captura eventos y guarda TODOS sin filtrar nada.

    F3.6 (E-CAL-05): distingue "API sin eventos" (checkpoint intacto) de
    "error de API" (reintentado y auditado como FAILED, sin tocar checkpoint).
    """
    ahora = datetime.now(timezone.utc)
    desde = ahora - timedelta(days=incluir_pasado)
    hasta = ahora + timedelta(days=dias_adelante)

    logger.info(f"Rango: {desde.strftime('%Y-%m-%d %H:%M')} a {hasta.strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"Paises: {paises}")

    try:
        eventos_raw = fetch_calendar_events(desde, hasta, paises)
    except ErrorApi as e:
        # Error de API tras reintentos: NO tocar checkpoint (E-CAL-05)
        logger.error(f"API no disponible tras reintentos: {e}")
        _auditar_calendario_falla(ahora, str(e))
        return 0, 0

    if not eventos_raw:
        # API respondió sin eventos: PARTIAL_FAIL, checkpoint intacto (F3.6)
        logger.warning("No se obtuvieron eventos (API ok, sin eventos en rango). "
                       "Checkpoint NO se reinicia.")
        _auditar_calendario_parcial(ahora)
        return 0, 0

    # Convertir a diccionarios planos - SIN FILTRO, SIN TRANSFORMACION
    eventos_para_guardar = [evento_a_dict(e) for e in eventos_raw]

    logger.info(f"Eventos a guardar: {len(eventos_para_guardar)} (sin filtro de importancia)")

    # === CSV (sin cambios) ===
    guardar_eventos(eventos_para_guardar, auto_rotate=auto_rotate, dias_mantener=dias_mantener)

    # === BD (nuevo v3.1.0) ===
    if config.DB_WRITE_ENABLED:
        try:
            from application.event_service import process_calendar_batch
            inserted = process_calendar_batch(eventos_raw)
            logger.info(f"BD: {inserted} eventos insertados/actualizados")
        except Exception as e:
            logger.error(f"BD: Error insertando eventos: {e}")
            # El CSV ya se guardó — no propagar error al caller

    # Checkpoint local (sin cambios) — except explícito (F3.6, E-CAL-06/07)
    try:
        fechas = []
        for e in eventos_raw:
            f = e.get('date', '')
            if f:
                fechas.append(f)
        if fechas:
            max_fecha = max(fechas)
            dt = datetime.fromisoformat(max_fecha.replace('Z', '+00:00'))
            max_ts = int(dt.timestamp())
        else:
            max_ts = 0
    except (TypeError, ValueError) as exc:
        logger.warning(f"No se pudo calcular timestamp del checkpoint: {exc}")
        max_ts = 0

    guardar_checkpoint(max_ts, len(eventos_para_guardar), len(eventos_raw))
    return len(eventos_para_guardar), len(eventos_raw)


def _auditar_calendario_falla(run_start: datetime, error: str):
    """Audita un fallo de API del calendario en BD (si está activa)."""
    if not config.DB_WRITE_ENABLED:
        return
    try:
        from application.event_service import process_calendar_batch  # noqa: F401
        from db.audit_repository import log_sync_run
        from db.postgresql_connection import PostgreSQLConnector
        db = PostgreSQLConnector(
            config.PG_HOST, config.PG_PORT,
            config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD
        )
        if db.connect():
            log_sync_run(db, {
                'script_name': config.SCRIPT_NAME_CALENDARIO,
                'run_start': run_start,
                'records_fetched': 0,
                'records_upserted': 0,
                'records_failed': 0,
                'status': 'FAILED',
                'error_message': f'API calendar: {error}',
                'execution_mode': 'manual',
                'source_params': {'condicion': 'error API tras reintentos', 'checkpoint': 'intacto'},
            })
            db.disconnect()
    except Exception as e:
        logger.error(f"BD: no se pudo auditar fallo del calendario: {e}")


def _auditar_calendario_parcial(run_start: datetime):
    """Audita PARTIAL_FAIL (API ok sin eventos; checkpoint intacto)."""
    if not config.DB_WRITE_ENABLED:
        return
    try:
        from db.audit_repository import log_sync_run
        from db.postgresql_connection import PostgreSQLConnector
        db = PostgreSQLConnector(
            config.PG_HOST, config.PG_PORT,
            config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD
        )
        if db.connect():
            log_sync_run(db, {
                'script_name': config.SCRIPT_NAME_CALENDARIO,
                'run_start': run_start,
                'records_fetched': 0,
                'records_upserted': 0,
                'records_failed': 0,
                'status': 'PARTIAL_FAIL',
                'error_message': 'API ok pero sin eventos en rango',
                'execution_mode': 'manual',
                'source_params': {'condicion': 'sin eventos', 'checkpoint': 'intacto'},
            })
            db.disconnect()
    except Exception as e:
        logger.error(f"BD: no se pudo auditar PARTIAL_FAIL del calendario: {e}")


# ==============================================================================
# 6. MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Calendario Economico TradingView - Captura Raw V4")
    parser.add_argument('--paises', type=str, default=PAISES_POR_DEFECTO,
                       help=f'Paises separados por coma (default: {PAISES_POR_DEFECTO})')
    parser.add_argument('--dias', type=int, default=2,
                       help='Dias hacia adelante (default: 2)')
    parser.add_argument('--pasado', type=int, default=1,
                       help='Dias hacia atras (default: 1)')
    parser.add_argument('--no-rotate', action='store_true',
                       help='Desactivar rotacion automatica')
    parser.add_argument('--rotate-now', action='store_true',
                       help='Forzar rotacion manual')
    parser.add_argument('--dias-mantener', type=int, default=DIAS_MANTENER_DEFAULT,
                       help=f'Dias a mantener en archivo principal (default: {DIAS_MANTENER_DEFAULT})')
    parser.add_argument('--status', action='store_true',
                       help='Mostrar estado del archivo principal')
    parser.add_argument('--reset-month', action='store_true',
                       help='Reiniciar el mes (borrar historico del mes actual)')

    args = parser.parse_args()

    print("""
    =============================================
      CALENDARIO ECONOMICO TRADINGVIEW - V5 RAW
      Guarda TODO tal cual viene de la API
      v3.1.0: BD heatmap_stock (DB_WRITE_ENABLED)
    =============================================
    """)

    asegurar_directorios()

    if args.status:
        mostrar_estado()
        checkpoint = cargar_checkpoint()
        print(f"\nCheckpoint:")
        print(f"  Ultima revision: {checkpoint.get('fecha_ultima_revision', 'N/A')}")
        print(f"  Eventos encontrados: {checkpoint.get('eventos_encontrados', 0)}")
        print(f"  Eventos nuevos: {checkpoint.get('eventos_acumulados', 0)}")
        return

    if args.reset_month:
        reset_mes()
        return

    if args.rotate_now:
        logger.info("Forzando rotacion manual...")
        rotar_eventos_recientes(force_rotate=True, dias_mantener=args.dias_mantener)
        return

    # Gate NYSE con pre_min=90 (F2.2): arranque a las 08:00 ET.
    try:
        import pandas as pd
        from db.sessions import en_ventana_nyse
        if not en_ventana_nyse(pre_min=90):
            logger.info("Fuera de la ventana NYSE (pre_min=90): se omite la captura")
            return
    except Exception as e:
        logger.warning(f"Gate NYSE no disponible ({e}); se captura igualmente")

    nuevos, totales = capturar_eventos(
        paises=args.paises,
        dias_adelante=min(args.dias, 2),
        incluir_pasado=args.pasado,
        auto_rotate=not args.no_rotate,
        dias_mantener=args.dias_mantener
    )

    logger.info(f"Captura completada: {nuevos} eventos nuevos de {totales} encontrados")


if __name__ == "__main__":
    main()
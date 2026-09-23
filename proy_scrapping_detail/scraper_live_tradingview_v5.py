"""
🚀 RADAR INTERMARKET - SCORER & PERSISTENCE ENGINE V5 (BD CONECTADA)
=================================================================
Script: scraper_live_tradingview_v5.py
Author: Wilson Zauma
Date: 2026-03-16 (v3) · 2026-08-22 (v4) · 2026-09-18 (v5)
Version: 5.0 (Universo ampliado + blindaje lock/cabecera + pausas rápidas + BD)

DESCRIPCIÓN:
    Motor de captura de alta fidelidad para el ecosistema de trading.
    Extrae métricas de momentum, volumen y liquidez directamente desde
    el scanner de TradingView sin dependencias de librerías de terceros.

CAMBIOS V5 (respecto a V4) — Roadmap 3.1.0:
    - Escritura a PostgreSQL `heatmap_stock` → `fact_market_series`
      (si DB_WRITE_ENABLED=true), vía application.market_service.
    - Batch buffering: 110 símbolos → 1 round-trip de BD por ciclo.
    - Flush parcial del batch antes del circuit breaker (sys.exit 1).
    - Logging unificado a `logging` (sustituye print).
    - CSV se mantiene como buffer raw / fallback (sin cambios).

CAPACIDADES V4 (preservadas):
    - Extracción Zero-Library (Requests-based).
    - Estandarización UTC Nativa.
    - Gestión de Persistencia: Rolling de 7 días (LIVE) y Archivo Mensual.
    - Redundancia Dinámica: Fallback automático entre Primarios y Respaldos.
    - Lock exclusivo fcntl + backoff 429 + circuit breaker.

ESTRUCTURA DE DATOS:
    - DATOS_LIVE_2/{SYMBOL}/{SYMBOL}.csv
    - DATOS_LIVE_2/{SYMBOL}_{YYYYMM}/historico_{SYMBOL}_{YYYYMM}.csv

MODO USO :
  (defecto) Solo descarga y organiza los archivos (+ BD si está activa).
    - python3 scraper_live_tradingview_v5.py

  Genera un archivo único con la última foto de todos los activos.
    - python3 scraper_live_tradingview_v5.py --consolidate
"""

import os
import sys
import time
import random
import argparse
import logging
import fcntl
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
import config
from config import CONFIG_ACTIVOS

BASE_DIR = "DATOS_LIVE"

# ==============================================================================
# 1. LOGGING UNIFICADO (D24 roadrmaap 3.1.0)
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger('scraper_v5')
# Silenciar demasiado ruido de pandas/urllib3
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('pandas').setLevel(logging.WARNING)

# ==============================================================================
# 2. CFONFIGURACIÓN DE ACTIVOS Y ENDPOINTS
# ==============================================================================
CAMPOS = "close,volume,RSI,CCI20,BBPower,ADX,Pivot.M.Camarilla.R3,Perf.W,change"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Resiliencia anti-bloqueo (rate-limit / protección de IP)
ESPERAS_BACKOFF_429 = [15, 45, 120]   # Backoff progresivo ante 429 (total máx: 180s)
PAUSA_ENFRIAMIENTO_ERROR = 20         # Pausa extra tras un fallo aislado
MAX_FALLOS_CONSECUTIVOS = 3           # Circuit breaker: aborta el ciclo completo

# ==============================================================================
# 3. MOTOR DE EXTRACCIÓN (Método Testing 07)
# ==============================================================================

def fetch_from_scanner(symbol):
    """Consulta directa al scanner de TradingView evitando librerías externas."""
    url = "https://scanner.tradingview.com/symbol"
    params = {"symbol": symbol, "fields": CAMPOS, "no_404": "true"}
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=12)
        if response.status_code == 200:
            data = response.json()
            # Guardar timestamp como segundos UTC (int)
            data["timestamp_utc"] = int(datetime.now(timezone.utc).timestamp())
            data["fecha_iso"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            data["simbolo"] = symbol
            return data
        elif response.status_code == 429:
            return "429"
        return None
    except Exception as e:
        logger.error(f"Error conexión {symbol}: {e}")
        return None

def sanitizar_nombre(nombre):
    """Limpia caracteres especiales para nombres de carpetas y archivos."""
    return nombre.replace(":", "-").replace("!", "")

# ==============================================================================
# 4. GESTIÓN DE ARCHIVOS Y ROTACIÓN (7 Días + Histórico Mensual)
# ==============================================================================

def rotar_datos(file_path, folder_name):
    """Mueve registros antiguos a históricos mensuales y limpia el archivo LIVE."""
    if not os.path.exists(file_path): return
    try:
        df = pd.read_csv(file_path)
        if df.empty: return

        df['timestamp_dt'] = pd.to_datetime(df['timestamp_utc'], unit='s', utc=True)

        ahora = datetime.now(timezone.utc)
        limite_7_dias = ahora - timedelta(days=7)

        historico_df = df[df['timestamp_dt'] <= limite_7_dias].copy()
        live_df = df[df['timestamp_dt'] > limite_7_dias].copy()

        if 'timestamp_dt' in historico_df.columns:
            historico_df = historico_df.drop(columns=['timestamp_dt'])
        if 'timestamp_dt' in live_df.columns:
            live_df = live_df.drop(columns=['timestamp_dt'])

        if not historico_df.empty:
            historico_df['mes_folder'] = pd.to_datetime(historico_df['timestamp_utc'], unit='s', utc=True).dt.strftime("%Y%m")

            for mes, data_mes in historico_df.groupby('mes_folder'):
                hist_dir = os.path.join(BASE_DIR, f"{folder_name}_{mes}")
                os.makedirs(hist_dir, exist_ok=True)
                hist_file = os.path.join(hist_dir, f"historico_{folder_name}_{mes}.csv")

                data_mes_drop = data_mes.drop(columns=['mes_folder'])
                escribir_header = not os.path.exists(hist_file) or os.path.getsize(hist_file) == 0
                data_mes_drop.to_csv(
                    hist_file, mode='a', header=escribir_header, index=False
                )

            live_df.to_csv(file_path, index=False)

    except Exception as e:
        logger.error(f"Error rotación {folder_name}: {e}")

def consolidar_analisis():
    """Consolida la última captura de cada símbolo en un CSV único para testeo."""
    logger.info("Generando consolidado integral de test")

    consolidados_dir = os.path.join(BASE_DIR, "consolidados")
    os.makedirs(consolidados_dir, exist_ok=True)

    filas = []
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith(".csv") and not file.startswith("historico_") and "consolidado" not in file:
                try:
                    file_path = os.path.join(root, file)
                    df = pd.read_csv(file_path)
                    if not df.empty:
                        filas.append(df.iloc[-1:])
                except Exception as e:
                    logger.warning(f"Error leyendo {file}: {e}")

    if filas:
        final_df = pd.concat(filas, ignore_index=True)
        ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f"consolidado_{ts}.csv"
        out_path = os.path.join(consolidados_dir, filename)
        final_df.to_csv(out_path, index=False)
        logger.info(f"Consolidado generado: {out_path} — {len(final_df)} símbolos")
    else:
        logger.warning("No se encontraron datos para consolidar")

# ==============================================================================
# 5. FLUJO BD (ROADMAP 3.1.0) — BATCH BUFFER + FLUSH
# ==============================================================================

def flush_radar_batch(batch_buffer):
    """
    Envía el batch acumulado a fact_market_series vía market_service.
    No lanza excepciones: un fallo de BD no tumba el ciclo.
    Retorna cantidad insertada o 0.
    """
    if not batch_buffer:
        return 0
    if not config.DB_WRITE_ENABLED:
        return 0

    from application.market_service import process_radar_batch, prepare_bd_row

    # Convertir respuestas crudas (claves nombradas del /symbol) a filas BD
    bd_rows = [
        prepare_bd_row(item.get('simbolo'), item)
        for item in batch_buffer
        if isinstance(item, dict) and item.get('simbolo') and 'timestamp_utc' in item
    ]

    if not bd_rows:
        logger.warning("Batch BD vacío tras preparación de filas")
        return 0

    try:
        inserted = process_radar_batch(bd_rows)
        logger.info(f"BD: {inserted}/{len(bd_rows)} series escritas en fact_market_series")
        return inserted
    except Exception as e:
        logger.error(f"BD: fallo al escribir fact_market_series: {e}")
        return 0

# ==============================================================================
# 6. FLUJO PRINCIPAL
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Scraper Live V5 - TradingView Scanner")
    parser.add_argument('--consolidate', action='store_true', help="Genera un CSV consolidado al finalizar.")
    args = parser.parse_args()

    lock_path = "/tmp/scraper_live_tradingview_v5.lock"
    lock_fh = open(lock_path, "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logger.warning("Ya existe una instancia del scraper en ejecución. Saliendo sin duplicar escrituras.")
        sys.exit(0)

    logger.info(f"SCRAPER LIVE V5 | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC "
                f"| BD_WRITE={'ON' if config.DB_WRITE_ENABLED else 'OFF'}")

    # Recolectar lista única de símbolos (Primarios y Respaldos)
    todos_simbolos = set()
    for cat in CONFIG_ACTIVOS.values():
        for meta in cat.values():
            todos_simbolos.add(meta["primario"])
            todos_simbolos.add(meta["respaldo"])

    lista_ordenada = sorted(list(todos_simbolos))

    fallos_consecutivos = 0
    batch_buffer = []  # Buffer de respuestas crudas para el flush BD (v3.1.0)

    for i, symbol in enumerate(lista_ordenada):
        folder_clean = sanitizar_nombre(symbol)
        path_base = os.path.join(BASE_DIR, folder_clean)
        os.makedirs(path_base, exist_ok=True)
        csv_file = os.path.join(path_base, f"{folder_clean}.csv")

        logger.info(f"[{i+1}/{len(lista_ordenada)}] {symbol}...")

        res = fetch_from_scanner(symbol)

        # Reintento con backoff progresivo ante rate-limit (429)
        if res == "429":
            for espera in ESPERAS_BACKOFF_429:
                logger.warning(f"BLOQUEO 429. Backoff {espera}s...")
                time.sleep(espera)
                res = fetch_from_scanner(symbol)
                if res != "429":
                    break

        if isinstance(res, dict):
            fallos_consecutivos = 0
            # CSV (sin cambios) — buffer raw / fallback
            df_new = pd.DataFrame([res])
            escribir_header = not os.path.exists(csv_file) or os.path.getsize(csv_file) == 0
            df_new.to_csv(csv_file, mode='a', header=escribir_header, index=False)
            rotar_datos(csv_file, folder_clean)

            # BD (nuevo) — acumular al batch para un solo flush por ciclo
            if config.DB_WRITE_ENABLED:
                batch_buffer.append(res)
        else:
            fallos_consecutivos += 1
            logger.error(f"FALLO ({fallos_consecutivos} consecutivos) en {symbol}")
            time.sleep(PAUSA_ENFRIAMIENTO_ERROR)

            # Circuit breaker: flush parcial del batch acumulado y abortar
            if fallos_consecutivos >= MAX_FALLOS_CONSECUTIVOS:
                logger.warning("CIRCUIT BREAKER: 3 fallos consecutivos. "
                              "Flush parcial BD antes de abortar.")
                flush_radar_batch(batch_buffer)
                batch_buffer.clear()
                logger.warning("Ciclo abortado para proteger la IP (reintentará el próximo cron).")
                sys.exit(1)

        # Pausa aleatoria para simular tráfico humano
        if i < len(lista_ordenada) - 1:
            time.sleep(random.uniform(0.4, 1.2))

    # Flush del batch completo al final del ciclo (1 round-trip a BD)
    if config.DB_WRITE_ENABLED and batch_buffer:
        flush_radar_batch(batch_buffer)
        batch_buffer.clear()

    if args.consolidate:
        consolidar_analisis()

    logger.info("PROCESO FINALIZADO")

if __name__ == "__main__":
    main()
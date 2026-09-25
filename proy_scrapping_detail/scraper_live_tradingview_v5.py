"""
🚀 RADAR INTERMARKET - SCORER & PERSISTENCE ENGINE V5 (BD CONECTADA)
=================================================================
Script: scraper_live_tradingview_v5.py
Author: Wilson Zauma
Date: 2026-03-16 (v3) · 2026-08-22 (v4) · 2026-09-18 (v5)
Version: 5.1 (FASE 3: batch /america/scan + CAMPOS extendido + trazabilidad + prioridad)

DESCRIPCIÓN:
    Motor de captura de alta fidelidad para el ecosistema de trading.
    Extrae métricas de momentum, volumen y liquidez directamente desde
    el scanner de TradingView sin dependencias de librerías de terceros.

CAMBIOS V5.1 (FASE 3 · Captura fiable):
    - F3.2 · CAMPOS extendido: bloques |5, |15, |60 + Pivot.M.Camarilla.R3|15
            + premarket_* + gap + update_mode.
    - F3.1 · Captura batch: POST /america/scan para el universo equity/ETF
            (1 round-trip); GET /symbol individual para FX/crypto/futuros/TVC.
    - F3.3 · Trazabilidad: update_mode, cycle_id, fetched_at, feed_delay_s,
            premarket_*, gap en fact_market_series.
    - F3.4 · Prioridad de símbolos + circuit breaker por exchange (no global).
    - F3.10 · 1 fila de auditoría de ciclo (cycle_id + duración + fallidos),
            incluidos ciclos saltados.
    - Anti-429: REQUEST_DELAY_S + MAX_RETRIES con backoff.

CAPACIDADES V5 (preservadas):
    - Extracción Zero-Library (Requests-based).
    - Estandarización UTC Nativa.
    - Gestión de Persistencia: Rolling de 7 días (LIVE) y Archivo Mensual.
    - CSV buffer raw / fallback.
    - Escritura a PostgreSQL `heatmap_stock` → `fact_market_series`.

ESTRUCTURA DE DATOS:
    - DATOS_LIVE_2/{SYMBOL}/{SYMBOL}.csv
    - DATOS_LIVE_2/{SYMBOL}_{YYYYMM}/historico_{SYMBOL}_{YYYYMM}.csv

MODO USO:
    (defecto) Solo descarga y organiza los archivos (+ BD si está activa).
      - python3 scraper_live_tradingview_v5.py
    Genera un archivo único con la última foto de todos los activos.
      - python3 scraper_live_tradingview_v5.py --consolidate
"""

import os
import sys
import csv
import time
import random
import argparse
import logging
import fcntl
import uuid
import requests
import pandas as pd
from collections import Counter
from datetime import datetime, timezone, timedelta
import config
from config import CONFIG_ACTIVOS

BASE_DIR = "DATOS_LIVE"

# ==============================================================================
# 1. LOGGING UNIFICADO
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger('scraper_v5')
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('pandas').setLevel(logging.WARNING)

# ==============================================================================
# 2. CFONFIGURACIÓN DE ACTIVOS Y ENDPOINTS
# ==============================================================================

# --- F3.2 · CAMPOS extendido (roadmap: BASE_1D + bloques |TF + pivote |15) ---
BASE_1D = (
    "close,volume,RSI,CCI20,BBPower,ADX,"
    "Pivot.M.Camarilla.R3,Perf.W,change,"
    "premarket_close,premarket_change,premarket_volume,gap"
)


def _bloque(tf: str) -> str:
    """Bloque de columnas con sufijo de timeframe (F3.2)."""
    return ",".join(f"{c}|{tf}" for c in
                    ("volume", "RSI", "CCI20", "BBPower", "ADX", "change"))


CAMPOS = ",".join([
    BASE_1D,
    _bloque("5"),
    _bloque("15"),
    _bloque("60"),                 # NUEVO: TF válido, barra de régimen
    "Pivot.M.Camarilla.R3|15",     # NUEVO: pivote diario confirmado (Test H)
    "update_mode",
])
CAMPOS_LIST = CAMPOS.split(",")

URL_SCAN = "https://scanner.tradingview.com/america/scan?label-product=heatmap-stock"
URL_SYMBOL = "https://scanner.tradingview.com/symbol"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Origin": "https://es.tradingview.com",
    "Referer": "https://es.tradingview.com/heatmap/stock/",
    "Accept": "application/json, text/plain, */*",
}

# Resistencias anti-bloqueo (rate-limit / protección de IP)
ESPERAS_BACKOFF_429 = [15, 45, 120]
PAUSA_ENFRIAMIENTO_ERROR = 20
MAX_FALLOS_CONSECUTIVOS = 3

# F3.4 · Prioridad de captura (los críticos primero)
PRIORIDADES = {
    "AMEX:SPY": 0,
    "NASDAQ:QQQ": 1,
    "CBOE:VX1!": 2,
    "TVC:VIX": 3,
    "TVC:US10Y": 4,
    "TVC:US02Y": 5,
    "AMEX:UUP": 6,
    "ICEUS:DX1!": 7,
    "CME_MINI:NQ1!": 8,
    "CME_MINI:ES1!": 9,
}

# Prefijos que responde POST /america/scan (universo equity/ETF de america)
BATCH_PREFIJOS = {"NASDAQ", "NYSE", "AMEX"}


def _prioridad(symbol: str) -> int:
    return PRIORIDADES.get(symbol, 1000)


def ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ==============================================================================
# 3. MOTOR DE EXTRACCIÓN INDIVIDUAL (GET /symbol)
# ==============================================================================

def fetch_from_scanner(symbol, cycle_id=None):
    """Consulta individual al scanner (funciona para TODAS las clases:
    FX, cripto, futuros CME/CBOT, TVC). Retorna dict o "429" o None."""
    params = {"symbol": symbol, "fields": CAMPOS, "no_404": "true"}
    try:
        response = requests.get(URL_SYMBOL, params=params, headers=HEADERS, timeout=12)
        if response.status_code == 200:
            data = response.json()
            if not isinstance(data, dict) or not data:
                return None
            data["timestamp_utc"] = int(datetime.now(timezone.utc).timestamp())
            data["fecha_iso"] = ahora_iso()
            data["simbolo"] = symbol
            data["fetched_at"] = datetime.now(timezone.utc)
            data["cycle_id"] = cycle_id
            return data
        elif response.status_code == 429:
            return "429"
        return None
    except Exception as e:
        logger.error(f"Error conexión {symbol}: {e}")
        return None


# ==============================================================================
# 4. MOTOR DE EXTRACCIÓN BATCH (POST /america/scan) — F3.1
# ==============================================================================

def post_scan(tickers: list, columns: list, filtro: list | None = None,
              timeout: int = 25) -> dict:
    """POST /america/scan con anti-429 (REQUEST_DELAY_S + MAX_RETRIES backoff).

    Retorna dict {symbol: {campo: valor}} o dict con '_error'.
    """
    time.sleep(config.REQUEST_DELAY_S)  # anti-429 obligatorio
    body = {
        "symbols": {"tickers": tickers},
        "columns": columns,
    }
    if filtro:
        body["filter"] = filtro

    for intento in range(config.MAX_RETRIES):
        try:
            r = requests.post(URL_SCAN, headers=HEADERS, json=body, timeout=timeout)
            if r.status_code == 200:
                payload = r.json()
                return _batch_a_diccionarios(payload, columns)
            if r.status_code == 429:
                espera = config.RETRY_BACKOFF_BASE_S * (intento + 1)
                logger.warning(f"BLOQUEO 429 batch (intento {intento+1}/"
                               f"{config.MAX_RETRIES}), esperando {espera}s...")
                time.sleep(espera)
                continue
            return {"_error": f"HTTP {r.status_code}", "_body": r.text[:300]}
        except Exception as e:
            return {"_error": str(e)}
    return {"_error": "HTTP 429 agotado"}


def _batch_a_diccionarios(payload: dict, columns: list) -> dict:
    """Convierte data[] del scan (d posicional) en dict {symbol: {column: valor}}."""
    result = {}
    for item in payload.get("data") or []:
        sym = item.get("s")
        d = item.get("d") or []
        fila = {}
        for i, col in enumerate(columns):
            fila[col] = d[i] if i < len(d) else None
        fila["timestamp_utc"] = int(datetime.now(timezone.utc).timestamp())
        fila["fecha_iso"] = ahora_iso()
        fila["simbolo"] = sym
        fila["fetched_at"] = datetime.now(timezone.utc)
        result[sym] = fila
    return result


def fetch_batch_from_scanner(symbols: list, cycle_id=None) -> dict:
    """Batch único para símbolos de america (equity/ETF, BATCH_PREFIJOS).
    Los que el endpoint no devuelve se reintentarán individualmente (caller).
    """
    filtrable = [s for s in symbols if s.split(":")[0] in BATCH_PREFIJOS]
    if not filtrable:
        return {}
    resp = post_scan(filtrable, CAMPOS_LIST)
    if "_error" in resp:
        logger.error(f"Batch /america/scan falló: {resp.get('_error')}")
        return {}
    for sym, fila in resp.items():
        fila["cycle_id"] = cycle_id
    return resp


def sanitizar_nombre(nombre):
    """Limpia caracteres especiales para nombres de carpetas y archivos."""
    return nombre.replace(":", "-").replace("!", "")


# ==============================================================================
# 5b. APPEND SEGURO CON MIGRACIÓN DE ESQUEMA (v4 12 cols -> v5.1 38 cols)
# ==============================================================================

def _leer_cabecera_csv(file_path):
    """Devuelve la lista de columnas de la cabecera o None si no existe/vacío."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return None
    try:
        with open(file_path, "r", newline="", encoding="utf-8") as f:
            primera = f.readline().strip()
        return primera.split(",") if primera else None
    except Exception as e:
        logger.error(f"Error leyendo cabecera {file_path}: {e}")
        return None


def _migrar_y_escribir(file_path, df_new):
    """Reescribe el CSV unificando esquemas (v4 -> v5.1) sin corromper filas.

    - Parsea el CSV existente tolerando filas con distinto número de campos.
    - Reindexa al esquema nuevo (columnas de df_new), rellenando con NaN.
    - Añade la fila nueva y sobrescribe el archivo.
    """
    columnas_nuevas = list(df_new.columns)
    registros = []
    try:
        with open(file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            cabecera = next(reader, None)
            if cabecera is None:
                df_new.to_csv(file_path, index=False)
                return
            for fila in reader:
                if not fila:
                    continue
                if len(fila) == len(cabecera):
                    registros.append(dict(zip(cabecera, fila)))
                elif len(fila) == len(columnas_nuevas):
                    registros.append(dict(zip(columnas_nuevas, fila)))
                # resto: fila corrupta -> se descarta
    except Exception as e:
        logger.error(f"Error migrando {file_path}: {e}")
        df_new.to_csv(file_path, index=False)
        return

    df_hist = pd.DataFrame(registros) if registros else pd.DataFrame(columns=columnas_nuevas)
    df_total = pd.concat([df_hist, df_new], ignore_index=True)
    df_total = df_total.reindex(columns=columnas_nuevas)
    df_total.to_csv(file_path, index=False)


def escribir_fila_csv(file_path, df_new):
    """Append seguro: si la cabecera existente difiere del esquema actual,
    migra el archivo para evitar CSVs corruptos (v4 -> v5.1)."""
    cabecera = _leer_cabecera_csv(file_path)
    columnas = list(df_new.columns)
    if cabecera is None:
        df_new.to_csv(file_path, mode="a", header=True, index=False)
        return
    if cabecera == columnas:
        df_new.to_csv(file_path, mode="a", header=False, index=False)
        return
    logger.warning(f"Esquema cambiado en {os.path.basename(file_path)} "
                   f"({len(cabecera)} -> {len(columnas)} cols). Migrando...")
    _migrar_y_escribir(file_path, df_new)


# ==============================================================================
# 5. GESTIÓN DE ARCHIVOS Y ROTACIÓN (7 Días + Histórico Mensual)
# ==============================================================================

def rotar_datos(file_path, folder_name):
    """Mueve registros antiguos a históricos mensuales y limpia el archivo LIVE."""
    if not os.path.exists(file_path): return
    try:
        df = pd.read_csv(file_path, on_bad_lines='skip')
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
                    df = pd.read_csv(file_path, on_bad_lines='skip')
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
# 6. FLUJO BD — BATCH BUFFER + FLUSH
# ==============================================================================

def flush_radar_batch(batch_buffer, cycle_id=None):
    """
    Envía el batch acumulado a fact_market_series vía market_service.
    No lanza excepciones: un fallo de BD no tumba el ciclo.
    Propaga el contrato de estado de process_radar_batch:
    {'inserted': int, 'status': 'SUCCESS'|'FAILED'|'SKIPPED', 'error': str|None}.
    """
    empty = {'inserted': 0, 'status': 'SKIPPED', 'error': 'batch vacío o BD desactivada'}
    if not batch_buffer:
        return empty
    if not config.DB_WRITE_ENABLED:
        return empty

    from application.market_service import process_radar_batch, prepare_bd_row

    # Convertir respuestas crudas (claves nombradas) a filas BD
    bd_rows = [
        prepare_bd_row(item.get('simbolo'), item)
        for item in batch_buffer
        if isinstance(item, dict) and item.get('simbolo') and 'timestamp_utc' in item
    ]

    if not bd_rows:
        logger.warning("Batch BD vacío tras preparación de filas")
        return {'inserted': 0, 'status': 'SKIPPED', 'error': 'sin filas BD válidas'}

    try:
        resultado = process_radar_batch(bd_rows, cycle_id=cycle_id,
                                        scanner_raw=batch_buffer)
        logger.info(f"BD: {resultado['inserted']}/{len(bd_rows)} series escritas "
                    f"({resultado['status']})")
        return resultado
    except Exception as e:
        logger.error(f"BD: fallo al escribir fact_market_series: {e}")
        return {'inserted': 0, 'status': 'FAILED', 'error': str(e)}


# ==============================================================================
# 6b. AUDITORÍA DE CICLO (F3.10)
# ==============================================================================

def auditoria_ciclo(cycle_id, inicio, capturados, fallidos, status, error=None):
    """Registra UNA fila de auditoría por ciclo, incluso si fue SKIPPED.
    source_params: cycle_id + duración + símbolos fallidos (F3.10).
    """
    if not config.DB_WRITE_ENABLED:
        return
    try:
        from db.postgresql_connection import PostgreSQLConnector
        from db.audit_repository import log_sync_run
        db = PostgreSQLConnector(
            config.PG_HOST, config.PG_PORT,
            config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD
        )
        if not db.connect():
            logger.error("BD: auditoría de ciclo no registrada (sin conexión)")
            return
        duracion_s = round((datetime.now(timezone.utc) - inicio).total_seconds(), 1)
        log_sync_run(db, {
            'script_name': config.SCRIPT_NAME_SCRAPER,
            'run_start': inicio,
            'records_fetched': capturados,
            'records_upserted': capturados - len(fallidos),
            'records_failed': len(fallidos),
            'status': status,
            'error_message': error,
            'execution_mode': 'manual',
            'source_params': {
                'cycle_id': str(cycle_id),
                'duracion_s': duracion_s,
                'simbolos_fallidos': sorted(fallidos),
            }
        })
        db.disconnect()
    except Exception as e:
        logger.error(f"BD: auditoría de ciclo falló: {e}")


# ==============================================================================
# 7. FLUJO PRINCIPAL
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

    inicio = datetime.now(timezone.utc)
    cycle_id = uuid.uuid4()
    logger.info(f"SCRAPER LIVE V5 | {inicio.strftime('%Y-%m-%d %H:%M:%S')} UTC "
                f"| BD_WRITE={'ON' if config.DB_WRITE_ENABLED else 'OFF'} "
                f"| ciclo {cycle_id}")

    # Recolectar lista única de símbolos (Primarios y Respaldos)
    todos_simbolos = set()
    for cat in CONFIG_ACTIVOS.values():
        for meta in cat.values():
            todos_simbolos.add(meta["primario"])
            todos_simbolos.add(meta["respaldo"])

    # F3.4 · Ordenar por prioridad (críticos primero, luego alfabético)
    lista_ordenada = sorted(list(todos_simbolos), key=lambda s: (_prioridad(s), s))

    # Gate por clase de activo (F2.2): filtrar el símbolo, no abortar el ciclo.
    from db.sessions import asset_class_de, en_ventana
    clase_por_simbolo = {s: asset_class_de(s) for s in lista_ordenada}
    lista_en_ventana = [s for s in lista_ordenada if en_ventana(clase_por_simbolo[s])]

    if not lista_en_ventana:
        logger.warning("Ningún símbolo dentro de ventana: ciclo SKIPPED (auditoría).")
        auditoria_ciclo(cycle_id, inicio, 0, [], 'SKIPPED',
                        'todos los símbolos fuera de su ventana de clase')
        sys.exit(0)

    for s in lista_ordenada:
        if s in lista_en_ventana:
            continue
        logger.info(f"Fuera de ventana ({clase_por_simbolo[s]}) — omitido: {s}")

    # F3.1 · Batch único para equity/ETF (america); individual para el resto
    batch_data = fetch_batch_from_scanner(lista_en_ventana, cycle_id=cycle_id)
    if batch_data:
        logger.info(f"Batch /america/scan devolvió {len(batch_data)} símbolos")

    fallos_por_exchange: Counter = Counter()
    batch_buffer = []
    simbolos_fallidos = []
    capturados = 0

    # F3.4 · Circuit breaker por exchange: un exchange roto no aborta el ciclo
    exchanges_rotos = set()

    for i, symbol in enumerate(lista_en_ventana):
        prefijo = symbol.split(":")[0]
        if prefijo in exchanges_rotos:
            logger.warning(f"CIRCUIT BREAKER: exchange {prefijo} bloqueado, omitiendo {symbol}")
            simbolos_fallidos.append(symbol)
            continue

        folder_clean = sanitizar_nombre(symbol)
        path_base = os.path.join(BASE_DIR, folder_clean)
        os.makedirs(path_base, exist_ok=True)
        csv_file = os.path.join(path_base, f"{folder_clean}.csv")

        logger.info(f"[{i+1}/{len(lista_en_ventana)}] {symbol}...")

        # 1er intento: batch (si el endpoint lo devolvió)
        res = batch_data.get(symbol)

        # Fallback individual (FX/crypto/futuros/TVC, o no devuelto por el batch)
        if res is None:
            res = fetch_from_scanner(symbol, cycle_id=cycle_id)

            # Reintento con backoff progresivo ante rate-limit (429)
            if res == "429":
                for espera in ESPERAS_BACKOFF_429:
                    logger.warning(f"BLOQUEO 429 {symbol}. Backoff {espera}s...")
                    time.sleep(espera)
                    res = fetch_from_scanner(symbol, cycle_id=cycle_id)
                    if res != "429":
                        break

        if isinstance(res, dict):
            fallos_por_exchange[prefijo] = 0
            capturados += 1
            # CSV (sin cambios) — buffer raw / fallback
            df_new = pd.DataFrame([res])
            escribir_fila_csv(csv_file, df_new)
            rotar_datos(csv_file, folder_clean)

            # BD (nuevo) — acumular al batch para un solo flush por ciclo
            if config.DB_WRITE_ENABLED:
                batch_buffer.append(res)
        else:
            fallos_por_exchange[prefijo] += 1
            simbolos_fallidos.append(symbol)
            logger.error(f"FALLO ({fallos_por_exchange[prefijo]} consecutivos en {prefijo}) "
                         f"en {symbol}")
            time.sleep(PAUSA_ENFRIAMIENTO_ERROR)

            # F3.4 · Breaker POR EXCHANGE (no global): sigue con los demás
            if fallos_por_exchange[prefijo] >= MAX_FALLOS_CONSECUTIVOS:
                exchanges_rotos.add(prefijo)
                logger.warning(f"CIRCUIT BREAKER: exchange {prefijo} superó "
                               f"{MAX_FALLOS_CONSECUTIVOS} fallos. Sigue el resto del ciclo.")

        # Pausa aleatoria para simular tráfico humano (solo en fallback individual)
        if i < len(lista_en_ventana) - 1 and res is not None and symbol not in batch_data:
            time.sleep(random.uniform(0.4, 1.2))

    # Flush del batch completo al final del ciclo (1 round-trip a BD)
    if config.DB_WRITE_ENABLED and batch_buffer:
        resultado = flush_radar_batch(batch_buffer, cycle_id=cycle_id)
        if resultado.get('status') == 'SUCCESS':
            batch_buffer.clear()

    # F3.10 · Auditoría de ciclo
    estado = 'SUCCESS' if (capturados and not simbolos_fallidos) else \
             ('PARTIAL_FAIL' if capturados else 'FAILED')
    auditoria_ciclo(cycle_id, inicio, capturados, simbolos_fallidos, estado,
                    None if estado == 'SUCCESS' else f"{len(simbolos_fallidos)} símbolos fallidos")

    if args.consolidate:
        consolidar_analisis()

    logger.info(f"CICLO {cycle_id} FINALIZADO: {capturados} capturados, "
                f"{len(simbolos_fallidos)} fallidos ({estado})")


if __name__ == "__main__":
    main()
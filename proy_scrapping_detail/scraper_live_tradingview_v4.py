"""
🚀 RADAR INTERMARKET - SCORER & PERSISTENCE ENGINE V4
====================================================
Script: scraper_live_tradingview_v4.py
Author: Wilson Zauma
Date: 2026-03-16 (v3) · 2026-08-22 (v4)
Version: 4.0 (Universo ampliado + blindaje lock/cabecera + pausas rápidas)

DESCRIPCIÓN:
    Motor de captura de alta fidelidad para el ecosistema de trading.
    Extrae métricas de momentum, volumen y liquidez directamente desde
    el scanner de TradingView sin dependencias de librerías de terceros.

CAMBIOS V4 (respecto a V3):
    - Universo ampliado vía config.py externo (113 primarios+respaldos).
    - Lock exclusivo fcntl anti-solapamiento de ciclos cron.
    - Cabecera condicional robusta (fichero inexistente O vacío).
    - Pausas entre símbolos reducidas (0,4–1,2 s): ciclo ~135 s para */3.
    - Backoff progresivo ante 429 (15/45/120s) + circuit breaker (3 fallos).

CAPACIDADES:
    - Extracción Zero-Library (Requests-based).
    - Estandarización UTC Nativa.
    - Gestión de Persistencia: Rolling de 7 días (LIVE) y Archivo Mensual.
    - Redundancia Dinámica: Fallback automático entre Primarios y Respaldos.

ESTRUCTURA DE DATOS:
    - DATOS_LIVE_2/{SYMBOL}/{SYMBOL}.csv
    - DATOS_LIVE_2/{SYMBOL}_{YYYYMM}/historico_{SYMBOL}_{YYYYMM}.csv

MODO USO :
  (defecto) Solo descarga y organiza los archivos.
    - python3 scraper_live_tradingview_v4.py

  Genera un archivo único con la última foto de todos los activos
  para que verifiques la salud de los datos rápidamente.
    - python3 scraper_live_tradingview_v4.py --consolidate

"""

import os
import sys
import time
import random
import argparse
import fcntl
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
from config import CONFIG_ACTIVOS

# ==============================================================================
# 1. CONFIGURACIÓN DE ACTIVOS Y ENDPOINTS (Basado en Testing 07)
# ==============================================================================
# CONFIG_ACTIVOS = {
#     "NASDAQ": {
#         "QQQ": {"primario": "NASDAQ:QQQ", "respaldo": "CME_MINI:NQ1!"},
#         'SPY': {"primario": "AMEX:SPY", "respaldo": "AMEX:SPY"},
#         'AAPL': {"primario": "NASDAQ:AAPL", "respaldo": "NASDAQ:AAPL"},
#         'MSFT': {"primario": "NASDAQ:MSFT", "respaldo": "NASDAQ:MSFT"},
#         'NVDA': {"primario": "NASDAQ:NVDA", "respaldo": "NASDAQ:NVDA"},
#         'AMZN': {"primario": "NASDAQ:AMZN", "respaldo": "NASDAQ:AMZN"},
#         'GOOGL': {"primario": "NASDAQ:GOOGL", "respaldo": "NASDAQ:GOOGL"},
#         'META': {"primario": "NASDAQ:META", "respaldo": "NASDAQ:META"},
#         'TSLA': {"primario": "NASDAQ:TSLA", "respaldo": "NASDAQ:TSLA"},
#         'AVGO': {"primario": "NASDAQ:AVGO", "respaldo": "NASDAQ:AVGO"},
#         'NFLX': {"primario": "NASDAQ:NFLX", "respaldo": "NASDAQ:NFLX"},
#         'ADBE': {"primario": "NASDAQ:ADBE", "respaldo": "NASDAQ:ADBE"},
#         'QCOM': {"primario": "NASDAQ:QCOM", "respaldo": "NASDAQ:QCOM"},
#         'ABNB': {"primario": "NASDAQ:ABNB", "respaldo": "NASDAQ:ABNB"},
#         'XOM': {"primario": "NYSE:XOM", "respaldo": "NYSE:XOM"},
#     }
# }

CAMPOS = "close,volume,RSI,CCI20,BBPower,ADX,Pivot.M.Camarilla.R3,Perf.W,change"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
BASE_DIR = "DATOS_LIVE"

# Resiliencia anti-bloqueo (rate-limit / protección de IP)
ESPERAS_BACKOFF_429 = [15, 45, 120]   # Backoff progresivo ante 429 (total máx: 180s)
PAUSA_ENFRIAMIENTO_ERROR = 20         # Pausa extra tras un fallo aislado
MAX_FALLOS_CONSECUTIVOS = 3           # Circuit breaker: aborta el ciclo completo

# ==============================================================================
# 2. MOTOR DE EXTRACCIÓN (Método Testing 07)
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

            # También guardar versión ISO para legibilidad (opcional)
            data["fecha_iso"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            data["simbolo"] = symbol
            return data
        elif response.status_code == 429:
            return "429"
        return None
    except Exception as e:
        print(f" Error conexión {symbol}: {e}")
        return None

def sanitizar_nombre(nombre):
    """Limpia caracteres especiales para nombres de carpetas y archivos."""
    return nombre.replace(":", "-").replace("!", "")

# ==============================================================================
# 3. GESTIÓN DE ARCHIVOS Y ROTACIÓN (7 Días + Histórico Mensual)
# ==============================================================================

def rotar_datos(file_path, folder_name):
    """Mueve registros antiguos a históricos mensuales y limpia el archivo LIVE."""
    if not os.path.exists(file_path): return
    try:
        df = pd.read_csv(file_path)
        if df.empty: return

        # ✅ ACTUALIZADO: timestamp_utc ahora es numérico (segundos)
        # Convertir de segundos a datetime para comparación
        df['timestamp_dt'] = pd.to_datetime(df['timestamp_utc'], unit='s', utc=True)

        ahora = datetime.now(timezone.utc)
        limite_7_dias = ahora - timedelta(days=7)

        historico_df = df[df['timestamp_dt'] <= limite_7_dias].copy()
        live_df = df[df['timestamp_dt'] > limite_7_dias].copy()

        # Eliminar columna temporal antes de guardar
        if 'timestamp_dt' in historico_df.columns:
            historico_df = historico_df.drop(columns=['timestamp_dt'])
        if 'timestamp_dt' in live_df.columns:
            live_df = live_df.drop(columns=['timestamp_dt'])

        if not historico_df.empty:
            # Agrupar por mes/año para el histórico
            historico_df['mes_folder'] = pd.to_datetime(historico_df['timestamp_utc'], unit='s', utc=True).dt.strftime("%Y%m")

            for mes, data_mes in historico_df.groupby('mes_folder'):
                hist_dir = os.path.join(BASE_DIR, f"{folder_name}_{mes}")
                os.makedirs(hist_dir, exist_ok=True)
                hist_file = os.path.join(hist_dir, f"historico_{folder_name}_{mes}.csv")

                # Append al histórico mensual
                data_mes_drop = data_mes.drop(columns=['mes_folder'])
                escribir_header = not os.path.exists(hist_file) or os.path.getsize(hist_file) == 0
                data_mes_drop.to_csv(
                    hist_file, mode='a', header=escribir_header, index=False
                )

            # Sobrescribir LIVE solo con los últimos 7 días
            live_df.to_csv(file_path, index=False)

    except Exception as e:
        print(f" Error rotación {folder_name}: {e}")

def consolidar_analisis():
    """
    Consolida la última captura de cada símbolo en un CSV único para testeo.
    El archivo se guarda dentro de DATOS_LIVE/consolidados/
    """
    print("\n--- 📊 GENERANDO CONSOLIDADO INTEGRAL DE TEST ---")

    # Crear carpeta de consolidados dentro de DATOS_LIVE
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
                    print(f"   ⚠️ Error leyendo {file}: {e}")

    if filas:
        final_df = pd.concat(filas, ignore_index=True)
        ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

        # Guardar dentro de DATOS_LIVE/consolidados/
        filename = f"consolidado_{ts}.csv"
        out_path = os.path.join(consolidados_dir, filename)

        final_df.to_csv(out_path, index=False)
        print(f"✅ Consolidado generado: {out_path}")
        print(f"📊 Total símbolos: {len(final_df)}")
    else:
        print("⚠️ No se encontraron datos para consolidar")


# ==============================================================================
# 4. FLUJO PRINCIPAL
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Scraper Live V4 - TradingView Scanner")
    parser.add_argument('--consolidate', action='store_true', help="Genera un CSV consolidado al finalizar.")
    args = parser.parse_args()

    lock_path = "/tmp/scraper_live_tradingview_v4.lock"
    lock_fh = open(lock_path, "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("⚠️ Ya existe una instancia del scraper en ejecución. Saliendo sin duplicar escrituras.")
        sys.exit(0)

    print(f"--- 🚀 SCRAPER LIVE V4 | 🕒 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC ---")

    # Recolectar lista única de símbolos (Primarios y Respaldos)
    todos_simbolos = set()
    for cat in CONFIG_ACTIVOS.values():
        for meta in cat.values():
            todos_simbolos.add(meta["primario"])
            todos_simbolos.add(meta["respaldo"])

    lista_ordenada = sorted(list(todos_simbolos))

    fallos_consecutivos = 0
    for i, symbol in enumerate(lista_ordenada):
        folder_clean = sanitizar_nombre(symbol)
        path_base = os.path.join(BASE_DIR, folder_clean)
        os.makedirs(path_base, exist_ok=True)
        csv_file = os.path.join(path_base, f"{folder_clean}.csv")

        print(f"🔎 [{i+1}/{len(lista_ordenada)}] {symbol}... (ok)", end=" ", flush=True)

        res = fetch_from_scanner(symbol)

        # Reintento con backoff progresivo ante rate-limit (429)
        if res == "429":
            for espera in ESPERAS_BACKOFF_429:
                print(f"⚠️ BLOQUEO 429. Backoff {espera}s...", end=" ", flush=True)
                time.sleep(espera)
                res = fetch_from_scanner(symbol)
                if res != "429":
                    break

        if isinstance(res, dict):
            fallos_consecutivos = 0
            # Guardar en su respectiva base de datos
            df_new = pd.DataFrame([res])
            escribir_header = not os.path.exists(csv_file) or os.path.getsize(csv_file) == 0
            df_new.to_csv(csv_file, mode='a', header=escribir_header, index=False)

            # Limpieza y rotación
            rotar_datos(csv_file, folder_clean)
            print("")
        else:
            fallos_consecutivos += 1
            print(f"❌ FALLO ({fallos_consecutivos} consecutivos)")
            time.sleep(PAUSA_ENFRIAMIENTO_ERROR)

            # Circuit breaker: abortar el ciclo si el endpoint sigue limitando
            if fallos_consecutivos >= MAX_FALLOS_CONSECUTIVOS:
                print(f"🛑 CIRCUIT BREAKER: {fallos_consecutivos} fallos consecutivos. "
                      f"Abortando ciclo para proteger la IP (reintentará el próximo cron).")
                sys.exit(1)

        # Pausa aleatoria para simular tráfico humano
        if i < len(lista_ordenada) - 1:
            # time.sleep(random.uniform(2.5, 5.0))
            time.sleep(random.uniform(0.4, 1.2))

    if args.consolidate:
        consolidar_analisis()

    print(f"\n---  PROCESO FINALIZADO ---")

if __name__ == "__main__":
    main()

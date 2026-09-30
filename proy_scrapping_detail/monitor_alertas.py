#!/usr/bin/env python3
"""
MONITOR DE ALERTAS - FASE 3.11
==============================
Script: monitor_alertas.py
Descripción: Ejecutado por cron cada 9 min. Solo actúa DENTRO de la ventana
             NYSE (fuera de ella no consulta nada). Verifica varias condiciones
             y envía un ÚNICO mensaje de Telegram si alguna se cumple:

   1. Radar (nuevo): `now() - max(timestamp_utc) > 10 min` sobre
      fact_market_series → el scraper (que actualiza la BD cada 3 min) se cayó.
   2. CSV críticos (nuevo): última fila de NASDAQ-QQQ / OANDA-XAUUSD /
      OANDA-EURUSD con antigüedad > 10 min (se lee solo la cola del CSV).
   3. Heatmap: `now() - max(timestamp_utc) > intervalo_heatmap + gracia`
      sobre fact_heatmap_snapshot, con ventana de gracia por slot.
   4. Auditoría (nuevo): filas FAILED en audit_sync_run (últimos 30 min).
   5. 429 recurrente: más de MONITOR_MAX_429 menciones de 429 en logs (1 h).
   6. DB_WRITE_ENABLED=false: los scrapers no escriben en BD.

Este monitor es SOLO lectura (BD + CSV): NO llama al endpoint de TradingView.
El cooldown (20 min ≈ 2 ciclos) evita reenviar la MISMA condición en cada
corrida; se identifica por el conjunto de códigos de alerta (no por el texto,
que cambia con los minutos).

Uso:
    python monitor_alertas.py

Dependencias:
    - requests
    - psycopg2
    - python-dotenv
"""

import hashlib
import json
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_logger():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger('monitor_alertas')


logger = get_logger()

# --- Umbrales (por env, con default) ---
MONITOR_INTERVALO_MIN = int(os.getenv("MONITOR_INTERVALO_MIN", "9"))      # cadencia del cron
RADAR_MAX_EDAD_MIN = int(os.getenv("MONITOR_RADAR_MAX_EDAD_MIN", "10"))  # radar/CSV
INTERVALO_HEATMAP_MIN = int(os.getenv("MONITOR_HEATMAP_INTERVALO_MIN", "15"))
GRACIA_HEATMAP_MIN = int(os.getenv("MONITOR_HEATMAP_GRACIA_MIN", "5"))
AUDIT_VENTANA_MIN = int(os.getenv("MONITOR_AUDIT_VENTANA_MIN", "30"))
COOLDOWN_MIN = int(os.getenv("MONITOR_ALERTAS_COOLDOWN_MIN", "20"))      # ≈ 2 ciclos
MONITOR_MAX_429 = int(os.getenv("MONITOR_MAX_429", "5"))

# CSV críticos del radar (carpeta por símbolo con el mismo nombre).
CSV_CRITICOS = ("NASDAQ-QQQ", "OANDA-XAUUSD", "OANDA-EURUSD")

# Estado del cooldown (ignorado por git: .gitignore incluye /logs_ejecucion).
ESTADO_PATH = Path(__file__).parent / "logs_ejecucion" / "monitor_alertas_state.json"


def slot_heatmap(ahora, intervalo_min: int):
    """Devuelve (slot_vencido, minutos_desde_slot) alineados al cron `*/N`.

    El slot más reciente es el múltiplo de `intervalo_min` dentro de la hora
    (`:00`, `:15`, `:30`, `:45` para 15 min). El cron del heatmap añade ~20 s
    internos, de modo que en los primeros minutos tras un slot la corrida
    sigue en vuelo y todavía no debe considerarse caída.
    """
    slot = ahora.replace(
        minute=ahora.minute - (ahora.minute % intervalo_min), second=0, microsecond=0
    )
    return slot, (ahora - slot).total_seconds() / 60


def revolver_http_errors() -> list:
    """Lee el log del radar/calendario buscando '429' en las últimas entradas."""
    import config
    hits = []
    dirs = [getattr(config, 'LOG_DIR', None) or 'LOGS', '../LOGS']
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            if not (fname.endswith('.log')):
                continue
            path = os.path.join(d, fname)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if (time.time() - mtime) < 3600:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                    for line in fh:
                        if '429' in line:
                            hits.append(f"{fname}: {line.strip()[:160]}")
    return hits


def leer_ultimo_ts_csv(path: str, tail_bytes: int = 65536):
    """Devuelve (datetime_utc, error) del último `timestamp_utc` de un CSV.

    Eficiente: lee la cabecera + SOLO los últimos `tail_bytes` del archivo, no
    el CSV completo. Se descarta la primera línea del bloque por si quedó
    parcialmente cortada.
    """
    try:
        if not os.path.exists(path):
            return None, "no existe"
        with open(path, "rb") as f:
            header = f.readline().decode("utf-8", "ignore").strip().split(",")
            try:
                idx = header.index("timestamp_utc")
            except ValueError:
                return None, "sin columna timestamp_utc"
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                return None, "archivo vacío"
            n = min(tail_bytes, size)
            f.seek(size - n)
            data = f.read().decode("utf-8", "ignore")
        lineas = data.splitlines()
        if size > n and lineas:
            lineas = lineas[1:]  # primera línea probablemente parcial
        lineas = [ln for ln in lineas if ln.strip()]
        if not lineas:
            return None, "sin filas de datos"
        campos = lineas[-1].split(",")
        if idx >= len(campos):
            return None, "columna timestamp_utc fuera de rango"
        return datetime.fromtimestamp(float(campos[idx]), tz=timezone.utc), None
    except Exception as e:
        return None, f"error leyendo CSV: {e}"


def _cargar_estado() -> dict:
    try:
        with open(ESTADO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _debe_enviar(clave: str) -> bool:
    """True si la condición cambió o pasó el cooldown desde el último envío."""
    estado = _cargar_estado()
    if estado.get("clave") != clave:
        return True
    fecha = estado.get("fecha")
    if not fecha:
        return True
    try:
        dt = datetime.fromisoformat(fecha)
    except Exception:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 60 >= COOLDOWN_MIN


def _marcar_envio(clave: str) -> None:
    try:
        ESTADO_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ESTADO_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"clave": clave, "fecha": datetime.now(timezone.utc).isoformat()},
                f, indent=2,
            )
    except Exception as e:
        logger.warning(f"No se pudo guardar estado de cooldown: {e}")


def main():
    import config
    from db.postgresql_connection import PostgreSQLConnector
    from db.sessions import en_ventana_nyse

    # --- Solo ventana NYSE: fuera de ella no se consulta nada (ni la BD) ---
    try:
        en_ventana = en_ventana_nyse()
    except Exception as e:
        logger.error(f"No se pudo evaluar la ventana NYSE ({e}); se omite el monitoreo.")
        return
    if not en_ventana:
        logger.info("Fuera de la ventana NYSE: se omite el monitoreo.")
        return

    # --- Telegram (mejor esfuerzo; no debe matar el monitor) ---
    token = os.getenv('TELEGRAM_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    # Identificador del servidor emisor (evita confundir prod con develop).
    server_id = os.getenv('SERVER_ID', '').strip() or socket.gethostname()

    def notificar(texto: str):
        import requests
        if not token or not chat_id:
            logger.warning(f"Sin TELEGRAM_TOKEN/CHAT_ID: no se envió alerta\n{texto}")
            return
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            r = requests.post(url, json={"chat_id": chat_id, "text": texto}, timeout=15)
            if r.status_code == 200:
                logger.info("Alerta enviada por Telegram")
            else:
                logger.error(f"Telegram respondió {r.status_code}: {r.text[:200]}")
        except Exception as e:
            logger.error(f"Error enviando Telegram: {e}")

    db = PostgreSQLConnector(
        config.PG_HOST, config.PG_PORT, config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD
    )
    if not db.connect():
        logger.error("No se pudo conectar a la BD; se omite la verificación.")
        sys.exit(1)

    # alertas: lista de (codigo_estable, texto). El código identifica la
    # condición (para el cooldown) sin los valores variables del texto.
    alertas = []

    def add(codigo: str, texto: str):
        alertas.append((codigo, texto))

    try:
        ahora = datetime.now(timezone.utc)

        # --- A3: DB_WRITE_ENABLED=OFF ---
        if not config.DB_WRITE_ENABLED:
            add("db_write_off",
                "⚠️ DB_WRITE_ENABLED=false en proy_scrapping_detail/.env "
                "(los scrapers no escriben en BD)")

        # --- A1: heatmap fresco (timestamp_utc está indexado: consulta ~2 ms) ---
        row = db.execute_query(
            "SELECT MAX(timestamp_utc) AS max_ts FROM fact_heatmap_snapshot"
        )
        max_ts = (row[0]['max_ts'] if row and row[0] else None)
        if max_ts is None:
            add("heatmap_sin_datos", "⚠️ fact_heatmap_snapshot sin registros en ventana")
        else:
            antiguedad_min = (ahora - max_ts).total_seconds() / 60
            umbral_min = INTERVALO_HEATMAP_MIN + GRACIA_HEATMAP_MIN
            slot, desde_slot = slot_heatmap(ahora, INTERVALO_HEATMAP_MIN)
            if desde_slot < GRACIA_HEATMAP_MIN:
                logger.info(
                    f"Ventana de gracia ({desde_slot:.1f} min desde el slot "
                    f"{slot:%H:%M}): corrida del heatmap aún en vuelo, no se alerta."
                )
            elif antiguedad_min > umbral_min:
                slots_perdidos = antiguedad_min / INTERVALO_HEATMAP_MIN
                add("heatmap_viejo",
                    f"⚠️ Heatmap sin datos frescos: último hace {antiguedad_min:.1f} min "
                    f"(umbral {umbral_min:.0f} min; {slots_perdidos:.1f} slots perdidos) "
                    f"[max={max_ts.isoformat()}]")
            else:
                logger.info(f"heatmap OK: {antiguedad_min:.1f} min de antigüedad.")

        # --- A4: radar fresco (fact_market_series, cada 3 min) ---
        row = db.execute_query(
            "SELECT MAX(timestamp_utc) AS max_ts FROM fact_market_series"
        )
        max_ts = (row[0]['max_ts'] if row and row[0] else None)
        if max_ts is None:
            add("radar_sin_datos", "⚠️ Radar: fact_market_series sin registros en ventana")
        else:
            edad_min = (ahora - max_ts).total_seconds() / 60
            if edad_min > RADAR_MAX_EDAD_MIN:
                add("radar_viejo",
                    f"⚠️ Radar sin datos frescos: último hace {edad_min:.1f} min "
                    f"(umbral {RADAR_MAX_EDAD_MIN} min) [max={max_ts.isoformat()}]")
            else:
                logger.info(f"radar OK: {edad_min:.1f} min de antigüedad.")

        # --- A5: CSV críticos del radar (se lee solo la cola del archivo) ---
        raiz = str(config.FILES_OUTPUT_SCRAPPING)
        for sym in CSV_CRITICOS:
            ruta = os.path.join(raiz, sym, f"{sym}.csv")
            ts, err = leer_ultimo_ts_csv(ruta)
            if ts is None:
                add(f"csv_falta:{sym}", f"⚠️ CSV {sym}: {err}")
            else:
                edad_min = (ahora - ts).total_seconds() / 60
                if edad_min > RADAR_MAX_EDAD_MIN:
                    add(f"csv_viejo:{sym}",
                        f"⚠️ CSV {sym} sin frescura: último hace {edad_min:.1f} min "
                        f"(umbral {RADAR_MAX_EDAD_MIN} min)")
                else:
                    logger.info(f"CSV {sym} OK: {edad_min:.1f} min.")

        # --- A6: auditoría con FAILED reciente ---
        rows = db.execute_query(
            "SELECT script_name, count(*) AS n FROM audit_sync_run "
            "WHERE status='FAILED' "
            f"AND run_start > now() - interval '{AUDIT_VENTANA_MIN} min' "
            "GROUP BY script_name ORDER BY n DESC"
        )
        # execute_query devuelve [{'rows_affected': N}] cuando no hay filas.
        fallos = [r for r in rows if 'script_name' in r]
        for r in fallos:
            add(f"audit_failed:{r['script_name']}",
                f"⚠️ audit_sync_run FAILED: {r['script_name']} ×{r['n']} "
                f"(últimos {AUDIT_VENTANA_MIN} min)")
        if not fallos:
            logger.info("auditoría OK: sin FAILED recientes.")

        # --- A2: 429 recurrente (última hora en logs) ---
        anomalias_429 = revolver_http_errors()
        if len(anomalias_429) > MONITOR_MAX_429:
            add("http_429",
                f"⚠️ {len(anomalias_429)} menciones de HTTP 429 en la última hora (logs)")

        # --- Único mensaje (cooldown por conjunto de códigos) ---
        if alertas:
            clave = hashlib.sha1(
                "\n".join(sorted(c for c, _ in alertas)).encode("utf-8")
            ).hexdigest()
            if _debe_enviar(clave):
                msg = (f"🚨 MONITOR HEATMAP_STOCK [{server_id}]\n"
                       + "\n".join(f"• {t}" for _, t in alertas))
                logger.info(msg)
                notificar(msg)
                _marcar_envio(clave)
            else:
                logger.info(
                    f"{len(alertas)} alerta(s) suprimida(s) por cooldown "
                    f"({COOLDOWN_MIN} min)."
                )
        else:
            logger.info("Sin alertas: todo OK (radar/heatmap frescos, DB_WRITE on, "
                        "CSV OK, sin 429, audit OK).")

    finally:
        db.disconnect()


if __name__ == "__main__":
    main()

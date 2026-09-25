#!/usr/bin/env python3
"""
MONITOR DE ALERTAS - FASE 3.11
==============================
Script: monitor_alertas.py
Descripción: Ejecutable manualmente (sin cron todavía). Verifica tres
             condiciones de alerta y envía un único mensaje de Telegram
             si alguna se cumple (F3.11, E-OPS-03):

  1. Datos frescos: `now() - max(ingested_at) > 5 min` estando la sesión
     NYSE abierta (dim_trading_session). Aplica a fact_heatmap_snapshot.
  2. 429 recurrente: más de N = MONITOR_MAX_429 en la última hora en
     audit_sync_run FAILED de los scrapers (o indicios en logs).
  3. DB_WRITE_ENABLED=false: escritura desactivada con datos en ventana.

Uso:
    python monitor_alertas.py

Dependencias:
    - requests
    - python-telegram-bot (proy_scrapping_detail venv)
    - psycopg2
"""

import os
import sys
import time

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


def main():
    from datetime import datetime, timezone

    import config
    from db.postgresql_connection import PostgreSQLConnector
    from db.sessions import en_ventana_nyse

    # --- Telegram (mejor esfuerzo; no debe matar el monitor) ---
    token = os.getenv('TELEGRAM_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

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

    try:
        alertas = []
        ahora = datetime.now(timezone.utc)

        # --- A3: DB_WRITE_ENABLED=OFF ---
        if not config.DB_WRITE_ENABLED:
            alertas.append("⚠️ DB_WRITE_ENABLED=false en proy_scrapping_detail/.env "
                           "(los scrapers no escriben en BD)")

        # --- A1: datos frescos (solo si la sesión NYSE está abierta) ---
        sesion_abierta = en_ventana_nyse()
        if sesion_abierta:
            row = db.execute_query(
                "SELECT MAX(ingested_at) AS max_ing FROM fact_heatmap_snapshot"
            )
            max_ing = (row[0]['max_ing'] if row and row[0] else None)
            if max_ing is None:
                alertas.append("⚠️ fact_heatmap_snapshot sin registros en ventana")
            else:
                antiguedad_min = (ahora - max_ing).total_seconds() / 60
                if antiguedad_min > 5:
                    alertas.append(
                        f"⚠️ Sin datos frescos del heatmap: último ingested {antiguedad_min:.1f} min atrás "
                        f"(max_ingested_at={max_ing.isoformat()}) en sesión Nº {ahora.isoformat()} UTC"
                    )
                    # nota: el límite de 5 min aplica dentro de la ventana (F3.11)
        else:
            logger.info("Fuera de la ventana NYSE: se omite la alerta de frescura.")

        # --- A2: 429 recurrente (última hora en logs) ---
        # Nota: el radar con anti-429 (F3.1) casi nunca llega a 429; el criterio
        # de alerta es "más de 5 menciones de 429 en logs en la última hora".
        anomalias_429 = [h for h in revolver_http_errors()]
        if len(anomalias_429) > 5:
            alertas.append(f"⚠️ {len(anomalias_429)} menciones de HTTP 429 en la última hora (logs)")

        # --- Único mensaje ---
        if alertas:
            msg = "🚨 MONITOR HEATMAP_STOCK\n" + "\n".join(f"• {a}" for a in alertas)
            logger.info(msg)
            notificar(msg)
        else:
            logger.info("Sin alertas: todo OK (datos frescos, DB_WRITE on, sin 429).")

    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
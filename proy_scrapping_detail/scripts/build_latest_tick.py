#!/usr/bin/env python3
# file: proy_scrapping_detail/scripts/build_latest_tick.py
"""F4.3 · Job de `latest_market_tick` (último tick por activo).

El radar ya reescribe la tabla en cada ciclo (mismo `timestamp_utc` que
`fact_market_series`, vía `market_service.process_radar_batch`). Este
script es la herramienta operativa de F4.3:

Modos:
  (default / --status)  Estado de `latest_market_tick`: cobertura del
                        universo BATCH (equity/ETF), frescura (max
                        timestamp_utc / fetched_at) y 1 fila por activo.
  --prime               Priming en vivo: llama `POST /america/scan` para el
                        universo equity/ETF (BATCH), proyecta el último tick
                        y hace UPSERT (una fila por activo, E-DSH-04).
                        ADVERTENCIA: herramienta manual; NO añadir a cron
                        (anti-429 del radar).

Uso:
  ./venv/bin/python scripts/build_latest_tick.py --status
  ./venv/bin/python scripts/build_latest_tick.py --prime
"""
import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

PARENT = Path(__file__).resolve().parents[1]
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

import config  # noqa: E402
from db.audit_repository import log_sync_run  # noqa: E402
from db.latest_tick_repository import (  # noqa: E402
    get_latest_ticks,
    upsert_latest_tick_batch,
)
from db.market_repository import get_asset_id_cache  # noqa: E402
from db.postgresql_connection import PostgreSQLConnector  # noqa: E402
from scraper_live_tradingview_v5 import (  # noqa: E402
    BATCH_PREFIJOS,
    CAMPOS_LIST,
    CONFIG_ACTIVOS,
    post_scan,
)

SCRIPT_NAME = "latest_market_tick"
logger = logging.getLogger("latest_tick")


def _watchlist_batch() -> list:
    """Símbolos del universo radar que responde el batch /america/scan."""
    tickers = set()
    for cat in CONFIG_ACTIVOS.values():
        for meta in cat.values():
            tickers.add(meta["primario"])
            tickers.add(meta["respaldo"])
    return sorted(t for t in tickers if t.split(":")[0] in BATCH_PREFIJOS)


def status(db):
    filas = get_latest_ticks(db)
    logger.info("latest_market_tick: %d filas (una por activo)", len(filas))
    if not filas:
        logger.warning("Tabla vacía — usar --prime para el primer poblamiento")
        return

    max_ts = max(f["timestamp_utc"] for f in filas if f["timestamp_utc"])
    max_fetch = max(f["fetched_at"] for f in filas if f["fetched_at"]) or ""
    logger.info("Frescura: max timestamp_utc=%s | max fetched_at=%s",
                max_ts, max_fetch)
    logger.info("Por clase: %s", {c: sum(1 for f in filas if f["asset_class"] == c)
                                  for c in sorted({f["asset_class"] for f in filas})})

    for fila in ("NVDA", "SPY", "QQQ"):
        hit = [f for f in filas if f["symbol"].endswith(f":{fila}")]
        if hit:
            f = hit[0]
            logger.info("  %s | close=%s | rsi(base)=%s | RSI|15=%s | update_mode=%s",
                        f["symbol"], f["close"], f["rsi"], f["rsi_15"],
                        f["update_mode"])


def prime(db, ciclo_inicio):
    asset_cache = get_asset_id_cache(db)
    tickers = _watchlist_batch()
    logger.info("Llamando /america/scan (anti-429 %ss) para %d símbolos…",
                config.REQUEST_DELAY_S, len(tickers))
    resp = post_scan(tickers, CAMPOS_LIST)
    if "_error" in resp:
        logger.error("scan falló: %s", resp.get("_error"))
        return 0

    items = [fila for fila in resp.values() if isinstance(fila, dict)]
    escritas = upsert_latest_tick_batch(db, items, asset_cache)
    log_sync_run(db, {
        "script_name": SCRIPT_NAME,
        "run_start": ciclo_inicio,
        "records_fetched": len(items),
        "records_upserted": escritas,
        "records_failed": 0,
        "status": "SUCCESS",
        "execution_mode": "manual",
        "source_params": {"modo": "prime", "simbolos_batch": len(tickers)},
    })
    logger.info("prime: %d filas en latest_market_tick", escritas)
    return escritas


def main() -> int:
    parser = argparse.ArgumentParser(description="Job F4.3 · latest_market_tick")
    parser.add_argument("--status", action="store_true",
                        help="Estado de la tabla (default)")
    parser.add_argument("--prime", action="store_true",
                        help="Priming: llama /america/scan y upserta 1 fila/activo")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    db = PostgreSQLConnector(
        config.PG_HOST, config.PG_PORT,
        config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD,
    )
    if not db.connect():
        logger.error("No se pudo conectar a PostgreSQL")
        return 1

    ciclo_inicio = datetime.now(timezone.utc)
    try:
        if args.prime:
            prime(db, ciclo_inicio)
        else:
            status(db)
        return 0
    except Exception as e:
        logger.exception("FALLO en job latest_tick: %s", e)
        return 1
    finally:
        db.disconnect()


if __name__ == "__main__":
    sys.exit(main())
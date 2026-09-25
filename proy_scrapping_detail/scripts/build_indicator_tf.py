#!/usr/bin/env python3
# file: proy_scrapping_detail/scripts/build_indicator_tf.py
"""F4.2 · Job de `fact_market_indicator_tf` (indicadores multi-TF en largo).

El radar ya persiste las filas largas en cada ciclo (mismo timestamp_utc
que `fact_market_series`, vía `market_service.process_radar_batch`). Este
script es la herramienta operativa de F4.2:

Modos:
  (default / --status)  Estadísticas de la ventana en `fact_market_indicator_tf`
                        (filas por tf, activos, frescura por símbolo).
  --from-scan           Priming/verificación en vivo: llama `POST
                        /america/scan` para el universo equity/ETF (BATCH),
                        proyecta los bloques `|TF` y los upserta como filas
                        largas (tf='15' y '5', D12). ADVERTENCIA: herramienta
                        manual; NO añadir a cron (anti-429 del radar).
  --verify              Compara `RSI|15` de la tabla (último ciclo) contra
                        `RSI|15` del scan en vivo (aceptación de F4.2).
                        El repintado dentro de la vela permite pequeñas
                        diferencias: se reportan con tolerancia.

Uso:
  ./venv/bin/python scripts/build_indicator_tf.py --status --days 7
  ./venv/bin/python scripts/build_indicator_tf.py --from-scan
  ./venv/bin/python scripts/build_indicator_tf.py --verify --tolerance 0.5
"""
import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PARENT = Path(__file__).resolve().parents[1]
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

import config  # noqa: E402
from db.audit_repository import log_sync_run  # noqa: E402
from db.indicator_repository import (  # noqa: E402
    TFS_INDICADOR,
    asegurar_particion,
    insert_indicator_tf_batch,
)
from db.market_repository import get_asset_id_cache  # noqa: E402
from db.postgresql_connection import PostgreSQLConnector  # noqa: E402
from scraper_live_tradingview_v5 import (  # noqa: E402
    BATCH_PREFIJOS,
    CAMPOS_LIST,
    CONFIG_ACTIVOS,
    post_scan,
)

SCRIPT_NAME = "indicator_tf"
logger = logging.getLogger("indicator_tf")


def _watchlist_batch() -> list:
    """Símbolos del universo radar que responde el batch /america/scan."""
    tickers = set()
    for cat in CONFIG_ACTIVOS.values():
        for meta in cat.values():
            tickers.add(meta["primario"])
            tickers.add(meta["respaldo"])
    return sorted(t for t in tickers if t.split(":")[0] in BATCH_PREFIJOS)


def _ventana(args) -> tuple:
    hasta = datetime.now(timezone.utc)
    return hasta - timedelta(days=args.days), hasta


def status(db, desde, hasta):
    rows = db.execute_query(
        """SELECT tf, count(*) AS filas, count(DISTINCT asset_id) AS activos,
                  min(timestamp_utc) AS primer, max(timestamp_utc) AS ultimo
           FROM fact_market_indicator_tf
           WHERE timestamp_utc >= %s AND timestamp_utc < %s
           GROUP BY tf ORDER BY tf""",
        (desde, hasta),
    )
    total = 0
    for r in rows:
        total += r["filas"]
        logger.info("tf=%s | filas=%s | activos=%s | %s → %s",
                    r["tf"], r["filas"], r["activos"],
                    r["primer"], r["ultimo"])
    logger.info("Total filas en ventana: %d", total)
    return rows


def from_scan(db, ciclo_inicio):
    asset_cache = get_asset_id_cache(db)
    tickers = _watchlist_batch()
    logger.info("Llamando /america/scan (anti-429 %ss) para %d símbolos…",
                config.REQUEST_DELAY_S, len(tickers))
    resp = post_scan(tickers, CAMPOS_LIST)
    if "_error" in resp:
        logger.error("scan falló: %s", resp.get("_error"))
        return 0

    items = [fila for fila in resp.values() if isinstance(fila, dict)]
    escritas = insert_indicator_tf_batch(db, items, asset_cache,
                                         tfs=TFS_INDICADOR)
    log_sync_run(db, {
        "script_name": SCRIPT_NAME,
        "run_start": ciclo_inicio,
        "records_fetched": len(items),
        "records_upserted": escritas,
        "records_failed": 0,
        "status": "SUCCESS",
        "execution_mode": "manual",
        "source_params": {"modo": "from-scan", "tfs": list(TFS_INDICADOR),
                          "simbolos_batch": len(tickers)},
    })
    logger.info("from-scan: %d filas largas en fact_market_indicator_tf", escritas)
    return escritas


def verify(db, tolerance, ciclo_inicio):
    asset_cache = get_asset_id_cache(db)
    tickers = _watchlist_batch()
    resp = post_scan(tickers, CAMPOS_LIST)
    if "_error" in resp:
        logger.error("scan falló: %s", resp.get("_error"))
        return 1

    ok = diffs = sin_db = absentes = 0
    peores = []
    for sym, fila in resp.items():
        rsi_scan = fila.get("RSI|15")
        if rsi_scan is None or rsi_scan == "":
            absentes += 1
            continue
        aid = asset_cache.get(sym)
        if aid is None:
            continue
        rows = db.execute_query(
            """SELECT rsi, timestamp_utc FROM fact_market_indicator_tf
               WHERE asset_id=%s AND tf='15'
               ORDER BY timestamp_utc DESC LIMIT 1""", (aid,))
        if not rows:
            sin_db += 1
            continue
        rsi_db = rows[0]["rsi"]
        if rsi_db is None:
            sin_db += 1
            continue
        diff = abs(float(rsi_db) - float(rsi_scan))
        if diff <= tolerance:
            ok += 1
        else:
            diffs += 1
            peores.append((sym, rsi_db, float(rsi_scan), round(diff, 3)))

    logger.info("RSI|15 vs scan en vivo [tol=%s]: %d ok | %d diff | %d sin fila BD | %d sin RSI en scan",
                tolerance, ok, diffs, sin_db, absentes)
    for sym, a, b, d in sorted(peores, key=lambda x: -x[3])[:8]:
        logger.warning("  %s: db=%s scan=%s diff=%s", sym, a, b, d)
    log_sync_run(db, {
        "script_name": SCRIPT_NAME,
        "run_start": ciclo_inicio,
        "records_fetched": ok + diffs + sin_db + absentes,
        "records_upserted": 0,
        "records_failed": diffs,
        "status": "SUCCESS" if diffs == 0 else "FAILED",
        "execution_mode": "manual",
        "source_params": {"modo": "verify", "tolerance": tolerance,
                          "ok": ok, "diffs": diffs, "sin_db": sin_db},
    })
    return 0 if diffs == 0 else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Job F4.2 · fact_market_indicator_tf")
    parser.add_argument("--status", action="store_true",
                        help="Estadísticas de la ventana (default)")
    parser.add_argument("--from-scan", action="store_true",
                        help="Priming: llama /america/scan y upserta filas largas")
    parser.add_argument("--verify", action="store_true",
                        help="Compara RSI|15 BD vs scan en vivo (aceptación F4.2)")
    parser.add_argument("--days", type=int, default=7, help="Ventana (default 7)")
    parser.add_argument("--tolerance", type=float, default=0.5,
                        help="Tolerancia RSI para --verify (default 0.5)")
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
        if args.verify and not args.from_scan:
            codigo = verify(db, args.tolerance, ciclo_inicio)
        elif args.from_scan:
            from_scan(db, ciclo_inicio)
            codigo = 0
        else:
            desde, hasta = _ventana(args)
            logger.info("Ventana: %s → %s (%s días)", desde.isoformat(),
                        hasta.isoformat(), (hasta - desde).days)
            status(db, desde, hasta)
            codigo = 0
        return codigo
    except Exception as e:
        logger.exception("FALLO en job indicator_tf: %s", e)
        return 1
    finally:
        db.disconnect()


if __name__ == "__main__":
    sys.exit(main())
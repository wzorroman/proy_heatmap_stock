#!/usr/bin/env python3
# file: proy_scrapping_detail/scripts/build_market_bar_15m.py
"""F4.1 · Job de agregación de barras de 15 min (`fact_market_bar_15m`).

Implementa la regla de cierre de barra **F4.1b** (M-CAP-03 reformulada,
roadmap v2.3; cierra H21 y E-RAD-15):

    - Último tick en [T_cierre − 20 s, T_cierre − 5 s] → 'definitive'
    - Último tick en [T_cierre − 5 s,  T_cierre + 15 s] → 'provisional'
    - Fuera de ambos rangos                                   → 'unknown'

Uso:
    python scripts/build_market_bar_15m.py                 # últimos 7 días
    python scripts/build_market_bar_15m.py --days 1
    python scripts/build_market_bar_15m.py --since 2026-09-20T00:00:00Z --until 2026-09-23T00:00:00Z
    python scripts/build_market_bar_15m.py --dry-run       # solo reporte

Re-corridas seguras: el upsert ON CONFLICT revisa barras previas cuando
llegan ticks nuevos (p. ej. el muestreo T−10 s de F4.1c) o se corrige data.
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PARENT = Path(__file__).resolve().parents[1]
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

import config  # noqa: E402
from db.audit_repository import log_sync_run  # noqa: E402
from db.bar_repository import (  # noqa: E402
    agrupar_barras,
    ahora_utc,
    leer_sesiones,
    leer_ticks,
    resumen_calidad,
    upsert_barras,
)
from db.postgresql_connection import PostgreSQLConnector  # noqa: E402

SCRIPT_NAME = "bar_15m"

logger = logging.getLogger("bar_15m")


def _parse_iso(texto: str) -> datetime:
    dt = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _ventana(args) -> tuple:
    hasta = _parse_iso(args.until) if args.until else ahora_utc()
    if args.since:
        desde = _parse_iso(args.since)
    else:
        desde = hasta - timedelta(days=args.days)
    return desde, hasta


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Agrega fact_market_series en barras de 15 min (F4.1/F4.1b)"
    )
    parser.add_argument("--days", type=int, default=7,
                        help="Días hacia atrás desde --until (default 7)")
    parser.add_argument("--since", help="Desde (ISO 8601, tz-aware)")
    parser.add_argument("--until", help="Hasta (ISO 8601, tz-aware), default ahora")
    parser.add_argument("--dry-run", action="store_true",
                        help="No escribe BD: solo lee y reporta")
    parser.add_argument("--verbose", action="store_true", help="Log debug")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    desde, hasta = _ventana(args)
    logger.info("Ventana: %s → %s (%s días)", desde.isoformat(),
                hasta.isoformat(), (hasta - desde).days)

    db = PostgreSQLConnector(
        config.PG_HOST, config.PG_PORT,
        config.PG_DATABASE, config.PG_USER, config.PG_PASSWORD,
    )
    if not db.connect():
        logger.error("No se pudo conectar a PostgreSQL")
        return 1

    run_start = ahora_utc()
    try:
        ticks = leer_ticks(db, desde, hasta)
        logger.info("Ticks leídos: %d", len(ticks))
        if not ticks:
            logger.info("Sin ticks en la ventana — nada que agregar")
            return 0

        sesiones = leer_sesiones(db, desde, hasta)
        barras = agrupar_barras(ticks, sesiones_por_dia=sesiones)
        resumen = resumen_calidad(barras)

        logger.info(
            "Barras: %d | definitive=%d (%.1f%%) | provisional=%d (%.1f%%) | "
            "unknown=%d | n_ticks>=3: %.1f%%",
            resumen["total"], resumen["definitive"], resumen["pct_definitive"],
            resumen["provisional"], resumen["pct_provisional"],
            resumen["unknown"], resumen["pct_n_ticks_ge3"],
        )

        if args.dry_run:
            logger.info("DRY-RUN: sin escritura a BD")
            return 0

        # F4.1b: 0% provisional tras un ciclo completo (reporte objetivo)
        escritas = upsert_barras(db, barras)
        log_sync_run(db, {
            "script_name": SCRIPT_NAME,
            "run_start": run_start,
            "records_fetched": len(ticks),
            "records_upserted": escritas,
            "records_failed": 0,
            "status": "SUCCESS",
            "execution_mode": "cron",
            "source_params": {
                "desde_utc": desde.isoformat(),
                "hasta_utc": hasta.isoformat(),
                "barras": resumen["total"],
                "close_quality": {
                    "definitive": resumen["definitive"],
                    "provisional": resumen["provisional"],
                    "unknown": resumen["unknown"],
                },
            },
        })
        logger.info("Job bar_15m completado: %d barras en fact_market_bar_15m",
                    escritas)
        return 0
    except Exception as e:
        logger.exception("FALLO en job bar_15m: %s", e)
        try:
            log_sync_run(db, {
                "script_name": SCRIPT_NAME,
                "run_start": run_start,
                "records_fetched": 0,
                "records_upserted": 0,
                "records_failed": 0,
                "status": "FAILED",
                "error_message": str(e),
                "execution_mode": "cron",
                "source_params": {"desde_utc": desde.isoformat(),
                                  "hasta_utc": hasta.isoformat()},
            })
        except Exception as audit_error:
            logger.error("No se pudo auditar el fallo: %s", audit_error)
        return 1
    finally:
        db.disconnect()


if __name__ == "__main__":
    sys.exit(main())
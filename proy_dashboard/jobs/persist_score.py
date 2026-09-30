"""jobs/persist_score.py — persistencia del score de mercado.

Modos:
  --cycle     Calcula el ciclo actual (latest_market_tick) y hace UPSERT.
  --backfill  Recalcula desde `fact_market_series` (--since obligatorio).
  --dry-run   Calcula e informa, sin escribir.

Cron: cada 3 min (mismo carril que el radar V5, offset +2 min).
"""

from __future__ import annotations

import argparse
import fcntl
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Permite ejecutar el script directamente (python jobs/persist_score.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.container import Container
from core.logging_config import get_logger, setup_global_logging
from core.settings import get_settings

logger = get_logger("jobs.persist_score")

LOCK_PATH = "/tmp/proy_dashboard_persist_score.lock"


def _parse_iso(valor: str) -> datetime:
    dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _cycle(container: Container, args: argparse.Namespace) -> int:
    scores, mercado = container.score_service.calcular_ciclo()
    checksum = container.score_service.checksum_mercado(mercado)
    logger.info(
        "ciclo %s — n=%s momentum=%s radar=%s market=%s zona=%s",
        mercado.timestamp_utc, mercado.n_simbolos, mercado.score_momentum,
        mercado.score_radar, mercado.score_market, mercado.zona,
    )
    if args.dry_run:
        logger.info("dry-run: no se escribe")
        return 0

    detalle = [
        {
            "asset_id": s.asset_id,
            "timestamp_utc": mercado.timestamp_utc,
            "score_general": s.score_general,
            "zona": s.zona,
            "componentes": [asdict(c) for c in s.componentes],
        }
        for s in scores
    ]
    n_detalle = container.score_repo.upsert_detalle(detalle)
    n_agg = container.score_repo.upsert_agg(
        {
            "timestamp_utc": mercado.timestamp_utc,
            "score_momentum": mercado.score_momentum,
            "score_15min": mercado.score_15min,
            "score_radar": mercado.score_radar,
            "score_market": mercado.score_market,
            "zona": mercado.zona,
            "n_simbolos": mercado.n_simbolos,
            "source_checksum": checksum,
        }
    )
    logger.info("escrito detalle=%s agg=%s", n_detalle, n_agg)
    return 0


def _backfill(container: Container, args: argparse.Namespace) -> int:
    if not args.since:
        logger.error("--backfill requiere --since <ISO>")
        return 2
    since = _parse_iso(args.since)
    until = _parse_iso(args.until) if args.until else None

    ciclos = 0
    filas = 0
    for ts, detalle, agg in container.score_service.calcular_desde_series(since):
        if until is not None and ts > until:
            continue
        ciclos += 1
        filas += len(detalle)
        if not args.dry_run:
            container.score_repo.upsert_detalle(detalle)
            container.score_repo.upsert_agg(agg)
    logger.info(
        "backfill %s ciclos, %s filas (dry_run=%s, since=%s)",
        ciclos, filas, args.dry_run, since.isoformat(),
    )
    return 0


def run(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="persist_score")
    parser.add_argument("--cycle", action="store_true", help="calcular el ciclo actual")
    parser.add_argument("--backfill", action="store_true", help="recalcular desde series")
    parser.add_argument("--since", help="ISO datetime de inicio (backfill)")
    parser.add_argument("--until", help="ISO datetime de fin (backfill)")
    parser.add_argument("--dry-run", action="store_true", help="no escribir")
    args = parser.parse_args(argv)

    if args.backfill and not args.since:
        print("--backfill requiere --since <ISO>", file=sys.stderr)
        return 2

    settings = get_settings()
    setup_global_logging(settings)

    # Anti-solapamiento: si otra corrida está activa, salir.
    with open(LOCK_PATH, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            logger.warning("Otra corrida activa; se omite (%s)", LOCK_PATH)
            return 0

        container = Container.build(settings=settings, connect=True)
        if not container.db_habilitada:
            logger.error("BD no configurada; abortando")
            return 3
        if not settings.db_write_enabled and not args.dry_run:
            logger.warning("DB_WRITE_ENABLED=false; nada que hacer")
            return 0

        try:
            if args.backfill:
                return _backfill(container, args)
            return _cycle(container, args)
        except Exception as exc:  # pragma: no cover - defensivo
            logger.exception("Error en persist_score: %s", exc)
            return 1
        finally:
            container.close()


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())

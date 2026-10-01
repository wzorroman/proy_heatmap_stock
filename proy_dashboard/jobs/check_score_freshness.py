"""jobs/check_score_freshness.py — watchdog de frescura del score de mercado.

Falla (exit 5) si el último ciclo de ``fact_market_score_agg`` es más antiguo que
el umbral configurado (``panels.score_max_age_min``, default 20 min). Pensado para
cron cada 10 min: un ``persist_score`` caído se detecta en minutos, no en horas.

Modos:
  (sin flags)        evalúa: exit 0 si fresco, 5 si rancio.
  --max-edad-min N   umbral explícito (sobreescribe la config).
  --dry-run          informa siempre con exit 0.

Códigos de salida:
  0 fresco · 1 error · 2 argumentos · 3 BD no configurada · 5 rancio.

Cron sugerido: ver docs/automatizacion_cronjobs.md (job H).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# Permite ejecutar el script directamente (python jobs/check_score_freshness.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.container import Container
from core.logging_config import get_logger, setup_global_logging
from core.settings import get_settings

logger = get_logger("jobs.check_score_freshness")

UMBRAL_DEFAULT_MIN = 20


def _umbral(settings, override: Optional[float]) -> float:
    if override is not None:
        return float(override)
    return float(settings.business("panels", "score_max_age_min", default=UMBRAL_DEFAULT_MIN))


def run(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="check_score_freshness")
    parser.add_argument(
        "--max-edad-min",
        type=float,
        default=None,
        help="umbral en minutos (default: panels.score_max_age_min)",
    )
    parser.add_argument("--dry-run", action="store_true", help="informa sin fallar")
    args = parser.parse_args(argv)

    settings = get_settings()
    setup_global_logging(settings)
    umbral = _umbral(settings, args.max_edad_min)

    container = Container.build(settings=settings, connect=True)
    if not container.db_habilitada:
        logger.error("BD no configurada; no se puede verificar la frescura del score")
        return 3

    try:
        edad = container.score_repo.fetch_agg_edad_minutos()
    except Exception as exc:  # pragma: no cover - defensivo
        logger.exception("Error consultando fact_market_score_agg: %s", exc)
        return 1
    finally:
        container.close()

    if edad is None:
        logger.error(
            "RANCIO — fact_market_score_agg está vacía (sin ningún ciclo). umbral=%.0f min",
            umbral,
        )
        return 0 if args.dry_run else 5

    if edad > umbral:
        logger.error(
            "RANCIO — último ciclo hace %.1f min (> %.0f min). "
            "Revisa el cron de persist_score.",
            edad,
            umbral,
        )
        return 0 if args.dry_run else 5

    logger.info("FRESCO — último ciclo hace %.1f min (umbral %.0f min)", edad, umbral)
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())

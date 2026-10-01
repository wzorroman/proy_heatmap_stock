"""repositories/score_repo.py — persistencia y lectura del score."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable, Optional, Sequence

from repositories.base import BaseRepository

_INSERT_DETALLE = """
INSERT INTO fact_market_score
    (asset_id, timestamp_utc, score_general, zona, componentes)
VALUES %s
ON CONFLICT (asset_id, timestamp_utc) DO UPDATE SET
    score_general = EXCLUDED.score_general,
    zona          = EXCLUDED.zona,
    componentes   = EXCLUDED.componentes,
    ingested_at   = CURRENT_TIMESTAMP
"""

_INSERT_AGG = """
INSERT INTO fact_market_score_agg
    (timestamp_utc, score_momentum, score_15min, score_radar, score_market,
     zona, n_simbolos, source_checksum)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (timestamp_utc) DO UPDATE SET
    score_momentum = EXCLUDED.score_momentum,
    score_15min    = EXCLUDED.score_15min,
    score_radar    = EXCLUDED.score_radar,
    score_market   = EXCLUDED.score_market,
    zona           = EXCLUDED.zona,
    n_simbolos     = EXCLUDED.n_simbolos,
    source_checksum= EXCLUDED.source_checksum,
    ingested_at    = CURRENT_TIMESTAMP
"""


class ScoreRepository(BaseRepository):
    def upsert_detalle(self, scores: Iterable[dict]) -> int:
        """scores: iterable de dicts con asset_id, timestamp_utc, score_general,
        zona, componentes (dict)."""
        values = [
            (
                s["asset_id"],
                s["timestamp_utc"],
                s.get("score_general"),
                s.get("zona"),
                json.dumps(s.get("componentes", []), default=str),
            )
            for s in scores
        ]
        if not values:
            return 0
        return self.execute_values(_INSERT_DETALLE, values)

    def upsert_agg(self, agg: dict) -> int:
        return self.execute(
            _INSERT_AGG,
            (
                agg["timestamp_utc"],
                agg.get("score_momentum"),
                agg.get("score_15min"),
                agg.get("score_radar"),
                agg.get("score_market"),
                agg.get("zona"),
                agg.get("n_simbolos"),
                agg.get("source_checksum"),
            ),
        )

    def fetch_agg_latest(self) -> Optional[dict]:
        return self.fetch_one(
            "SELECT * FROM fact_market_score_agg ORDER BY timestamp_utc DESC LIMIT 1"
        )

    def fetch_agg_edad_minutos(self) -> Optional[float]:
        """Minutos desde el último ciclo agregado.

        Devuelve ``None`` si la tabla está vacía (no hay ningún ciclo), que el
        watchdog trata como rancio. ``now()`` y ``timestamp_utc`` son timestamptz,
        así que la resta es un interval sin ambigüedad de zona horaria.
        """
        row = self.fetch_one(
            "SELECT now() - max(timestamp_utc) AS edad FROM fact_market_score_agg"
        )
        if not row or row.get("edad") is None:
            return None
        return row["edad"].total_seconds() / 60.0

    def fetch_agg_history(
        self, since: datetime, until: Optional[datetime] = None
    ) -> list[dict]:
        if until:
            return self.fetch(
                "SELECT * FROM fact_market_score_agg "
                "WHERE timestamp_utc BETWEEN %s AND %s ORDER BY timestamp_utc",
                (since, until),
            )
        return self.fetch(
            "SELECT * FROM fact_market_score_agg "
            "WHERE timestamp_utc >= %s ORDER BY timestamp_utc",
            (since,),
        )

    def fetch_detalle(self, since: datetime) -> list[dict]:
        return self.fetch(
            "SELECT * FROM fact_market_score WHERE timestamp_utc >= %s "
            "ORDER BY timestamp_utc, asset_id",
            (since,),
        )

    def latest_cycle_timestamp(self) -> Optional[datetime]:
        row = self.fetch_one("SELECT max(timestamp_utc) AS ts FROM latest_market_tick")
        return row["ts"] if row else None

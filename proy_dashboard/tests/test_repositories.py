"""Tests de la Fase 3 — repositorios (solo SQL).

  - Degradación sin conector (unitario, sin BD).
  - Integración de lectura contra la BD real (se salta si no está accesible).
  - Roundtrip de escritura del score contra la BD scratch del docker.
"""

from datetime import datetime, timezone

import pytest

from repositories import (
    BaseRepository,
    EventsRepository,
    HeatmapRepository,
    LatestTickRepository,
    ScoreRepository,
    SeriesRepository,
    SessionRepository,
)


# ── Degradación sin conector ─────────────────────────────────────────────────
def test_repos_sin_conector_degradan():
    for repo in (
        BaseRepository(),
        LatestTickRepository(),
        ScoreRepository(),
        HeatmapRepository(),
        EventsRepository(),
        SeriesRepository(),
        SessionRepository(),
    ):
        assert repo.habilitado is False

    assert LatestTickRepository().fetch_all() == []
    assert LatestTickRepository().max_timestamp() is None
    assert HeatmapRepository().fetch_latest() == []
    assert HeatmapRepository().vol_map() == {}
    assert EventsRepository().fetch_eventos() == []
    assert ScoreRepository().fetch_agg_latest() is None
    assert ScoreRepository().upsert_agg({"timestamp_utc": datetime.now(timezone.utc)}) == 0


# ── Integración de lectura (BD real) ─────────────────────────────────────────
def test_latest_tick_repo(live_connector):
    repo = LatestTickRepository(live_connector)
    rows = repo.fetch_all()

    assert rows, "latest_market_tick sin filas"
    claves = set(rows[0].keys())
    for c in ("asset_id", "symbol", "asset_class", "timestamp_utc", "close",
              "change_pct", "rsi", "rsi_15", "adx_15", "logical_key"):
        assert c in claves, f"falta clave {c}"
    assert repo.max_timestamp() is not None

    equity_etf = repo.fetch_all(asset_classes=["equity", "etf"])
    assert all(r["asset_class"] in ("equity", "etf") for r in equity_etf)

    riesgo = repo.fetch_by_logical_keys(["VIX", "US10Y", "DXY", "TLT"])
    assert isinstance(riesgo, list)


def test_heatmap_repo(live_connector):
    repo = HeatmapRepository(live_connector)
    rows = repo.fetch_latest(limit=10)

    assert rows, "fact_heatmap_snapshot sin filas en la última ventana"
    for c in ("asset_id", "symbol", "sector", "daily_change_pct", "market_cap",
              "price_heatmap", "avg_vol_10d", "high_52w", "low_52w"):
        assert c in rows[0], f"falta clave {c}"
    assert repo.max_timestamp() is not None
    assert len(repo.vol_map()) > 0

    sectores = repo.sectores(min_activos=5)
    assert sectores
    assert {"sector", "n_activos", "change_medio"}.issubset(sectores[0].keys())

    rotacion = repo.rotacion(ventanas=5)
    assert len(rotacion) >= 1

    dist = repo.distribucion_change(limit=50)
    assert all(isinstance(x, float) for x in dist)


def test_events_repo(live_connector):
    repo = EventsRepository(live_connector)
    rows = repo.fetch_eventos(limit=10)

    assert isinstance(rows, list)
    assert repo.max_timestamp() is not None


def test_series_repo(live_connector):
    repo = SeriesRepository(live_connector)
    desde = datetime(2026, 9, 1, tzinfo=timezone.utc)
    rows = repo.fetch_desde(desde, asset_classes=["equity", "etf"], limit=100)

    assert isinstance(rows, list)
    if rows:
        for c in ("asset_id", "symbol", "asset_class", "timestamp_utc", "rsi", "change_pct"):
            assert c in rows[0]
        assert repo.distinct_timestamps(desde) is not None


# ── Escritura (BD scratch del docker, migración 0009) ────────────────────────
def test_score_repo_roundtrip(docker_connector):
    repo = ScoreRepository(docker_connector)
    ts = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    assert repo.upsert_agg(
        {
            "timestamp_utc": ts,
            "score_momentum": 6.5,
            "score_15min": 5.5,
            "score_radar": 4.5,
            "score_market": 5.75,
            "zona": "NEUTRAL",
            "n_simbolos": 120,
        }
    ) == 1

    latest = repo.fetch_agg_latest()
    # el roundtrip escribe un timestamp antiguo; fetch_agg_latest puede no ser
    # ese si la tabla tiene datos posteriores, por eso se consulta por rango.
    filas = repo.fetch_agg_history(ts, ts)
    assert len(filas) == 1
    assert float(filas[0]["score_market"]) == 5.75
    assert filas[0]["n_simbolos"] == 120

    # idempotencia
    repo.upsert_agg({"timestamp_utc": ts, "score_market": 7.0, "n_simbolos": 121})
    filas = repo.fetch_agg_history(ts, ts)
    assert len(filas) == 1
    assert float(filas[0]["score_market"]) == 7.0

    docker_connector.execute("DELETE FROM fact_market_score_agg WHERE timestamp_utc = %s", (ts,))

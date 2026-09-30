"""Tests de la Fase 4 — job persist_score (dry-run y escritura en scratch)."""

from dataclasses import replace
from datetime import datetime, timezone

import jobs.persist_score as job
from core.settings import get_settings
from repositories import ScoreRepository


def test_parse_iso():
    dt = job._parse_iso("2026-09-29T00:00:00Z")
    assert dt.tzinfo is not None
    assert dt.year == 2026
    assert job._parse_iso("2026-09-29T00:00:00").tzinfo is not None


def test_backfill_requiere_since():
    # Se valida antes de tocar la BD → no requiere conexión.
    assert job.run(["--backfill"]) == 2


def test_cycle_dry_run_live(live_connector):
    # live_connector salta el test si la BD no está accesible.
    assert job.run(["--cycle", "--dry-run"]) == 0


def test_backfill_dry_run_live(live_connector):
    assert job.run(["--backfill", "--since", "2026-09-29T03:00:00Z", "--dry-run"]) == 0


def test_cycle_escribe_scratch(docker_connector, monkeypatch):
    base = get_settings()
    scratch = replace(
        base,
        db_host="localhost",
        db_name="heatmap_stock_test",
        db_user="postgres",
        db_password="postgres",
    )
    monkeypatch.setattr(job, "get_settings", lambda: scratch)

    inicio = datetime.now(timezone.utc)
    assert job.run(["--cycle"]) == 0

    repo = ScoreRepository(docker_connector)
    filas = repo.fetch_agg_history(inicio)
    try:
        assert len(filas) == 1
        assert filas[0]["timestamp_utc"] >= inicio
    finally:
        docker_connector.execute(
            "DELETE FROM fact_market_score_agg WHERE timestamp_utc >= %s", (inicio,)
        )

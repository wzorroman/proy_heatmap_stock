"""Tests de la Fase 6 — API JSON (routers)."""

from fastapi.testclient import TestClient

from web.app import app


def _client():
    return TestClient(app)


def test_score_latest():
    with _client() as client:
        r = client.get("/api/score/latest")
    assert r.status_code == 200
    data = r.json()
    assert "mercado" in data and "n_activos" in data
    for k in ("score_momentum", "score_15min", "score_radar", "score_market", "zona"):
        assert k in data["mercado"]


def test_score_history():
    with _client() as client:
        r = client.get("/api/score/history", params={"hours": 24})
    assert r.status_code == 200
    data = r.json()
    assert data["hours"] == 24
    assert isinstance(data["history"], list)


def test_momentum_top():
    with _client() as client:
        r = client.get("/api/momentum/top", params={"n": 5})
    assert r.status_code == 200
    data = r.json()
    assert len(data["top"]) <= 5
    assert len(data["bottom"]) <= 5
    assert "n" in data


def test_heatmap_endpoints():
    with _client() as client:
        tree = client.get("/api/heatmap/treemap", params={"limit": 10}).json()
        sect = client.get("/api/heatmap/sectors").json()
        rot = client.get("/api/heatmap/rotation").json()
        dist = client.get("/api/heatmap/distribution").json()

    assert len(tree["items"]) <= 10
    assert isinstance(sect["sectores"], list)
    assert isinstance(rot["ventanas"], list)
    assert isinstance(dist["change_pct"], list)


def test_indicators_endpoint():
    with _client() as client:
        r = client.get("/api/indicators", params={"ind": "rsi", "tf": "1d", "n": 5})
        malo = client.get("/api/indicators", params={"ind": "nope"})

    assert r.status_code == 200
    assert len(r.json()["items"]) <= 5
    assert malo.json()["estado"] == "WARN"


def test_indicators_histogram():
    with _client() as client:
        r = client.get("/api/indicators/histogram", params={"ind": "rsi", "bins": 5})

    data = r.json()
    assert len(data["counts"]) == 5
    assert len(data["edges"]) == 6


def test_events_endpoints():
    with _client() as client:
        ev = client.get("/api/events", params={"hours": 72}).json()
        sp = client.get("/api/events/surprises").json()

    assert isinstance(ev["eventos"], list)
    assert isinstance(sp["sorpresas"], list)


def test_risk_endpoint():
    with _client() as client:
        r = client.get("/api/risk")

    data = r.json()
    assert "score_radar" in data
    assert isinstance(data["componentes"], list)
    assert len(data["componentes"]) == 4

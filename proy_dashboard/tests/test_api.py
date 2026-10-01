"""Tests de los endpoints base (Fase 0): /api/health, /api/version y /."""

from fastapi.testclient import TestClient

from web.app import app


def test_version_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/version")

    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "proy_dashboard"
    assert data["version"] == "1.0.21"
    assert "env" in data


def test_health_endpoint_degrada_sin_crash():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("OK", "WARN")
    assert "db" in data["modulos"]
    assert data["modulos"]["db"]["estado"] in ("OK", "WARN", "ERROR")
    assert "timestamp_utc" in data


def test_index_carga_libs_locales():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    html = response.text
    # Librerías servidas desde local (sin CDN)
    assert "/static/vendor/echarts/6.1.0/echarts.min.js" in html
    assert "/static/vendor/htmx/2.0.11/htmx.min.js" in html
    assert "/static/app.css" in html
    assert "/static/app.js" in html
    assert "http://" not in html.replace("http://localhost", "")


def test_static_vendorizado_disponible():
    with TestClient(app) as client:
        echarts = client.get("/static/vendor/echarts/6.1.0/echarts.min.js")
        htmx = client.get("/static/vendor/htmx/2.0.11/htmx.min.js")

    assert echarts.status_code == 200
    assert htmx.status_code == 200

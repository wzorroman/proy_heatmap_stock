"""Tests de la Fase 7 — web (Jinja2 + HTMX + ECharts)."""

import re

from fastapi.testclient import TestClient

from web.app import app

PARTIALS = [
    "header", "sectors", "sector_risk", "momentum", "change_rsi",
    "alcistas", "bajistas", "riesgo_gauges",
    "riesgo_fx", "volume", "range52w", "rsi_limites", "precios",
    "score_history", "multiframe", "calendar", "health", "tabla_sector",
]


def _client():
    return TestClient(app)


def test_pagina_principal_muestra_zona_horaria():
    """El subtítulo indica la zona de visualización (APP_TIMEZONE)."""
    from core.settings import get_settings
    from core.timezone import tz_label

    settings = get_settings()
    with _client() as client:
        html = client.get("/").text

    assert 'class="tz-badge"' in html
    assert settings.timezone in html
    assert tz_label(settings.timezone) in html


def test_pagina_principal():
    with _client() as client:
        r = client.get("/")

    assert r.status_code == 200
    html = r.text
    # fragmentos HTMX declarados
    assert 'hx-get="/partials/header"' in html
    assert 'hx-get="/partials/momentum"' in html
    assert 'hx-trigger="load, every' in html
    # mapa sectorial, riesgo divergente y RSI (top) deshabilitados
    assert "/partials/treemap" not in html
    assert "/partials/risk" not in html
    assert "/partials/indicators" not in html
    # placeholders honestos
    assert "SMA20/50 de precio" in html
    assert "Distribución histórica / backtest" in html
    # librerías locales
    assert "/static/vendor/echarts/6.1.0/echarts.min.js" in html
    # health en la primera fila
    assert 'hx-get="/partials/health"' in html


def test_partial_rsi_limites_es_grafico():
    with _client() as client:
        r = client.get("/partials/rsi_limites")

    assert r.status_code == 200
    assert "renderChart(" in r.text
    assert "acciones top por capitalización" in r.text


def test_partials_responsivos():
    with _client() as client:
        for nombre in PARTIALS:
            r = client.get(f"/partials/{nombre}")
            assert r.status_code == 200, nombre
            assert '<article class="card' in r.text, nombre


def test_partials_de_grafico_renderizan_echarts():
    graficos = ["header", "sectors", "momentum", "change_rsi",
                "volume", "range52w", "rsi_limites", "precios",
                "score_history", "multiframe"]
    with _client() as client:
        for nombre in graficos:
            r = client.get(f"/partials/{nombre}")
            assert "renderChart(" in r.text, nombre


def test_partial_calendario_es_tabla():
    with _client() as client:
        r = client.get("/partials/calendar")

    assert "Calendario de hoy" in r.text
    assert "<table" in r.text


def test_partial_health_es_lista():
    with _client() as client:
        r = client.get("/partials/health")

    assert "Health" in r.text
    assert "health-list" in r.text
    assert "health-mod" in r.text
    assert "health-detalle" in r.text


def test_cards_riesgo_listas_y_sector():
    with _client() as client:
        gauges = client.get("/partials/riesgo_gauges").text
        fx = client.get("/partials/riesgo_fx").text
        sector = client.get("/partials/sector_risk").text
        alcistas = client.get("/partials/alcistas").text
        bajistas = client.get("/partials/bajistas").text

    assert "Termómetro de Riesgo" in gauges
    assert "Movimiento FX / Macro" in fx
    assert "Sector Risk Gauge" in sector
    assert "Alcistas del Día" in alcistas
    assert "Bajistas del Día" in bajistas


def test_partial_precios_con_barras():
    with _client() as client:
        r = client.get("/partials/precios")

    assert r.status_code == 200
    assert "renderChart(" in r.text
    # 3 tarjetas × (precio+SMA20+SMA50+RSI+ADX+cruce) = 18 barras
    assert r.text.count('class="metrica"') >= 6
    assert "SMA20 vs SMA50" in r.text
    assert "Rango 48h" in r.text


def test_partial_screener_signal_en_ingles():
    with _client() as client:
        r = client.get("/partials/screener_15m", params={"compact": 1})

    assert r.status_code == 200
    # Etiqueta visible en inglés; la clase de color conserva COMPRAR/VENDER
    assert ">BUY<" in r.text or ">SELL<" in r.text or ">NEUTRAL<" in r.text
    assert ">COMPRAR<" not in r.text and ">VENDER<" not in r.text


def test_partial_screener_una_sola_tabla():
    with _client() as client:
        r = client.get("/partials/screener_15m", params={"compact": 1})

    assert r.status_code == 200
    assert r.text.count('class="screener-table"') == 1
    assert "screener-dual" not in r.text


def test_confluencia_resalta_seleccion():
    with _client() as client:
        r = client.get("/partials/confluencia")

    assert r.status_code == 200
    assert "chart-confluencia" in r.text
    # Estilo de resaltado del símbolo seleccionado en el screener
    assert "emphasis" in r.text


def test_ib_acciones_filas_seleccionables():
    with _client() as client:
        r = client.get("/partials/ib_acciones")

    assert r.status_code == 200
    # Misma clase/data que el screener → el resaltado se propaga solo
    assert 'class="screener-row"' in r.text
    assert "data-symbol=" in r.text


def test_ib_acciones_mismo_orden_que_screener():
    with _client() as client:
        screener = client.get("/partials/screener_15m", params={"compact": 1}).text
        ib = client.get("/partials/ib_acciones").text

    syms_screener = re.findall(r'data-symbol="([^"]+)"', screener)
    syms_ib = re.findall(r'data-symbol="([^"]+)"', ib)
    assert syms_screener
    assert syms_ib == syms_screener


def test_ib_acciones_muestra_zona_horaria():
    """La hora de ruptura lleva al lado su zona (derivada de APP_TIMEZONE)."""
    from core.settings import get_settings
    from core.timezone import tz_label

    with _client() as client:
        r = client.get("/partials/ib_acciones")

    assert r.status_code == 200
    etiqueta = tz_label(get_settings().timezone)
    assert 'class="hora-tz"' in r.text
    assert f'<span class="hora-tz">{etiqueta}</span>' in r.text


def test_layout_velas_junto_a_mapa_sectorial():
    with _client() as client:
        html = client.get("/").text

    # Fila del screener: screener + rango inicial por acción + confluencia
    assert 'hx-get="/partials/screener_15m?compact=1"' in html
    assert 'hx-get="/partials/ib_acciones"' in html
    assert 'hx-get="/partials/confluencia"' in html
    # Fila de velas + mapa de calor 15m
    assert 'hx-get="/partials/velas_15m"' in html
    assert 'hx-get="/partials/sector_15m"' in html
    # El card de velas es el target del screener/rango inicial
    assert 'id="trading-velas-card"' in html


def test_partial_tabla_sector():
    with _client() as client:
        default = client.get("/partials/tabla_sector")
        finance = client.get("/partials/tabla_sector", params={"sector": "Finance"})
        buscado = client.get("/partials/tabla_sector", params={"q": "nvda"})

    assert default.status_code == 200
    assert "Stocks por sector" in default.text
    assert "Technology Services" in default.text  # sector por defecto
    assert 'name="sector"' in default.text
    assert 'name="q"' in default.text  # buscador
    assert "MSFT" in default.text and "META" in default.text
    assert "NASDAQ:MSFT" in default.text  # símbolo completo
    assert "Finance" in finance.text
    # iconos
    assert "tlogo" in default.text
    # búsqueda por símbolo
    assert "Búsqueda" in buscado.text
    assert "NVDA" in buscado.text

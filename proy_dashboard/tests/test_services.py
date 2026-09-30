"""Tests de la Fase 5 — servicios de momentum, heatmap, indicadores, eventos,
sesión y health."""

from datetime import datetime, timedelta, timezone

from core.settings import load_settings
from services.event_service import EventService
from services.health_service import HealthService
from services.heatmap_service import HeatmapService
from services.indicator_service import IndicatorService
from services.momentum_service import MomentumService
from services.precio_service import PrecioService
from services.session_service import SessionService

UTC = timezone.utc


def _settings(clean_env, empty_env_file, config_file):
    return load_settings(env_file=empty_env_file, config_path=config_file)


# ── fakes ────────────────────────────────────────────────────────────────────
class FakeLatestTickRepo:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetch_all(self, asset_classes=None):
        return list(self._rows)

    def max_timestamp(self):
        return self._rows[0]["timestamp_utc"] if self._rows else None

    def fetch_by_logical_keys(self, keys):
        return [r for r in self._rows if r.get("logical_key") in keys]


class FakeHeatmapRepo:
    def __init__(self, latest=None, sectores=None, rotacion=None, dist=None):
        self._latest = latest or []
        self._sectores = sectores or []
        self._rotacion = rotacion or []
        self._dist = dist or []

    def fetch_latest(self, limit=None, asset_classes=None):
        return self._latest[:limit] if limit else self._latest

    def sectores(self, min_activos=5):
        return self._sectores

    def rotacion(self, ventanas=12):
        return self._rotacion

    def distribucion_change(self, limit=1000):
        return self._dist

    def max_timestamp(self):
        return None


class FakeIndicatorRepo:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetch_recent(self, tf, limit=3000, asset_classes=None):
        return list(self._rows)[:limit]

    def max_timestamp(self, tf=None):
        return None


class FakeEventsRepo:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetch_eventos(self, **kwargs):
        return list(self._rows)

    def max_timestamp(self):
        return None


class FakeSessionRepo:
    def __init__(self, row=None):
        self._row = row

    def estado_sesion(self, dia):
        return self._row


# ── momentum ─────────────────────────────────────────────────────────────────
def test_momentum_top_bottom(clean_env, empty_env_file, config_file):
    rows = [
        {"symbol": "A", "asset_class": "equity", "change_pct": 5.0, "close": 1, "rsi": 60, "adx_15": 30},
        {"symbol": "B", "asset_class": "equity", "change_pct": -3.0, "close": 1, "rsi": 40, "adx_15": 20},
        {"symbol": "C", "asset_class": "etf", "change_pct": 1.0, "close": 1, "rsi": 50, "adx_15": 25},
    ]
    svc = MomentumService(FakeLatestTickRepo(rows), _settings(clean_env, empty_env_file, config_file))
    res = svc.top_bottom(n=2)

    assert res["top"][0]["symbol"] == "A"
    assert res["bottom"][0]["symbol"] == "B"
    assert res["n"] == 3


# ── heatmap ──────────────────────────────────────────────────────────────────
def test_heatmap_treemap_y_sectores(clean_env, empty_env_file, config_file):
    latest = [
        {"symbol": "NASDAQ:NVDA", "company_name": "NVDA", "sector": "Tech",
         "market_cap": 5_000_000, "daily_change_pct": 1.2, "price_heatmap": 228,
         "volatility_d": 2.2, "high_52w": 236, "low_52w": 164},
    ]
    sectores = [{"sector": "Tech", "n_activos": 100, "change_medio": 0.5,
                 "market_cap_total": 1e12, "ganadores": 60, "perdedores": 40}]
    repo = FakeHeatmapRepo(latest=latest, sectores=sectores, rotacion=[], dist=[1.0, -0.5])
    svc = HeatmapService(repo, _settings(clean_env, empty_env_file, config_file))

    tree = svc.treemap()
    assert tree[0]["symbol"] == "NASDAQ:NVDA"
    assert tree[0]["value"] == 5_000_000.0

    sec = svc.sectores()
    assert sec[0]["sector"] == "Tech"
    assert sec[0]["ganadores"] == 60
    assert svc.distribucion_change() == [1.0, -0.5]


# ── indicadores ──────────────────────────────────────────────────────────────
def test_indicator_por_indicador_y_histograma(clean_env, empty_env_file, config_file):
    rows = [
        {"symbol": "A", "rsi": 70, "adx_15": 30, "cci20_15": 100, "bbpower_15": 10},
        {"symbol": "B", "rsi": 50, "adx_15": 25, "cci20_15": 0, "bbpower_15": 0},
        {"symbol": "C", "rsi": 30, "adx_15": 20, "cci20_15": -100, "bbpower_15": -10},
    ]
    svc = IndicatorService(
        FakeLatestTickRepo(rows), FakeIndicatorRepo(),
        _settings(clean_env, empty_env_file, config_file),
    )

    rsi = svc.por_indicador("rsi", "1d", n=2)
    assert [d["symbol"] for d in rsi] == ["A", "B"]

    hist = svc.histograma("rsi", "1d", bins=2)
    assert sum(hist["counts"]) == 3
    assert len(hist["edges"]) == 3


def test_indicator_tf(clean_env, empty_env_file, config_file):
    rows = [
        {"asset_id": 1, "symbol": "A", "rsi": 80, "adx": 30, "cci20": 0, "bbpower": 0, "change_pct": 0},
        {"asset_id": 1, "symbol": "A", "rsi": 20, "adx": 30, "cci20": 0, "bbpower": 0, "change_pct": 0},
        {"asset_id": 2, "symbol": "B", "rsi": 55, "adx": 30, "cci20": 0, "bbpower": 0, "change_pct": 0},
    ]
    svc = IndicatorService(
        FakeLatestTickRepo(), FakeIndicatorRepo(rows),
        _settings(clean_env, empty_env_file, config_file),
    )
    data = svc.por_indicador("rsi", "15", n=5)

    # toma el primer registro (más reciente) por activo: A=80, B=55
    valores = {d["symbol"]: d["valor"] for d in data}
    assert valores == {"A": 80.0, "B": 55.0}


# ── eventos ──────────────────────────────────────────────────────────────────
def test_event_sorpresas(clean_env, empty_env_file, config_file):
    rows = [
        {"event_id": 1, "title": "CPI", "country": "US", "category": "inflacion",
         "importance": 1, "event_timestamp": datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
         "actual_raw": 105, "forecast_raw": 100, "actual_display": "105", "forecast_display": "100"},
    ]
    svc = EventService(FakeEventsRepo(rows), _settings(clean_env, empty_env_file, config_file))
    sorpresas = svc.sorpresas()

    assert len(sorpresas) == 1
    assert sorpresas[0]["sorpresa_pct"] == 5.0


def test_event_proximos(clean_env, empty_env_file, config_file):
    rows = [
        {"event_id": 1, "title": "NFP", "country": "US", "category": None,
         "importance": 1, "event_timestamp": datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
         "actual_raw": None, "forecast_raw": None},
    ]
    svc = EventService(FakeEventsRepo(rows), _settings(clean_env, empty_env_file, config_file))
    prox = svc.proximos()

    assert prox[0]["title"] == "NFP"
    assert prox[0]["sorpresa_pct"] is None


# ── sesión ───────────────────────────────────────────────────────────────────
def test_session_estado(clean_env, empty_env_file, config_file):
    row = {
        "session_date": datetime(2026, 9, 30, tzinfo=UTC).date(),
        "is_session": True, "is_early_close": False,
        "opens_at": datetime(2026, 9, 30, 13, 30, tzinfo=UTC),
        "closes_at": datetime(2026, 9, 30, 20, 0, tzinfo=UTC),
    }
    svc = SessionService(FakeSessionRepo(row), _settings(clean_env, empty_env_file, config_file))
    estado = svc.estado(datetime(2026, 9, 30, 15, 0, tzinfo=UTC))

    assert estado["fase"] == "OPEN"
    assert estado["is_session"] is True


def test_session_sin_datos(clean_env, empty_env_file, config_file):
    svc = SessionService(FakeSessionRepo(None), _settings(clean_env, empty_env_file, config_file))
    assert svc.estado(datetime(2026, 9, 30, 15, 0, tzinfo=UTC))["fase"] == "SIN_DATOS"


# ── health ───────────────────────────────────────────────────────────────────
def test_health_degrada_sin_bd(clean_env, empty_env_file, config_file):
    settings = _settings(clean_env, empty_env_file, config_file)
    svc = HealthService(settings, FakeLatestTickRepo(), FakeHeatmapRepo(), FakeEventsRepo())
    resultado = svc.check()

    assert resultado["status"] == "WARN"
    assert resultado["modulos"]["db"]["estado"] == "WARN"
    assert resultado["modulos"]["data"]["estado"] == "WARN"
    assert resultado["app"]["version"] == settings.version


# ── precio: barras de métricas (escalas) ─────────────────────────────────────
def test_precio_metricas_escalas(clean_env, empty_env_file, config_file):
    settings = load_settings(env_file=empty_env_file, config_path=config_file)
    svc = PrecioService(series_repo=None, score_service=None, settings=settings)

    metricas = svc._metricas(close=105, sma20=100, sma50=98, rsi=75, adx=30, lo=95, hi=110)
    d = {m["clave"]: m for m in metricas}

    assert set(d) == {"precio", "sma20", "sma50", "rsi", "adx", "cruce"}
    # rango de ventana [95..110]: precio 105 -> 66.7%
    assert d["precio"]["pct"] == 66.7
    assert d["precio"]["color"] == "azul"
    # precio 105 > sma20 100 -> verde; marcador del precio presente
    assert d["sma20"]["color"] == "verde"
    assert d["sma20"]["marca"] == 66.7
    # RSI 75 >= 70 -> rojo
    assert d["rsi"]["color"] == "rojo"
    assert d["rsi"]["pct"] == 75.0
    # ADX 30 sobre max 50 -> 60%
    assert d["adx"]["pct"] == 60.0
    # cruce SMA20>SMA50 -> centrada, signo positivo
    assert d["cruce"]["centrada"] is True
    assert d["cruce"]["signo"] == 1
    assert d["cruce"]["color"] == "verde"


def test_precio_metricas_limites(clean_env, empty_env_file, config_file):
    settings = load_settings(env_file=empty_env_file, config_path=config_file)
    svc = PrecioService(series_repo=None, score_service=None, settings=settings)

    metricas = svc._metricas(close=90, sma20=120, sma50=130, rsi=20, adx=10, lo=95, hi=110)
    d = {m["clave"]: m for m in metricas}

    # valores fuera del rango se recortan a 0..100
    assert d["precio"]["pct"] == 0.0
    assert d["sma20"]["pct"] == 100.0
    # precio < sma -> rojo
    assert d["sma20"]["color"] == "rojo"
    # RSI 20 <= 30 -> verde
    assert d["rsi"]["color"] == "verde"
    # ADX 10 < 20 -> azul (sin tendencia)
    assert d["adx"]["color"] == "azul"
    # cruce negativo
    assert d["cruce"]["signo"] == -1
    assert d["cruce"]["color"] == "rojo"

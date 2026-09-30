"""Tests de la Fase 4 — score_service (unitario con repositorios fake)."""

from datetime import datetime, timedelta, timezone

from core.settings import load_settings
from domain.market import ActivoTick
from services.score_service import ScoreService


# ── repositorios fake ────────────────────────────────────────────────────────
class FakeLatestTickRepo:
    def __init__(self, rows):
        self._rows = rows

    def fetch_all(self, asset_classes=None):
        if asset_classes:
            return [r for r in self._rows if r.get("asset_class") in asset_classes]
        return list(self._rows)

    def fetch_by_logical_keys(self, keys):
        return [r for r in self._rows if r.get("logical_key") in keys]

    def max_timestamp(self):
        return self._rows[0]["timestamp_utc"] if self._rows else None


class FakeHeatmapRepo:
    def __init__(self, vol_map=None):
        self._vol = vol_map or {}

    def vol_map(self):
        return dict(self._vol)


class FakeIndicatorRepo:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetch_recent(self, tf, limit=3000):
        return list(self._rows)[:limit]


class FakeSeriesRepo:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetch_desde(self, since, asset_classes=None, limit=200000):
        return list(self._rows)


def _settings(clean_env, empty_env_file, config_file):
    return load_settings(env_file=empty_env_file, config_path=config_file)


def _service(settings, ticks=(), vol=None, indicators=()):
    return ScoreService(
        FakeLatestTickRepo(list(ticks)),
        FakeHeatmapRepo(vol),
        FakeIndicatorRepo(list(indicators)),
        FakeSeriesRepo(),
        settings,
    )


def _tick(asset_id, symbol, asset_class="equity", *, rsi=50, adx=25, cci=0, bb=0, change=0.0, volume=None):
    return ActivoTick(
        asset_id=asset_id, symbol=symbol,
        timestamp_utc=datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc),
        asset_class=asset_class, close=100.0, change_pct=change, volume=volume,
        rsi=rsi, rsi_15=rsi, cci20_15=cci, bbpower_15=bb, adx_15=adx,
    )


# ── primitivas ───────────────────────────────────────────────────────────────
def test_normalizar(clean_env, empty_env_file, config_file):
    svc = _service(_settings(clean_env, empty_env_file, config_file))

    assert svc.normalizar("rsi", 50) == 0.5
    assert svc.normalizar("rsi", 0) == 0.0
    assert svc.normalizar("rsi", 100) == 1.0
    assert svc.normalizar("rsi", 150) == 1.0        # clamp
    assert svc.normalizar("change", 0) == 0.5
    assert svc.normalizar("cci20", 0) == 0.5
    assert svc.normalizar("rsi", None) is None


def test_zona_umbrales(clean_env, empty_env_file, config_file):
    svc = _service(_settings(clean_env, empty_env_file, config_file))

    assert svc.zona(8.0) == "COMPRAR"
    assert svc.zona(6.5) == "COMPRAR"
    assert svc.zona(5.0) == "NEUTRAL"
    assert svc.zona(4.5) == "VENDER"
    assert svc.zona(1.0) == "VENDER"
    assert svc.zona(None) == "NEUTRAL"


def test_score_activo_neutro(clean_env, empty_env_file, config_file):
    svc = _service(_settings(clean_env, empty_env_file, config_file))
    score = svc.score_activo(_tick(1, "NASDAQ:NVDA"))

    # todos los indicadores en el punto medio → score medio
    assert score.score_general == 5.0
    assert score.zona == "NEUTRAL"
    assert len(score.componentes) == 6


def test_score_activo_renorm_nan(clean_env, empty_env_file, config_file):
    svc = _service(_settings(clean_env, empty_env_file, config_file))
    # solo rsi disponible, en el punto medio → 5.0
    score = svc.score_activo(_tick(1, "NASDAQ:NVDA", adx=None, cci=None, bb=None, change=None))

    assert score.score_general == 5.0


def test_score_activo_volumen(clean_env, empty_env_file, config_file):
    svc = _service(_settings(clean_env, empty_env_file, config_file))
    # vol_ratio=2 (máximo) empuja al alza
    score = svc.score_activo(_tick(1, "NASDAQ:NVDA"), vol_ratio=2.0)

    assert score.score_general > 5.0


def test_score_momentum(clean_env, empty_env_file, config_file):
    svc = _service(_settings(clean_env, empty_env_file, config_file))
    assert svc.score_momentum([]) is None

    from domain.score import ScoreActivo
    scores = [ScoreActivo(1, "A", 4.0), ScoreActivo(2, "B", 6.0), ScoreActivo(3, "C", None)]
    assert svc.score_momentum(scores) == 5.0


# ── PASO 3 radar ─────────────────────────────────────────────────────────────
def test_score_radar_directo_inverso(clean_env, empty_env_file, config_file):
    rows = [
        {"logical_key": "VIX", "is_canonical": True, "symbol": "TVC:VIX", "rsi": 50, "close": 15, "change_pct": 0},
        {"logical_key": "US10Y", "is_canonical": True, "symbol": "TVC:US10Y", "rsi": 60, "close": 5, "change_pct": 0},
        {"logical_key": "DXY", "is_canonical": True, "symbol": "TVC:DXY", "rsi": 40, "close": 100, "change_pct": 0},
        {"logical_key": "TLT", "is_canonical": True, "symbol": "NASDAQ:TLT", "rsi": 70, "close": 81, "change_pct": 0},
    ]
    svc = _service(_settings(clean_env, empty_env_file, config_file), ticks=rows)
    score, items = svc.score_radar()

    # (30*5 + 25*4 + 25*6 + 20*7) / 100 = 5.4
    assert round(score, 4) == 5.4
    assert len(items) == 4
    assert all(i.estado != "SIN_DATOS" for i in items)


def test_score_radar_prefiere_canonico(clean_env, empty_env_file, config_file):
    rows = [
        {"logical_key": "DXY", "is_canonical": False, "symbol": "AMEX:UUP", "rsi": 10, "close": 28, "change_pct": 0},
        {"logical_key": "DXY", "is_canonical": True, "symbol": "TVC:DXY", "rsi": 90, "close": 100, "change_pct": 0},
    ]
    svc = _service(_settings(clean_env, empty_env_file, config_file), ticks=rows)
    _, items = svc.score_radar()
    dxy = next(i for i in items if i.logical_key == "DXY")

    assert dxy.symbol == "TVC:DXY"


# ── PASO 2b ──────────────────────────────────────────────────────────────────
def test_score_15min(clean_env, empty_env_file, config_file):
    rows = [
        {"asset_id": 1, "rsi": 50, "adx": 25, "cci20": 0, "bbpower": 0, "change_pct": 0},
        {"asset_id": 1, "rsi": 50, "adx": 25, "cci20": 0, "bbpower": 0, "change_pct": 0},
        {"asset_id": 2, "rsi": 50, "adx": 25, "cci20": 0, "bbpower": 0, "change_pct": 0},
    ]
    svc = _service(_settings(clean_env, empty_env_file, config_file), indicators=rows)

    assert svc.score_15min() == 5.0


def test_score_15min_sin_datos(clean_env, empty_env_file, config_file):
    svc = _service(_settings(clean_env, empty_env_file, config_file))
    assert svc.score_15min() is None


# ── ciclo completo ───────────────────────────────────────────────────────────
def test_calcular_ciclo(clean_env, empty_env_file, config_file):
    ticks = [
        {"asset_id": 1, "symbol": "NASDAQ:NVDA", "asset_class": "equity",
         "timestamp_utc": datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc),
         "close": 228, "change_pct": 1.0, "volume": 1000, "rsi": 60, "rsi_15": 60,
         "cci20_15": 50, "bbpower_15": 10, "adx_15": 30, "logical_key": None},
        {"asset_id": 2, "symbol": "AMEX:SPY", "asset_class": "etf",
         "timestamp_utc": datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc),
         "close": 764, "change_pct": -0.5, "volume": 2000, "rsi": 45, "rsi_15": 45,
         "cci20_15": -20, "bbpower_15": -5, "adx_15": 20, "logical_key": None},
        {"asset_id": 1011, "symbol": "TVC:VIX", "asset_class": "index",
         "timestamp_utc": datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc),
         "close": 15, "change_pct": 0, "volume": None, "rsi": 50, "rsi_15": None,
         "cci20_15": None, "bbpower_15": None, "adx_15": None, "logical_key": "VIX",
         "is_canonical": True},
    ]
    svc = _service(
        _settings(clean_env, empty_env_file, config_file),
        ticks=ticks,
        vol={"1": 1000.0, "2": 1000.0},
    )
    scores, mercado = svc.calcular_ciclo()

    assert len(scores) == 3
    assert mercado.n_simbolos == 3
    assert mercado.timestamp_utc == datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)
    assert mercado.score_momentum is not None
    assert mercado.score_radar is not None
    assert mercado.pesos and mercado.zonas


def test_calcular_desde_series_bucket(clean_env, empty_env_file, config_file):
    base = datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)
    rows = [
        {"asset_id": 1, "symbol": "A", "asset_class": "equity",
         "timestamp_utc": base + timedelta(minutes=1), "rsi": 60, "adx": 30,
         "cci20": 0, "bbpower": 0, "change_pct": 1},
        {"asset_id": 2, "symbol": "B", "asset_class": "equity",
         "timestamp_utc": base + timedelta(minutes=2), "rsi": 40, "adx": 20,
         "cci20": 0, "bbpower": 0, "change_pct": -1},
        # mismo bucket que el anterior; A se queda con el valor más nuevo
        {"asset_id": 1, "symbol": "A", "asset_class": "equity",
         "timestamp_utc": base + timedelta(minutes=5), "rsi": 80, "adx": 30,
         "cci20": 0, "bbpower": 0, "change_pct": 2},
        # bucket siguiente
        {"asset_id": 1, "symbol": "A", "asset_class": "equity",
         "timestamp_utc": base + timedelta(minutes=40), "rsi": 50, "adx": 25,
         "cci20": 0, "bbpower": 0, "change_pct": 0},
    ]
    svc = ScoreService(
        FakeLatestTickRepo([]), FakeHeatmapRepo(), FakeIndicatorRepo(),
        FakeSeriesRepo(rows), _settings(clean_env, empty_env_file, config_file),
    )
    generado = list(svc.calcular_desde_series(base))

    assert len(generado) == 2  # dos buckets de 15 min
    ts1, detalle1, agg1 = generado[0]
    assert agg1["n_simbolos"] == 2
    assert agg1["score_momentum"] is not None
    # A usa la fila más nueva del bucket (rsi=80)
    fila_a = next(d for d in detalle1 if d["asset_id"] == 1)
    assert fila_a["componentes"][0]["valor"] == 80.0

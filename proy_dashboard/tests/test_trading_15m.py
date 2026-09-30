"""Tests de los servicios de trading a 15 min."""

from datetime import datetime, timezone

import pytest

from core.settings import load_settings
from services.bar_15m_service import Bar15mService
from services.confluencia_service import ConfluenciaService
from services.divergencia_service import DivergenciaService
from services.initial_balance_service import InitialBalanceService
from services.screener_15m_service import Screener15mService
from services.sector_15m_service import Sector15mService

UTC = timezone.utc


def _settings(clean_env, empty_env_file, config_file):
    return load_settings(env_file=empty_env_file, config_path=config_file)


class FakeBarRepo:
    def __init__(self, barras=None, ticks=None):
        self._barras = barras or []
        self._ticks = ticks or []

    def fetch_barras(self, symbol, since, limit=500):
        return [b for b in self._barras if b["symbol"] == symbol and b["timestamp_utc"] >= since][:limit]

    def fetch_ticks(self, symbol, since, limit=5000):
        return [t for t in self._ticks if t["symbol"] == symbol and t["timestamp_utc"] >= since][:limit]

    def fetch_latest_per_symbol(self, symbols, since):
        seen = set()
        out = []
        for b in sorted(self._barras, key=lambda x: x["timestamp_utc"], reverse=True):
            sym = b["symbol"]
            if sym in symbols and sym not in seen and b["timestamp_utc"] >= since:
                seen.add(sym)
                out.append(b)
        return out


class FakeLatestTickRepo:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetch_all(self, asset_classes=None):
        return list(self._rows)


class FakeIndicatorRepo:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetch_recent(self, tf, limit=3000, asset_classes=None):
        return [r for r in self._rows if r.get("tf") == tf][:limit]


# ── Bar15mService: funciones puras ───────────────────────────────────────────
def test_sma_simple():
    assert Bar15mService.calc_sma([1.0, 2.0, 3.0, 4.0], 2) == [1.0, 1.5, 2.5, 3.5]


def test_sma_con_nones():
    assert Bar15mService.calc_sma([1.0, None, 3.0], 2) == [1.0, 1.0, 3.0]


def test_bollinger_constante():
    upper, middle, lower = Bar15mService.calc_bollinger([5.0] * 5, ventana=3)
    assert middle == [5.0, 5.0, 5.0, 5.0, 5.0]
    assert upper == [None, 5.0, 5.0, 5.0, 5.0]
    assert lower == [None, 5.0, 5.0, 5.0, 5.0]


def test_bollinger_variable():
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    upper, middle, lower = Bar15mService.calc_bollinger(vals, ventana=3)
    # media ventana 3 en índice 2 = 2.0; desv muestral ~1.0; k=2 -> upper=4.0, lower=0.0
    assert middle[2] == 2.0
    assert upper[2] == pytest.approx(4.0, abs=0.01)
    assert lower[2] == pytest.approx(0.0, abs=0.01)


def test_vwap_dos_barras():
    barras = [
        {"open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 100.0},
        {"open": 11.0, "high": 13.0, "low": 10.0, "close": 12.0, "volume": 200.0},
    ]
    vwap = Bar15mService.calc_vwap(barras)
    tp1 = (10 + 12 + 9 + 11) / 4.0  # 10.5
    tp2 = (11 + 13 + 10 + 12) / 4.0  # 11.5
    assert vwap[0] == tp1
    assert vwap[1] == pytest.approx((tp1 * 100 + tp2 * 200) / 300.0)


def test_ensamblar_ticks_agrupa_15m():
    t0 = datetime(2026, 9, 30, 14, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 9, 30, 14, 5, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 30, 14, 15, 0, tzinfo=UTC)
    ticks = [
        {"symbol": "A", "timestamp_utc": t0, "close": 10.0, "volume": 1.0},
        {"symbol": "A", "timestamp_utc": t1, "close": 11.0, "volume": 2.0},
        {"symbol": "A", "timestamp_utc": t2, "close": 12.0, "volume": 3.0},
    ]
    barras = Bar15mService.ensamblar_ticks(ticks)
    assert len(barras) == 2
    assert barras[0]["open"] == 10.0
    assert barras[0]["high"] == 11.0
    assert barras[0]["close"] == 11.0
    assert barras[0]["volume"] == 3.0
    assert barras[1]["close"] == 12.0


def test_analyze_genera_senal_compra(clean_env, empty_env_file, config_file):
    settings = _settings(clean_env, empty_env_file, config_file)
    base = datetime(2026, 9, 30, 14, 0, 0, tzinfo=UTC)
    barras = [
        {
            "symbol": "NASDAQ:TEST",
            "timestamp_utc": base + _minutes(i * 15),
            "open": 100.0 + i,
            "high": 101.0 + i,
            "low": 99.0 + i,
            "close": 100.5 + i,
            "volume": 1000.0,
        }
        for i in range(25)
    ]
    latest = [
        {
            "symbol": "NASDAQ:TEST",
            "asset_class": "equity",
            "rsi_15": 55.0,
            "adx_15": 25.0,
        }
    ]
    svc = Bar15mService(FakeBarRepo(barras), FakeLatestTickRepo(latest), settings)
    res = svc.analyze("NASDAQ:TEST")

    assert res["sin_datos"] is False
    assert res["symbol"] == "NASDAQ:TEST"
    assert len(res["barras"]) == 25
    assert res["ultimo"]["close"] == 100.5 + 24
    # Precio > VWAP, SMA9 > SMA21 en tendencia creciente, ADX ok, RSI ok -> COMPRAR/NEUTRAL
    assert res["signal"] in ("COMPRAR", "NEUTRAL")


# ── Screener15mService ───────────────────────────────────────────────────────
def test_screener_signal_compra():
    cfg = {"rsi_sobrecompra": 70, "rsi_sobreventa": 30, "adx_min": 20, "vol_ratio_min": 1.0}
    assert Screener15mService.calc_signal(105.0, 100.0, 1.2, 55.0, 25.0, cfg) == "COMPRAR"


def test_screener_signal_venta():
    cfg = {"rsi_sobrecompra": 70, "rsi_sobreventa": 30, "adx_min": 20, "vol_ratio_min": 1.0}
    assert Screener15mService.calc_signal(95.0, 100.0, 1.2, 55.0, 25.0, cfg) == "VENDER"


def test_screener_signal_neutral_adx_bajo():
    cfg = {"rsi_sobrecompra": 70, "rsi_sobreventa": 30, "adx_min": 20, "vol_ratio_min": 1.0}
    assert Screener15mService.calc_signal(105.0, 100.0, 1.2, 55.0, 10.0, cfg) == "NEUTRAL"


def test_screener_scan(clean_env, empty_env_file, config_file):
    settings = _settings(clean_env, empty_env_file, config_file)
    base = datetime(2026, 9, 30, 14, 0, 0, tzinfo=UTC)
    barras = [
        {"symbol": "NASDAQ:A", "timestamp_utc": base + _minutes(i * 15),
         "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0 + i * 0.1, "volume": 1000.0}
        for i in range(12)
    ] + [
        {"symbol": "NASDAQ:B", "timestamp_utc": base + _minutes(i * 15),
         "open": 20.0, "high": 21.0, "low": 19.0, "close": 20.0 - i * 0.1, "volume": 1000.0}
        for i in range(12)
    ]
    latest = [
        {"symbol": "NASDAQ:A", "asset_class": "equity", "rsi_15": 55.0, "adx_15": 25.0},
        {"symbol": "NASDAQ:B", "asset_class": "equity", "rsi_15": 45.0, "adx_15": 25.0},
    ]
    svc = Screener15mService(FakeBarRepo(barras), FakeLatestTickRepo(latest), settings)
    filas = svc.scan()

    assert len(filas) == 2
    simbolos = {f["symbol"]: f for f in filas}
    assert "NASDAQ:A" in simbolos
    assert "NASDAQ:B" in simbolos
    assert simbolos["NASDAQ:A"]["change_pct"] > 0
    assert simbolos["NASDAQ:B"]["change_pct"] < 0


# ── ConfluenciaService ───────────────────────────────────────────────────────
def test_confluencia_estado_tf_alcista():
    assert ConfluenciaService.estado_tf(0.5, 55.0) == {"signo": 1, "label": "ALCISTA", "rsi": 55.0}


def test_confluencia_estado_tf_sobrecompra():
    # RSI >= 70 anula el cambio positivo
    assert ConfluenciaService.estado_tf(0.5, 75.0) == {"signo": -1, "label": "BAJISTA", "rsi": 75.0}


def test_confluencia_estado_tf_sobreventa():
    assert ConfluenciaService.estado_tf(-0.5, 25.0) == {"signo": 1, "label": "ALCISTA", "rsi": 25.0}


def test_confluencia_score_compra():
    s5 = {"signo": 1, "label": "ALCISTA", "rsi": 55.0}
    s15 = {"signo": 1, "label": "ALCISTA", "rsi": 55.0}
    s1d = {"signo": 1, "label": "ALCISTA", "rsi": 55.0}
    assert ConfluenciaService.score_confluencia(s5, s15, s1d) == (3, "COMPRAR", "verde")


def test_confluencia_score_venta():
    s5 = {"signo": -1, "label": "BAJISTA", "rsi": 45.0}
    s15 = {"signo": -1, "label": "BAJISTA", "rsi": 45.0}
    s1d = {"signo": -1, "label": "BAJISTA", "rsi": 45.0}
    assert ConfluenciaService.score_confluencia(s5, s15, s1d) == (-3, "VENDER", "rojo")


def test_confluencia_scan(clean_env, empty_env_file, config_file):
    settings = _settings(clean_env, empty_env_file, config_file)
    indicators = [
        {"symbol": "NASDAQ:A", "tf": "5", "rsi": 55.0, "change_pct": 0.2},
        {"symbol": "NASDAQ:A", "tf": "15", "rsi": 60.0, "change_pct": 0.5},
        {"symbol": "NASDAQ:B", "tf": "5", "rsi": 45.0, "change_pct": -0.1},
        {"symbol": "NASDAQ:B", "tf": "15", "rsi": 40.0, "change_pct": -0.3},
    ]
    latest = [
        {"symbol": "NASDAQ:A", "asset_class": "equity", "rsi": 55.0, "change_pct": 1.0},
        {"symbol": "NASDAQ:B", "asset_class": "equity", "rsi": 45.0, "change_pct": -1.0},
    ]
    svc = ConfluenciaService(FakeIndicatorRepo(indicators), FakeLatestTickRepo(latest), settings)
    filas = svc.scan()

    assert len(filas) == 2
    por_simbolo = {f["symbol"]: f for f in filas}
    assert por_simbolo["NASDAQ:A"]["signal"] == "COMPRAR"
    assert por_simbolo["NASDAQ:B"]["signal"] == "VENDER"


# ── InitialBalanceService ────────────────────────────────────────────────────
def _ib_barras(symbol="NASDAQ:X", cierre_post=103.5):
    """IB 09:30–09:45 NY (13:30–13:45 UTC) + una barra posterior a las 10:00."""
    base = datetime(2026, 9, 30, 13, 30, 0, tzinfo=UTC)
    return [
        {"symbol": symbol, "timestamp_utc": base, "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.5},
        {"symbol": symbol, "timestamp_utc": base + _minutes(15), "open": 100.5, "high": 102.0, "low": 100.0, "close": 101.0},
        {"symbol": symbol, "timestamp_utc": base + _minutes(30), "open": 101.0, "high": 104.0, "low": 101.0, "close": cierre_post},
    ]


def test_ib_ruptura_alcista():
    fila = InitialBalanceService.evaluar("NASDAQ:X", _ib_barras(cierre_post=103.5))
    assert fila["ruptura"] == "ALCISTA"
    assert fila["ib_high"] == 102.0
    assert fila["ib_low"] == 99.0
    assert fila["hora"] == "10:00"
    assert fila["fuerza_pct"] == pytest.approx(1.4706, abs=0.01)


def test_ib_ruptura_bajista():
    fila = InitialBalanceService.evaluar("NASDAQ:X", _ib_barras(cierre_post=98.0))
    assert fila["ruptura"] == "BAJISTA"
    assert fila["hora"] == "10:00"


def test_ib_dentro_del_rango():
    fila = InitialBalanceService.evaluar("NASDAQ:X", _ib_barras(cierre_post=101.0))
    assert fila["ruptura"] == "DENTRO"
    assert fila["hora"] == ""


def test_ib_sin_barras():
    assert InitialBalanceService.evaluar("NASDAQ:X", []) is None


def test_ib_scan_prioriza_rupturas(clean_env, empty_env_file, config_file):
    settings = _settings(clean_env, empty_env_file, config_file)
    barras = _ib_barras("NASDAQ:A", cierre_post=103.5) + _ib_barras("NASDAQ:B", cierre_post=101.0)
    latest = [
        {"symbol": "NASDAQ:A", "asset_class": "equity"},
        {"symbol": "NASDAQ:B", "asset_class": "equity"},
    ]
    svc = InitialBalanceService(FakeBarRepo(barras), FakeLatestTickRepo(latest), settings)
    data = svc.scan_por_accion(["NASDAQ:A", "NASDAQ:B"])

    assert data["n_rupturas"] == 1
    assert data["filas"][0]["symbol"] == "NASDAQ:A"
    assert data["filas"][0]["ruptura"] == "ALCISTA"


def test_ib_evaluar_lote_alineado_sin_truncar(clean_env, empty_env_file, config_file):
    """`evaluar_lote` conserva el orden de entrada y no reordena ni trunca."""
    settings = _settings(clean_env, empty_env_file, config_file)
    barras = (
        _ib_barras("NASDAQ:A", cierre_post=101.0)
        + _ib_barras("NASDAQ:B", cierre_post=103.5)
        + _ib_barras("NASDAQ:C", cierre_post=98.0)
    )
    svc = InitialBalanceService(FakeBarRepo(barras), FakeLatestTickRepo([]), settings)

    lote = svc.evaluar_lote(["NASDAQ:A", "NASDAQ:B", "NASDAQ:C"])

    assert list(lote.keys()) == ["NASDAQ:A", "NASDAQ:B", "NASDAQ:C"]
    assert lote["NASDAQ:A"]["ruptura"] == "DENTRO"
    assert lote["NASDAQ:B"]["ruptura"] == "ALCISTA"
    assert lote["NASDAQ:C"]["ruptura"] == "BAJISTA"


def test_ib_evaluar_lote_omite_sin_barras(clean_env, empty_env_file, config_file):
    settings = _settings(clean_env, empty_env_file, config_file)
    svc = InitialBalanceService(
        FakeBarRepo(_ib_barras("NASDAQ:A", cierre_post=103.5)),
        FakeLatestTickRepo([]),
        settings,
    )

    lote = svc.evaluar_lote(["NASDAQ:A", "NASDAQ:Z"])

    assert list(lote.keys()) == ["NASDAQ:A"]


# ── Sector15mService ─────────────────────────────────────────────────────────
def test_sector_15m_agrega_y_ordena():
    sector_map = {"NASDAQ:A": "Tech", "NASDAQ:B": "Tech", "NASDAQ:C": "Energy"}
    filas = [
        {"symbol": "NASDAQ:A", "change_pct": 2.0},
        {"symbol": "NASDAQ:B", "change_pct": -1.0},
        {"symbol": "NASDAQ:C", "change_pct": 0.5},
    ]
    out = Sector15mService.agregar(sector_map, filas)

    assert [s["sector"] for s in out] == ["Tech", "Energy"]
    assert out[0]["change_pct"] == pytest.approx(0.5)
    assert out[0]["n"] == 2
    assert out[1]["n"] == 1


# ── DivergenciaService ───────────────────────────────────────────────────────
def _bars_por_cierre(closes):
    return [
        {"high": c, "low": c, "close": c, "timestamp_utc": 0} for c in closes
    ]


def test_rsi_serie_alcista():
    closes = [float(i) for i in range(1, 30)]
    rsi = DivergenciaService.rsi_serie(closes, 14)
    assert rsi[13] is None
    assert rsi[-1] == pytest.approx(100.0)


def test_rsi_serie_bajista():
    closes = [float(i) for i in range(30, 1, -1)]
    rsi = DivergenciaService.rsi_serie(closes, 14)
    assert rsi[-1] == pytest.approx(0.0)


def test_divergencia_bajista():
    closes = [10.0, 9.93, 10.34, 10.09, 10.51, 10.33, 10.27, 10.58, 10.89,
              10.89, 10.58, 10.61, 10.56, 10.95, 10.75, 10.69, 11.06, 10.73,
              10.71, 11.01]
    fila = DivergenciaService.detectar(
        "NASDAQ:X", _bars_por_cierre(closes), k=1, rsi_min=1.0, min_sep=3, periodo=3
    )
    assert fila["tipo"] == "BAJISTA"
    assert fila["rsi_delta"] < 0
    assert fila["p2"] > fila["p1"]


def test_divergencia_alcista():
    closes = [10.0, 10.03, 9.6, 9.93, 9.89, 9.76, 9.95, 9.95, 9.89, 9.99,
              9.59, 9.57, 9.45, 9.77, 10.06, 9.83, 9.76, 9.41, 9.31, 9.51]
    fila = DivergenciaService.detectar(
        "NASDAQ:X", _bars_por_cierre(closes), k=1, rsi_min=1.0, min_sep=3, periodo=3
    )
    assert fila["tipo"] == "ALCISTA"
    assert fila["rsi_delta"] > 0
    assert fila["p2"] < fila["p1"]


def test_divergencia_sin_patron():
    closes = [10.0 + i * 0.2 for i in range(24)]
    assert DivergenciaService.detectar("NASDAQ:X", _bars_por_cierre(closes)) is None


# ── helpers ──────────────────────────────────────────────────────────────────
def _minutes(n: int):
    from datetime import timedelta
    return timedelta(minutes=n)

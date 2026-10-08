"""services/bar_15m_service.py — análisis de barras 15 min para un ticker.

Calcula velas 15m, SMA 9/21, Bollinger 20/2, VWAP, volumen relativo y una
señal de compra/venta simple. Si las barras materializadas están desactualizadas,
puede ensamblar barras a partir de ticks de `fact_market_series`.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import sqrt
from typing import Any, Optional

from core.settings import Settings
from core.timezone import now_utc


def _f(valor: Any) -> Optional[float]:
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _r4(valor: Any) -> Optional[float]:
    """Normaliza a máximo 4 decimales para estandarizar la salida."""
    v = _f(valor)
    return round(v, 4) if v is not None else None


def _floor_15m(ts: datetime) -> datetime:
    """Redondea hacia abajo a múltiplo de 15 minutos."""
    ts = ts.astimezone(timezone.utc)
    return ts.replace(minute=(ts.minute // 15) * 15, second=0, microsecond=0)


def _floor_5m(ts: datetime) -> datetime:
    """Redondea hacia abajo a múltiplo de 5 minutos."""
    ts = ts.astimezone(timezone.utc)
    return ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)


def _sma(valores: list[Optional[float]], ventana: int) -> list[Optional[float]]:
    salida: list[Optional[float]] = []
    for i in range(len(valores)):
        trozo = [v for v in valores[max(0, i - ventana + 1) : i + 1] if v is not None]
        salida.append(sum(trozo) / len(trozo) if trozo else None)
    return salida


def _bollinger(
    valores: list[Optional[float]], ventana: int = 20, k: float = 2.0
) -> tuple[list[Optional[float]], list[Optional[float]], list[Optional[float]]]:
    """Devuelve (upper, middle, lower)."""
    middle = _sma(valores, ventana)
    upper: list[Optional[float]] = []
    lower: list[Optional[float]] = []
    for i in range(len(valores)):
        trozo = [v for v in valores[max(0, i - ventana + 1) : i + 1] if v is not None]
        if len(trozo) < 2:
            upper.append(None)
            lower.append(None)
            continue
        media = sum(trozo) / len(trozo)
        var = sum((x - media) ** 2 for x in trozo) / (len(trozo) - 1)
        desv = sqrt(var)
        upper.append(media + k * desv)
        lower.append(media - k * desv)
    return upper, middle, lower


def _vwap(barras: list[dict]) -> list[Optional[float]]:
    """VWAP acumulado sobre la ventana de barras (typical price * volume)."""
    cum_pv = 0.0
    cum_v = 0.0
    salida: list[Optional[float]] = []
    prev: Optional[float] = None
    for b in barras:
        o, h, l, c, v = _f(b.get("open")), _f(b.get("high")), _f(b.get("low")), _f(b.get("close")), _f(b.get("volume"))
        if None in (o, h, l, c):
            salida.append(prev)
            continue
        if v is None or v <= 0:
            salida.append(prev)
            continue
        tp = (o + h + l + c) / 4.0
        cum_pv += tp * v
        cum_v += v
        prev = cum_pv / cum_v
        salida.append(prev)
    return salida


def _volume_ratio(barras: list[dict], ventana: int = 10) -> Optional[float]:
    if len(barras) < 1:
        return None
    volumenes = [_f(b.get("volume")) for b in barras]
    validos = [v for v in volumenes if v is not None and v > 0]
    if not validos:
        return None
    ultimo = validos[-1]
    media = sum(validos[-ventana:-1]) / max(1, len(validos[-ventana:-1]))
    if not media:
        return None
    return ultimo / media


def _signal(
    close: Optional[float],
    vwap: Optional[float],
    sma9: Optional[float],
    sma21: Optional[float],
    vol_ratio: Optional[float],
    rsi: Optional[float],
    adx: Optional[float],
    cfg: dict,
) -> tuple[str, dict]:
    """Señal y factores que la justifican."""
    if close is None or vwap is None:
        return "NEUTRAL", {"motivo": "sin precio/vwap"}

    sobrecompra = float(cfg.get("rsi_sobrecompra", 70))
    sobreventa = float(cfg.get("rsi_sobreventa", 30))
    adx_min = float(cfg.get("adx_min", 20))
    vol_min = float(cfg.get("vol_ratio_min", 1.0))

    arriba_vwap = close > vwap
    cruce_alcista = sma9 is not None and sma21 is not None and sma9 > sma21
    tendencia = adx is not None and adx >= adx_min
    volumen = vol_ratio is not None and vol_ratio >= vol_min
    rsi_ok_compra = rsi is not None and sobreventa < rsi < sobrecompra
    rsi_ok_venta = rsi is not None and (rsi >= sobrecompra or rsi <= sobreventa)

    factores = {
        "arriba_vwap": arriba_vwap,
        "cruce_alcista": cruce_alcista,
        "tendencia": tendencia,
        "volumen": volumen,
        "rsi": rsi,
        "adx": adx,
        "vol_ratio": vol_ratio,
    }

    if arriba_vwap and cruce_alcista and tendencia and volumen and rsi_ok_compra:
        return "COMPRAR", factores
    if (not arriba_vwap) and (not cruce_alcista) and tendencia and volumen and rsi_ok_venta:
        return "VENDER", factores
    return "NEUTRAL", factores


class Bar15mService:
    def __init__(
        self,
        bar_repo,
        latest_tick_repo,
        settings: Settings,
    ) -> None:
        self.bar_repo = bar_repo
        self.latest_tick_repo = latest_tick_repo
        self.settings = settings

    def _cfg(self) -> dict:
        return self.settings.business("trading_15m", default={})

    def _horas(self) -> int:
        return int(self._cfg().get("horas", 48))

    def _stale_minutos(self) -> int:
        return int(self._cfg().get("stale_min", 60))

    def analyze(self, symbol: str, horas: Optional[int] = None) -> dict:
        """Devuelve barras 15m + indicadores + señal para un símbolo."""
        horas = int(horas or self._horas())
        desde = now_utc() - timedelta(hours=horas)

        barras = self.bar_repo.fetch_barras(symbol, desde)
        if self._necesita_fallback(barras):
            ticks = self.bar_repo.fetch_ticks(symbol, desde)
            if ticks:
                barras = self._ensamblar_desde_ticks(ticks)

        barras = [b for b in barras if all(_f(b.get(k)) is not None for k in ("open", "high", "low", "close"))]
        if not barras:
            return {"symbol": symbol, "barras": [], "sin_datos": True}

        closes = [_f(b["close"]) for b in barras]
        sma9 = _sma(closes, 9)
        sma21 = _sma(closes, 21)
        bb_upper, bb_middle, bb_lower = _bollinger(closes, 20, 2.0)
        vwap = _vwap(barras)
        vol_ratio = _volume_ratio(barras, 10)

        # Últimos valores
        ultimo = barras[-1]
        last_close = closes[-1]
        last_sma9 = sma9[-1]
        last_sma21 = sma21[-1]
        last_vwap = vwap[-1]
        last_bb = {
            "upper": bb_upper[-1],
            "middle": bb_middle[-1],
            "lower": bb_lower[-1],
        }

        # RSI/ADX 15m del último tick
        rsi_15, adx_15 = self._latest_indicators(symbol)

        senal, factores = _signal(
            close=last_close,
            vwap=last_vwap,
            sma9=last_sma9,
            sma21=last_sma21,
            vol_ratio=vol_ratio,
            rsi=rsi_15,
            adx=adx_15,
            cfg=self._cfg(),
        )

        serie = []
        for i, b in enumerate(barras):
            serie.append(
                {
                    "ts": b["timestamp_utc"].strftime("%d/%m %H:%M"),
                    "open": _r4(b["open"]),
                    "high": _r4(b["high"]),
                    "low": _r4(b["low"]),
                    "close": _r4(b["close"]),
                    "volume": _f(b.get("volume")),
                    "sma9": _r4(sma9[i]),
                    "sma21": _r4(sma21[i]),
                    "bb_upper": _r4(bb_upper[i]),
                    "bb_middle": _r4(bb_middle[i]),
                    "bb_lower": _r4(bb_lower[i]),
                    "vwap": _r4(vwap[i]),
                }
            )

        return {
            "symbol": symbol,
            "sin_datos": False,
            "barras": serie,
            "signal": senal,
            "factores": factores,
            "ultimo": {
                "close": _r4(last_close),
                "vwap": _r4(last_vwap),
                "sma9": _r4(last_sma9),
                "sma21": _r4(last_sma21),
                "bb": {
                    "upper": _r4(last_bb["upper"]),
                    "middle": _r4(last_bb["middle"]),
                    "lower": _r4(last_bb["lower"]),
                },
                "vol_ratio": _r4(vol_ratio),
                "rsi_15": rsi_15,
                "adx_15": adx_15,
            },
        }

    def _necesita_fallback(self, barras: list[dict]) -> bool:
        """True si no hay barras o la más reciente es más vieja que stale_min."""
        if not barras:
            return True
        max_ts = max(b["timestamp_utc"] for b in barras)
        return (now_utc() - max_ts) > timedelta(minutes=self._stale_minutos())

    def _ensamblar_desde_ticks(self, ticks: list[dict]) -> list[dict]:
        """Agrupa ticks en buckets de 15 min formando OHLCV."""
        buckets: dict[datetime, list[dict]] = defaultdict(list)
        for t in ticks:
            ts = t.get("timestamp_utc")
            if ts is None:
                continue
            buckets[_floor_15m(ts)].append(t)

        barras = []
        for inicio in sorted(buckets):
            vals = buckets[inicio]
            closes = [_f(v.get("close")) for v in vals]
            vols = [_f(v.get("volume")) for v in vals]
            closes = [c for c in closes if c is not None]
            vols = [v for v in vols if v is not None]
            if not closes:
                continue
            barras.append(
                {
                    "timestamp_utc": inicio,
                    "open": vals[0]["close"],
                    "high": max(closes),
                    "low": min(closes),
                    "close": vals[-1]["close"],
                    "volume": sum(vols) if vols else None,
                    "n_ticks": len(vals),
                }
            )
        return barras

    def _latest_indicators(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        rows = self.latest_tick_repo.fetch_all(asset_classes=["equity"])
        for r in rows:
            if r.get("symbol") == symbol:
                return _f(r.get("rsi_15")), _f(r.get("adx_15"))
        # Si no coincide exacto, buscar sin prefijo
        ticker = symbol.split(":")[-1]
        for r in rows:
            if r.get("symbol", "").split(":")[-1] == ticker:
                return _f(r.get("rsi_15")), _f(r.get("adx_15"))
        return None, None

    # ── funciones puras expuestas para tests ──────────────────────────────────
    @staticmethod
    def calc_sma(valores: list[Optional[float]], ventana: int) -> list[Optional[float]]:
        return _sma(valores, ventana)

    @staticmethod
    def calc_bollinger(
        valores: list[Optional[float]], ventana: int = 20, k: float = 2.0
    ) -> tuple[list[Optional[float]], list[Optional[float]], list[Optional[float]]]:
        return _bollinger(valores, ventana, k)

    @staticmethod
    def calc_vwap(barras: list[dict]) -> list[Optional[float]]:
        return _vwap(barras)

    @staticmethod
    def ensamblar_ticks(ticks: list[dict]) -> list[dict]:
        """Wrapper estático para testear el ensamblaje (15m)."""
        svc = Bar15mService.__new__(Bar15mService)
        return svc._ensamblar_desde_ticks(ticks)

    @staticmethod
    def ensamblar_ticks_5m(ticks: list[dict]) -> list[dict]:
        """Agrupa ticks en buckets de 5 min formando OHLCV."""
        buckets: dict[datetime, list[dict]] = defaultdict(list)
        for t in ticks:
            ts = t.get("timestamp_utc")
            if ts is None:
                continue
            buckets[_floor_5m(ts)].append(t)

        barras = []
        for inicio in sorted(buckets):
            vals = buckets[inicio]
            closes = [_f(v.get("close")) for v in vals]
            vols = [_f(v.get("volume")) for v in vals]
            closes = [c for c in closes if c is not None]
            vols = [v for v in vols if v is not None]
            if not closes:
                continue
            barras.append(
                {
                    "timestamp_utc": inicio,
                    "open": vals[0]["close"],
                    "high": max(closes),
                    "low": min(closes),
                    "close": vals[-1]["close"],
                    "volume": sum(vols) if vols else None,
                    "n_ticks": len(vals),
                }
            )
        return barras

"""services/precio_service.py — precio + SMA20/50 + señal y recomendaciones.

Replica (adaptado a la BD) las tarjetas de referencia "Precio QQQ/SPY/ORO
(48h) — SMA20/SMA50" con la señal compuesta y las recomendaciones accionables.

Datos:
  - `fact_market_series` (close, rsi, cci20, bbpower, adx, volume) → serie y SMA.
  - `score_service` (momentum global / radar) → contexto macro.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from core.settings import Settings
from core.timezone import now_utc


def _f(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _sma(valores: list[float], ventana: int) -> list[Optional[float]]:
    salida: list[Optional[float]] = []
    for i in range(len(valores)):
        inicio = max(0, i - ventana + 1)
        trozo = [v for v in valores[inicio : i + 1] if v is not None]
        salida.append(sum(trozo) / len(trozo) if trozo else None)
    return salida


class PrecioService:
    def __init__(self, series_repo, score_service, settings: Settings) -> None:
        self.series_repo = series_repo
        self.score_service = score_service
        self.settings = settings

    def _config_tarjetas(self) -> list[dict]:
        return self.settings.business("precio", "tarjetas", default=[])

    def analisis_todas(self) -> list[dict]:
        """Analiza todas las tarjetas de precio (una sola lectura del ciclo)."""
        _, mercado = self.score_service.calcular_ciclo()
        momentum = mercado.score_momentum
        radar = mercado.score_radar
        horas = int(self.settings.business("precio", "horas", default=48))
        return [
            self._analisis(tarjeta, momentum, radar, horas)
            for tarjeta in self._config_tarjetas()
        ]

    def _analisis(self, tarjeta: dict, momentum, radar, horas: int) -> dict:
        symbol = tarjeta["symbol"]
        desde = now_utc() - timedelta(hours=horas)
        rows = self.series_repo.fetch_serie(symbol, desde, limit=5000)

        base = {
            "clave": tarjeta.get("clave"),
            "titulo": tarjeta.get("titulo", symbol),
            "symbol": symbol,
            "sin_datos": True,
        }
        if not rows:
            return base

        closes = [_f(r.get("close")) for r in rows]
        valid = [c for c in closes if c is not None]
        if not valid:
            return base
        sma20 = _sma(closes, 20)
        sma50 = _sma(closes, 50)

        serie = [
            {
                "ts": rows[i]["timestamp_utc"].strftime("%d/%m %H:%M"),
                "close": closes[i],
                "sma20": sma20[i],
                "sma50": sma50[i],
            }
            for i in range(len(rows))
        ]

        ultimo = rows[-1]
        close = closes[-1] if closes[-1] is not None else valid[-1]
        rsi = _f(ultimo.get("rsi"))
        adx = _f(ultimo.get("adx"))
        bbpower = _f(ultimo.get("bbpower"))
        cci = _f(ultimo.get("cci20"))

        vol_ratio = None
        volumenes = [_f(r.get("volume")) for r in rows]
        volumenes = [v for v in volumenes if v]
        if volumenes:
            media = sum(volumenes[-20:]) / len(volumenes[-20:])
            if media:
                vol_ratio = volumenes[-1] / media

        s20 = sma20[-1] if sma20 else None
        s50 = sma50[-1] if sma50 else None
        soporte = min(valid)
        resistencia = max(valid)
        dist_soporte = ((close - soporte) / close * 100) if close and soporte else None
        dist_resistencia = ((resistencia - close) / close * 100) if close and resistencia else None

        score = self._score(
            momentum=momentum,
            radar=radar,
            close=close,
            sma20=s20,
            rsi=rsi,
            adx=adx,
            bbpower=bbpower,
            vol_ratio=vol_ratio,
        )
        signal = "COMPRAR" if score >= 60 else ("VENDER" if score <= 40 else "NEUTRAL")

        return {
            "clave": tarjeta.get("clave"),
            "titulo": tarjeta.get("titulo", symbol),
            "symbol": symbol,
            "sin_datos": False,
            "serie": serie,
            "close": close,
            "rsi": rsi,
            "adx": adx,
            "cci20": cci,
            "bbpower": bbpower,
            "vol_ratio": vol_ratio,
            "sma20": s20,
            "sma50": s50,
            "soporte": soporte,
            "resistencia": resistencia,
            "dist_soporte": dist_soporte,
            "dist_resistencia": dist_resistencia,
            "signal_score": score,
            "signal": signal,
            "rango": {"lo": soporte, "hi": resistencia},
            "metricas": self._metricas(
                close=close,
                sma20=s20,
                sma50=s50,
                rsi=rsi,
                adx=adx,
                lo=soporte,
                hi=resistencia,
            ),
            "recomendaciones": self._recomendaciones(
                signal, close, s20, s50, soporte, resistencia,
                dist_soporte, dist_resistencia, adx,
            ),
        }

    def _escala(self) -> dict:
        return self.settings.business("precio", "escala", default={}) or {}

    def _metricas(self, *, close, sma20, sma50, rsi, adx, lo, hi) -> list[dict]:
        """View models de las barras 0–100% para la tarjeta de precio.

        Referencias: Precio/SMA20/SMA50 → rango de la ventana `[lo, hi]`; RSI →
        0–100; ADX → 0–`adx_max`; cruce SMA20/SMA50 → barra centrada ±`cruce_max_pct`.
        """
        escala = self._escala()
        rango = (hi - lo) or 1.0

        def pos(v):
            if v is None:
                return None
            return round(max(0.0, min(100.0, (float(v) - lo) / rango * 100.0)), 1)

        def clamp100(v):
            if v is None:
                return None
            return round(max(0.0, min(100.0, float(v))), 1)

        marca = pos(close) if escala.get("marcar_precio_en_sma", True) else None

        def color_precio_vs_sma(sma):
            if close is None or sma is None:
                return "gris"
            return "verde" if close > sma else "rojo"

        zonas = escala.get("rsi_zonas", [30, 70])

        def color_rsi(v):
            if v is None:
                return "gris"
            if v <= zonas[0]:
                return "verde"
            if v >= zonas[1]:
                return "rojo"
            return "azul"

        adx_max = float(escala.get("adx_max", 50) or 50)

        def color_adx(v):
            if v is None:
                return "gris"
            if v >= 25:
                return "verde"
            if v >= 20:
                return "amarillo"
            return "azul"

        cruce_max = float(escala.get("cruce_max_pct", 0.5) or 0.5)

        metricas = [
            {
                "clave": "precio", "etiqueta": "Precio",
                "texto": f"{close:.2f}" if close is not None else "—",
                "pct": pos(close), "color": "azul", "marca": None,
                "centrada": False, "signo": 1,
            },
            {
                "clave": "sma20", "etiqueta": "SMA20",
                "texto": f"{sma20:.2f}" if sma20 is not None else "—",
                "pct": pos(sma20), "color": color_precio_vs_sma(sma20), "marca": marca,
                "centrada": False, "signo": 1,
            },
            {
                "clave": "sma50", "etiqueta": "SMA50",
                "texto": f"{sma50:.2f}" if sma50 is not None else "—",
                "pct": pos(sma50), "color": color_precio_vs_sma(sma50), "marca": marca,
                "centrada": False, "signo": 1,
            },
            {
                "clave": "rsi", "etiqueta": "RSI",
                "texto": f"{rsi:.1f}" if rsi is not None else "—",
                "pct": clamp100(rsi), "color": color_rsi(rsi), "marca": None,
                "centrada": False, "signo": 1, "zonas": zonas,
            },
            {
                "clave": "adx", "etiqueta": "ADX",
                "texto": f"{adx:.1f}" if adx is not None else "—",
                "pct": clamp100(adx / adx_max * 100.0) if adx is not None else None,
                "color": color_adx(adx), "marca": None, "centrada": False, "signo": 1,
            },
        ]

        if sma20 is not None and sma50:
            dev = (sma20 - sma50) / sma50 * 100.0
            pct = min(50.0, abs(dev) / cruce_max * 50.0)
            metricas.append(
                {
                    "clave": "cruce", "etiqueta": "SMA20 vs SMA50",
                    "texto": f"{dev:+.2f}%", "pct": round(pct, 1),
                    "color": "verde" if dev >= 0 else "rojo", "marca": None,
                    "centrada": True, "signo": 1 if dev >= 0 else -1,
                }
            )
        return metricas

    @staticmethod
    def _score(*, momentum, radar, close, sma20, rsi, adx, bbpower, vol_ratio) -> float:
        score = 0.0
        if momentum is not None:
            score += float(momentum) * 3.0
        if close is not None and sma20 is not None and close > sma20:
            score += 25.0
        if adx is not None:
            if adx >= 25:
                score += 15.0
            elif adx >= 20:
                score += 10.0
        if rsi is not None:
            if rsi < 30:
                score += 15.0
            elif rsi > 70:
                score -= 15.0
        if bbpower is not None:
            score += 10.0 if bbpower > 0 else -10.0
        if vol_ratio is not None:
            if vol_ratio > 1.2:
                score += 5.0
            elif vol_ratio < 0.8:
                score -= 5.0
        # Contexto macro: radar débil resta
        if radar is not None and radar < 4.5:
            score -= 10.0
        return round(score, 1)

    @staticmethod
    def _recomendaciones(signal, close, sma20, sma50, soporte, resistencia,
                         dist_soporte, dist_resistencia, adx) -> list[str]:
        recs: list[str] = []
        if signal == "COMPRAR":
            recs.append("Señal de COMPRA detectada.")
            if dist_resistencia is not None and dist_resistencia <= 1.5 and resistencia is not None:
                recs.append(f"⚠️ Precio cerca de resistencia ({resistencia:.2f}). No perseguir; esperar retroceso.")
            elif sma20 is not None and sma50 is not None and sma20 > sma50:
                recs.append("SMA20 sobre SMA50: momentum positivo confirmado.")
            else:
                recs.append("Puedes considerar entrada en retrocesos hacia SMA20.")
            if adx is not None and adx < 20:
                recs.append("⚠️ ADX bajo: tendencia aún débil. Usar stops ajustados.")
        elif signal == "VENDER":
            recs.append("Señal de VENTA detectada.")
            if dist_soporte is not None and dist_soporte <= 1.5 and soporte is not None:
                recs.append(f"⚠️ Precio cerca de soporte ({soporte:.2f}). No vender en mínimos; esperar rebote.")
            elif sma20 is not None and sma50 is not None and sma20 < sma50:
                recs.append("SMA20 bajo SMA50: momentum negativo confirmado.")
            else:
                recs.append("Puedes considerar salir o mantener stops en resistencia.")
            if adx is not None and adx < 20:
                recs.append("⚠️ ADX bajo: la caída podría ser temporal.")
        else:
            recs.append("Señal NEUTRAL: sin dirección clara.")
            if soporte is not None and resistencia is not None:
                recs.append(f"Mercado en rango: entre {soporte:.2f} y {resistencia:.2f}.")
            recs.append("Esperar ruptura de soporte o resistencia para tomar posición.")
        return recs

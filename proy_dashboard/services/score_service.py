"""services/score_service.py — motor de score (PASO 1/2/2b/3).

Lógica pura de negocio; sin SQL (usa repositorios) ni presentación. Todos los
pesos, zonas y umbrales vienen de `config_dashboard.json` (cero números mágicos).

  PASO 1  score por activo [0,10]
  PASO 2  score momentum (media ponderada de equity/etf)
  PASO 2b score 15 min (media de los últimos N registros por temporalidad)
  PASO 3  score radar intermarket (VIX/US10Y/DXY/TLT)
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from core.logging_config import get_logger
from core.settings import Settings
from core.timezone import ensure_utc, now_utc
from domain.market import ActivoTick, RiesgoItem
from domain.score import ComponenteScore, ScoreActivo, ScoreMercado

logger = get_logger("services.score_service")


def _f(valor: Any) -> Optional[float]:
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


# Nombre de componente (pesos) → clave de normalización en config_dashboard.json
_NORM_KEY = {
    "rsi": "rsi",
    "adx": "adx",
    "cci20": "cci20",
    "bbpower": "bbpower",
    "volume": "volume_ratio",
    "change": "change_pct",
}

# Catálogo de análisis del histograma 15m: (clave, condición, sugerencia).
# El texto NO repite métricas (media/percentil/%); esas van en las etiquetas.
_ANALISIS_REGLAS = [
    ("sin_datos", "n = 0", "Sin datos de score 15m para analizar."),
    (
        "compra_euforia",
        "zona COMPRAR y %COMPRAR ≥ 80",
        "Amplia mayoría alcista: mercado eufórico. Cuidado con sobrecompra; "
        "considera asegurar ganancias.",
    ),
    (
        "compra_fuerte",
        "zona COMPRAR y %COMPRAR ≥ 60",
        "Sesgo alcista claro: favorece largos. Espera retrocesos para entrar.",
    ),
    (
        "compra_leve",
        "zona COMPRAR y %COMPRAR < 60",
        "Sesgo alcista leve: prefiere confirmación con volumen antes de entrar.",
    ),
    (
        "venta_capitulacion",
        "zona VENDER y %VENDER ≥ 80",
        "Amplia mayoría bajista: posible capitulación. Cuidado con sobreventa y rebotes.",
    ),
    (
        "venta_fuerte",
        "zona VENDER y %VENDER ≥ 60",
        "Sesgo bajista claro: favorece cortos o postura defensiva. "
        "Espera rebotes para vender.",
    ),
    (
        "venta_leve",
        "zona VENDER y %VENDER < 60",
        "Sesgo bajista leve: prefiere confirmación antes de vender.",
    ),
    (
        "dividido",
        "NEUTRAL con %COMPRAR ≥ 25 y %VENDER ≥ 25",
        "Mercado dividido (bimodal): hay extremos en ambos lados; "
        "opera selectivo, no el índice.",
    ),
    (
        "inclina_alcista",
        "NEUTRAL con (%COMPRAR − %VENDER) ≥ 15",
        "Inclinación alcista dentro del rango: vigila ruptura al alza.",
    ),
    (
        "inclina_bajista",
        "NEUTRAL con (%VENDER − %COMPRAR) ≥ 15",
        "Inclinación bajista dentro del rango: vigila ruptura a la baja.",
    ),
    (
        "rango",
        "NEUTRAL sin inclinación",
        "Sin sesgo claro: mercado en rango. Espera ruptura para tomar posición.",
    ),
]


class ScoreService:
    def __init__(
        self,
        latest_tick_repo,
        heatmap_repo,
        indicator_repo,
        series_repo,
        settings: Settings,
    ) -> None:
        self.latest_tick_repo = latest_tick_repo
        self.heatmap_repo = heatmap_repo
        self.indicator_repo = indicator_repo
        self.series_repo = series_repo
        self.settings = settings

    # ── configuración ────────────────────────────────────────────────────────
    def _pesos(self) -> dict:
        return self.settings.business("score", "weights", default={})

    def _norm_cfg(self, nombre: str) -> dict:
        return self.settings.business("score", "normalization", default={}).get(nombre, {})

    def _clamp(self) -> dict:
        return self.settings.business("score", "clamp", default={"min": 0, "max": 10})

    def _zonas(self) -> dict:
        return self.settings.business("score", "zones", default={"comprar": 6.5, "vender": 4.5})

    def _momentum_cfg(self) -> dict:
        return self.settings.business("score", "momentum", default={"asset_classes": ["equity", "etf"]})

    def _score15_cfg(self) -> dict:
        return self.settings.business("score", "score_15min", default={"tf": "15", "last_n": 5})

    def _radar_cfg(self) -> dict:
        return self.settings.business("score", "radar", default={"components": []})

    # ── primitivas ───────────────────────────────────────────────────────────
    def normalizar(self, nombre: str, valor: Optional[float]) -> Optional[float]:
        """Normaliza un valor a [0,1] según la config; None si falta o mal rango."""
        if valor is None:
            return None
        cfg = self._norm_cfg(_NORM_KEY.get(nombre, nombre))
        lo, hi = cfg.get("min"), cfg.get("max")
        if lo is None or hi is None or hi == lo:
            return None
        x = (float(valor) - float(lo)) / (float(hi) - float(lo))
        return max(0.0, min(1.0, x))

    def _puntuar(self, valores: dict) -> tuple[Optional[float], list[ComponenteScore]]:
        """PASO 1: Σ(peso·norm)/Σpeso (renorm de NaN) escalado a [0,10]."""
        pesos = self._pesos()
        componentes: list[ComponenteScore] = []
        num = 0.0
        den = 0.0
        for nombre, valor in valores.items():
            peso = float(pesos.get(nombre, 0.0))
            norm = self.normalizar(nombre, valor)
            componentes.append(ComponenteScore(nombre, _f(valor), norm, peso))
            if norm is not None and peso > 0:
                num += peso * norm
                den += peso
        if den == 0:
            return None, componentes
        score = (num / den) * 10.0
        clamp = self._clamp()
        score = max(float(clamp["min"]), min(float(clamp["max"]), score))
        return score, componentes

    def zona(self, score: Optional[float]) -> str:
        if score is None:
            return "NEUTRAL"
        zonas = self._zonas()
        if score >= float(zonas["comprar"]):
            return "COMPRAR"
        if score <= float(zonas["vender"]):
            return "VENDER"
        return "NEUTRAL"

    def _row_a_tick(self, row: dict) -> ActivoTick:
        return ActivoTick(
            asset_id=row["asset_id"],
            symbol=row["symbol"],
            timestamp_utc=row["timestamp_utc"],
            asset_class=row.get("asset_class"),
            close=_f(row.get("close")),
            change_pct=_f(row.get("change_pct")),
            volume=_f(row.get("volume")),
            rsi=_f(row.get("rsi")),
            rsi_15=_f(row.get("rsi_15")),
            cci20_15=_f(row.get("cci20_15")),
            bbpower_15=_f(row.get("bbpower_15")),
            adx_15=_f(row.get("adx_15")),
            pivot_r3_15=_f(row.get("pivot_r3_15")),
        )

    # ── PASO 1 ───────────────────────────────────────────────────────────────
    def score_activo(self, tick: ActivoTick, vol_ratio: Optional[float] = None) -> ScoreActivo:
        valores = {
            "rsi": tick.rsi,
            "adx": tick.adx_15,
            "cci20": tick.cci20_15,
            "bbpower": tick.bbpower_15,
            "volume": vol_ratio,
            "change": tick.change_pct,
        }
        score, componentes = self._puntuar(valores)
        return ScoreActivo(tick.asset_id, tick.symbol, score, self.zona(score), componentes)

    # ── PASO 2 ───────────────────────────────────────────────────────────────
    def score_momentum(self, scores: list[ScoreActivo]) -> Optional[float]:
        valores = [s.score_general for s in scores if s.score_general is not None]
        if not valores:
            return None
        return sum(valores) / len(valores)

    # ── PASO 2b ──────────────────────────────────────────────────────────────
    def score_15min(self) -> Optional[float]:
        cfg = self._score15_cfg()
        tf = str(cfg.get("tf", "15"))
        last_n = int(cfg.get("last_n", 5))
        rows = self.indicator_repo.fetch_recent(tf, limit=max(last_n * 200, 1000))
        if not rows:
            return None
        por_asset: dict[int, list[dict]] = defaultdict(list)
        for row in rows:  # vienen DESC: los últimos N por activo
            if len(por_asset[row["asset_id"]]) < last_n:
                por_asset[row["asset_id"]].append(row)
        promedios: list[float] = []
        for filas in por_asset.values():
            puntajes = []
            for r in filas:
                score, _ = self._puntuar(
                    {
                        "rsi": _f(r.get("rsi")),
                        "adx": _f(r.get("adx")),
                        "cci20": _f(r.get("cci20")),
                        "bbpower": _f(r.get("bbpower")),
                        "volume": None,
                        "change": _f(r.get("change_pct")),
                    }
                )
                if score is not None:
                    puntajes.append(score)
            if puntajes:
                promedios.append(sum(puntajes) / len(puntajes))
        if not promedios:
            return None
        return sum(promedios) / len(promedios)

    def distribucion_15min(self, bins: int = 8) -> dict:
        """Histograma del score 15m por acción + media, zonas y descripción."""
        cfg = self._score15_cfg()
        tf = str(cfg.get("tf", "15"))
        last_n = int(cfg.get("last_n", 5))
        rows = self.indicator_repo.fetch_recent(
            tf, limit=max(last_n * 300, 1500), asset_classes=["equity"]
        )
        scores = self._scores_por_activo(rows, last_n)
        return self.histograma_de_scores(scores, bins=bins, tf=tf, zonas=self._zonas())

    def _scores_por_activo(self, rows: list[dict], last_n: int) -> list[float]:
        por_asset: dict[int, list[dict]] = defaultdict(list)
        for row in rows:  # vienen DESC: los últimos N por activo
            if len(por_asset[row["asset_id"]]) < last_n:
                por_asset[row["asset_id"]].append(row)

        scores: list[float] = []
        for filas in por_asset.values():
            puntajes = []
            for r in filas:
                score, _ = self._puntuar(
                    {
                        "rsi": _f(r.get("rsi")),
                        "adx": _f(r.get("adx")),
                        "cci20": _f(r.get("cci20")),
                        "bbpower": _f(r.get("bbpower")),
                        "volume": None,
                        "change": _f(r.get("change_pct")),
                    }
                )
                if score is not None:
                    puntajes.append(score)
            if puntajes:
                scores.append(sum(puntajes) / len(puntajes))
        return scores

    # ── PASO 3 ───────────────────────────────────────────────────────────────
    def score_radar(self) -> tuple[Optional[float], list[RiesgoItem]]:
        cfg = self._radar_cfg()
        componentes_cfg = cfg.get("components", [])
        claves = [c["logical_key"] for c in componentes_cfg]
        rows = self.latest_tick_repo.fetch_by_logical_keys(claves)

        preferido: dict[str, dict] = {}
        for r in rows:
            lk = r.get("logical_key")
            if lk is None or r.get("rsi") is None:
                continue
            actual = preferido.get(lk)
            if actual is None or (r.get("is_canonical") and not actual.get("is_canonical")):
                preferido[lk] = r

        items: list[RiesgoItem] = []
        num = 0.0
        den = 0.0
        for comp in componentes_cfg:
            lk = comp["logical_key"]
            peso = float(comp.get("weight", 0.0))
            direccion = comp.get("direction", "direct")
            row = preferido.get(lk)
            if row is None:
                items.append(RiesgoItem(lk, symbol="", estado="SIN_DATOS"))
                continue
            p = float(row["rsi"]) / 100.0
            norm_dir = p * 10.0 if direccion == "direct" else (1.0 - p) * 10.0
            items.append(
                RiesgoItem(
                    logical_key=lk,
                    symbol=row["symbol"],
                    valor=_f(row.get("close")),
                    change_pct=_f(row.get("change_pct")),
                    rsi=_f(row.get("rsi")),
                    norm_dir=norm_dir,
                    estado=self._estado_riesgo(norm_dir),
                )
            )
            num += peso * norm_dir
            den += peso

        score = (num / den) if den else None
        return score, items

    def _estado_riesgo(self, norm_dir: float) -> str:
        if norm_dir >= 6.5:
            return "ALCISTA"
        if norm_dir <= 3.5:
            return "BAJISTA"
        return "NEUTRO"

    # ── histograma de score 15m (puro) ───────────────────────────────────────
    @staticmethod
    def tf_label(tf) -> str:
        """Etiqueta de temporalidad: '15' → '15m', '5' → '5m', '1d' → '1D'."""
        t = str(tf).lower()
        if t in ("1", "1d", "d", "diario"):
            return "1D"
        return f"{t}m" if t.isdigit() else str(tf)

    @staticmethod
    def zona_de(score: Optional[float], zonas: dict) -> str:
        if score is None:
            return "NEUTRAL"
        if score >= float(zonas["comprar"]):
            return "COMPRAR"
        if score <= float(zonas["vender"]):
            return "VENDER"
        return "NEUTRAL"

    @staticmethod
    def catalogo_analisis() -> list[dict]:
        """Todas las combinaciones posibles del análisis (para revisión)."""
        return [
            {"clave": c, "condicion": cond, "texto": t}
            for c, cond, t in _ANALISIS_REGLAS
        ]

    @staticmethod
    def sugerencia_hist(media, percentil, n_compra, n_venta, n, zonas) -> str:
        """Sugerencia accionable (sin repetir métricas ya mostradas en etiquetas)."""
        return ScoreService._opcion_analisis(media, percentil, n_compra, n_venta, n, zonas)[
            "texto"
        ]

    @staticmethod
    def _opcion_analisis(media, percentil, n_compra, n_venta, n, zonas) -> dict:
        pc = round(n_compra / n * 100) if n else 0
        pv = round(n_venta / n * 100) if n else 0
        zona = ScoreService.zona_de(media, zonas)

        if not n:
            clave = "sin_datos"
        elif zona == "COMPRAR":
            clave = "compra_euforia" if pc >= 80 else (
                "compra_fuerte" if pc >= 60 else "compra_leve"
            )
        elif zona == "VENDER":
            clave = "venta_capitulacion" if pv >= 80 else (
                "venta_fuerte" if pv >= 60 else "venta_leve"
            )
        elif pc >= 25 and pv >= 25:
            clave = "dividido"
        elif pc - pv >= 15:
            clave = "inclina_alcista"
        elif pv - pc >= 15:
            clave = "inclina_bajista"
        else:
            clave = "rango"

        texto = next((r[2] for r in _ANALISIS_REGLAS if r[0] == clave), "")
        return {"clave": clave, "texto": texto}

    @staticmethod
    def histograma_de_scores(scores, bins: int = 8, tf="15", zonas=None) -> dict:
        """Construye el histograma (edges/counts) y métricas de contexto."""
        zonas = zonas or {"comprar": 6.5, "vender": 4.5}
        n = len(scores)
        if n == 0:
            return {
                "edges": [], "counts": [], "n": 0, "media": None,
                "percentil": None, "tf_label": ScoreService.tf_label(tf),
                "pct_compra": 0, "pct_venta": 0, "zona": "NEUTRAL",
                "descripcion": ScoreService.sugerencia_hist(0, 0, 0, 0, 0, zonas),
            }

        lo, hi = min(scores), max(scores)
        if hi == lo:
            hi = lo + 1.0
        ancho = (hi - lo) / bins
        counts = [0] * bins
        for v in scores:
            counts[min(bins - 1, int((v - lo) / ancho))] += 1
        edges = [lo + i * ancho for i in range(bins + 1)]

        media = sum(scores) / n
        percentil = round(sum(1 for s in scores if s <= media) / n * 100)
        n_compra = sum(1 for s in scores if s >= zonas["comprar"])
        n_venta = sum(1 for s in scores if s <= zonas["vender"])

        return {
            "edges": edges,
            "counts": counts,
            "n": n,
            "media": round(media, 2),
            "percentil": percentil,
            "tf_label": ScoreService.tf_label(tf),
            "pct_compra": round(n_compra / n * 100),
            "pct_venta": round(n_venta / n * 100),
            "zona": ScoreService.zona_de(media, zonas),
            "descripcion": ScoreService.sugerencia_hist(
                round(media, 2), percentil, n_compra, n_venta, n, zonas
            ),
        }

    # ── riesgo: gauges e interpretación FX/Macro ─────────────────────────────
    def riesgo_gauges(self) -> list[dict]:
        """Termómetro de riesgo por componente: valor + nivel (0–100) + etiqueta.

        Sin percentil 60d disponible, el nivel usa ``riesgo = (10 - norm_dir) * 10``
        (mayor = más riesgo). Etiquetas BAJO/NORMAL/ALTO con umbrales 40/60.
        """
        _, items = self.score_radar()
        salida = []
        for it in items:
            if it.norm_dir is None:
                continue
            nivel = (10.0 - float(it.norm_dir)) * 10.0
            if nivel < 40:
                label, color = "BAJO", "verde"
            elif nivel < 60:
                label, color = "NORMAL", "amarillo"
            else:
                label, color = "ALTO", "rojo"
            salida.append(
                {
                    "clave": it.logical_key,
                    "symbol": it.symbol,
                    "valor": it.valor,
                    "change_pct": it.change_pct,
                    "nivel": round(nivel, 1),
                    "label": label,
                    "color": color,
                    "estado": it.estado,
                }
            )
        return salida

    def fx_macro(self) -> list[dict]:
        """Movimiento FX/Macro: VIX/DXY/TLT/US10Y/ORO/OIL con su cambio %."""
        notas = {
            "VIX": "Volatilidad",
            "DXY": "Dólar",
            "TLT": "Bonos largos",
            "US10Y": "Yields 10Y",
            "ORO": "Oro",
            "OIL": "Crudo",
        }
        rows = self.latest_tick_repo.fetch_by_logical_keys(list(notas.keys()))
        preferido: dict[str, dict] = {}
        for r in rows:
            lk = r.get("logical_key")
            if lk is None or r.get("change_pct") is None:
                continue
            actual = preferido.get(lk)
            if actual is None or (r.get("is_canonical") and not actual.get("is_canonical")):
                preferido[lk] = r

        salida = []
        for clave, base in notas.items():
            r = preferido.get(clave)
            if r is None:
                continue
            ch = float(r["change_pct"])
            salida.append(
                {"clave": clave, "change_pct": ch, "nota": base, "valor": _f(r.get("close"))}
            )
        return salida

    # ── ciclo completo ───────────────────────────────────────────────────────
    def calcular_ciclo(self, ts: Optional[datetime] = None) -> tuple[list[ScoreActivo], ScoreMercado]:
        ticks = self.latest_tick_repo.fetch_all()
        vol_map = self.heatmap_repo.vol_map()
        clases = set(self._momentum_cfg().get("asset_classes", []))

        scores: list[ScoreActivo] = []
        momentum_scores: list[ScoreActivo] = []
        ts_max: Optional[datetime] = None

        for row in ticks:
            tick = self._row_a_tick(row)
            if tick.timestamp_utc and (ts_max is None or tick.timestamp_utc > ts_max):
                ts_max = tick.timestamp_utc
            vol_ratio = None
            avg = vol_map.get(tick.asset_id)
            if avg and tick.volume:
                vol_ratio = tick.volume / float(avg)
            sa = self.score_activo(tick, vol_ratio)
            scores.append(sa)
            if tick.asset_class in clases:
                momentum_scores.append(sa)

        momentum = self.score_momentum(momentum_scores)
        score15 = self.score_15min()
        radar, _ = self.score_radar()

        disponibles = [s for s in (momentum, radar) if s is not None]
        market = sum(disponibles) / len(disponibles) if disponibles else None

        timestamp = ts or ts_max or now_utc()
        mercado = ScoreMercado(
            timestamp_utc=timestamp,
            score_momentum=momentum,
            score_15min=score15,
            score_radar=radar,
            score_market=market,
            zona=self.zona(market),
            n_simbolos=len(scores),
            pesos=self._pesos(),
            zonas=self._zonas(),
        )
        return scores, mercado

    # ── backfill desde series ────────────────────────────────────────────────
    def calcular_desde_series(
        self, since: datetime, asset_classes: Optional[list[str]] = None
    ) -> Iterator[tuple[datetime, list[dict], dict]]:
        """Genera (timestamp, detalle, agg) a partir de `fact_market_series`.

        El radar escribe en sub-lotes (cada ciclo cubre pocos símbolos), así que
        se agrupa por *bucket* de tiempo (config `data.backfill_bucket_min`) y se
        toma el último valor por activo dentro del bucket → universo completo por
        ciclo histórico.
        """
        minutos = int(self.settings.business("data", "backfill_bucket_min", default=15))
        ancho_s = max(60, minutos * 60)
        filas = self.series_repo.fetch_desde(since, asset_classes=asset_classes)
        clases = set(self._momentum_cfg().get("asset_classes", []))

        buckets: dict[int, dict[int, dict]] = defaultdict(dict)
        for fila in filas:
            epoch = int(ensure_utc(fila["timestamp_utc"]).timestamp())
            marca = epoch - (epoch % ancho_s)
            anterior = buckets[marca].get(fila["asset_id"])
            if anterior is None or fila["timestamp_utc"] > anterior["timestamp_utc"]:
                buckets[marca][fila["asset_id"]] = fila

        for marca in sorted(buckets):
            ts = datetime.fromtimestamp(marca + ancho_s, tz=timezone.utc)
            detalle: list[dict] = []
            momentum_scores: list[float] = []
            for fila in buckets[marca].values():
                score, comps = self._puntuar(
                    {
                        "rsi": _f(fila.get("rsi")),
                        "adx": _f(fila.get("adx")),
                        "cci20": _f(fila.get("cci20")),
                        "bbpower": _f(fila.get("bbpower")),
                        "volume": None,
                        "change": _f(fila.get("change_pct")),
                    }
                )
                detalle.append(
                    {
                        "asset_id": fila["asset_id"],
                        "timestamp_utc": ts,
                        "score_general": score,
                        "zona": self.zona(score),
                        "componentes": [asdict(c) for c in comps],
                    }
                )
                if fila.get("asset_class") in clases and score is not None:
                    momentum_scores.append(score)
            momentum = (sum(momentum_scores) / len(momentum_scores)) if momentum_scores else None
            agg = {
                "timestamp_utc": ts,
                "score_momentum": momentum,
                "score_15min": None,
                "score_radar": None,
                "score_market": momentum,
                "zona": self.zona(momentum),
                "n_simbolos": len(detalle),
                "source_checksum": self._checksum(ts, len(detalle), momentum),
            }
            yield ts, detalle, agg

    @staticmethod
    def _checksum(ts: datetime, n: int, score: Optional[float]) -> str:
        raw = f"{ts.isoformat()}|{n}|{score}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def checksum_mercado(self, mercado: ScoreMercado) -> str:
        return self._checksum(mercado.timestamp_utc, mercado.n_simbolos, mercado.score_market)

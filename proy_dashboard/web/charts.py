"""web/charts.py — constructores de opciones ECharts (solo presentación).

Reciben view models (dicts ya calculados por los servicios) y devuelven el dict
`option` que el navegador dibuja con `renderChart`. Sin lógica de negocio.
"""

from __future__ import annotations

import math

VERDE = "#3fb950"
ROJO = "#f85149"
# Versiones pastel para superficies grandes (heatmap de confluencia)
VERDE_PASTEL = "#258f3d"
ROJO_PASTEL = "#a03737"
# Bordes vivos para el resaltado de confluencia (mismo tono, más claro)
VERDE_VIVO = "#7ee787"
ROJO_VIVO = "#ff9492"
NEUTRAL_VIVO = "#9fb3c8"
AMARILLO = "#d6a72c"
AZUL = "#58a6ff"
MUTED = "#8b98a5"
CLARO = "#c9d6e5"
BORDE = "#2a323d"
GRID = {"left": 74, "right": 18, "top": 22, "bottom": 34}

# GIF transparente 1×1: rellena el hueco de los símbolos sin logo (alineación uniforme).
_PIXEL = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

_ZONA_COLOR = {"COMPRAR": VERDE, "VENDER": ROJO, "NEUTRAL": AMARILLO}


def _base() -> dict:
    return {
        "backgroundColor": "transparent",
        "color": [AZUL, VERDE, AMARILLO, ROJO],
        "textStyle": {"color": MUTED, "fontFamily": "system-ui, sans-serif"},
        "grid": dict(GRID),
    }


def _eje_x(categorias, *, rotate=0, fontSize=12) -> dict:
    return {
        "type": "category",
        "data": categorias,
        "axisLabel": {"color": MUTED, "fontSize": fontSize, "rotate": rotate},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "axisTick": {"lineStyle": {"color": BORDE}},
    }


def _eje_y(minimo=None, maximo=None) -> dict:
    return {
        "type": "value",
        "min": minimo,
        "max": maximo,
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }


def gauge_option(valor, minimo=0, maximo=10, titulo="", zona=None) -> dict:
    valor = valor if valor is not None else 0
    color = _ZONA_COLOR.get(zona or "", AZUL)
    return {
        "backgroundColor": "transparent",
        "series": [
            {
                "type": "gauge",
                "min": minimo,
                "max": maximo,
                "startAngle": 210,
                "endAngle": -30,
                "progress": {"show": True, "width": 14, "itemStyle": {"color": color}},
                "axisLine": {"lineStyle": {"width": 14, "color": [[1, "#232b35"]]}},
                "axisTick": {"show": False},
                "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "pointer": {"show": False},
                "detail": {
                    "valueAnimation": True,
                    "formatter": "{value}",
                    "color": color,
                    "fontSize": 30,
                    "fontWeight": "bold",
                    "offsetCenter": [0, "20%"],
                },
                "title": {"show": bool(titulo), "offsetCenter": [0, "62%"], "color": MUTED, "fontSize": 11},
                "data": [{"value": round(float(valor), 2), "name": titulo}],
            }
        ],
    }


def _colores(valores, umbral=0.0, positivo_arriba=True) -> list[str]:
    out = []
    for v in valores:
        v = v or 0
        arriba = v >= umbral
        bueno = arriba if positivo_arriba else not arriba
        out.append(VERDE if bueno else ROJO)
    return out


def _data_barras(valores, colores) -> list[dict]:
    """Color por dato (ECharts ignora `itemStyle.color` como array)."""
    return [{"value": v, "itemStyle": {"color": c}} for v, c in zip(valores, colores)]


def _barra_horizontal(categorias, valores, *, sufijo="", color_por_signo=True, umbral=0.0) -> dict:
    op = _base()
    op["tooltip"] = {"trigger": "axis", "axisPointer": {"type": "shadow"}}
    op["xAxis"] = _eje_y()  # eje de valores
    op["yAxis"] = {
        "type": "category",
        "data": categorias,
        "axisLabel": {"color": MUTED, "fontSize": 13, "fontWeight": "bold"},
        "axisLine": {"lineStyle": {"color": BORDE}},
    }
    colores = _colores(valores, umbral) if color_por_signo else [AZUL] * len(valores)
    op["series"] = [
        {
            "type": "bar",
            "data": _data_barras(valores, colores),
            "itemStyle": {"borderRadius": [0, 4, 4, 0]},
            "label": {
                "show": True,
                "position": "right",
                "color": MUTED,
                "fontSize": 10,
                "formatter": "{c}" + sufijo,
            },
        }
    ]
    return op


def bar_option(categorias, valores, *, sufijo="", color_por_signo=True, vertical=False, umbral=0.0) -> dict:
    if not vertical:
        return _barra_horizontal(
            categorias, valores, sufijo=sufijo, color_por_signo=color_por_signo, umbral=umbral
        )

    op = _base()
    op["tooltip"] = {"trigger": "axis"}
    op["xAxis"] = _eje_x(categorias, rotate=60)
    op["yAxis"] = _eje_y()
    colores = _colores(valores, umbral) if color_por_signo else [AZUL] * len(valores)
    op["series"] = [{"type": "bar", "data": _data_barras(valores, colores)}]
    return op


def treemap_option(items) -> dict:
    data = [
        {
            "name": i["symbol"],
            "value": [float(i.get("value") or 0), round(float(i.get("change_pct") or 0), 2)],
        }
        for i in items
    ]
    return {
        "backgroundColor": "transparent",
        "tooltip": {"formatter": "{b}<br/>Cap: {c0}<br/>Cambio: {c1}%"},
        "visualMap": {
            "type": "continuous",
            "min": -5,
            "max": 5,
            "dimension": 1,
            "show": False,
            "inRange": {"color": [ROJO, "#3a424c", VERDE]},
        },
        "series": [
            {
                "type": "treemap",
                "roam": False,
                "nodeClick": False,
                "breadcrumb": {"show": False},
                "visualDimension": 1,
                "itemStyle": {"borderColor": "#0b0f14", "borderWidth": 1, "gapWidth": 1},
                "label": {"show": True, "fontSize": 10, "color": "#0d1117", "fontWeight": "bold"},
                "data": data,
            }
        ],
    }


def sector_15m_option(sectores) -> dict:
    """Treemap de calor: cambio medio 15m por sector (área = nº de acciones)."""
    data = [
        {
            "name": s["sector"],
            "value": [int(s.get("n") or 1), round(float(s.get("change_pct") or 0), 4)],
        }
        for s in sectores
    ]
    # Escala dinámica: los cambios 15m son pequeños (~0.1%), un rango fijo los deja grises.
    cambios = [abs(d["value"][1]) for d in data] or [0.0]
    rango = max(max(cambios), 0.05)
    return {
        "backgroundColor": "transparent",
        "tooltip": {"formatter": "{b}<br/>Cambio 15m: {c1}%<br/>Acciones: {c0}"},
        "visualMap": {
            "type": "continuous",
            "min": -rango,
            "max": rango,
            "dimension": 1,
            "show": False,
            "inRange": {"color": [ROJO, "#3a424c", VERDE]},
        },
        "series": [
            {
                "type": "treemap",
                "roam": False,
                "nodeClick": False,
                "breadcrumb": {"show": False},
                "visualDimension": 1,
                "itemStyle": {"borderColor": "#0b0f14", "borderWidth": 1, "gapWidth": 2},
                "label": {
                    "show": True,
                    "fontSize": 11,
                    "color": "#0d1117",
                    "fontWeight": "bold",
                    "formatter": "{b}\n{c1}%",
                },
                "data": data,
            }
        ],
    }


def sectors_option(sectores) -> dict:
    datos = sorted(sectores, key=lambda s: (s.get("change_medio") or 0))
    categorias = [s["sector"] for s in datos]
    valores = [round(s.get("change_medio") or 0, 2) for s in datos]
    return _barra_horizontal(categorias, valores, sufijo="%", umbral=0.0)


def momentum_option(top, bottom, logos=None) -> dict:
    # Orden visual (index 0 = borde inferior):
    #   más positivo (abajo) → menos positivo → menos negativo → más negativo (arriba).
    # Así los extremos quedan en los bordes y el neutro en el centro.
    filas = list(top) + list(reversed(bottom))
    categorias = [f["symbol"] for f in filas]
    valores = [round(f["change_pct"], 2) for f in filas]
    op = _barra_horizontal(categorias, valores, sufijo="%", umbral=0.0)
    logos = logos or {}

    # Tooltip rico (logo + ticker + badge + métricas), mismo patrón que G2.
    op["tooltipHtml"] = True
    op["tooltip"] = {"trigger": "item", "axisPointer": {"type": "shadow"}}
    op["tooltipWidth"] = 200
    op["tooltipRows"] = [
        {"label": "Cambio", "key": "change_pct", "dec": 2, "signed": True, "suffix": "%"},
        {"label": "Precio", "key": "close", "dec": 2},
        {"label": "Previo", "key": "prev_close", "dec": 2},
        {"label": "RSI", "key": "rsi", "dec": 1},
        {"label": "ADX 15m", "key": "adx", "dec": 1},
    ]
    for item, f in zip(op["series"][0]["data"], filas):
        ch = float(f["change_pct"])
        item["extra"] = {
            "ticker": f.get("ticker") or f["symbol"].split(":")[-1],
            "logo": logos.get(f["symbol"]) or f.get("logo"),
            "badge": {"text": "ALCISTA" if ch >= 0 else "BAJISTA",
                      "side": "pos" if ch >= 0 else "neg"},
            "change_pct": ch,
            "close": f.get("close"),
            "prev_close": f.get("prev_close"),
            "rsi": f.get("rsi"),
            "adx": f.get("adx"),
        }

    if logos:
        # Icono [logo] + [símbolo] en las etiquetas del eje Y (rich text de ECharts).
        rich = {
            "sym": {"color": CLARO, "fontSize": 11, "fontWeight": "bold",
                    "align": "left", "verticalAlign": "middle",
                    "width": 52, "overflow": "truncate", "padding": [0, 0, 0, 4]},
        }
        for i, f in enumerate(filas):
            # Logo del símbolo o pixel transparente (mantiene la alineación uniforme).
            url = logos.get(f["symbol"]) or _PIXEL
            rich[f"i{i}"] = {
                "backgroundColor": {"image": url, "width": 13, "height": 13},
                "width": 13, "height": 13, "align": "left", "verticalAlign": "middle",
            }
        op["grid"] = {"left": 96, "right": 18, "top": 22, "bottom": 34}
        op["yAxis"]["axisLabel"] = {"rich": rich, "margin": 6, "interval": 0}
    return op


def _color_indicador(tipo, valor) -> str:
    if tipo == "rsi":
        if valor >= 70:
            return ROJO
        if valor <= 30:
            return VERDE
        return AZUL
    if tipo == "adx":
        return VERDE if valor >= 25 else MUTED
    if tipo in ("cci20", "bbpower"):
        return VERDE if valor >= 0 else ROJO
    return AZUL


def indicator_option(items, *, sufijo="", tipo="rsi") -> dict:
    ordenados = list(items)[::-1]
    categorias = [i["symbol"] for i in ordenados]
    valores = [round(i["valor"], 2) for i in ordenados]
    colores = [_color_indicador(tipo, v) for v in valores]
    op = _base()
    op["tooltip"] = {"trigger": "axis"}
    op["xAxis"] = _eje_y()
    op["yAxis"] = {
        "type": "category",
        "data": categorias,
        "axisLabel": {"color": MUTED, "fontSize": 13, "fontWeight": "bold"},
        "axisLine": {"lineStyle": {"color": BORDE}},
    }
    op["series"] = [
        {
            "type": "bar",
            "data": _data_barras(valores, colores),
            "itemStyle": {"borderRadius": [0, 4, 4, 0]},
            "label": {"show": True, "position": "right", "color": MUTED, "fontSize": 11, "formatter": "{c}" + sufijo},
        }
    ]
    return op


def histograma_option(edges, counts, *, color=AZUL) -> dict:
    categorias = [f"{edges[i]:.1f}–{edges[i + 1]:.1f}" for i in range(len(counts))]
    op = _base()
    op["tooltip"] = {"trigger": "axis"}
    op["xAxis"] = _eje_x(categorias, rotate=45, fontSize=9)
    op["yAxis"] = _eje_y()
    op["series"] = [{"type": "bar", "data": counts, "itemStyle": {"color": color, "borderRadius": [3, 3, 0, 0]}}]
    return op


def score_hist_option(dist, *, comprar=6.5, vender=4.5) -> dict:
    """Histograma del score 15m con barras por zona y marca de la media."""
    edges = dist.get("edges") or []
    counts = dist.get("counts") or []
    media = dist.get("media")
    op = _base()
    op["tooltip"] = {"trigger": "axis"}
    # Gráfico angosto (2 columnas): márgenes mínimos para usar todo el ancho.
    op["grid"] = {"left": 6, "right": 8, "top": 18, "bottom": 6, "containLabel": True}
    if not counts:
        op["xAxis"] = _eje_x([])
        op["yAxis"] = _eje_y()
        op["series"] = [{"type": "bar", "data": []}]
        return op

    categorias = [f"{edges[i]:.1f}–{edges[i + 1]:.1f}" for i in range(len(counts))]
    data = []
    for i, c in enumerate(counts):
        centro = (edges[i] + edges[i + 1]) / 2
        color = VERDE if centro >= comprar else (ROJO if centro <= vender else "#3a424c")
        data.append({"value": c, "itemStyle": {"color": color, "borderRadius": [3, 3, 0, 0]}})

    op["xAxis"] = _eje_x(categorias, rotate=45, fontSize=8)
    op["yAxis"] = _eje_y()
    serie = {"type": "bar", "data": data}
    if media is not None:
        ancho = (edges[1] - edges[0]) or 1.0
        idx = max(0, min(len(counts) - 1, int((media - edges[0]) / ancho)))
        serie["markLine"] = {
            "symbol": "none",
            "silent": True,
            "label": {
                "formatter": f"Mercado {media:.1f}",
                "color": "#0b0f14",
                "fontSize": 9,
                "fontWeight": "bold",
                "position": "insideEndTop",
                "backgroundColor": AMARILLO,
                "padding": [2, 4],
                "borderRadius": 3,
            },
            "lineStyle": {"color": AMARILLO, "type": "dashed", "width": 2},
            "data": [{"xAxis": idx}],
        }
    op["series"] = [serie]
    return op


def _vertical_markline(idx, y0, y1, *, color, width=1.5, type_="dashed", label=None):
    lab = {"show": False} if not label else {
        "show": True, "formatter": label, "position": "insideStartTop",
        "color": color, "fontSize": 8,
    }
    ls = {"color": color, "type": type_, "width": width}
    return [
        {"coord": [idx, y0], "lineStyle": ls, "label": dict(lab), "symbol": "none"},
        {"coord": [idx, y1], "lineStyle": ls, "label": lab, "symbol": "none"},
    ]


def line_option(
    puntos,
    *,
    nombre="",
    color=AZUL,
    y_min=None,
    y_max=None,
    zonas=None,
    mark_lines=None,
    market_hours=None,
    market_open_lines=None,
    market_open_label="APERTURA",
) -> dict:
    x = [p[0] for p in puntos]
    y = [p[1] for p in puntos]
    op = _base()
    op["tooltip"] = {"trigger": "axis"}
    op["xAxis"] = _eje_x(x, fontSize=9)
    op["yAxis"] = _eje_y(y_min, y_max)
    serie = {
        "type": "line",
        "name": nombre,
        "data": y,
        "smooth": True,
        "showSymbol": True,
        "symbol": "circle",
        "symbolSize": 5,
        "itemStyle": {"color": "#00d4ff", "borderColor": "#0b1220", "borderWidth": 1},
        "emphasis": {"scale": 1.5, "itemStyle": {"color": "#5ee7ff", "borderWidth": 2}},
        "lineStyle": {"color": color, "width": 2},
        "areaStyle": {
            "color": {
                "type": "linear",
                "x": 0, "y": 0, "x2": 0, "y2": 1,
                "colorStops": [
                    {"offset": 0, "color": "rgba(88,166,255,0.28)"},
                    {"offset": 1, "color": "rgba(88,166,255,0.02)"},
                ],
            }
        },
    }
    # Líneas horizontales (zonas COMPRAR/VENDER)
    if zonas:
        serie["markLine"] = {
            "silent": True,
            "symbol": "none",
            "label": {"show": True, "color": MUTED, "fontSize": 9, "position": "insideEndTop"},
            "data": [
                {"yAxis": zonas["comprar"], "lineStyle": {"color": VERDE, "type": "dashed"},
                 "label": {"formatter": "COMPRAR"}},
                {"yAxis": zonas["vender"], "lineStyle": {"color": ROJO, "type": "dashed"},
                 "label": {"formatter": "VENDER"}},
            ],
        }
    # Líneas verticales: separadores de día (naranja) y apertura NY (gris)
    y0 = y_min if y_min is not None else 0
    y1 = y_max if y_max is not None else 10
    vlines = []
    if mark_lines:
        vlines += [_vertical_markline(i, y0, y1, color="#ff9f40") for i in mark_lines]
    if market_open_lines:
        vlines += [
            _vertical_markline(i, y0, y1, color="#b8c2cc", type_="solid", label=market_open_label)
            for i in market_open_lines
        ]
    if vlines:
        if "markLine" not in serie:
            serie["markLine"] = {"silent": True, "symbol": "none", "data": []}
        serie["markLine"]["data"].extend(vlines)
    # Sombreado horario NY: markArea Gris CLARO sobre la serie (z alto), contraste con el azul
    if market_hours:
        areas = serie.get("markArea", {"silent": True, "z": 3, "data": [], "label": {"show": False}})
        serie["markArea"] = areas
        for area in market_hours:
            area[0]["itemStyle"] = {
                "color": "rgba(200,208,216,0.12)",
                "borderColor": "rgba(200,208,216,0.50)",
                "borderWidth": 1,
                "borderType": "dotted",
            }
        areas["data"].extend(market_hours)
    op["series"] = [serie]
    return op


def multiframe_option(series: dict, *, categorias) -> dict:
    """Multi-TF estilo `bar-rich-text`: barras agrupadas con etiquetas ricas.

    Basado en el ejemplo de ECharts "Weather Statistics" (bar-rich-text):
    barras horizontales por activo con eje categórico estilizado, etiquetas de
    texto enriquecido y líneas guía en los límites del RSI (30 / 70).
    """
    op = _base()
    op["tooltip"] = {"trigger": "axis", "axisPointer": {"type": "shadow"}}
    op["legend"] = {
        "data": list(series.keys()),
        "textStyle": {"color": MUTED, "fontSize": 12},
        "top": 0,
    }
    op["grid"] = {"left": 132, "right": 48, "top": 34, "bottom": 14}
    op["xAxis"] = {
        "type": "value",
        "min": 0,
        "max": 100,
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }
    op["yAxis"] = {
        "type": "category",
        "inverse": True,
        "data": categorias,
        "axisLabel": {
            "margin": 12,
            "formatter": "{sym|{value}}",
            "rich": {
                "sym": {
                    "fontSize": 13,
                    "fontWeight": "bold",
                    "color": "#dfe6ee",
                    "align": "right",
                    "lineHeight": 20,
                }
            },
        },
        "axisLine": {"lineStyle": {"color": BORDE}},
    }

    paleta = [AZUL, AMARILLO]
    salida = []
    for i, (nombre, valores) in enumerate(series.items()):
        serie = {
            "type": "bar",
            "name": nombre,
            "data": valores,
            "barWidth": "30%",
            "itemStyle": {"color": paleta[i % len(paleta)], "borderRadius": [0, 4, 4, 0]},
            "label": {
                "show": True,
                "position": "right",
                "formatter": "{v|{c}}",
                "rich": {"v": {"color": MUTED, "fontSize": 11, "fontWeight": "bold"}},
            },
        }
        if i == 0:
            serie["markLine"] = {
                "silent": True,
                "symbol": "none",
                "lineStyle": {"width": 1},
                "data": [
                    {"xAxis": 30, "lineStyle": {"color": VERDE, "type": "dashed"},
                     "label": {"formatter": "30", "color": VERDE, "fontSize": 9}},
                    {"xAxis": 70, "lineStyle": {"color": ROJO, "type": "dashed"},
                     "label": {"formatter": "70", "color": ROJO, "fontSize": 9}},
                ],
            }
        salida.append(serie)
    op["series"] = salida
    return op


def diverging_riesgo_option(items, neutral=5.0) -> dict:
    """Termómetro de riesgo divergente centrado en `neutral`.

    Cada componente se dibuja como desviación respecto al neutral:
    a la **derecha** (rojo) = más riesgo (riesgo > neutral),
    a la **izquierda** (verde) = menos riesgo (riesgo < neutral).
    El eje Y muestra el símbolo y su nivel de riesgo (0 = seguro, 10 = máximo).
    """
    filas = [i for i in items if getattr(i, "norm_dir", None) is not None]
    riesgos = [10.0 - float(i.norm_dir) for i in filas]
    categorias = [f"{i.logical_key}   {r:.1f}" for i, r in zip(filas, riesgos)]
    desvios = [round(r - neutral, 2) for r in riesgos]
    maxabs = (max([abs(d) for d in desvios] + [1.0])) * 1.2

    data = [{"value": d, "itemStyle": {"color": ROJO if d >= 0 else VERDE}} for d in desvios]

    op = _base()
    op["grid"] = {"left": 128, "right": 28, "top": 8, "bottom": 8}
    op["tooltip"] = {"trigger": "axis", "axisPointer": {"type": "shadow"}}
    op["xAxis"] = {
        "type": "value",
        "min": -maxabs,
        "max": maxabs,
        "axisLabel": {"show": False},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }
    op["yAxis"] = {
        "type": "category",
        "data": categorias,
        "axisLabel": {"color": MUTED, "fontSize": 13, "fontWeight": "bold"},
        "axisLine": {"lineStyle": {"color": BORDE}},
    }
    op["series"] = [
        {
            "type": "bar",
            "data": data,
            "barWidth": "58%",
            "markLine": {
                "silent": True,
                "symbol": "none",
                "lineStyle": {"color": MUTED, "width": 2},
                "data": [{"xAxis": 0}],
                "label": {"show": False},
            },
        }
    ]
    return op


def _fmt_cap(valor) -> str:
    """Capitalización legible: 4.95T · 877.70B · 211.80B · 12.30M."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "—"
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(v) >= div:
            return f"{v / div:.2f}{suf}"
    return f"{v:,.0f}"


def scatter_rsi_option(
    puntos,
    *,
    oportunidad_alto=60.0,
    oportunidad_bajo=40.0,
    limite_alto=70.0,
    limite_bajo=30.0,
) -> dict:
    """Dot-plot RSI (1D) de acciones top-cap en zona de oportunidad.

    Eje Y = RSI (0–100) con **bandas de zona** (sobrecompra ≥70, oportunidad alta
    60–70, oportunidad baja 30–40, sobreventa ≤30). Los puntos se ordenan en dos
    bloques **ALTA | BAJA** (RSI descendente). Tamaño = capitalización; color =
    lado; **relleno = extremo** (≥70 / ≤30) · **hueco = oportunidad** (60–70 / 30–40).
    Tooltip rico con logo, zona, RSI, cambio %, capitalización y sector.
    """
    alta = sorted(
        (p for p in puntos if float(p["rsi"]) >= oportunidad_alto),
        key=lambda p: float(p["rsi"]),
        reverse=True,
    )
    baja = sorted(
        (p for p in puntos if float(p["rsi"]) <= oportunidad_bajo),
        key=lambda p: float(p["rsi"]),
        reverse=True,
    )
    ordenados = alta + baja

    caps = [float(p.get("market_cap") or 0) for p in ordenados]
    cap_min = min(caps) if caps else 0.0
    cap_max = max(caps) if caps else 1.0
    span = (cap_max - cap_min) or 1.0

    data = []
    for p in ordenados:
        rsi = float(p["rsi"])
        frac = ((float(p.get("market_cap") or 0) - cap_min) / span) ** 0.5
        extremo = rsi >= limite_alto or rsi <= limite_bajo
        if rsi >= limite_alto:
            color, zona, side = ROJO, "SOBRECOMPRA", "neg"
        elif rsi >= oportunidad_alto:
            color, zona, side = ROJO, "OPORTUNIDAD ALTA", "neg"
        elif rsi <= limite_bajo:
            color, zona, side = VERDE, "SOBREVENTA", "pos"
        else:
            color, zona, side = VERDE, "OPORTUNIDAD BAJA", "pos"
        # relleno = extremo · hueco = oportunidad (mismo color, solo borde)
        if extremo:
            item = {"color": color, "borderColor": "#0b0f14", "borderWidth": 1}
        else:
            item = {"color": "transparent", "borderColor": color, "borderWidth": 2}
        data.append(
            {
                "value": round(rsi, 1),
                "name": p["symbol"],
                "symbolSize": round(9 + frac * 31, 1),
                "itemStyle": item,
                "extra": {
                    "ticker": p.get("ticker") or p["symbol"].split(":")[-1],
                    "logo": p.get("logo"),
                    "badge": {"text": zona, "side": side},
                    "rsi": rsi,
                    "change_pct": p.get("change_pct"),
                    "cap_txt": _fmt_cap(p.get("market_cap")),
                    "sector": p.get("sector"),
                },
            }
        )

    def _band(y0, y1, color, texto, pos):
        return [
            {
                "yAxis": y0,
                "itemStyle": {"color": color},
                "label": {"show": True, "formatter": texto, "position": pos,
                          "color": MUTED, "fontSize": 9},
            },
            {"yAxis": y1},
        ]

    op = _base()
    op["tooltipHtml"] = True
    op["tooltip"] = {"trigger": "item"}
    op["tooltipRows"] = [
        {"label": "RSI", "key": "rsi", "dec": 1},
        {"label": "Cambio", "key": "change_pct", "dec": 2, "signed": True, "suffix": "%"},
        {"label": "Capitalización", "key": "cap_txt"},
        {"label": "Sector", "key": "sector"},
    ]
    op["grid"] = {"left": 46, "right": 22, "top": 46, "bottom": 16}
    op["xAxis"] = {
        "type": "category",
        "data": [p["symbol"] for p in ordenados],
        # El nombre ya va en el punto → sin etiquetas de eje X
        "axisLabel": {"show": False},
        "axisTick": {"show": False},
        "axisLine": {"show": False},
    }
    op["yAxis"] = {
        "type": "value",
        "min": 0,
        "max": 100,
        "name": "RSI",
        "nameTextStyle": {"color": MUTED},
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }

    markline_data = [
        {
            "yAxis": limite_alto,
            "lineStyle": {"color": AMARILLO, "type": "dashed", "width": 1.5},
            "label": {"formatter": f"{int(limite_alto)}", "color": AMARILLO,
                      "fontSize": 10, "position": "insideEndTop"},
        },
        {
            "yAxis": limite_bajo,
            "lineStyle": {"color": AMARILLO, "type": "dashed", "width": 1.5},
            "label": {"formatter": f"{int(limite_bajo)}", "color": AMARILLO,
                      "fontSize": 10, "position": "insideEndBottom"},
        },
    ]
    # Divisor vertical punteado (gris claro) entre los bloques ALTA | BAJA.
    if alta and baja:
        markline_data.append(
            {
                "xAxis": ordenados[len(alta)]["symbol"],
                "lineStyle": {"color": CLARO, "type": "dashed", "width": 1.5},
                "label": {"show": False},
            }
        )

    # Cabeceras de bloque (ALTA a la izquierda, BAJA a la derecha), bien separadas.
    areas = [
        _band(limite_alto, 100, "rgba(248, 81, 73, 0.10)", "sobrecompra", "insideBottomRight"),
        _band(oportunidad_alto, limite_alto, "rgba(248, 81, 73, 0.035)", "oportunidad alta", "insideBottomRight"),
        _band(limite_bajo, oportunidad_bajo, "rgba(63, 185, 80, 0.035)", "oportunidad baja", "insideTopRight"),
        _band(0, limite_bajo, "rgba(63, 185, 80, 0.10)", "sobreventa", "insideLeft"),
    ]

    def _cabecera(x_ini, x_fin, texto, pos):
        return [
            {
                "xAxis": x_ini,
                "yAxis": 100,
                "itemStyle": {"color": "transparent"},
                "label": {"show": True, "formatter": texto, "position": pos,
                          "color": MUTED, "fontSize": 11, "fontWeight": "bold"},
            },
            {"xAxis": x_fin, "yAxis": 0},
        ]

    if alta and baja:
        x_alta0, x_alta1 = ordenados[0]["symbol"], ordenados[len(alta) - 1]["symbol"]
        x_baja0, x_baja1 = ordenados[len(alta)]["symbol"], ordenados[-1]["symbol"]
        # cabeceras arriba
        areas.append(_cabecera(x_alta0, x_alta1, "ALTA", "insideTopLeft"))
        areas.append(_cabecera(x_baja0, x_baja1, "BAJA", "insideTopRight"))
        # cabeceras abajo (espejo)
        areas.append(_cabecera(x_alta0, x_alta1, "ALTA", "insideBottomLeft"))
        areas.append(_cabecera(x_baja0, x_baja1, "BAJA", "insideBottomRight"))

    op["series"] = [
        {
            "type": "scatter",
            "data": data,
            "label": {
                "show": True,
                "formatter": "{b}",
                "position": "top",
                "color": "#dfe6ee",
                "fontSize": 10,
                "fontWeight": "bold",
            },
            "labelLayout": {"hideOverlap": True},
            "markArea": {
                "silent": True,
                "data": areas,
            },
            "markLine": {
                "silent": True,
                "symbol": "none",
                "data": markline_data,
            },
        }
    ]
    return op


def scatter_bollinger_option(puntos, *, k: float = 2.0) -> dict:
    """Dot-plot de reversión Bollinger: eje Y = posición en la banda (σ).

    Cada punto es un activo que tocó/se acercó a una banda de Bollinger (20, k).
    Eje Y = `z = (close − SMA20) / σ`:
      - `+k` = banda superior, `0` = SMA20 (media), `−k` = banda inferior.
    Las líneas punteadas amarillas en ±k SON las bandas de Bollinger.
    Color: rojo = CORTO (rechazo banda superior), verde = LARGO (rebote inferior).
    Tamaño: proporcional al volumen relativo.
    """
    validos = [p for p in puntos if p.get("z_banda") is not None]
    # Orden por σ descendente: escalera de "más extendido arriba" a "abajo".
    validos.sort(key=lambda p: float(p["z_banda"]), reverse=True)
    categorias = [p["symbol"] for p in validos]
    zs = [float(p["z_banda"]) for p in validos]
    vols = [float(p.get("vol_ratio") or 1.0) for p in validos]
    vol_min = min(vols) if vols else 1.0
    vol_max = max(vols) if vols else 2.0
    span = (vol_max - vol_min) or 1.0
    # Rango simétrico que siempre incluye las bandas ±k.
    limite = round(max(k, max((abs(z) for z in zs), default=k)) + 0.5, 1)

    data = []
    for p in validos:
        frac = ((float(p.get("vol_ratio") or 1.0) - vol_min) / span) ** 0.5
        color = ROJO if p.get("lado") == "CORTO" else VERDE
        # C: "ACCIONABLE" (perforó la banda) = punto relleno;
        #    "CERCA" (watchlist) = punto hueco/atenuado.
        accionable = p.get("estado") == "ACCIONABLE"
        if accionable:
            item_style = {"color": color, "borderColor": "#0b0f14", "borderWidth": 1}
        else:
            item_style = {
                "color": "transparent",
                "borderColor": color,
                "borderWidth": 2,
                "opacity": 0.85,
            }
        data.append(
            {
                "value": round(float(p["z_banda"]), 2),
                "name": p["symbol"],
                "symbolSize": round(9 + frac * 31, 1),
                "itemStyle": item_style,
                "label": {"color": "#dfe6ee" if accionable else MUTED},
                # Datos para el tooltip HTML (lo construye card_chart.html).
                "extra": {
                    "ticker": p.get("ticker"),
                    "tipo": p.get("tipo"),
                    "lado": p.get("lado"),
                    "estado": p.get("estado"),
                    "nota": p.get("nota"),
                    "dist_banda": p.get("dist_banda"),
                    "vol_ratio": p.get("vol_ratio"),
                    "close": p.get("close"),
                    "change_pct": p.get("change_pct"),
                    "rsi_15": p.get("rsi_15"),
                    "score": p.get("score"),
                    "logo": p.get("logo"),
                },
            }
        )

    def _line(y, color, etiqueta, pos):
        return {
            "yAxis": y,
            "lineStyle": {"color": color, "type": "dashed", "width": 1.5},
            "label": {"formatter": etiqueta, "color": color, "fontSize": 10, "position": pos},
        }

    op = _base()
    # El tooltip se arma como HTML en el navegador (ver card_chart.html).
    op["tooltipHtml"] = True
    op["tooltip"] = {"trigger": "item"}
    op["grid"] = {"left": 52, "right": 22, "top": 46, "bottom": 16}
    op["xAxis"] = {
        "type": "category",
        "data": categorias,
        "axisLabel": {"show": False},
        "axisTick": {"show": False},
        "axisLine": {"show": False},
    }
    op["yAxis"] = {
        "type": "value",
        "min": -limite,
        "max": limite,
        "name": "Posición en banda (σ)",
        "nameTextStyle": {"color": MUTED},
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }
    op["series"] = [
        {
            "type": "scatter",
            "data": data,
            "label": {
                "show": True,
                "formatter": "{b}",
                "position": "top",
                "color": "#dfe6ee",
                "fontSize": 10,
                "fontWeight": "bold",
            },
            "labelLayout": {"hideOverlap": True},
            "markLine": {
                "silent": True,
                "symbol": "none",
                "data": [
                    _line(k, AMARILLO, "banda superior", "insideEndTop"),
                    _line(0, MUTED, "SMA20 (media)", "insideEndTop"),
                    _line(-k, AMARILLO, "banda inferior", "insideEndBottom"),
                ],
            },
        }
    ]
    return op


def scatter_tendencia_option(puntos, *, adx_min: float = 25.0, k: float = 2.0) -> dict:
    """Cuadrante K2: X = posición en la banda (σ), Y = ADX 15m (panel K2).

    Comparte universo y eje X con K1 (mismos símbolos, mismo z_banda). Color por
    lado de K1 (rojo CORTO / verde LARGO). Línea horizontal en `adx_min` (umbral
    de tendencia) y verticales en 0 (SMA20) y ±k (bandas de Bollinger). El tooltip
    se arma con `tooltipRows`.
    """
    validos = [
        p for p in puntos
        if p.get("z_banda") is not None and p.get("adx_15") is not None
    ]
    data = []
    for p in validos:
        lado = p.get("lado")
        color = ROJO if lado == "CORTO" else VERDE
        data.append(
            {
                "value": [round(float(p["z_banda"]), 2), round(float(p["adx_15"]), 1)],
                "name": p["symbol"],
                "symbolSize": 14,
                "itemStyle": {"color": color, "borderColor": "#0b0f14", "borderWidth": 1},
                "extra": {
                    "ticker": p.get("ticker"),
                    "lado": lado,
                    "badge": {
                        "text": p.get("tipo") or lado or "—",
                        "side": "neg" if lado == "CORTO" else "pos",
                    },
                    "z_banda": p.get("z_banda"),
                    "adx": p.get("adx_15"),
                    "close": p.get("close"),
                    "change_pct": p.get("change_pct"),
                    "rsi_15": p.get("rsi_15"),
                    "score": p.get("score"),
                    "vol_ratio": p.get("vol_ratio"),
                    "logo": p.get("logo"),
                },
            }
        )

    zs = [float(p["z_banda"]) for p in validos]
    ys = [float(p["adx_15"]) for p in validos]
    x_abs = round(max((abs(z) for z in zs), default=k) * 1.15, 2) or k
    y_max = round(max(ys + [adx_min], default=adx_min) * 1.15, 1)

    def _xline(x, color, fmt, pos):
        return {
            "xAxis": x,
            "lineStyle": {"color": color, "type": "dashed", "width": 1.5 if x != 0 else 1},
            "label": {"formatter": fmt, "color": color, "fontSize": 10, "position": pos},
        }

    op = _base()
    op["tooltipHtml"] = True
    op["tooltip"] = {"trigger": "item"}
    op["tooltipRows"] = [
        {"label": "Posición (σ)", "key": "z_banda", "dec": 2, "signed": True},
        {"label": "ADX 15m", "key": "adx", "dec": 1},
        {"label": "Close", "key": "close", "dec": 2},
        {"label": "Chg", "key": "change_pct", "dec": 2, "signed": True, "suffix": "%"},
        {"label": "RSI 15m", "key": "rsi_15", "dec": 1},
        {"label": "Score", "key": "score", "dec": 2},
    ]
    op["grid"] = {"left": 52, "right": 18, "top": 30, "bottom": 50}
    op["xAxis"] = {
        "type": "value",
        "name": "Posición en banda (σ)",
        "nameLocation": "middle",
        "nameGap": 30,
        "nameTextStyle": {"color": MUTED},
        "min": -x_abs,
        "max": x_abs,
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }
    op["yAxis"] = {
        "type": "value",
        "name": "ADX 15m",
        "nameTextStyle": {"color": MUTED},
        "min": 0,
        "max": y_max,
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }
    op["series"] = [
        {
            "type": "scatter",
            "data": data,
            "label": {
                "show": True,
                "formatter": "{b}",
                "position": "top",
                "color": "#dfe6ee",
                "fontSize": 10,
                "fontWeight": "bold",
            },
            "labelLayout": {"hideOverlap": True},
            "markArea": {
                "silent": True,
                "data": [
                    [
                        {"xAxis": -x_abs, "yAxis": adx_min, "itemStyle": {"color": "rgba(255, 255, 255, 0.04)"}},
                        {"xAxis": x_abs, "yAxis": y_max},
                    ],
                ],
            },
            "markLine": {
                "silent": True,
                "symbol": "none",
                "data": [
                    _xline(k, AMARILLO, f"+{k:g} sup", "insideEndTop"),
                    _xline(0, MUTED, "SMA20", "insideEndTop"),
                    _xline(-k, AMARILLO, f"-{k:g} inf", "insideEndBottom"),
                    {
                        "yAxis": adx_min,
                        "lineStyle": {"color": AMARILLO, "type": "dashed", "width": 1.5},
                        "label": {
                            "formatter": f"ADX {adx_min:g}",
                            "color": AMARILLO,
                            "fontSize": 10,
                            "position": "insideEndTop",
                        },
                    },
                ],
            },
        }
    ]
    return op


def scatter_divergencia_5m_option(puntos) -> dict:
    """Scatter K3 — Divergencia Precio/RSI 5m: X = RSI ini, Y = RSI fin.

    Cada divergencia es un punto: verde = ALCISTA (RSI↑), rojo = BAJISTA (RSI↓).
    La diagonal y = x separa: por encima = RSI subió (mejor soporte para ALCISTA);
    por debajo = RSI bajó (mejor transición a BAJISTA).
    """
    validos = [p for p in puntos if p.get("rsi1") is not None and p.get("rsi2") is not None]
    data = []
    for p in validos:
        lado = p.get("tipo")  # "ALCISTA" o "BAJISTA"
        color = VERDE if lado == "ALCISTA" else ROJO
        # Confluencia de la tríada K (K1+K2+K3): anillo dorado.
        conf = bool(p.get("confluencia"))
        data.append(
            {
                "value": [round(float(p["rsi1"]), 1), round(float(p["rsi2"]), 1)],
                "name": p["symbol"],
                "symbolSize": 17 if conf else 14,
                "itemStyle": {
                    "color": color,
                    "borderColor": AMARILLO if conf else "#0b0f14",
                    "borderWidth": 3 if conf else 1,
                },
                "extra": {
                    "ticker": p.get("ticker"),
                    "lado": lado,
                    "badge": {
                        "text": lado or "—",
                        "side": "pos" if lado == "ALCISTA" else "neg",
                    },
                    "rsi1": p.get("rsi1"),
                    "rsi2": p.get("rsi2"),
                    "p1": p.get("p1"),
                    "p2": p.get("p2"),
                    "precio_delta": p.get("precio_delta"),
                    "rsi_delta": p.get("rsi_delta"),
                    "confluencia": conf,
                    "logo": p.get("logo"),
                },
            }
        )

    # Rango simétrico que incluya los RSI observados.
    vals = [float(p["rsi1"]) for p in validos] + [float(p["rsi2"]) for p in validos]
    vmin = max(1, min(vals) - 5) if vals else 25
    vmax = min(100, max(vals) + 5) if vals else 75

    op = _base()
    op["tooltipHtml"] = True
    op["tooltip"] = {"trigger": "item"}
    op["tooltipRows"] = [
        {"label": "RSI ini", "key": "rsi1", "dec": 1},
        {"label": "RSI fin", "key": "rsi2", "dec": 1},
        {"label": "Δ RSI", "key": "rsi_delta", "dec": 1, "signed": True},
        {"label": "Δ Precio", "key": "precio_delta", "dec": 2, "signed": True, "suffix": "%"},
        {"label": "P1", "key": "p1", "dec": 2},
        {"label": "P2", "key": "p2", "dec": 2},
    ]
    op["grid"] = {"left": 52, "right": 22, "top": 30, "bottom": 50}
    op["xAxis"] = {
        "type": "value",
        "name": "RSI ini (5m)",
        "nameLocation": "middle",
        "nameGap": 30,
        "nameTextStyle": {"color": MUTED},
        "min": vmin,
        "max": vmax,
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }
    op["yAxis"] = {
        "type": "value",
        "name": "RSI fin (5m)",
        "nameTextStyle": {"color": MUTED},
        "min": vmin,
        "max": vmax,
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }
    op["series"] = [
        {
            "type": "scatter",
            "data": data,
            "label": {
                "show": True,
                "formatter": "{b}",
                "position": "top",
                "color": "#dfe6ee",
                "fontSize": 10,
                "fontWeight": "bold",
            },
            "labelLayout": {"hideOverlap": True},
            "markLine": {
                "silent": True,
                "symbol": "none",
                "data": [
                    {
                        "xAxis": vmin,
                        "yAxis": vmin,
                        "lineStyle": {"color": MUTED, "type": "dashed", "width": 1},
                        "label": {"formatter": "y = x", "color": MUTED, "fontSize": 10},
                    }
                ],
            },
        }
    ]
    return op


def scatter_vwap_ib_option(puntos) -> dict:
    """Scatter J2 — VWAP + Initial Balance: X = distancia al VWAP %, Y = volumen.

    Verde = LARGO (IB UP + precio > VWAP), rojo = CORTO (IB DOWN + precio < VWAP).
    Línea vertical en 0 = VWAP. El tooltip se arma con `tooltipRows`.
    """
    validos = [
        p for p in puntos
        if p.get("dist_vwap") is not None and p.get("vol_ratio") is not None
    ]
    data = []
    for p in validos:
        lado = p.get("lado")  # LARGO / CORTO
        color = VERDE if lado == "LARGO" else ROJO
        conf = bool(p.get("confluencia"))  # confluencia de la fila J → anillo dorado
        data.append(
            {
                "value": [round(float(p["dist_vwap"]), 2), round(float(p["vol_ratio"]), 2)],
                "name": p["symbol"],
                "symbolSize": 17 if conf else 14,
                "itemStyle": {
                    "color": color,
                    "borderColor": AMARILLO if conf else "#0b0f14",
                    "borderWidth": 3 if conf else 1,
                },
                "extra": {
                    "ticker": p.get("ticker"),
                    "lado": lado,
                    "badge": {"text": lado or "—", "side": "pos" if lado == "LARGO" else "neg"},
                    "ib": p.get("ruptura"),
                    "hora": p.get("hora"),
                    "close": p.get("close"),
                    "vwap": p.get("vwap"),
                    "dist_vwap": p.get("dist_vwap"),
                    "vol_ratio": p.get("vol_ratio"),
                    "confluencia": conf,
                    "logo": p.get("logo"),
                },
            }
        )

    xs = [abs(float(p["dist_vwap"])) for p in validos]
    x_abs = round(max(xs + [1.0]) * 1.15, 2) or 1.0
    ys = [float(p["vol_ratio"]) for p in validos]
    y_max = round(max(ys + [2.0]) * 1.1, 2)

    op = _base()
    op["tooltipHtml"] = True
    op["tooltip"] = {"trigger": "item"}
    op["tooltipRows"] = [
        {"label": "IB", "key": "ib"},
        {"label": "Hora", "key": "hora"},
        {"label": "Close", "key": "close", "dec": 2},
        {"label": "VWAP", "key": "vwap", "dec": 2},
        {"label": "Dist. VWAP", "key": "dist_vwap", "dec": 2, "signed": True, "suffix": "%"},
        {"label": "Volumen", "key": "vol_ratio", "dec": 2, "suffix": "x"},
    ]
    op["grid"] = {"left": 52, "right": 20, "top": 28, "bottom": 50}
    op["xAxis"] = {
        "type": "value",
        "name": "Distancia al VWAP (%)",
        "nameLocation": "middle",
        "nameGap": 30,
        "nameTextStyle": {"color": MUTED},
        "min": -x_abs,
        "max": x_abs,
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }
    op["yAxis"] = {
        "type": "value",
        "name": "Volumen rel.",
        "nameTextStyle": {"color": MUTED},
        "min": 0,
        "max": y_max,
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }
    op["series"] = [
        {
            "type": "scatter",
            "data": data,
            "label": {
                "show": True,
                "formatter": "{b}",
                "position": "top",
                "color": "#dfe6ee",
                "fontSize": 10,
                "fontWeight": "bold",
            },
            "labelLayout": {"hideOverlap": True},
            "markLine": {
                "silent": True,
                "symbol": "none",
                "data": [
                    {
                        "xAxis": 0,
                        "lineStyle": {"color": MUTED, "type": "dashed", "width": 1.5},
                        "label": {"formatter": "VWAP", "color": MUTED, "fontSize": 10, "position": "insideEndTop"},
                    }
                ],
            },
        }
    ]
    return op


def _change_rsi_neutro(change: float, rsi: float) -> bool:
    """Sin valor de decisión: RSI en zona neutra o cambio de precio casi nulo."""
    return 40.0 <= rsi <= 60.0 or abs(change) <= 0.3


def change_rsi_visible(puntos) -> list:
    """Puntos con potencial de oportunidad (descarta la zona central neutra)."""
    return [
        p
        for p in puntos
        if not _change_rsi_neutro(float(p["change_pct"]), float(p["rsi"]))
    ]


def change_rsi_option(puntos) -> dict:
    """Scatter Change% vs RSI (momentum confirmado).

    x = cambio % (línea vertical en 0), y = RSI (líneas 30/70); cada acción es un
    punto etiquetado con su ticker y coloreado por el signo del cambio. Los puntos
    de la zona central (RSI 40-60 o |change| <= 0.3%) se omiten por no representar
    oportunidad potencial. El tooltip se arma con `tooltipRows` (icono + métricas).
    """
    data = []
    for p in puntos:
        ch = float(p["change_pct"])
        rsi = float(p["rsi"])
        if ch > 0.3:
            color, tipo, lado = VERDE, "ALCISTA", "pos"
        elif ch < -0.3:
            color, tipo, lado = ROJO, "BAJISTA", "neg"
        else:
            color, tipo, lado = AMARILLO, "NEUTRO", "neu"
        if rsi > 70:
            zona = "Sobrecompra"
        elif rsi < 30:
            zona = "Sobreventa"
        else:
            zona = "Neutra"
        data.append(
            {
                "value": [round(ch, 2), round(rsi, 1)],
                "name": p["symbol"],
                "itemStyle": {"color": color, "borderColor": "#0b0f14", "borderWidth": 1},
                "extra": {
                    "ticker": p.get("ticker") or p["symbol"].split(":")[-1],
                    "logo": p.get("logo"),
                    "badge": {"text": tipo, "side": lado},
                    "change_pct": ch,
                    "rsi": rsi,
                    "zona": zona,
                },
            }
        )

    # Eje X simétrico (mismo rango a izquierda y derecha) para centrar el 0.
    # La guía inferior reparte las palabras de forma uniforme en ese rango.
    cambios = [d["value"][0] for d in data]
    xmin = min(cambios) if cambios else 0.0
    xmax = max(cambios) if cambios else 0.0
    limite = max(abs(xmin), abs(xmax))
    limite = max(2.0, float(math.ceil(limite / 2.0) * 2))
    guia = [
        {"value": [-limite, 15], "name": "pierde mucho", "label": {"align": "left"}},
        {"value": [-limite / 2, 15], "name": "pierde"},
        {"value": [0.0, 15], "name": "0"},
        {"value": [limite / 2, 15], "name": "gana"},
        {"value": [limite, 15], "name": "gana mucho", "label": {"align": "right"}},
    ]

    op = _base()
    op["tooltipHtml"] = True
    op["tooltip"] = {"trigger": "item"}
    op["tooltipWidth"] = 220
    op["tooltipRows"] = [
        {"label": "Cambio", "key": "change_pct", "dec": 2, "signed": True, "suffix": "%"},
        {"label": "RSI 1D", "key": "rsi", "dec": 1},
        {"label": "Zona RSI", "key": "zona"},
    ]
    op["grid"] = {"left": 50, "right": 16, "top": 26, "bottom": 34}
    op["xAxis"] = {
        "type": "value",
        "min": -limite,
        "max": limite,
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }
    op["yAxis"] = {
        "type": "value",
        "name": "RSI",
        "min": 15,
        "max": 85,
        "nameTextStyle": {"color": MUTED},
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }
    op["series"] = [
        {
            "type": "scatter",
            "data": data,
            "symbolSize": 12,
            "label": {
                "show": True,
                "formatter": "{b}",
                "position": "top",
                "color": "#dfe6ee",
                "fontSize": 9,
            },
            "labelLayout": {"hideOverlap": True},
            "markLine": {
                "silent": True,
                "symbol": "none",
                "data": [
                    {"yAxis": 70, "lineStyle": {"color": ROJO, "type": "dashed", "width": 1},
                     "label": {"formatter": "sobrecompra  70", "color": ROJO, "fontSize": 9,
                               "position": "insideEndTop"}},
                    {"yAxis": 30, "lineStyle": {"color": VERDE, "type": "dashed", "width": 1},
                     "label": {"formatter": "sobreventa  30", "color": VERDE, "fontSize": 9,
                               "position": "insideEndBottom"}},
                    {"xAxis": 0, "lineStyle": {"color": MUTED, "type": "dashed", "width": 1},
                     "label": {"show": False}},
                ],
            },
        },
        {
            "type": "scatter",
            "symbolSize": 0,
            "silent": True,
            "z": 5,
            "data": guia,
            "label": {
                "show": True,
                "formatter": "{b}",
                "position": "top",
                "color": CLARO,
                "fontSize": 9,
            },
            "tooltip": {"show": False},
        },
    ]
    return op


def precio_option(serie) -> dict:
    """Precio intradía + SMA20 (amarillo punteado) + SMA50 (verde discontinuo)."""
    x = [s["ts"] for s in serie]
    op = _base()
    op["tooltip"] = {"trigger": "axis"}
    op["legend"] = {
        "data": ["Precio", "SMA20", "SMA50"],
        "textStyle": {"color": MUTED, "fontSize": 11},
        "top": 0,
        "itemWidth": 14,
    }
    op["grid"] = {"left": 54, "right": 18, "top": 34, "bottom": 58}
    op["xAxis"] = _eje_x(x, rotate=60, fontSize=9)
    op["yAxis"] = {
        "type": "value",
        "scale": True,
        "axisLabel": {"color": MUTED, "fontSize": 11},
        "axisLine": {"lineStyle": {"color": BORDE}},
        "splitLine": {"lineStyle": {"color": "#1e252e"}},
    }

    def _linea(nombre, valores, color, tipo="solid", ancho=2):
        return {
            "type": "line",
            "name": nombre,
            "data": valores,
            "smooth": True,
            "showSymbol": False,
            "lineStyle": {"color": color, "width": ancho, "type": tipo},
        }

    op["series"] = [
        _linea("Precio", [s["close"] for s in serie], AZUL),
        _linea("SMA20", [s["sma20"] for s in serie], AMARILLO, "dotted", 1),
        _linea("SMA50", [s["sma50"] for s in serie], VERDE, "dashed", 1),
    ]
    return op


def candlestick_option(serie, signal="NEUTRAL") -> dict:
    """Velas 15m + volumen + SMA9/21, Bollinger, VWAP y señal."""
    x = [s["ts"] for s in serie]
    candle = [[s["open"], s["close"], s["low"], s["high"]] for s in serie]
    vol_colores = [VERDE if s["close"] >= s["open"] else ROJO for s in serie]
    vol_data = _data_barras([s.get("volume") or 0 for s in serie], vol_colores)

    signal_color = {"COMPRAR": VERDE, "VENDER": ROJO}.get(signal, AMARILLO)

    op = _base()
    op["tooltip"] = {"trigger": "axis", "axisPointer": {"type": "cross"}}
    op["legend"] = {
        "data": ["Velas", "Vol", "SMA9", "SMA21", "BB Upper", "BB Lower", "VWAP"],
        "textStyle": {"color": MUTED, "fontSize": 10},
        "top": 0,
        "itemWidth": 12,
    }
    op["grid"] = [
        {"left": 54, "right": 18, "top": 38, "height": "52%"},
        {"left": 54, "right": 18, "top": "68%", "height": "18%"},
    ]
    op["xAxis"] = [
        {
            "type": "category",
            "data": x,
            "gridIndex": 0,
            "axisLabel": {"show": False},
            "axisLine": {"lineStyle": {"color": BORDE}},
        },
        {
            "type": "category",
            "data": x,
            "gridIndex": 1,
            "axisLabel": {"color": MUTED, "fontSize": 9, "rotate": 60},
            "axisLine": {"lineStyle": {"color": BORDE}},
        },
    ]
    op["yAxis"] = [
        {
            "type": "value",
            "scale": True,
            "gridIndex": 0,
            "axisLabel": {"color": MUTED, "fontSize": 10},
            "axisLine": {"lineStyle": {"color": BORDE}},
            "splitLine": {"lineStyle": {"color": "#1e252e"}},
        },
        {
            "type": "value",
            "gridIndex": 1,
            "axisLabel": {"show": False},
            "axisLine": {"lineStyle": {"color": BORDE}},
            "splitLine": {"show": False},
        },
    ]

    def _line(name, vals, color, tipo="solid", ancho=1, idx=0):
        return {
            "type": "line",
            "name": name,
            "xAxisIndex": idx,
            "yAxisIndex": idx,
            "data": vals,
            "smooth": True,
            "showSymbol": False,
            "lineStyle": {"color": color, "width": ancho, "type": tipo},
        }

    op["series"] = [
        {
            "type": "candlestick",
            "name": "Velas",
            "xAxisIndex": 0,
            "yAxisIndex": 0,
            "data": candle,
            "itemStyle": {"color": VERDE, "color0": ROJO, "borderColor": VERDE, "borderColor0": ROJO},
        },
        {
            "type": "bar",
            "name": "Vol",
            "xAxisIndex": 1,
            "yAxisIndex": 1,
            "data": vol_data,
        },
        _line("SMA9", [s.get("sma9") for s in serie], AMARILLO, ancho=1),
        _line("SMA21", [s.get("sma21") for s in serie], AZUL, "dashed", 1),
        _line("BB Upper", [s.get("bb_upper") for s in serie], MUTED, "dotted", 1),
        _line("BB Lower", [s.get("bb_lower") for s in serie], MUTED, "dotted", 1),
        _line("VWAP", [s.get("vwap") for s in serie], "#d6a72c", "solid", 2),
    ]

    if signal in ("COMPRAR", "VENDER"):
        op["series"][0]["markPoint"] = {
            "data": [
                {
                    "name": signal,
                    "coord": [len(serie) - 1, serie[-1]["close"]],
                    "value": signal,
                    "itemStyle": {"color": signal_color},
                    "label": {"color": "#fff", "fontSize": 10, "fontWeight": "bold"},
                }
            ]
        }

    return op


def confluencia_option(filas) -> dict:
    """Heatmap de alineación 5m/15m/1D."""
    simbolos = [f["symbol"].split(":")[-1] for f in filas]
    tfs = ["5m", "15m", "1D"]
    borde_vivo = {1: VERDE_VIVO, -1: ROJO_VIVO, 0: NEUTRAL_VIVO}
    data = []
    for i, f in enumerate(filas):
        for j, key in enumerate(["signal_5m", "signal_15m", "signal_1d"]):
            val = {"ALCISTA": 1, "BAJISTA": -1, "NEUTRAL": 0}.get(f.get(key, "NEUTRAL"), 0)
            # formato heatmap: [xIndex(tf), yIndex(símbolo), valor]
            # el borde toma el tono vivo del propio círculo al resaltarse
            data.append(
                {
                    "value": [j, i, val],
                    "itemStyle": {
                        "borderColor": borde_vivo.get(val, NEUTRAL_VIVO),
                        "borderWidth": 0,
                    },
                }
            )

    op = _base()
    op["tooltip"] = {"position": "top"}
    op["grid"] = {"left": 54, "right": 10, "top": 30, "bottom": 12}
    op["xAxis"] = {
        "type": "category",
        "data": tfs,
        # Etiquetas de timeframe arriba y en color más claro que la leyenda
        "position": "top",
        "axisLabel": {"color": CLARO, "fontSize": 10, "fontWeight": "bold"},
        "axisTick": {"show": False},
        "axisLine": {"lineStyle": {"color": BORDE}},
    }
    op["yAxis"] = {
        "type": "category",
        "data": simbolos,
        # inverse=True → el primer símbolo del screener queda arriba (mismo orden visual)
        "inverse": True,
        "axisLabel": {"color": MUTED, "fontSize": 10},
        "axisLine": {"lineStyle": {"color": BORDE}},
    }
    op["visualMap"] = {
        "min": -1,
        "max": 1,
        "show": False,
        # Tonos pastel (verde alcista / rojo bajista) para suavizar el heatmap
        "inRange": {"color": [ROJO_PASTEL, "#2f3844", VERDE_PASTEL]},
    }
    # Círculos en vez de celdas para que el heatmap no se deforme
    op["series"] = [
        {
            "type": "scatter",
            "symbol": "circle",
            "symbolSize": 12,
            "data": data,
            # Resaltado: borde con el tono vivo del propio círculo, nítido (sin blur)
            "emphasis": {
                "scale": 1.35,
                "itemStyle": {"borderWidth": 2.5, "shadowBlur": 0},
            },
        }
    ]
    return op

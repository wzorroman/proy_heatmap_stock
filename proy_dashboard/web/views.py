"""web/views.py — páginas y fragmentos HTMX.

Cada endpoint de ``/partials/*`` obtiene un view model de los servicios, construye
la `option` con ``web.charts`` y renderiza una plantilla. Sin lógica de negocio
en las plantillas ni en JS.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from core.container import Container
from core.timezone import ensure_utc, format_hora, get_tz, now_utc, tz_label
from web import charts
from web.logos import logo_url
from web.templating import templates

router = APIRouter(prefix="/partials", tags=["partials"])


def _bandera(codigo: str) -> str:
    """Código de país ISO-2 → emoji de bandera (p. ej. 'US' → 🇺🇸)."""
    if not codigo or len(codigo) != 2 or not codigo.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in codigo.upper())


def _container(request: Request) -> Container:
    return request.app.state.container


def _fmt_hora_lima(iso: str) -> str:
    """ISO UTC → hora local de Lima (America/Lima) legible: '30/09 15:34'."""
    try:
        dt = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso
    local = ensure_utc(dt).astimezone(get_tz("America/Lima"))
    return local.strftime("%d/%m %H:%M")


def _card(request: Request, titulo, chart_id, option, *, nota=None, altura=280, accent=None, fill=False):
    return templates.TemplateResponse(
        request,
        "partials/card_chart.html",
        {
            "titulo": titulo,
            "chart_id": chart_id,
            "option": option,
            "nota": nota,
            "altura": altura,
            "accent": accent,
            "fill": fill,
        },
    )


@router.get("/header", response_class=HTMLResponse)
def header(request: Request):
    c = _container(request)
    scores, mercado = c.score_service.calcular_ciclo()
    fase = c.session_service.estado()
    return templates.TemplateResponse(
        request,
        "partials/header.html",
        {
            "mercado": mercado,
            "fase": fase,
            "n_activos": len(scores),
            "option": charts.gauge_option(mercado.score_market, titulo="Mercado", zona=mercado.zona),
        },
    )


# Mapa sectorial (treemap) deshabilitado por ahora: no aporta valor.
# @router.get("/treemap", response_class=HTMLResponse)
# def treemap(request: Request):
#     c = _container(request)
#     items = c.heatmap_service.treemap()
#     return _card(
#         request, "Mapa sectorial (heatmap)", "chart-treemap",
#         charts.treemap_option(items),
#         nota=f"{len(items)} activos · color = cambio diario · tamaño = capitalización",
#         altura=380,
#     )


@router.get("/sectors", response_class=HTMLResponse)
def sectors(request: Request):
    c = _container(request)
    tf = c.settings.business("sectores", "timeframe", default="1D")
    sectores = c.heatmap_service.sectores()
    return _card(
        request, f"Sectorial — cambio medio ({tf})", "chart-sectors",
        charts.sectors_option(sectores),
        nota=f"{len(sectores)} sectores · cambio {tf}",
        fill=True,
    )


@router.get("/momentum", response_class=HTMLResponse)
def momentum(request: Request):
    c = _container(request)
    data = c.momentum_service.top_bottom()
    return _card(
        request, "Momentum — top/bottom (1D)", "chart-momentum",
        charts.momentum_option(data["top"], data["bottom"]),
        nota=(
            f'<span class="pos">▲ alcistas</span> · <span class="neg">▼ bajistas</span> · '
            f'{data["n"]} activos con cambio'
        ),
        altura=460,
        accent=charts.AZUL,
    )


# RSI (top) eliminado: duplica la información del scatter RSI top-cap.
# @router.get("/indicators", response_class=HTMLResponse)
# def indicators(request: Request):
#     c = _container(request)
#     items = c.indicator_service.por_indicador("rsi", "1d")
#     return _card(
#         request, "RSI (top)", "chart-indicators",
#         charts.indicator_option(items, tipo="rsi"),
#         nota=(
#             'RSI base (1D) · <span class="neg">rojo ≥70 sobrecompra</span> · '
#             '<span class="pos">verde ≤30 sobreventa</span>'
#         ),
#         altura=340,
#         accent=charts.VERDE,
#     )


@router.get("/volume", response_class=HTMLResponse)
def volume(request: Request):
    c = _container(request)
    data = c.heatmap_service.anomalia_volumen()
    categorias = [d["symbol"] for d in data][::-1]
    valores = [round(d["ratio"], 2) for d in data][::-1]
    return _card(
        request, "Anomalía de volumen", "chart-volume",
        charts.bar_option(categorias, valores, color_por_signo=False),
        nota="volumen / media 10d",
        altura=340,
    )


@router.get("/range52w", response_class=HTMLResponse)
def range52w(request: Request):
    c = _container(request)
    data = c.heatmap_service.rango_52w()
    categorias = [d["symbol"] for d in data][::-1]
    valores = [round(d["pct"], 1) for d in data][::-1]
    return _card(
        request, "Posición en rango 52s", "chart-range52w",
        charts.bar_option(categorias, valores, sufijo="%", umbral=50.0),
        nota="0% = mínimo 52s · 100% = máximo 52s",
        altura=340,
    )


@router.get("/rsi_limites", response_class=HTMLResponse)
def rsi_limites(request: Request):
    """RSI de las acciones top por capitalización EN OPORTUNIDAD (≥60 o ≤40)."""
    c = _container(request)
    puntos = c.heatmap_service.top_equity_rsi()
    op_alto = c.settings.business("rsi", "oportunidad_alto", default=60)
    op_bajo = c.settings.business("rsi", "oportunidad_bajo", default=40)
    lim_alto = c.settings.business("rsi", "limite_alto", default=70)
    lim_bajo = c.settings.business("rsi", "limite_bajo", default=30)
    return _card(
        request,
        f"RSI 1D · acciones top por capitalización (≥{op_alto} / ≤{op_bajo})",
        "chart-rsi-scatter",
        charts.scatter_rsi_option(
            puntos,
            oportunidad_alto=op_alto,
            oportunidad_bajo=op_bajo,
            limite_alto=lim_alto,
            limite_bajo=lim_bajo,
        ),
        nota=(
            f'{len(puntos)} acciones en oportunidad · '
            f'<span class="neg">≥{op_alto}</span> · <span class="pos">≤{op_bajo}</span> · '
            f'límites {lim_bajo}/{lim_alto} en amarillo · tamaño = capitalización'
        ),
        accent=charts.AZUL,
        fill=True,
    )


# Riesgo intermarket (divergente) deshabilitado: duplica el Termómetro de Riesgo.
# @router.get("/risk", response_class=HTMLResponse)
# def risk(request: Request):
#     c = _container(request)
#     score, items = c.score_service.score_radar()
#     if score is None:
#         color = charts.MUTED
#     elif score >= 6.5:
#         color = charts.VERDE
#     elif score <= 4.5:
#         color = charts.ROJO
#     else:
#         color = charts.AMARILLO
#     score_txt = f"{score:.2f}" if score is not None else "—"
#     return _card(
#         request, "Riesgo intermarket (divergente)", "chart-risk",
#         charts.diverging_riesgo_option(items),
#         nota=(
#             f'score radar <b style="color:{color}">{score_txt}</b> · '
#             '<span class="neg">derecha rojo = más riesgo</span> · '
#             '<span class="pos">izquierda verde = menos riesgo</span> · '
#             'centro = neutral (5/10)'
#         ),
#         altura=300,
#         accent=color,
#     )


@router.get("/riesgo_gauges", response_class=HTMLResponse)
def riesgo_gauges(request: Request):
    c = _container(request)
    return templates.TemplateResponse(
        request, "partials/risk_gauges.html",
        {"gauges": c.score_service.riesgo_gauges()},
    )


@router.get("/riesgo_fx", response_class=HTMLResponse)
def riesgo_fx(request: Request):
    c = _container(request)
    gauges = c.score_service.riesgo_gauges()
    driver = max(gauges, key=lambda g: g["nivel"], default=None)
    return templates.TemplateResponse(
        request, "partials/riesgo_fx.html",
        {"driver": driver, "riesgos": gauges, "fx": c.score_service.fx_macro()},
    )


@router.get("/sector_risk", response_class=HTMLResponse)
def sector_risk(request: Request):
    c = _container(request)
    tf = c.settings.business("sectores", "timeframe", default="1D")
    return templates.TemplateResponse(
        request,
        "partials/sector_risk.html",
        {"sectores": c.heatmap_service.sector_risk(), "timeframe": tf},
    )


def _momentum_items(rows: list) -> list:
    max_abs = max([abs(r["change_pct"]) for r in rows] or [1.0]) or 1.0
    return [
        {
            "ticker": r["symbol"].split(":")[-1],
            "change_pct": r["change_pct"],
            "pct": round(abs(r["change_pct"]) / max_abs * 100, 1),
            "prev_close": r.get("prev_close"),
            "close": r.get("close"),
            "logo": logo_url(r["symbol"]),
        }
        for r in rows
    ]


@router.get("/alcistas", response_class=HTMLResponse)
def alcistas(request: Request):
    c = _container(request)
    data = c.momentum_service.top_bottom()
    return templates.TemplateResponse(
        request,
        "partials/momentum_lista.html",
        {"titulo": "Alcistas del Día", "color": "verde", "items": _momentum_items(data["top"])},
    )


@router.get("/bajistas", response_class=HTMLResponse)
def bajistas(request: Request):
    c = _container(request)
    data = c.momentum_service.top_bottom()
    return templates.TemplateResponse(
        request,
        "partials/momentum_lista.html",
        {"titulo": "Bajistas del Día", "color": "rojo", "items": _momentum_items(data["bottom"])},
    )


@router.get("/change_rsi", response_class=HTMLResponse)
def change_rsi(request: Request):
    c = _container(request)
    puntos = c.momentum_service.change_rsi()
    return _card(
        request, "Momentum Confirmado — Change vs RSI (1D)", "chart-change-rsi",
        charts.change_rsi_option(puntos),
        nota=f"{len(puntos)} acciones · color por cambio · líneas RSI 30/70",
        altura=460,
        accent=charts.VERDE,
    )


@router.get("/precios", response_class=HTMLResponse)
def precios(request: Request):
    """Fila con las 3 tarjetas de precio (QQQ/SPY/ORO) + SMA20/50 + señal."""
    c = _container(request)
    tarjetas = c.precio_service.analisis_todas()
    ib_simbolos = set(c.initial_balance_service.mercado_simbolos())
    tz = c.settings.timezone
    for t in tarjetas:
        t["ib"] = None
        t["logo"] = logo_url(t["symbol"])
        if t.get("symbol") in ib_simbolos and not t.get("sin_datos"):
            t["ib"] = c.initial_balance_service.evaluar_symbol(t["symbol"])
            if t["ib"]:
                t["ib"]["hora"] = format_hora(t["ib"].get("hora_utc"), tz)
        if t.get("sin_datos"):
            t["accent"] = charts.MUTED
            continue
        t["option"] = charts.precio_option(t["serie"])
        t["accent"] = {"COMPRAR": charts.VERDE, "VENDER": charts.ROJO}.get(
            t["signal"], charts.AMARILLO
        )
    return templates.TemplateResponse(
        request,
        "partials/precios.html",
        {"tarjetas": tarjetas, "tz_label": tz_label(tz)},
    )


@router.get("/score_history", response_class=HTMLResponse)
def score_history(request: Request):
    c = _container(request)
    desde = now_utc() - timedelta(hours=int(c.settings.business("panels", "history_hours_default", default=24)))
    rows = c.score_repo.fetch_agg_history(desde)
    tz_view = get_tz(c.settings.timezone)
    tz_ny = get_tz("America/New_York")
    puntos = []
    mark_lines = []
    market_hours = []
    market_open_lines = []
    last_date = None
    in_market = False
    market_start_idx = None
    for r in rows:
        ts = r["timestamp_utc"]
        if r.get("score_market") is None:
            continue
        label = ts.astimezone(tz_view).strftime("%d/%m %H:%M")
        puntos.append((label, round(float(r["score_market"]), 2)))
        idx = len(puntos) - 1
        # Separador de día (medianoche en zona de visualización)
        local_date = ts.astimezone(tz_view).date()
        if last_date is not None and local_date != last_date:
            mark_lines.append(idx)
        last_date = local_date
        # Horario de mercado NY 9:30-16:00 ET (con DST correcto)
        ny = ts.astimezone(tz_ny)
        minutos = ny.hour * 60 + ny.minute
        is_market = 9 * 60 + 30 <= minutos < 16 * 60
        if is_market and not in_market:
            in_market = True
            market_start_idx = idx
            market_open_lines.append(idx)
        elif not is_market and in_market:
            in_market = False
            market_hours.append([{"xAxis": market_start_idx}, {"xAxis": idx - 1}])
            market_start_idx = None
    if in_market and market_start_idx is not None:
        market_hours.append([{"xAxis": market_start_idx}, {"xAxis": len(puntos) - 1}])
    zonas = c.settings.business("score", "zones", default={"comprar": 6.5, "vender": 4.5})
    # Apertura NY expresada en la zona de visualización (APP_TIMEZONE)
    from datetime import datetime as _dt

    apertura_local = (
        _dt.now(tz_ny).replace(hour=9, minute=30, second=0, microsecond=0)
        .astimezone(tz_view)
        .strftime("%H:%M")
    )
    return _card(
        request, "Evolución del score de mercado", "chart-score-history",
        charts.line_option(
            puntos, y_min=0, y_max=10, zonas=zonas,
            mark_lines=mark_lines, market_hours=market_hours,
            market_open_lines=market_open_lines,
        ),
        nota=(
            f"{len(puntos)} ciclos · <span style='color:#ff9f40'>▮</span> medianoche · "
            f"<span style='color:#b8c2cc'>▮</span> apertura NY {apertura_local} {tz_label(c.settings.timezone)}"
        ),
        altura=260,
    )


@router.get("/multiframe", response_class=HTMLResponse)
def multiframe(request: Request):
    c = _container(request)
    # Selección RSI 1D top con 5m y 15m alineados: ambos <40 o ambos >60.
    op_alto = float(c.settings.business("rsi", "oportunidad_alto", default=60))
    op_bajo = float(c.settings.business("rsi", "oportunidad_bajo", default=40))
    puntos = c.heatmap_service.top_equity_rsi()
    simbolos = [p["symbol"] for p in puntos]
    rsi1d = {p["symbol"]: float(p["rsi"]) for p in puntos if p.get("rsi") is not None}
    rsi5 = {
        d["symbol"]: d["valor"]
        for d in c.indicator_service.por_indicador("rsi", "5", n=10000)
    }
    rsi15 = {
        d["symbol"]: d["valor"]
        for d in c.indicator_service.por_indicador("rsi", "15", n=10000)
    }
    categorias = [
        s
        for s in simbolos
        if s in rsi5
        and s in rsi15
        and (
            (rsi5[s] < op_bajo and rsi15[s] < op_bajo)
            or (rsi5[s] > op_alto and rsi15[s] > op_alto)
        )
    ]
    categorias.sort(key=lambda s: rsi1d.get(s, 0.0), reverse=True)
    series = {
        "RSI 5m": [round(rsi5[s], 1) for s in categorias],
        "RSI 15m": [round(rsi15[s], 1) for s in categorias],
    }
    return _card(
        request, "Multi-TF (RSI 5m vs 15m)", "chart-multiframe",
        charts.multiframe_option(series, categorias=categorias),
        nota=(
            f'{len(categorias)} acciones · 5m y 15m ambos '
            f'<span class="pos">&lt;{int(op_bajo)}</span> o '
            f'<span class="neg">&gt;{int(op_alto)}</span> · de la selección RSI 1D top'
        ),
        accent=charts.AMARILLO,
        fill=True,
    )


@router.get("/calendar", response_class=HTMLResponse)
def calendar(request: Request, pais: str | None = None, nivel: str | None = None):
    """Calendario de HOY: eventos ya pasados y por venir, filtrable por país e importancia."""
    c = _container(request)
    pais_def = str(c.settings.business("events", "today_country", default="ALL") or "ALL")
    nivel_def = str(c.settings.business("events", "today_importance_level", default=1))
    pais_sel = (pais or pais_def).upper()
    nivel_sel = (nivel or nivel_def).lower()

    eventos = c.event_service.eventos_del_dia(country=pais_sel, nivel=nivel_sel)
    tz = get_tz(c.settings.timezone)
    rows = []
    for e in eventos:
        ts = datetime.fromisoformat(e["event_timestamp"]).astimezone(tz)
        sorp = e["sorpresa_pct"]
        sorp_cls = "pos" if (sorp or 0) > 0 else ("neg" if (sorp or 0) < 0 else "")
        imp = e["importance"]
        imp_txt = "★" * imp if imp and imp > 0 else ("" if imp is None else str(imp))
        imp_cls = "neg" if (imp or 0) >= 2 else ("neu" if imp == 1 else "muted")
        pais = e["country"] or ""
        pais_txt = f"{_bandera(pais)} {pais}".strip()
        rows.append(
            {
                "clase": "pasado" if e.get("pasado") else "",
                "cells": [
                    {"texto": ts.strftime("%d/%m")},
                    {"texto": ts.strftime("%H:%M")},
                    {"texto": pais_txt},
                    {"texto": e["title"] or ""},
                    {"texto": imp_txt, "clase": imp_cls},
                    {"texto": e["actual"] or "—", "clase": sorp_cls},
                    {"texto": e["forecast"] or "—", "clase": "muted"},
                    {"texto": f"{sorp:+.1f}%" if sorp is not None else "—", "clase": sorp_cls},
                ],
            }
        )
    if not rows:
        rows = [
            {
                "clase": "",
                "cells": ["—", "—", "—", "Sin eventos para el filtro", "", "", "", ""],
            }
        ]

    niveles = [
        ("todos", "Todos"),
        ("1", "Nivel 1 · alta"),
        ("2", "Nivel 2 · media"),
        ("3", "Nivel 3 · baja"),
    ]
    paises = [("ALL", "Todos")] + [
        (p, f"{_bandera(p)} {p}") for p in c.event_service.paises()
    ]
    nivel_txt = dict(niveles).get(nivel_sel, "Todos")
    pais_txt = dict(paises).get(pais_sel, pais_sel)
    return templates.TemplateResponse(
        request,
        "partials/calendar.html",
        {
            "titulo": f"Calendario de hoy · {nivel_txt} · {pais_txt} ({len(eventos)})",
            "headers": [
                "Fecha",
                f"Hora {tz.key.split('/')[-1]}",
                "País",
                "Evento",
                "Imp.",
                "Actual",
                "Prev.",
                "Sorpresa",
            ],
            "rows": rows,
            "paises": paises,
            "pais_sel": pais_sel,
            "niveles": niveles,
            "nivel_sel": nivel_sel,
        },
    )


def _fmt(v, dec=2):
    try:
        return f"{float(v):.{dec}f}"
    except (TypeError, ValueError):
        return "—"


def _cap(valor):
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "—"
    if v >= 1e12:
        return f"${v / 1e12:.2f}T"
    if v >= 1e9:
        return f"${v / 1e9:.1f}B"
    if v >= 1e6:
        return f"${v / 1e6:.0f}M"
    return f"${v:,.0f}"


def _pos52(precio, low, high):
    try:
        precio, low, high = float(precio), float(low), float(high)
    except (TypeError, ValueError):
        return "—"
    if high == low:
        return "—"
    return f"{(precio - low) / (high - low) * 100:.0f}%"


def _top_screener_symbols(container, preferido: str | None = None) -> list[str]:
    """Devuelve hasta 3 símbolos del screener: preferido primero, luego top screener."""
    todas = container.screener_15m_service.scan()
    accionables = [f for f in todas if f.get("signal") in ("COMPRAR", "VENDER")]
    ordenados = (accionables + [f for f in todas if f not in accionables]) if accionables else todas
    vistos = set()
    salida = []
    if preferido:
        salida.append(preferido.upper().strip())
        vistos.add(preferido.upper().strip())
    for f in ordenados:
        sym = f["symbol"].upper().strip()
        if sym not in vistos:
            salida.append(sym)
            vistos.add(sym)
        if len(salida) >= 3:
            break
    while len(salida) < 3:
        fallback = container.settings.business("trading_15m", "default_symbol", default="NASDAQ:NVDA")
        if fallback.upper().strip() not in vistos:
            salida.append(fallback.upper().strip())
            vistos.add(fallback.upper().strip())
        else:
            break
    return salida


@router.get("/velas_15m", response_class=HTMLResponse)
def velas_15m(request: Request, symbol: str | None = None):
    """Gráfico único de velas 15m para el símbolo seleccionado del screener."""
    c = _container(request)
    symbol = _top_screener_symbols(c, preferido=symbol)[0]
    data = c.bar_15m_service.analyze(symbol)
    chart_id = "chart-velas-15m"
    if data.get("sin_datos"):
        return templates.TemplateResponse(
            request,
            "partials/velas_15m.html",
            {"symbol": symbol, "sin_datos": True, "chart_id": chart_id, "option": {}},
        )
    return templates.TemplateResponse(
        request,
        "partials/velas_15m.html",
        {
            "symbol": symbol,
            "sin_datos": False,
            "chart_id": chart_id,
            "signal": data["signal"],
            "ultimo": data["ultimo"],
            "option": charts.candlestick_option(data["barras"], signal=data["signal"]),
        },
    )


def _screener_filas(container) -> tuple[list[dict], str, int]:
    """Selección única de filas del screener (compartida con confluencia)."""
    todas = container.screener_15m_service.scan()
    accionables = [f for f in todas if f.get("signal") in ("COMPRAR", "VENDER")]
    if len(accionables) >= 5:
        filas = accionables[:20]
        nota_extra = f"mostrando {len(filas)} de {len(accionables)} con señal"
    elif accionables:
        vistos = {f["symbol"] for f in accionables}
        extra = [f for f in todas if f["symbol"] not in vistos][: 15 - len(accionables)]
        filas = accionables + extra
        nota_extra = f"{len(accionables)} con señal + {len(extra)} top movimiento"
    else:
        filas = todas[:15]
        nota_extra = "sin señales claras; mostrando top 15 por movimiento"
    for f in filas:
        f["logo"] = logo_url(f["symbol"])
    return filas, nota_extra, len(todas)


@router.get("/screener_15m", response_class=HTMLResponse)
def screener_15m(request: Request, compact: bool = False):
    """Ranking de oportunidades 15m en acciones (solo señales accionables)."""
    c = _container(request)
    filas, nota_extra, total = _screener_filas(c)
    return templates.TemplateResponse(
        request,
        "partials/screener_15m.html",
        {"filas": filas, "nota_extra": nota_extra, "total": total, "compact": compact},
    )


@router.get("/confluencia", response_class=HTMLResponse)
def confluencia(request: Request):
    """Heatmap de alineación 5m/15m/1D sobre los mismos símbolos del screener."""
    c = _container(request)
    filas_screener, _, _ = _screener_filas(c)
    symbols = [f["symbol"] for f in filas_screener]
    filas = c.confluencia_service.scan(symbols=symbols)
    chart_id = "chart-confluencia"
    option = charts.confluencia_option(filas) if filas else {}
    return templates.TemplateResponse(
        request,
        "partials/confluencia.html",
        {"chart_id": chart_id, "option": option, "n": len(filas)},
    )


@router.get("/ib_acciones", response_class=HTMLResponse)
def ib_acciones(request: Request):
    """Rango inicial (09:30–10:00 NY) por acción, en el mismo orden del screener."""
    c = _container(request)
    filas_screener, _, _ = _screener_filas(c)
    symbols = [f["symbol"] for f in filas_screener]
    ib_por_symbol = c.initial_balance_service.evaluar_lote(symbols)
    tz = c.settings.timezone

    filas = []
    for symbol in symbols:
        fila = ib_por_symbol.get(symbol)
        if fila is None:
            fila = {
                "symbol": symbol,
                "ticker": symbol.split(":")[-1],
                "ib_low": None,
                "ib_high": None,
                "close": None,
                "ruptura": None,
                "fuerza_pct": None,
                "hora_utc": "",
                "sin_datos": True,
            }
        # La ventana se calcula en NY; la hora se muestra en la zona del usuario.
        fila["hora"] = format_hora(fila.get("hora_utc"), tz)
        fila["logo"] = logo_url(symbol)
        filas.append(fila)

    n_rupturas = sum(
        1 for f in filas if f["ruptura"] in ("ALCISTA", "BAJISTA")
    )
    return templates.TemplateResponse(
        request,
        "partials/ib_acciones.html",
        {
            "filas": filas,
            "total": len(filas),
            "n_rupturas": n_rupturas,
            "ib_minutos": c.initial_balance_service.ib_minutos(),
            "tz_label": tz_label(tz),
        },
    )


@router.get("/sector_15m", response_class=HTMLResponse)
def sector_15m(request: Request):
    """Mapa de calor del cambio medio 15m por sector."""
    c = _container(request)
    sectores = c.sector_15m_service.por_sector()
    return _card(
        request,
        "Mapa de calor 15m por sector",
        "chart-sector15m",
        charts.sector_15m_option(sectores),
        nota=f"{len(sectores)} sectores · cambio medio 15m · área = nº de acciones",
        fill=True,
    )


@router.get("/score_15m", response_class=HTMLResponse)
def score_15m(request: Request):
    """Histograma de la distribución del score 15m con descripción de contexto."""
    c = _container(request)
    dist = c.score_service.distribucion_15min()
    return templates.TemplateResponse(
        request,
        "partials/score_15m.html",
        {
            "titulo": f"Distribución score {dist['tf_label']}",
            "chart_id": "chart-score15m",
            "option": charts.score_hist_option(dist),
            "descripcion": dist["descripcion"],
            "media": dist["media"],
            "percentil": dist["percentil"],
            "pct_compra": dist["pct_compra"],
            "pct_venta": dist["pct_venta"],
            "zona": dist["zona"],
            "altura": 200,
        },
    )


@router.get("/divergencia", response_class=HTMLResponse)
def divergencia(request: Request):
    """Alertas de divergencia precio / RSI 15m sobre el universo del screener."""
    c = _container(request)
    filas_screener, _, _ = _screener_filas(c)
    symbols = [f["symbol"] for f in filas_screener]
    data = c.divergencia_service.scan(symbols)
    for f in data["filas"]:
        f["logo"] = logo_url(f["symbol"])
    return templates.TemplateResponse(request, "partials/divergencia.html", data)


@router.get("/tabla_sector", response_class=HTMLResponse)
def tabla_sector(request: Request, sector: str | None = None, q: str | None = None):
    """Tabla de stocks filtrada por sector y/o búsqueda de símbolo."""
    c = _container(request)
    data = c.heatmap_service.tabla_sector(sector, q)
    filas = []
    for r in data["filas"]:
        cambio = r.get("daily_change_pct")
        cambio = float(cambio) if cambio is not None else None
        vol, avg = r.get("volume"), r.get("avg_vol_10d")
        try:
            vol_ratio = float(vol) / float(avg) if vol and avg else None
        except (TypeError, ValueError):
            vol_ratio = None
        filas.append(
            {
                "ticker": r["symbol"].split(":")[-1],
                "symbol": r["symbol"],
                "nombre": r.get("company_name") or r["symbol"].split(":")[-1],
                "logo": logo_url(r["symbol"]),
                "sector": r.get("sector") or "—",
                "precio": _fmt(r.get("price_heatmap"), 2),
                "cambio": cambio,
                "cambio_txt": f"{cambio:+.2f}%" if cambio is not None else "—",
                "rsi": _fmt(r.get("rsi"), 1),
                "adx": _fmt(r.get("adx_15"), 1),
                "volat": _fmt(r.get("volatility_d"), 1),
                "pos52": _pos52(r.get("price_heatmap"), r.get("low_52w"), r.get("high_52w")),
                "cap": _cap(r.get("market_cap")),
                "vol": f"{vol_ratio:.2f}x" if vol_ratio is not None else "—",
            }
        )
    return templates.TemplateResponse(
        request,
        "partials/tabla_sector.html",
        {
            "sector_actual": data["sector"],
            "q": data["q"],
            "sectores": data["sectores"],
            "filas": filas,
        },
    )


@router.get("/health", response_class=HTMLResponse)
def health(request: Request):
    c = _container(request)
    datos = c.health_service.check()
    rows = []
    clase_estado = {"OK": "pos", "WARN": "neu", "ERROR": "neg"}
    for nombre, m in datos["modulos"].items():
        detalle = m.get("detalle")
        if detalle is None and m.get("timestamp_utc"):
            detalle = _fmt_hora_lima(m["timestamp_utc"])
        if detalle is None and m.get("edad_s") is not None:
            detalle = f"hace {round(float(m['edad_s']) / 60)} min"
        estado = m.get("estado")
        rows.append(
            {
                "modulo": nombre,
                "estado": estado,
                "estado_clase": clase_estado.get(estado, ""),
                "detalle": detalle if detalle is not None else "—",
            }
        )
    return templates.TemplateResponse(
        request,
        "partials/health.html",
        {"titulo": f"Health — {datos['status']}", "rows": rows},
    )

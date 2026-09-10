#!/usr/bin/env python3
"""
Frontend Streamlit - Heatmap Stock
Solo muestra datos, toda la logica esta en application/.
"""
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application.heatmap_service import fetch_price_evolution, fetch_sectors, fetch_heatmap_stats

REFRESH_INTERVAL = 150  # 2.5 minutos en segundos

GREEN = "#16a34a"
RED = "#dc2626"


def _style_price(row):
    styles = []
    direction = row.get("direction", 0)
    for col in row.index:
        if col == "price":
            if direction > 0:
                styles.append(f"color: {GREEN}")
            elif direction < 0:
                styles.append(f"color: {RED}")
            else:
                styles.append("color: #000000")
        else:
            styles.append("")
    return styles

st.set_page_config(
    page_title="Heatmap Stock",
    page_icon="\U0001F4C8",
    layout="wide",
)

st.title("Heatmap Stock - Última Hora")

# --- Sidebar: filtros ---
with st.sidebar:
    st.header("Filtros")
    search = st.text_input("Buscar símbolo...")
    try:
        sectors = fetch_sectors()
        sector_filter = st.selectbox("Sector", ["Todos"] + sectors)
    except Exception:
        sector_filter = "Todos"

# --- Métricas resumen ---
try:
    stats = fetch_heatmap_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Stocks", stats.get("total_stocks", 0))
    c2.metric("Subieron \U0001F7E2", stats.get("stocks_up", 0))
    c3.metric("Bajaron \U0001F534", stats.get("stocks_down", 0))
    c4.metric("Cambio Promedio", f"{stats.get('avg_change_pct', 0)}%")
except Exception as e:
    st.warning(f"No se pudieron obtener métricas: {e}")

# --- Tabla principal ---
try:
    data = fetch_price_evolution()

    if not data:
        st.info("No hay datos disponibles. Verifique que el scrapper este ejecutandose.")
    else:
        if search:
            data = [d for d in data if search.upper() in (d.get("symbol") or "").upper()]
        if sector_filter != "Todos":
            data = [d for d in data if sector_filter in (d.get("asset") or "")]

        df = pd.DataFrame(data)
        timestamp_cols = [k for k in df.columns if ':' in k]
        display_order = ["symbol", "asset", "price", "daily_change_pct", "mcap"] + timestamp_cols
        display_order = [c for c in display_order if c in df.columns]

        styler = df.style.apply(_style_price, axis=1)

        column_config = {
            "symbol": st.column_config.TextColumn("Symbol", width="small"),
            "asset": st.column_config.TextColumn("Asset", width="large"),
            "price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "daily_change_pct": st.column_config.NumberColumn("Change%", format="%.2f%%"),
            "mcap": st.column_config.TextColumn("Market Cap", width="small"),
        }
        for col in timestamp_cols:
            column_config[col] = st.column_config.NumberColumn(col, format="%.2f")

        st.dataframe(
            styler,
            column_config=column_config,
            column_order=display_order,
            use_container_width=True,
            height=600,
        )
except Exception as e:
    st.error(f"Error al cargar datos: {e}")

# --- Footer con timestamp ---
now = datetime.now(timezone.utc)
st.caption(f"Última actualización: {now.strftime('%H:%M:%S UTC')} | Auto-refresh: {REFRESH_INTERVAL}s")

# --- Auto-refresh ---
time.sleep(REFRESH_INTERVAL)
st.rerun()

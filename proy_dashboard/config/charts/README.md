# Configuración por gráfico (`config/charts/`)

Cada gráfico del dashboard tiene **un archivo JSON propio**. Los archivos se
fusionan (deep-merge) sobre `config_dashboard.json` en orden de nombre y forman
la configuración única que consume `Settings.business(...)`.

## Convención

- **Nombre:** `<CODIGO>_<slug>.json` (p. ej. `J2_bollinger.json`).
- **`meta`:** bloque con los metadatos del gráfico. Se fusiona entre archivos.
  ```json
  { "meta": { "<slug>": { "codigo": "J2", "titulo": "Reversión Bollinger 15m" } } }
  ```
  - `slug`: identificador estable (no cambia si se reordena el dashboard).
  - `codigo`: letra de fila + número (A1, A2, …), visible en el título.
  - `titulo`: nombre legible del gráfico.
  - `ayuda` (opcional): texto del **popup `(+)`** del título. Se declara como **lista
    de líneas** (`["línea 1", "línea 2"]`) o como un único string con `\n`. Se lee con
    `Settings.chart_help(slug)` y cada línea se respeta tal cual (ideal para mapas ASCII).
    ```json
    { "meta": { "change_rsi": { "codigo": "G2", "titulo": "…",
      "ayuda": ["Mapa de cuadrantes", "", "  ▲", "  │ …"] } } }
    ```
  - `tf` (opcional): **tiempo de evaluación** del gráfico (`"5m"`, `"15m"`, `"1D"`).
    Se lee con `Settings.chart_tf(slug)` y se muestra como etiqueta ámbar
    (`.ib-time`) junto al título.
- **Config del gráfico:** el resto de claves (`trading_15m`, `score`, `panels`, …).
  Varios archivos pueden aportar claves distintas del mismo bloque; el merge las
  combina. Ejemplo: `E1_screener.json` y `J2_bollinger.json` aportan ambos a
  `trading_15m`.

## Códigos

| Código | Slug | Archivo |
|---|---|---|
| A1 | header | `A1_header.json` |
| A2 | riesgo_gauges | `A2_riesgo_gauges.json` |
| A3 | riesgo_fx | `A3_riesgo_fx.json` |
| A4 | score_15m | `A4_score_15m.json` |
| A5 | health | `A5_health.json` |
| B1 | precios | `B1_precios.json` |
| B2 | score_history | `B2_score_history.json` |
| C1 | sectores | `C1_sectores.json` |
| C2 | sector_risk | `C2_sector_risk.json` |
| D1 | alcistas | `D1_alcistas.json` |
| D2 | bajistas | `D2_bajistas.json` |
| D3 | divergencia | `D3_divergencia.json` |
| E1 | screener_15m | `E1_screener.json` |
| E2 | ib_acciones | `E2_ib_acciones.json` |
| E3 | confluencia | `E3_confluencia.json` |
| F1 | velas_15m | `F1_velas_15m.json` |
| F2 | sector_15m | `F2_sector_15m.json` |
| G1 | momentum | `G1_momentum.json` |
| G2 | change_rsi | `G2_change_rsi.json` |
| H1 | rsi_limites | `H1_rsi_limites.json` |
| H2 | multiframe | `H2_multiframe.json` |
| I1 | volume | `I1_volume.json` |
| I2 | range52w | `I2_range52w.json` |
| J1 | oportunidad_15m | `J1_oportunidad.json` |
| J2 | bollinger_15m | `J2_bollinger.json` |
| J3 | confluencia_placeholder | `J3_confluencia_placeholder.json` |
| J4 | divergencia_5m | `J4_divergencia_5m.json` |
| K1 | bollinger_scatter | `K1_bollinger_scatter.json` |
| L1 | calendar | `L1_calendar.json` |
| M1 | tabla_sector | `M1_tabla_sector.json` |

## Uso en código

- **Vistas (Python):** `c.settings.chart_code("bollinger_15m")` → `"J2"`.
- **Plantillas (Jinja):** `{{ chart_code('bollinger_15m') }}` (global registrado
  en `web/templating.py`).

Los códigos **no se hardcodean** en el código ni en las plantillas: se leen
siempre de estos JSON.

# J1 · Oportunidades Momentum 15m — lista con barra de impulso

> **Código:** J1 · **slug:** `oportunidad_15m`
> **Endpoint:** `/partials/oportunidad_15m`
> **Config:** `config/charts/J1_oportunidad.json`
> **Servicio:** `services/oportunidad_15m_service.py`
> **Plantilla:** `web/templates/partials/oportunidad_15m.html`
> **Vista:** `web/views.py::oportunidad_15m`
> **Ubicación en el dashboard:** card de **2/12 columnas**, en la **fila J** (`row-start`), junto a J2/J3/J4.
> **Documentación complementaria:** [`dashboard_explicacion_graph-J_momentum_VWAP-IB_confluencia.md`](dashboard_explicacion_graph-J_momentum_VWAP-IB_confluencia.md).

---

## 1. Qué es

Es una **lista de oportunidades de momentum alcista intradía (15m)**. Cada fila es un candidato y muestra: identidad (`[logo] ticker`), señal, una **barra de impulso** (posición del RSI) y métricas de apoyo.

```
J1 Oportunidades Momentum [15m]
┌──────────────────────────────────────────┐
│ 🖼 SBUX ★                          [LARGO] │
│ ▓▓▓▓▓▓▓│▓░░│░░░░░░░░░░  RSI 63   +0.69%   │
│ ADX 41 · Vol 1.47x · VWAP +1.26%          │
├──────────────────────────────────────────┤
│ 🖼 VZ                            [LARGO]   │
│ ▓▓▓▓▓▓▓▓│▓│░░░░░░░░░░  RSI 63   +0.06%    │
│ ADX 28 · Vol 2.34x · VWAP +0.67%          │
└──────────────────────────────────────────┘
   ██ verde <60 · ██ ámbar 60-70 · ██ rojo ≥70
   │ marcas verticales en RSI 60 y 70 (cortes de color)
```

- **Barra de impulso** = RSI (15m) en la escala **50 → 100**: el largo es `(RSI−50)/50` y el **color** indica la intensidad.
- **%Cambio** = variación del precio (verde ↑ / rojo ↓), separada de la barra.
- Se ordena por un **score compuesto** y el clic en la fila abre las **Velas 15m**.

## 2. Por qué aparece cada activo (criterios de selección)

Un símbolo **entra** si cumple **todo** (`_cumple` en el servicio):

1. **Precio por encima del VWAP** (`close > VWAP`) — momentum intradía positivo.
2. **RSI(15) en zona de fuerza:** `50 ≤ RSI ≤ 70` (sin sobrecompra extrema).
3. **ADX(15) ≥ 25** — tendencia fuerte (no un lateral).
4. **Volumen relativo ≥ 1.2x** (`vol_ratio`) — confirmación.
5. **Última barra alcista o plana** (`change_pct ≥ 0`) — buscamos **continuación**, no reversión.
6. Universo: **equities** del último tick con barras 15m recientes (`oportunidad_horas`, 48 h).

Se toman **hasta `oportunidad_max` (4)** ordenadas por score.

> **Analogía:** es como el **radar de "viento a favor"**: solo muestra los barcos (acciones) que ya **navegan con el viento** (por encima del VWAP), con **viento firme** (ADX), **combustible** (volumen) y sin virar (barra alcista).

## 3. Cómo se calcula

```
1. universo  = equities del último tick con barras recientes (48 h)
2. por símbolo con barras:
     close      = última barra
     change_pct = (close − prev_close) / prev_close
     dist_vwap  = (close − VWAP) / VWAP       (VWAP = Σ(típico·vol)/Σ(vol))
     vol_ratio  = volumen última barra / media 10 anteriores
     rsi_15, adx_15 = indicadores del último tick
3. filtrar con _cumple(...)   (close>VWAP, RSI∈[50,70], ADX≥25, Vol≥1.2, cambio≥0)
4. score = (10 − |RSI−60|/2) + ADX/5 + vol_ratio·2 + dist_vwap + change_pct
5. ordenar por score desc · cortar en oportunidad_max (4)
```

### Config (`config/charts/J1_oportunidad.json`)

```json
"trading_15m": {
  "oportunidad_horas": 48,
  "oportunidad_max": 4,
  "oportunidad_rsi_min": 50,
  "oportunidad_rsi_max": 70,
  "oportunidad_adx_min": 25,
  "oportunidad_vol_min": 1.2
}
```

## 4. Elementos visuales

| Elemento | Qué representa |
|---|---|
| **`[logo] TICKER ★`** | identidad; `★` = confluencia con la fila J (≥2 paneles) |
| **Badge `LARGO`** | señal: solo largos (momentum alcista) |
| **Barra de impulso** | posición del RSI en la **escala 50→100** (`(RSI−50)/50`) |
| **Color de la barra** | verde (<60) · ámbar (60–70) · rojo (≥70) |
| **Marcas verticales** | cortes de color: **RSI 60** (verde→ámbar) y **RSI 70** (ámbar→rojo) |
| **`RSI` dentro de la barra** | valor numérico del RSI (negro, legible sobre la barra) |
| **`%Cambio`** | variación del precio (verde/rojo) |
| **Línea de apoyo** | `ADX · Vol · VWAP` (tenue) |
| **Ayuda `(+)`** | popup sobrepuesto con esta **leyenda** (botón junto al título) |

### Leyenda (botón `(+)`)

El título tiene un botón **`(+)`** que muestra este "mapa/leyenda" en un **popup sobrepuesto** (CSS `.chart-help`/`.chart-help-pop`, mismo patrón que J2):

```
Leyenda — Oportunidades Momentum (15m)
Filtro: RSI 50-70 · ADX ≥25 · Vol ≥1.2x · >VWAP · barra alcista

Barra de impulso (escala RSI 50 → 100):
  ██ verde  = RSI < 60      impulso fresco con recorrido
  ██ ámbar  = RSI 60-70     calentando (zona de oportunidad)
  ██ rojo   = RSI ≥ 70      extendido / sobrecompra (raro por el filtro)
  │         = marcas en RSI 60 y 70 (cortes de color)
  texto dentro de la barra = valor del RSI

Cada fila: [logo] TICKER ★  LARGO · %Cambio · ADX · Vol · VWAP
Orden: por score (vol×2 + ADX/5 + VWAP + % + RSI cercano a 60)
Máximo: 4 filas · clic en fila → velas 15m
```

El texto de la leyenda se declara en `config/charts/J1_oportunidad.json` (`meta.oportunidad_15m.ayuda`), se lee con `Settings.chart_help("oportunidad_15m")` y se muestra con el mecanismo genérico `card_chart.html`/`.chart-help`.

## 5. Casos y cómo leer cada uno

### 5.1 Casos por color de la barra (posición del RSI)

| Barra | RSI | Lectura |
|---|---|---|
| **Verde** (fill ≤20%) | < 60 | Impulso **fresco**; hay recorrido dentro del rango 50–70. |
| **Ámbar** (20–40%) | 60–70 | **Calentando**; cerca del techo de la oportunidad; puede girar si se agota el volumen. |
| **Rojo** (≥40%) | ≥ 70 | **Extendido/sobrecompra**; raro, porque el filtro limita RSI ≤ 70. |

### 5.2 Casos por %Cambio

| %Cambio | Color | Lectura |
|---|---|---|
| `+` grande | verde | La última barra **empujó con fuerza**; momentum vigente. |
| `+` pequeño | verde | Sube apenas; la señal depende más del **volumen/ADX**. |
| `−` | rojo | No debería aparecer (fiiltro exige `change_pct ≥ 0`); si se ve, es por datos del tick. |

### 5.3 Cases por combinación de apoyo (ADX · Vol · VWAP)

| Patrón | Lectura |
|---|---|
| Barra verde/ámbar + **Vol alto** + **ADX alto** | Confianza alta: fuerza + volumen. |
| Barra ámbar + **Vol bajo** | Atención: si el volumen cae, el impulso puede **frenar** en 60–70. |
| **dist_vwap** grande | Precio "lejos" del VWAP → puede **volver** a él (pullback) o seguir con fuerza; vigilar. |

### 5.4 Mapa mental de lectura

```
   barra (RSI 50→100)
   ┌──────┬──────┬──────┐
   █ verde │ ámbar │ rojo │
   fresco │ atento │ extendido
   └──────┴──────┴──────┘
   │ RSI 60 │ RSI 70 │   ← cortes de color
   %Cambio verde = confirma · %Cambio plano = depende de Vol/ADX
   ★ = aparece en ≥2 paneles de la fila J (confluencia)
```

## 6. Ejemplos reales (snapshot 2026-10-08)

| Ticker | RSI 15m | Barra | %Cambio | ADX | Vol | VWAP | Score |
|---|---|---|---:|---:|---:|---:|---:|---:|
| **SBUX** | 63.1 | ámbar | +0.69% | 41.0 | 1.47x | +1.26% | 21.5 |
| **VZ** | 63.4 | ámbar | +0.06% | 28.0 | 2.34x | +0.67% | 19.3 |
| **MCD** | 68.6 | ámbar | +0.07% | 41.1 | 1.56x | +1.32% | 18.4 |

- Los tres están en **ámbar** (RSI 60–70), "calentando".
- **SBUX** es el de mayor score: **ADX 41** (tendencia fuerte) + **dist_vwap +1.26%**.
- **VZ** tiene el **volumen más alto** (2.34x), lo que le da score cercano a pesar de un % bajo.
- **MCD** está en el límite superior (RSI 68.6): el más cerca del corte rojo → mayor riesgo de agotamiento.

## 7. Oportunidades y qué revisar

1. **Fresco + volumen (verde/ámbar bajo):** mejor escenario de **continuación** (RSI <65 + Vol alto + ADX alto).
2. **Cerca del corte ámbar→rojo (RSI ~68):** posible **agotamiento**; esperar que el volumen siga.
3. **dist_vwap grande:** el precio "lejos" del VWAP puede **corregir**; confirmar con las velas.
4. **★ confluencia:** si el símbolo está en ≥2 paneles de la fila J (J1/J2/J3) la señal pesa más.

**Qué revisar siempre:**
- Es un panel de **continuación alcista**; no esperes señales bajistas aquí.
- El **score** está dominado por el **volumen (×2)**; un candidato con RSI medio y volumen alto gana a uno con RSI alto y volumen bajo.
- El clic en una fila abre **Velas 15m** (`#trading-velas-card`).

## 8. Analogías

- **Radar de viento a favor:** solo barcos que ya navegan con el viento (VWAP), con viento firme (ADX), combustible (volumen) y rumbo estable.
- **Termómetro de la barra:** el largo es cuánto "se calentó" el RSI (50→100); el color es la fase (fresco/atento/extendido).
- **Podio de momentum:** 4 candidatos ordenados por "cuánto combustible y viento" hay en la barra.

## 9. Referencias de código

| Qué | Dónde |
|---|---|
| Servicio | `services/oportunidad_15m_service.py` (`scan`, `_cumple`, `_score`) |
| Plantilla | `web/templates/partials/oportunidad_15m.html` (barra + `(+)`) |
| Vista / endpoint | `web/views.py::oportunidad_15m` (calcula `impulso_pct`, `impulso_clase`, `marcas`) |
| Leyenda `(+)` | `Settings.chart_help("oportunidad_15m")` · popup `.chart-help` en `card_chart.html`/app.css |
| Barras e indicadores 15m | `services/bar_15m_service.py` (`_vwap`, `_volume_ratio`) |
| Config | `config/charts/J1_oportunidad.json` (`meta.oportunidad_15m.titulo`/`tf`/`ayuda` + umbrales `trading_15m`) |
| Container | `core/container.py` (`oportunidad_15m_service`) |
| Dashboard | `web/templates/dashboard.html` (`cell dos row-start`, fila J) |
| Velas (clic) | `/partials/velas_15m?symbol=…` → `#trading-velas-card` |

---

*Documento generado 2026-10-08. Los valores numéricos son un snapshot y cambian con el mercado.*
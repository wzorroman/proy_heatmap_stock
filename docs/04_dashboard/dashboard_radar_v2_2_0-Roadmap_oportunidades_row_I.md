# Roadmap v2.2.0 — Fila I: reemplazo para trading 5-15 min

> **Ruta:** `docs/04_dashboard/dashboard_radar_v2_2_0-Roadmap_oportunidades_row_I.md`
> **Proyecto:** `proy_dashboard` — Dashboard de Contexto + Trading Intradía
> **Versión:** 2.2.0 · **Fecha:** 2026-10-08
> **Contexto:** la fila I (I1 «Anomalía de volumen» + I2 «Posición en rango 52s») se **eliminó** por baja utilidad para el timeframe 5-15m (datos diarios, sin dirección, sesgada a un solo extremo).

---

## 0. Objetivo

Ocupar el hueco de la fila I (2 tarjetas de 6/12, u 3 de 4/12) con paneles **realmente accionables en 5-15 min**, que complementen a las filas J (continuación) y K (reversión/analítica) ya existentes.

---

## 1. Opción 1 — Ruptura Máximo / Mínimo del Día Anterior

### 1.1 Figura ASCII

```
┌──────────────────────────────────────────────┐
│ Ruptura máx/min de ayer · 15m                │
├──────────────────────────────────────────────┤
│ 🟢 AAPL ROMPE MAX    close 336.08 · máx 334.23 │
│ 🟢 ADSK ROMPE MAX    close 235.58 · máx 230.92 │
│ 🔴 ARM  ROMPE MIN    close 297.14 · mín 301.83 │
│ 🔴 ASML ROMPE MIN    close 1799.5 · mín 1821.1 │
│ 🟢 COST ROMPE MAX    close 940.83 · máx 936.89 │
│ vol ≥ 1x filtra rupturas débiles               │
└──────────────────────────────────────────────┘
 fila clic → velas 15m · verde=rompe máx · rojo=rompe mín
```

### 1.2 Utilidad

Es una **señal estructural de continuación**: los niveles del día anterior (máx/mín) son referencias objetivas que el mercado respeta. Romperlos con **volumen ≥ 1x** indica que el movimiento se está **confirmando**, no que es ruido.

### 1.3 Cómo se interpreta

| Dato | Lectura |
|---|---|
| **ROMPE MAX** (verde) | el precio supera el máximo de ayer → presión compradora → continuación alcista probable |
| **ROMPE MIN** (rojo) | el precio perfora el mínimo de ayer → presión vendedora → continuación bajista probable |
| **Sin ruptura** | el precio sigue dentro del rango de ayer → no aparece (no es setup) |
| **Volumen ≥ 1x** | filtro de calidad: romper sin volumen es señal débil |

### 1.4 Datos

`fact_market_bar_15m` (OHLC + `session_date`): se agrupa por sesión; `máx_ayer = max(high)`, `mín_ayer = min(low)`; se compara con el `close` actual. Volumen relativo de la última barra.

---

## 2. Opción 2 — Breadth intradía 15m (% sobre VWAP)

### 2.1 Figura ASCII

```
┌──────────────────────────────────────────────┐
│ Breadth 15m · 44% sobre VWAP                 │
│  [█████████████████ 44%]  sobre VWAP          │
│  [████████████████▓ 56%]  bajo VWAP           │
│                                              │
│  >60% = sesgo alcista · <40% = sesgo bajista │
│  40-60% = plano / transición                 │
└──────────────────────────────────────────────┘
```

### 2.2 Utilidad

Es un **gauge de condiciones de mercado** (breadth): qué porcentaje de las acciones está arriba de su **propio VWAP 15m**. Te dice **cuándo** operar (timing): si el mercado está ancho alcista, las señales largas de la fila J valen más; si está ancho bajista, prima la cautela o los cortos.

### 2.3 Cómo se interpreta

| Bre% | Lectura |
|---|---|
| **> 60%** | sesgo **alcista** → favorecer largos (J1/J2) y reversiones K en banda inferior |
| **< 40%** | sesgo **bajista** → favorecer cortos / esperar; cuidar los largos de la fila J |
| **40–60%** | **plano / transición** → settings aislados, no exposición direccional |

Hoy: **31/70 = 44%** → breadth **plano** (no apoyar una dirección fuerte).

### 2.4 Datos

`fact_market_bar_15m` (para el VWAP de cada símbolo) o `latest_market_tick` (del screener). Conteo: `% = (# símbolos con close > VWAP) / total`.

---

## 3. Opción 3 — Setups Multi-Indicador 15m

### 3.1 Figura ASCII

```
┌──────────────────────────────────────────────┐
│ Setups multi-indicador 15m · alertas          │
├──────────────────────────────────────────────┤
│ 🔴 ADSK SOBRECOMPRA FUERTE  RSI 70.4 · CCI 143│
│          BBPower 2.42 · vol 1.88x            │
│ 🟢 META SOBREVENTA FUERTE   RSI 30.8 · CCI -252│
│          BBPower -5.71 · vol 1.55x           │
│ 🟢 UNH  SOBREVENTA FUERTE   RSI 29.2 · CCI -282│
│          BBPower -7.89 · vol 4.00x           │
└──────────────────────────────────────────────┘
 lista corta · solo extremos donde varios osciladores coinciden
```

### 3.2 Utilidad

Detecta **reversiones extremas** donde RSI + CCI + BBPower **coinciden** en sobrecompra/sobreventa. Son señales **raras pero de alta calidad**: una lista corta de vigilancia que **confirma** los extremos de banda (K1).

### 3.3 Cómo se interpreta

| Tipo | Condición | Lectura |
|---|---|---|
| **SOBRECOMPRA FUERTE** | `RSI ≥ 69` + `CCI ≥ +120` + `BBPower ≥ +2` | extensión al alza real → posible corrección/pausa |
| **SOBREVENTA FUERTE** | `RSI ≤ 31` + `CCI ≤ −120` + `BBPower ≤ −2` | extensión a la baja real → posible rebote |
| **parcial (2/3)** | solo 2 osciladores | señal más débil; esperar confirmación |

### 3.4 Datos

`latest_market_tick` (`rsi_15`, `cci20_15`, `bbpower_15`) + volumen (barra 15m).

---

## 4. Cómo se comportan entre sí

Los tres **no son redundantes**: cada uno mide una capa distinta y, leídos juntos, forman un **circuito de decisión** para 5-15m:

```
 [2] Breadth (¿cuándo?)  →  [1] Ruptura (¿qué/séñal?)  →  [3] Multi-IND (¿confirmación?)
   condición de mercado       señal estructural              confirmación por osciladores
```

| Ángulo | Panel | Pregunta que responde |
|---|---|---|
| **Condición** | Breadth | ¿el mercado apoya largos, cortos o ninguno? |
| **Señal** | Ruptura máx/mín ayer | ¿hay una **estructura** rota con volumen? |
| **Confirmación** | Multi-indicador | ¿los osciladores confirman el extremo/giro? |

**Ejemplo de lectura combinada:**
- Breadth **>60%** + `XYZ` **ROMPE MAX** + **SOBREVENTA/alcista** en multi-ind → **alta convicción larga**.
- Breadth **<40%** + `XYZ` **ROMPE MIN** + **SOBRECOMPRA FUERTE** → **alta convicción corta**.
- Breadth **plano (44%)** → hay que **filtrar más**: la señal (1) sola no basta.

Además se relacionan con el resto del dashboard:
- La **ruptura (1)** complementa a la fila **J** (continuación estructural).
- El **multi-ind (3)** complementa a **K1** (bandas de Bollinger) y a **K3** (divergencia).
- El **breadth (2)** filtra el **timing** de ambas filas.

---

## 5. Ventajas

- **Timeframe coherente:** los tres usan datos **5-15 min**, a diferencia de los paneles I eliminados (diarios).
- **Accionables:** (1) es señal; (2) es condición; (3) es confirmación — los tres **afectan la decisión**.
- **Complementarios:** cubren "qué hacer" (señal), "cuándo" (condición) e "ir a favor" (confirmación).
- **Reutilizan la infraestructura:** `fact_market_bar_15m`, `latest_market_tick` y `screener_15m_service` ya existen.

---

## 6. Utilidad general (resumen)

| Panel | Tipo | Utilidad 5-15m | Complementa |
|---|---|---|---|
| **1. Ruptura máx/mín ayer** | señal | alta (estructura) | fila J |
| **2. Breadth 15m** | gauge | alta (condición/timing) | filas J y K |
| **3. Setups multi-indicador** | confirmación | media (extremos) | K1 / K3 |

**Binomio sugerido para la fila I (2 tarjetas 6/12):** **Ruptura (1) + Breadth (2)** — una señal y un gauge. Si se quiere una fila de 3 (4/12): **1 + 2 + 3**.

---

## 7. Resumen de decisión

| Aspecto | Decisión |
|---|---|
| Fila I anterior | ❌ Eliminada (I1 Anomalía de volumen · I2 Posición rango 52s) |
| Reemplazo propuesto | **Opción 1 Ruptura máx/mín** · **Opción 2 Breadth 15m** · **Opción 3 Multi-indicador** |
| Binomio recomendado | **1 + 2** (señal + condición) |
| Triple opcional | **1 + 2 + 3** (señal + condición + confirmación) |
| Endpoints (a definir) | `/partials/ruptura_ayer` · `/partials/breadth_15m` · `/partials/setups_multi_ind` |
| Configs (a definir) | `config/charts/R1_*.json` … (o código `I1`/`I2` liberados) |

> **Nota:** esta es la **propuesta** para la fila I; aún no se ha codificado. Se documenta aquí para fijar el plan antes de implementar.

---

*Documento generado 2026-10-08. Los valores numéricos son un snapshot (44% breadth; AAPL/ADSK/ARM/ASML/COST en ruptura; ADSK/META/UNH en extremos multi-ind) y cambian con el mercado.*
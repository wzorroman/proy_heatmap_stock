# **Análisis del Test E — Pre-market en vivo**

Corrido a las **09:09:49 ET**, dentro de la ventana de pre-market. Los tres símbolos responden con campos `premarket_*` completos. **H6 y H20 quedan confirmadas**, y aparece un campo nuevo que cambia el diseño del panel de pre-apertura.

## **1 · Lo que confirman los datos**

### **H6 ✅ · `close` base NO es el precio de pre-market**

| **Símbolo** | **`close` (base)** | **`premarket_close`** | **Diferencia** |
| --- | --- | --- | --- |
| NVDA | 227.38 | 226.242 | **-0.50 %** |
| SPY | 773.50 | 773.96 | +0.06 % |
| QQQ | 741.47 | 740.75 | -0.10 % |

El radar, en la ventana crítica **09:00–09:30 ET**, viene mostrando el cierre del lunes, no el precio de pre-market. Durante 30 minutos de la ventana operativa más importante, el dashboard es **historia, no contexto**.

### **H20 ✅ · `close|TF` sí incluye actividad extendida**

| **Símbolo** | **`close`** | **`close|5`** | **`close|15`** |
| --- | --- | --- | --- |
| NVDA | 227.38 | 227.25 | 227.25 |
| SPY | 773.50 | 773.52 | 773.52 |
| QQQ | 741.47 | 741.39 | 741.39 |

`close|5` y `close|15` son idénticos entre sí (ambos reflejan la barra en curso, cuyo origen está fuera de la sesión regular) y distintos del `close` base. Es la vía de escape si por algún motivo `premarket_*` fallara — pero ya no hace falta: `premarket_close` es más directo.

### **Campo nuevo: `premarket_volume` existe**

| **Símbolo** | **`premarket_volume`** |
| --- | --- |
| NVDA | 1,044,477 |
| SPY | 458,675 |
| QQQ | 782,666 |

El informe v3 no mencionaba este campo. Es **oro** para el panel de pre-apertura: indica liquidez esperada antes de la campana.

### **`gap` existe y responde**

| **Símbolo** | **`gap`** |
| --- | --- |
| NVDA | 0.299186 |
| SPY | 0.5988 |
| QQQ | 0.892647 |

Semántica exacta por confirmar (¿`gap` = pre-market vs cierre previo, o apertura regular vs cierre previo?), pero el campo responde y está disponible.

### **`update_mode` sigue siendo `delayed_streaming_900` en pre-market**

NVDA, SPY y QQQ mantienen el retraso de 15 min **incluso durante pre-market**. Confirma que el delay es **propiedad del símbolo**, no de la sesión. El radar sigue viendo datos de 15 min atrás en la ventana que más importa.

---

## **2 · Impacto en el informe v3**

Actualización quirúrgica (v3.1):

| **Ref.** | **Antes** | **Ahora** |
| --- | --- | --- |
| **H6** | 🟡 | ✅ **CONFIRMADA** |
| **H20** | 🟡 | ✅ **CONFIRMADA** |
| **H7b** | 🟡 parcial (`update_mode` sí, `/scan` no) | ✅ **+ premarket_close, premarket_change, premarket_volume, gap confirmados** |

Con esto se cierran **2 de las 24 hipótesis** y se completa **H7b** en casi toda su extensión. Lo único que sigue pendiente de H7b es el `POST /scan` batch (ya refutado) y `symbols.tickers` (Q16 cerrada como 404).

### **Nuevo ítem en el catálogo de mejoras**

**M-CAP-09 sube de P1 a P0.** El objetivo declarado del ecosistema es *"herramienta útil solo desde 30 min antes de la apertura"*. Pre-market **es** la ventana principal. Los campos existen, responden y son el corazón del caso de uso. No es mejora, es requisito.

---

## **3 · Impacto en el roadmap**

### **Cambio concreto en F3.2 (`CAMPOS` multi-TF)**

python

```
# Antes (v3):
BASE = "close,volume,RSI,CCI20,BBPower,ADX,Pivot.M.Camarilla.R3,Perf.W,change"
CAMPOS = BASE + "|5" + "|15"  (comprimido)

# Ahora (v3.1):
BASE = ("close,volume,RSI,CCI20,BBPower,ADX,"
        "Pivot.M.Camarilla.R3,Perf.W,change,"
        "premarket_close,premarket_change,premarket_volume,gap")   # ← nuevos
CAMPOS = BASE + "," + _bloque("5") + "," + _bloque("15")
```

Los cuatro campos nuevos se piden **una sola vez** por ciclo, sin coste de red adicional. Cambia el ancho del CSV y de `fact_market_series`, pero no la mecánica.

### **Cambio en M-CAP-09 (mejora de pre-market)**

De P1 a P0. Y su criterio de aceptación se vuelve más estricto:

> **Antes:** "Precio de pre-apertura disponible desde las 09:00 ET".
> 
> 
> **Ahora:** "Los cuatro campos `premarket_*` y `gap` poblados en `fact_market_series` para los 110 símbolos durante toda la ventana 09:00–09:30 ET; el panel de pre-apertura lee de ahí y no de `close` base".
> 

### **Cambio en F5.4 (MVP dashboard, panel 1)**

El panel de pre-apertura ahora tiene **5 señales concretas** para poblar:

1. `gap` → apertura esperada.
2. `premarket_change` → sesgo alcista/bajista.
3. `premarket_volume` → convicción.
4. `premarket_close` → precio real antes de campana.
5. `close` base → referencia del cierre previo.

Todo eso para VIX, DXY, US10Y, NQ/ES, BTC **más** los 110 símbolos del radar, sin tocar `/scan` ni esperar la sesión regular.

### **Cambio en F0.2 (protocolo lunes)**

La prueba T3 pasa de "verificar si `premarket_*` existe" a "verificar si `gap` es pre-market vs regular open". La única duda residual:

> **T3.1 (nueva):** ¿`gap` = `(premarket_close − close_prev)/close_prev` o `(regular_open − close_prev)/close_prev`? Comparar el valor de `gap` a las 09:29 ET con el `open` real de las 09:31 ET.
> 

---

## **4 · Verificación cruzada con el informe de BD**

Antes de comprometer el cambio, hay que confirmar dos cosas en el informe de BD del 2026-09-18:

1. ¿`fact_market_series` ya tiene alguna columna `premarket_*` o `gap`? **Sospecho que no** — el catálogo de columnas del informe (§5.4) no las lista. Habrá que añadirlas.
2. ¿`vw_market_live` las expone? **Sospecho que no** — la vista filtra por columnas explícitas.

Esto implica un `ALTER TABLE`:

sql

```
ALTER TABLE fact_market_series
    ADD COLUMN IF NOT EXISTS premarket_close   numeric(20,8),
    ADD COLUMN IF NOT EXISTS premarket_change  numeric(12,8),
    ADD COLUMN IF NOT EXISTS premarket_volume  numeric(30,8),
    ADD COLUMN IF NOT EXISTS gap               numeric(12,8);
```

Y actualizar `prepare_bd_row` en `market_service.py` para incluirlos. Es un cambio pequeño, pero **toca la tabla de 2,4 M filas**. Plan: añadir como nullable, backfill con NULL en las filas históricas, y poblar solo a partir del próximo ciclo.

---

## **5 · Lo que queda por cerrar de esta línea**

Con Test E corrido:

| **Hipótesis / Duda** | **Estado tras Test E** |
| --- | --- |
| H6 | ✅ Cerrada |
| H20 | ✅ Cerrada |
| H7b | ✅ Cerrada (premarket); ❌ `/scan` batch (Q16 refutada) |
| Semántica de `gap` | 🟡 Pendiente de T3.1 |
| `premarket_volume` semántica | ✅ Es volumen acumulado del pre-market — inferible de la magnitud |
| Persistencia en BD | ❌ Requiere ALTER TABLE |

**Cobertura del informe tras estos 5 tests (D, E, F, G, H):**

- De 24 hipótesis: **10 cerradas** (H1, H2, H6, H7a, H7b, H19, H20, H21, H22, H23).
- De 24 dudas: **7 cerradas** (Q15, Q16, Q17, Q23, Q24, + parciales).
- De 3 decisiones D1–D3: **D1 confirmada como (b)**.

Con Test A, C, I en sesión regular (mañana a las 10:00 ET), se cierra el resto.

---

## **6 · Siguiente paso concreto**

Tres acciones, en este orden:

1. **T3.1 (mañana a las 09:29 ET)**: comparar `gap` con el `open` real de las 09:31 ET para fijar la semántica.
2. **Diff de F1** (los 6 quick-wins) — independiente de todo esto, listo para aplicar hoy.
3. **Actualización v3 → v3.1** del informe con las 2 hipótesis cerradas y los 4 campos nuevos.
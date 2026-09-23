# Roadmap Integral de Mejoras — Ecosistema `heatmap_stock`

> **Objetivo del ecosistema:** herramienta de apoyo a decisiones de trading en **timeframe de 15 min**, útil **solo desde 30 min antes de la apertura de NYSE/Nasdaq hasta el cierre** (09:00–16:00 ET).
> **Fecha:** 2026-09-19 · **Versión del documento:** 1.0 (borrador de trabajo)
> **Alcance:** BD `heatmap_stock` (PostgreSQL 17.10, timestamps en UTC) · radar (`proy_scrapping_detail`) · heatmap (`proy_heatmap`) · calendario económico · dashboard v2 (`proy_dashboard`, planificado).
> **Naturaleza:** consolida dudas, hipótesis, incongruencias, hallazgos y mejoras surgidas de la revisión de documentación y código. No describe cambios ya aplicados.

---

## Tabla de contenidos

0. [Cómo leer este documento](#0-cómo-leer-este-documento)
1. [Material revisado y límites de certeza](#1-material-revisado-y-límites-de-certeza)
2. [Resumen ejecutivo](#2-resumen-ejecutivo)
3. [Ventana operativa y modelo de tiempo](#3-ventana-operativa-y-modelo-de-tiempo)
4. [Registro de hipótesis](#4-registro-de-hipótesis)
5. [Registro de incongruencias](#5-registro-de-incongruencias)
6. [Dudas abiertas](#6-dudas-abiertas)
7. [Decisiones pendientes](#7-decisiones-pendientes)
8. [Hallazgos y mejoras por proyecto](#8-hallazgos-y-mejoras-por-proyecto)
9. [Plan por fases](#9-plan-por-fases)
10. [Riesgos y mitigaciones](#10-riesgos-y-mitigaciones)
11. [Criterios de aceptación globales](#11-criterios-de-aceptación-globales)
12. [Anexos](#12-anexos)
13. [Changelog](#13-changelog)

---

## 0. Cómo leer este documento

### 0.1 Convenciones de identificadores

| Prefijo | Significado |
|---|---|
| **H*n*** | Hipótesis (afirmación plausible aún no verificada del todo) |
| **I*n*** | Incongruencia (dos fuentes que se contradicen, o código vs. documentación) |
| **Q*n*** | Duda abierta (falta un dato o una respuesta) |
| **D*n*** | Decisión pendiente (requiere elegir entre opciones) |
| **BD-*nn*** | Mejora en la base de datos |
| **RAD-*nn*** | Mejora en el scraper del radar (`scraper_live_tradingview_v5.py`, `CONFIG_ACTIVOS`) |
| **HM-*nn*** | Mejora en el scraper del heatmap (`scrapper_heatmap_v1.py`) y su app |
| **CAL-*nn*** | Mejora en el calendario económico (`calendario_tradingview_live_v5.py`) |
| **DSH-*nn*** | Mejora en el dashboard v2 |
| **VAL-*nn*** | Validación estadística / calidad de datos |
| **OPS-*nn*** | Operación (cron, monitoreo, seguridad) |
| **DOC-*nn*** | Documentación |

### 0.2 Estado de la evidencia

| Marca | Significado |
|---|---|
| ✅ | **Confirmado**: hay evidencia directa en código, esquema o datos |
| 🟡 | **Probable**: hay evidencia indirecta; falta una comprobación puntual |
| 🔴 | **Por verificar**: se apoya en memoria o inferencia; sin evidencia en los archivos revisados |

### 0.3 Prioridad y esfuerzo

| Prioridad | Criterio |
|---|---|
| **P0** | Bloquea que la herramienta sea confiable para operar en 15 min |
| **P1** | Alto impacto en calidad de decisión o en robustez |
| **P2** | Mejora relevante, no bloqueante |
| **P3** | Limpieza, deuda menor |

| Esfuerzo | Estimación orientativa |
|---|---|
| **S** | < 0,5 día |
| **M** | 1–2 días |
| **L** | ≥ 3 días |

---

## 1. Material revisado y límites de certeza

### 1.1 Revisado

| Tipo | Archivo |
|---|---|
| Documentación | `bd_heatmap_informe_2026-09-18.md` (informe técnico de la BD) |
| Documentación | `dashboard_radar_v2_Roadmap.md` (plan del dashboard v2) |
| Documentación | `heatmap_stock_endpoint_scanner.md` (endpoint `/scan`, script v3) |
| Documentación | `heatmap_stock_documentacion_campos.md` (campos del heatmap; **obsoleta**, ver I1) |
| Documentación | `heatmap_stock_roadmap_migracion_a_1-0-2.md` (esquema v1.0.2) |
| Documentación | `scrapper_Roadmap_migracion_a_3-1-0.md` (radar y calendario a BD) |
| Código | `scraper_live_tradingview_v5.py` (radar) |
| Código | `scrapper_heatmap_v1.py` (heatmap) |
| Código | `calendario_tradingview_live_v5.py` (calendario) |
| Configuración | `CONFIG_ACTIVOS`, `METADATOS_ACTIVOS`, `CATEGORIA_DEFAULT` |

### 1.2 No revisado (los hallazgos sobre estas piezas son hipótesis)

| Pieza | Por qué importa |
|---|---|
| `application/market_service.py`, `db/market_repository.py` | Cómo se prepara y escribe cada fila del radar |
| `application/event_service.py`, `db/event_repository.py` | Solo se vio el **pseudocódigo** del roadmap 3.1.0; el código real puede diferir (H10) |
| `config.py` (`HEATMAP_BODY`, `HEATMAP_MAX_SYMBOLS`, `DB_WRITE_ENABLED`) | Orden real de columnas del heatmap y tope de símbolos |
| `db/partitions.py`, `create_partitions.py` | Zona horaria de los límites de partición (H11) |
| Crontab real y zona horaria del servidor | Horarios de ejecución (Q6) |
| App Streamlit de `proy_heatmap` | Coexistencia con el dashboard (D9) |
| Datos vivos de la BD (solo se vio el informe del 2026-09-18) | Todas las verificaciones SQL del Anexo A |

---

## 2. Resumen ejecutivo

### 2.1 Diez hallazgos que condicionan el diseño

| # | Hallazgo | Ref. |
|---|---|---|
| 1 | **Latencia acumulada:** feed del heatmap retrasado 15 min (confirmado), feed del radar probablemente igual (no medido), ciclo de captura de ~2–2,5 min y flush a BD solo al final del ciclo. | H1, H8, RAD-02 |
| 2 | **Indicadores del radar probablemente de timeframe diario** (`CAMPOS` sin sufijo) y **`volume` acumulado del día**: no sirven tal cual para decisiones de 15 min. | H2, H3, BD-04 |
| 3 | **No existe la unidad de trabajo de 15 min** (barras OHLCV) ni un **calendario de sesiones** (feriados, cierres anticipados). | BD-03, BD-04 |
| 4 | **Captura 24 h** (lun–jue) atada al cron en hora local; ninguna pieza conoce la ventana de mercado. El horario de verano de EE. UU. termina el **1-nov-2026**. | H4, RAD-01, OPS-01 |
| 5 | **Radar secuencial y en orden alfabético:** los símbolos macro (OANDA, SAXO, TVC) se capturan ~2 min después que SPY; el circuit breaker aborta todo lo que sigue. | RAD-02, RAD-04 |
| 6 | **Falta un mapeo lógico → físico** (VIX, DXY…). VIX primario es un **futuro**; "DXY" es un **ETF** (`UUP`) o un futuro, no el índice. | RAD-07, D2, D3 |
| 7 | **Universo del heatmap contaminado** (459 de 1.005 símbolos OTC, 127 preferentes) y **universo del radar sesgado a tecnología**, sin ETF sectoriales ni ES1!. | HM-02, RAD-06 |
| 8 | **Escala de importancia probablemente −1/0/1**: los 45 eventos con importancia 1 serían los de alto impacto y la "deuda D8" no sería un gap. | H5, CAL-04 |
| 9 | **Documentación de campos obsoleta** (índices `d[]` del layout antiguo) y etiquetas erróneas en el informe de la BD. | I1, I2, DOC-01 |
| 10 | **El score no está validado** y se calibraría con ~20 sesiones de equity: riesgo alto de sobreajuste. | H13, VAL-02, DSH-04 |

### 2.2 Camino crítico

```
Fase 0 (verificar + decidir)
   └─► Fase 1 (tiempo y sesión: UTC, dim_trading_session, gates)
          └─► Fase 2 (captura fiable: POST único, filtros, calendario por eventos)
                 └─► Fase 3 (modelo 15 min: barras, latest tick, snapshots enriquecidos)
                        └─► Fase 4 (MVP dashboard: pre-apertura + 15 min + eventos)
                               └─► Fase 5 (validación estadística + score)
                                      └─► Fase 6 (calidad, seguridad, retención)
```

### 2.3 Hitos con fecha

| Fecha límite | Hito | Motivo |
|---|---|---|
| **Antes del 2026-10-01** | Verificar contigüidad de particiones (Anexo A5) | El cambio de mes de `fact_market_series` y `fact_heatmap_snapshot` depende de límites coherentes |
| **Antes del 2026-11-01** | Gate de ventana por calendario NYSE en `America/New_York` | Fin del horario de verano de EE. UU.: la ventana se desplaza 1 h respecto a UTC y a un cron en hora de Lima |
| **Antes del 2026-12-31** | Crear particiones 2027 (hoy existen hasta `2026_12`) | Sin partición, el insert falla (`no partition of relation found`, ya visto en `audit_sync_run`) |
| **Antes del 2027-03-14** | Revalidar el gate con el inicio del horario de verano | Segundo domingo de marzo |

---

## 3. Ventana operativa y modelo de tiempo

### 3.1 Hechos

- La BD guarda `timestamptz` (internamente UTC). Los `-05:00` del informe son la zona de la sesión SQL (`America/Lima`), no un desfase de los datos.
- Lima es UTC−5 todo el año. Nueva York es UTC−4 (EDT) hasta el **1-nov-2026** y UTC−5 (EST) después.
- El evento *Fed Interest Rate Decision* aparece a las `13:00-05` (= 18:00 UTC = 14:00 ET), que es la hora real de un anuncio del FOMC: evidencia de que el UTC del calendario es correcto (H15).

### 3.2 Fases de la ventana

| Fase | ET | UTC (hasta 1-nov) | UTC (desde 1-nov) | Lima (hasta 1-nov) | Lectura |
|---|---|---|---|---|---|
| Pre-apertura | 09:00–09:30 | 13:00–13:30 | 14:00–14:30 | 08:00–08:30 | Plan del día: gap, futuros, VIX, eventos publicados a las 08:30 ET |
| Apertura | 09:30–10:30 | 13:30–14:30 | 14:30–15:30 | 08:30–09:30 | Máxima volatilidad; el retraso del feed pesa más |
| Media sesión | 10:30–14:00 | 14:30–18:00 | 15:30–19:00 | 09:30–13:00 | Menor volumen; señales más ruidosas |
| Tarde / FOMC | 14:00–15:00 | 18:00–19:00 | 19:00–20:00 | 13:00–14:00 | Posible catalizador |
| Cierre | 15:00–16:00 | 19:00–20:00 | 20:00–21:00 | 14:00–15:00 | Volumen alto, flujos de cierre |

> Los cierres anticipados (13:00 ET) y los feriados los debe resolver `dim_trading_session` (BD-03), no una tabla fija de horas.

### 3.3 Ventanas de captura recomendadas

| Proceso | Ventana (ET) | Motivo |
|---|---|---|
| Radar y heatmap | 09:00–16:00 | Es el rango en que el dashboard está activo |
| Calendario | **08:00**–16:00 | Los datos de las 08:30 ET (CPI, NFP, empleo semanal) salen 30 min **antes** de que abra el dashboard y deben estar cargados con su sorpresa a las 09:00 |
| Fuera de ventana | — | Sin captura densa; solo un cierre previo y el rango nocturno de futuros si se opera ES/NQ (Q3) |

### 3.4 Consecuencias de diseño

1. Las horas de sesión **nunca** se fijan en UTC ni en un cron de hora local: se calculan desde el calendario NYSE en `America/New_York`.
2. Dentro de la sesión regular, la fecha UTC coincide con la fecha ET (el cierre cae a las 20:00 o 21:00 UTC), por lo que `timestamp_utc::date` es válido para agrupar la sesión.
3. Los indicadores de 15 min necesitan **calentamiento**: RSI14, ADX14, CCI20 y SMA50 requieren barras de la(s) sesión(es) previa(s). Se calculan sobre barras de sesión regular encadenadas entre días; el VWAP se reinicia a las 09:30 ET.

---

## 4. Registro de hipótesis

> Cada hipótesis indica su evidencia, su estado, la verificación concreta (los códigos **A*n*** remiten a consultas del [Anexo A](#anexo-a--consultas-de-verificación)) y qué cambia según el resultado.

| ID | Hipótesis | Evidencia | Estado | Verificación | Impacto según resultado |
|---|---|---|---|---|---|
| **H1** | El feed del **radar** también va retrasado ~15 min (`delayed_streaming_900`). | Confirmado para el heatmap (`/scan`, columna `update_mode`, `stream_status` en BD). El radar usa `/symbol` anónimo y **no pide** `update_mode`. NVDA: 219,47 (radar 14:24:52) vs 219,405 (heatmap 14:23:36), casi idénticos → misma fuente probable. | 🟡 | Añadir `update_mode` a `CAMPOS`; comparar contra una fuente en tiempo real durante la apertura. | **Si cierta:** toda señal llega con una barra de retraso; la decisión de entrada no debe depender de este feed (Q1, D1). **Si falsa:** el retraso se limita al heatmap. |
| **H2** | Los indicadores del radar (`RSI`, `ADX`, `CCI20`, `BBPower`, `Pivot.M.Camarilla.R3`) son de **timeframe diario**. | `CAMPOS` no incluye sufijo de timeframe; `Perf.W` es semanal; nombres coinciden con las columnas del scanner, cuyo valor por defecto es diario. | 🟡 | Pedir `RSI` y `RSI\|15` en la misma llamada y comparar; observar cuánto varía el RSI dentro de una sesión. | **Si cierta:** el "score de 15 min" solo suaviza una señal diaria; hay que pedir variantes de 15 min o calcularlas (D4). |
| **H3** | `volume` es el **volumen acumulado del día**, no el del intervalo. | NVDA: 73,65 M (14:23:36) → 73,85 M (14:24:52): +192 k en 76 s; el doc del endpoint lo describe como "volumen actual"; promedio 10 d ≈ 102 M. | 🟡 | A2 (crece de forma monótona y se reinicia cada sesión). | **Si cierta:** `volume / vol_avg_2d` del dashboard es inválido; usar volumen relativo por hora del día (DSH-07) y deltas para barras (BD-04). |
| **H4** | La mayoría de los ticks de acciones fuera de sesión son **repeticiones** del último precio. | 52.800 ticks/día ÷ 110 = **480 ticks/activo/día** = captura 24 h; cron lun–jue 24 h + viernes hasta 16:59 (roadmap 3.1.0 §15.4). Una acción tiene ~130 ticks de sesión regular. | 🟡 | A1 (`count(DISTINCT close)` por hora ET). | **Si cierta:** RSI/ADX/rolling de volumen se contaminan; filtrar por sesión (RAD-10) y apagar captura densa fuera de ventana (RAD-01). |
| **H5** | La escala de `importance` de TradingView es **−1 / 0 / 1** (baja / media / alta), no −1..3. | El *Fed Interest Rate Decision* aparece con importancia 1; distribución 392 / 142 / 45 (pirámide típica); jamás aparece 2 ó 3 en 579 eventos. La escala −1..3 figura en los docs como decisión de diseño, sin fuente. | 🟡 | A3 (importancia de NFP, CPI, FOMC) e inspección de `raw_payload`. | **Si cierta:** D8 no es un gap; los 45 eventos con importancia 1 son los de alto impacto; hay que corregir comentarios de esquema y etiquetas (CAL-04, DOC-02). |
| **H6** | Fuera de la sesión regular, el campo `close` de acciones es el **cierre regular previo** (no el precio de pre-market). | `CAMPOS` pide `close` sin columnas de pre-market. | 🔴 | Entre 09:00 y 09:30 ET comparar `close` de NVDA en `/symbol` con `premarket_close` vía `/scan`. | **Si cierta:** en la primera media hora las acciones no se mueven en el radar; el panel de pre-apertura debe apoyarse en NQ1!/ES1!, VX1!, FX, BTC y columnas de pre-market (HM-06). |
| **H7** | El scanner soporta: sufijo de timeframe (`RSI\|15`), `premarket_change`, `premarket_close`, `gap`, `relative_volume_10d_calc`, `VWAP`, `ATR`, `description`, `update_mode` en `/symbol`, y `symbols.tickers` en el POST de `/scan`. | Solo memoria; ningún archivo revisado lo demuestra. | 🔴 | Llamadas de prueba con cada columna (Fase 0). | **Si cierta:** habilita RAD-02, RAD-03 y HM-06. **Si falsa:** calcular todo desde barras propias. |
| **H8** | El ciclo del radar dura **~1,7–2,4 min** y puede saltarse ciclos cuando se acumulan 429 (el lock hace salir al cron siguiente sin registrar nada). | Pausa aleatoria 0,4–1,2 s × 109 ≈ 87 s + latencia de 110 GET; backoff 429 hasta 180 s por símbolo; en el informe VIX (14:23:01) y NVDA (14:24:52) difieren ~1 min 50 s. | 🟡 | A6 (distribución de huecos entre ticks) y A7 (retraso de ingesta por símbolo). | **Si cierta:** los ticks de un mismo ciclo no son simultáneos y la cadencia real no está garantizada; agrupar por ciclo y pasar al POST único (RAD-02). |
| **H9** | Los cierres exactos `VIX = 15,00` y `US10Y = 5,00` del informe son **redondeos, estancamiento de feed o ejemplos ilustrativos**. | Valores redondos improbables para un rendimiento con 3–4 decimales. | 🔴 | A8 (proporción de cierres enteros y de valores distintos). | Si son artefactos, el termómetro de riesgo (percentil 60 d) usaría datos defectuosos. |
| **H10** | Los eventos del calendario capturados **en vivo** quedan con `captured_at` nulo. | `capturar_eventos` pasa `eventos_raw` a `process_calendar_batch`; `timestamp_captura` solo se agrega en `evento_a_dict` (ruta del CSV). El pseudocódigo hace `parse_iso(evento.get('timestamp_captura'))` → `None`. | 🔴 | A4 y lectura de `event_repository.py` real. | Sin `captured_at` no se puede medir la latencia de publicación del `actual` (H12). |
| **H11** | Los límites de partición mezclan **UTC y hora local del servidor**. | El informe dice "fronteras en hora local (America/Lima)"; `scrapper_heatmap_v1.py` calcula `first_day` en UTC. | 🔴 | A5 (`pg_get_expr(relpartbound)`). | Solapes o huecos al cambiar de mes; el error `no partition ... found` ya apareció en la auditoría. |
| **H12** | El `actual` de un evento llega a la BD **hasta 15 min tarde** (cron cada 15 min) más la latencia propia de TradingView. | Cadencia `*/15` del calendario; el upsert actualiza `last_updated_at` en cada corrida, lo que impide medirlo hoy. | 🟡 | Tras CAL-02, comparar `last_updated_at − event_timestamp`. | Justifica el polling por minuto alrededor de eventos de alto impacto (CAL-01). |
| **H13** | (**Hipótesis nula**) El score 0–10 **no tiene poder predictivo** sobre retornos a 15–60 min. | Sin evidencia; calibración prevista con ~20 sesiones de equity (desde 2026-08-22) y observaciones muy autocorrelacionadas. | 🔴 | VAL-02 (forward-return, walk-forward, con retraso del feed aplicado). | **Si no se rechaza:** el score se presenta solo como contexto, sin zonas COMPRAR/VENDER (D10). |
| **H14** | Los eventos de alto impacto producen **reacción medible** en QQQ, SPY, US10Y y oro entre +3 y +30 min. | 45 eventos con importancia 1 en 18 días; número con `actual` y `forecast` sin conocer (A9). Muestra pequeña. | 🔴 | VAL-03 (estudio de eventos sobre ticks de 3 min). | Si se confirma, justifica `fact_event_reaction` y el panel de reacción (BD-09, DSH-09). |
| **H15** | El UTC de los datos **cargados** (backfill) es correcto. | Radar: el CSV guarda epoch UTC y la carga usa `fromtimestamp(..., timezone.utc)` ✅. Heatmap: `datetime.now(timezone.utc)` ✅. Calendario: ISO con `Z`; el FOMC a las 14:00 ET lo confirma. Falta comprobar la carga histórica del calendario y de snapshots. | ✅ radar · 🟡 resto | A10 (concentración de closes distintos entre 13:00 y 21:00 UTC). | Si hay una segunda concentración desplazada 5 h, hay datos duplicados o mal etiquetados. |
| **H16** | El "momentum equity" es un **indicador sesgado a tecnología**. | De ~70 acciones: 11 semiconductores, 9 SaaS, 7 hardware, 7 gigantes (34) + MSTR y MARA. Sin ETF sectoriales (solo XLE y VGT). | ✅ (por conteo de config) | — | No representa el mercado amplio; requiere ETF sectoriales y amplitud del heatmap (RAD-06, DSH-08). |
| **H17** | Cadencia de 3 min basta para **barras de 15 min** (≈5 ticks por barra). | Cadencia nominal; pero H8 sugiere ciclos irregulares. | 🟡 | Distribución de `n_ticks` por barra tras BD-04. | Barras con < 3 ticks deben marcarse como de baja calidad. |
| **H18** | Los **endpoints no oficiales** de TradingView pueden cambiar sin aviso. | Precedentes en los docs: `Content-Type` incorrecto devolvía `d[]` vacío; el payload completo daba error 400; `sectorTranslated` desapareció. | ✅ (riesgo estructural) | Monitoreo de esquema (OPS-02). | Requiere validación de forma en cada respuesta y alertas de cambio. |

---

## 5. Registro de incongruencias

| ID | Fuente A dice… | Fuente B dice… | Riesgo | Resolución propuesta |
|---|---|---|---|---|
| **I1** | `heatmap_stock_documentacion_campos.md`: `d[3]` = cambio diario, `d[15]` = market cap, `d[25]` = precio (captura antigua de **502** símbolos). | Endpoint v3, `parse_vector` y el `raw_vector` de la BD: `d[1]` = cambio, `d[3]` = `Perf.1M`, `d[11]` = market cap, `d[23]` = precio (universo de **19.738** símbolos, se guardan ~1.000). | Alto: quien lea el vector con los índices viejos tomaría `Perf.1M` como cambio diario. | DOC-01: archivar el doc viejo y generar la tabla desde `HEATMAP_BODY["columns"]` (Anexo D). |
| **I2** | Informe de la BD §9.4: posiciones rotuladas "cambio5m?" y "volumen_relativo". | Layout v3: `d[2]` = `change_abs` y `d[24]` = `pricescale` (100). | Medio | DOC-02: corregir rótulos. |
| **I3** | Roadmap del dashboard §7.8: NVDA con RSI 65,4 y "ya pasó R3 +0,9%"; §7.5 muestra NFP/CPI/GDP con sorpresas; §7.3 muestra `DXY xx.xx`. | BD real: NVDA RSI 51,83 y R3 = 230,03 **por encima** del cierre (219,47); no hay evidencia de esos eventos en BD; el DXY no existe como índice. | Bajo–medio: los ejemplos parecen datos reales y no lo son. | DSH-11: marcar los ejemplos como ilustrativos o reemplazarlos por datos reales. |
| **I4** | `dim_asset` se declara **SCD Tipo 2** (`valid_from`, `valid_to`, `current_version`). | `symbol` es `UNIQUE` global (`dim_asset_symbol_key`): no puede existir una segunda versión del mismo símbolo. | Medio: el versionado prometido es imposible; las vistas filtran `current_version` sin necesidad. | BD-06 / D7: pasar a Tipo 1 o cambiar la unicidad a `UNIQUE (symbol) WHERE current_version`. |
| **I5** | Roadmap 1.0.2: **sin FK físicas** de los hechos hacia `dim_asset` (FK lógica). | Roadmap del dashboard: `fact_market_score ... REFERENCES dim_asset(asset_id)` (FK física); informe §10.1: "opcional añadir FK". | Bajo: convención inconsistente y coste distinto en upserts. | BD-08: fijar una convención y aplicarla igual a todos los hechos. |
| **I6** | Docs (esquema, roadmaps, informe): importancia **−1..3**, con "−1 = sin dato". | Datos: solo −1/0/1; el FOMC tiene 1; el 67 % de eventos con −1 sería "baja", no "sin dato" (H5). | Alto: filtros, etiquetas y la "deuda D8" están mal planteados. | CAL-04 y DOC-02 tras verificar H5. |
| **I7** | Docstring del radar: "Redundancia dinámica: **fallback automático** entre primarios y respaldos". | El código recorre **todos** los símbolos (primario y respaldo) sin lógica de fallback. | Medio: quien consuma datos debe decidir cuál usar; hoy no hay mapeo. | RAD-07: mapeo canónico lógico → físico; corregir el docstring (RAD-11). |
| **I8** | `dim_asset.company_name` documentado como nombre de la empresa. | `parse_vector` asigna `company_name = d[25]` = **ticker** (la columna `name`). | Bajo | HM-05: pedir la columna `description`. |
| **I9** | `dim_asset.sector_es`: "traducción pendiente". | El endpoint **ya no** devuelve `sectorTranslated` (docs del endpoint §4.2); nunca se poblará desde la fuente. | Bajo | HM-05: diccionario local de ~20 sectores. |
| **I10** | Informe §4: particiones con fronteras en **hora local** del servidor. | Decisión vigente: estandarizar todo en **UTC**; `scrapper_heatmap_v1.py` crea particiones con límites UTC. | Medio (H11) | BD-01 y BD-02: límites UTC explícitos y verificación de contigüidad. |
| **I11** | Roadmap del dashboard: fases "Sesión Madura (14:00–16:00 UTC)" y gráfico "[09:30–14:25 UTC]". | La sesión regular NYSE es 13:30–20:00 UTC (EDT) o 14:30–21:00 UTC (EST). | Medio | DSH-06: `session_service` en `America/New_York`. |
| **I12** | Roadmap del dashboard D7: crear `vw_heatmap_event_impact_relaxed` (sin filtro de moneda) para resolver la vista vacía. | El propio documento admite que "seguirá vacía" sin snapshots frecuentes; además el cruce snapshot × evento por ventana ±6 h relaciona los 1.000 activos con cada evento, lo que no mide impacto. | Medio: el remedio no resuelve el problema. | BD-09: sustituir por `fact_event_reaction`. |
| **I13** | Nomenclatura y versionado: `calendario_tradingview_live_v5.py` declara `Version: 3.1.0` y su `argparse` dice "Captura Raw V4"; el radar menciona `DATOS_LIVE_2` pero usa `DATOS_LIVE`; el heatmap se autodenomina `scrapper_heatmap.py`; `.env` usa `BD_HEATMAP_SERVER` y `config.py` lee `BD_HEATMAP_HOST`; roadmaps citan PostgreSQL 15+ y la BD es 17.10. | — | Bajo: confunde auditorías y despliegues. | DOC-03. |
| **I14** | Roadmap 1.0.2 muestra `CONFIG_ACTIVOS` con claves numéricas, `indicadores` y `primario: CBOE:VIX`, `EURUSD` con `OANDA` primario. | Config real: claves con nombre (`"VIX"`), sin `indicadores`, VIX primario `CBOE:VX1!`, EURUSD primario `FX_IDC:EURUSD`. | Bajo: el ejemplo del doc no es el volcado real. | DOC-03: regenerar el ejemplo desde `config/radar_activos.json`. |
| **I15** | Informe: `sync_checkpoint.calendario.last_timestamp = 2026-09-18 20:15:28-05`; rango de eventos hasta `2026-09-18 12:00-05`; último tick del radar `14:24:52-05`. | El significado de `last_timestamp` es ambiguo: el pseudocódigo lo define como `run_start`; el checkpoint JSON local usa la **fecha máxima de evento**. | Bajo | CAL-11: unificar la semántica. |
| **I16** | Conteos de activos: 1.060 (2026-09-13), 1.083 (2026-09-18); 1.005 símbolos en el CSV semilla; 1.000 por ventana de snapshot. | — | Bajo: es evolución lógica, pero no está documentada como tal. | DOC-02: indicar la fecha de cada conteo. |

---

## 6. Dudas abiertas

| ID | Duda | Por qué importa | Cómo resolverla |
|---|---|---|---|
| **Q1** | ¿Hay acceso a una **fuente en tiempo real** (API de broker o de datos de mercado) para 5–10 símbolos críticos (SPY, QQQ, VIX, NQ/ES, US10Y)? | Decide si la entrada se apoya solo en TradingView o en un diseño de dos niveles (D1). | Decisión del usuario. |
| **Q2** | ¿Se opera solo con **acciones y ETF de EE. UU.** o también futuros (ES/NQ) y forex? | Define si se apaga la captura fuera de ventana o se conserva el rango nocturno. | Decisión del usuario. |
| **Q3** | ¿Qué **decisión concreta** debe apoyar el dashboard (entrada/salida en QQQ/SPY, selección de acciones, filtro de eventos) y con qué horizonte? | Determina qué paneles entran en el MVP. | Decisión del usuario. |
| **Q4** | ¿El cambio a UTC se aplicó solo a datos nuevos o también al **histórico** (2,4 M de filas y 579 eventos)? | Evitar duplicados desplazados 5 h en indicadores y backtests. | A10; revisar los scripts `load_*_csv_to_db.py`. |
| **Q5** | ¿Cómo está el **crontab real** (horarios, `TZ`, quién ejecuta `scrapper_heatmap_v1.py`)? | Solo hay 3 snapshots: el heatmap parece manual. | `crontab -l` y `echo $TZ`. |
| **Q6** | ¿Qué símbolos devuelven campos nulos o rezagados (`CBOE`, `ICEUS`, `SAXO`, `CME_MINI`)? | Exchanges con datos de pago pueden devolver `null` o retraso mayor. | Tasa de nulos por símbolo (Anexo A11). |
| **Q7** | ¿Existen ticks del radar **posteriores a las 14:25 (Lima)** del 2026-09-18? | El cron declara viernes hasta 16:59; `last_timestamp` del calendario es posterior al último tick visto. | `SELECT max(timestamp_utc)` por día. |
| **Q8** | ¿Cuántos eventos con importancia 1 tienen `actual` **y** `forecast` (sorpresa computable)? | Tamaño de muestra de VAL-03 y del panel de sorpresas. | A9. |
| **Q9** | ¿`event_repository.py` real puebla `captured_at` en eventos en vivo? | Medir la latencia del `actual` (H10, H12). | Leer el código y A4. |
| **Q10** | ¿Cuánto histórico de ticks de 3 min se conserva? (~500 MB/mes en `fact_market_series`; ~1 GB/mes en snapshots solo en ventana, ~5 GB/mes si es 24 h). | Retención y costo de almacenamiento. | Decisión de retención (D8). |
| **Q11** | ¿Se mantiene el **Streamlit** de `proy_heatmap` junto al dashboard v2? | Evita duplicar paneles y lógica. | Decisión (D9). |
| **Q12** | ¿El dashboard se expondrá fuera de `localhost` (puerto 8100)? | Autenticación y rol de solo lectura. | Decisión de despliegue. |
| **Q13** | ¿Es aceptable depender de endpoints **no oficiales** de TradingView para una herramienta de trading? Conviene revisar sus términos de uso y definir un plan B (H18). | Riesgo operativo y legal de la fuente única. | Revisión propia; definir fuente alternativa. |
| **Q14** | ¿`fact_market_series.raw_payload` (hoy 100 % nulo) debe reactivarse? | Costo estimado ~366 MB/mes (roadmap 3.1.0 §15.4) frente a reproducibilidad. | Decisión (D8). |

---

## 7. Decisiones pendientes

| ID | Decisión | Opciones | Recomendación | Depende de |
|---|---|---|---|---|
| **D1** | Fuente de datos para la **decisión de entrada** | (a) Solo TradingView anónimo · (b) TradingView para contexto + fuente en tiempo real para 5–10 símbolos | **(b)** si H1 se confirma: contexto tolera 15 min de retraso; la entrada no | Q1, H1 |
| **D2** | Fuente canónica de **VIX** | `TVC:VIX` (spot) · `CBOE:VX1!` (futuro del mes, con roll) | **Ambas con roles distintos:** spot para nivel y percentil; futuro para pre-apertura | Q6 |
| **D3** | Fuente canónica de **DXY** | `TVC:DXY` (índice, validar disponibilidad) · `ICEUS:DX1!` (futuro) · `AMEX:UUP` (ETF, solo sesión regular) | Índice o futuro para pre-apertura; `UUP` solo como respaldo en sesión | H7 |
| **D4** | **Indicadores de 15 min** | (a) Pedirlos a TradingView (`\|15`) · (b) calcularlos desde barras propias | **Guardar ambos** en Fase 3 y decidir tras comparar (las barras propias se muestrean cada 3 min: sus H/L subestiman los extremos reales) | H2, H7 |
| **D5** | **Cadencia del heatmap** | 5 · 15 min | 15 min alineado al cierre de barra (:00, :15, :30, :45 + unos segundos) más un snapshot de pre-apertura | HM-01 |
| **D6** | **Universo del heatmap** | Top-N por market cap con filtro de liquidez | NASDAQ/NYSE/AMEX, acciones comunes, volumen en USD ≥ 20 M, N entre 600 y 800 | HM-02 |
| **D7** | `dim_asset`: **SCD2 real o Tipo 1** | Tipo 1 (quitar columnas de versión) · SCD2 con unicidad parcial | Tipo 1 si no hay necesidad real de historial de atributos | I4 |
| **D8** | **Retención** de ticks y `raw_payload` | Conservar 3 min todo · agregar a barras 15 min tras N meses | Conservar ticks 6 meses y barras de 15 min indefinidamente; `raw_payload` solo si hace falta reproducir | Q10, Q14 |
| **D9** | **Streamlit** existente | Coexistir · absorber en el dashboard v2 | Reutilizar los endpoints `/api/*` y retirar paneles duplicados | Q11 |
| **D10** | Presentación del **score** | Zonas COMPRAR/VENDER · solo contexto (valor + percentil + fase) | **Solo contexto** hasta rechazar H13 | VAL-02 |
| **D11** | Librería de **calendario de sesiones** | `exchange_calendars` · `pandas_market_calendars` | `exchange_calendars` (XNYS) | BD-03 |

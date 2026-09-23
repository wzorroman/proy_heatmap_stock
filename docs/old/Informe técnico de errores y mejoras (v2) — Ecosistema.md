# Informe técnico de errores y mejoras (v2) — Ecosistema heatmap_stock

**Objetivo del ecosistema:** herramienta de apoyo a decisiones de trading en **timeframe de 15 min**, útil **solo desde 30 min antes de la apertura de NYSE/Nasdaq hasta el cierre** (09:00–16:00 ET).
**Fecha del informe:** 2026-09-20 (domingo) · **Versión:** 1.0
**Alcance:** BD `heatmap_stock` (PostgreSQL 17.10, `timestamptz` en UTC) · radar (`scraper_live_tradingview_v5.py`) · heatmap (`scrapper_heatmap_v1.py`) · calendario (`calendario_tradingview_live_v5.py`) · dashboard v2 (planificado).
**Este informe sustituye y corrige** el borrador `Roadmap_Integral_de_Mejoras___Ecosistema.md` (incompleto) e incorpora el diagnóstico de campos del 2026-09-19 y los dos `config.py`. Las rectificaciones respecto a esos documentos están en el [Anexo F](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21).

## Tabla de contenidos

1. [Convenciones](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
2. [Alcance, método y límites](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
3. [Resumen ejecutivo](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
4. [Modelo de tiempo y ventana operativa](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
5. [Hechos técnicos verificados](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
6. [Catálogo de errores y defectos](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
7. [Catálogo de mejoras](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
8. [Incongruencias entre fuentes](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
9. [Hipótesis y estado de la evidencia](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
10. [Dudas abiertas y decisiones pendientes](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
11. [Plan por fases e hitos](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
12. [Trazabilidad hipótesis → decisión → error → mejora](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
13. [Riesgos](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
14. [Criterios de aceptación y KPIs](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21)
15. [Anexos](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21) (incluye [Anexo G · Evaluación de la segunda revisión externa](https://app.notion.com/p/Informe-t-cnico-de-errores-y-mejoras-v2-Ecosistema-heatmap_stock-3e3ccf9f614d80bf9d68e666656c451d?pvs=21), v1.1)

---

## 1. Convenciones

### 1.1 Identificadores

| Prefijo | Significado |
| --- | --- |
| **E-*CMP*-*nn*** | Error o defecto (CMP = `RAD` radar · `HM` heatmap · `CAL` calendario · `BD` base de datos · `OPS` operación · `DSH` dashboard · `DOC` documentación) |
| **M-*EJE*-*nn*** | Mejora (EJE = `CAP` captura · `DAT` modelo de datos · `VAL` validación · `DSH` dashboard · `OPS` operación · `DOC` documentación) |
| **I*n*** | Incongruencia entre dos fuentes |
| **H*n*** | Hipótesis |
| **Q*n*** / **D*n*** | Duda abierta / decisión pendiente |
| **A*n*** / **B.*n*** | Consulta SQL del Anexo A / fragmento de código del Anexo B |

### 1.2 Severidad de los errores

| Sev. | Criterio |
| --- | --- |
| **S1 · Crítico** | Invalida las decisiones de 15 min o hace perder/corromper datos sin aviso |
| **S2 · Alto** | Degrada de forma material la calidad de la señal o la robustez |
| **S3 · Medio** | Ineficiencia, deuda técnica o riesgo acotado |
| **S4 · Bajo** | Limpieza o cosmética |

### 1.3 Evidencia, prioridad y esfuerzo

| Marca | Evidencia |
| --- | --- |
| ✅ | **Confirmada** por código, esquema, datos o prueba ejecutada |
| 🟡 | **Probable**: evidencia indirecta; falta una comprobación puntual |
| 🔴 | **Por verificar**: se apoya en inferencia o memoria |

| Prioridad | Significado | Esfuerzo | Estimación |
| --- | --- | --- | --- |
| **P0** | Imprescindible antes de operar con la herramienta | **S** | < 0,5 día |
| **P1** | Alto valor o alto riesgo | **M** | 1–2 días |
| **P2** | Relevante, no bloqueante | **L** | ≥ 3 días |
| **P3** | Deuda o limpieza |  |  |

---

## 2. Alcance, método y límites

### 2.1 Material analizado

| Tipo | Archivo |
| --- | --- |
| Código | `scraper_live_tradingview_v5.py` (radar), `scrapper_heatmap_v1.py`, `calendario_tradingview_live_v5.py` |
| Configuración | `config.py` del radar (`VERSION 3.1.0`: `CONFIG_ACTIVOS`, `METADATOS_ACTIVOS`) y `config.py` del heatmap (`VERSION 1.0.2`: `HEATMAP_COLUMNS`, `HEATMAP_BODY`) |
| Datos y pruebas | `bd_heatmap_informe_2026-09-18.md` (estado de la BD) y `diagnostico_scrapper_v5_al_2026-09-19.md` (prueba `wztest_scraper_timeframes.py`, sábado 05:30 UTC) |
| Documentación | `dashboard_radar_v2_Roadmap.md`, `scrapper_Roadmap_migracion_a_3-1-0.md`, `heatmap_stock_roadmap_migracion_a_1-0-2.md`, `heatmap_stock_endpoint_scanner.md`, `heatmap_stock_documentacion_campos.md` |

### 2.2 No revisado (los hallazgos sobre estas piezas son hipótesis)

| Pieza | Consecuencia |
| --- | --- |
| `application/market_service.py`, `db/market_repository.py`, `application/event_service.py`, `db/event_repository.py` | Del lado de eventos solo se vio el **pseudocódigo** del roadmap 3.1.0; el código real puede diferir (H10) |
| `db/postgresql_connection.py` (`PostgreSQLConnector`) | No se sabe si `execute_query` hace commit en cada llamada (afecta E-HM-04) |
| `create_partitions.py` y `db/partitions.py` | Zona horaria de los límites de partición (H11) |
| Crontab real, `TZ` del servidor, logs de ejecución | Horarios y duración real de ciclos (Q5) |
| App Streamlit de `proy_heatmap` | Coexistencia con el dashboard (D9) |
| Datos vivos de la BD posteriores al informe del 2026-09-18 | Todas las verificaciones del Anexo A |

### 2.3 Método

Cada hallazgo se apoya en una de tres fuentes, indicada en su campo *Evidencia*: (a) lectura directa del código o del esquema, (b) resultado de la prueba de campos del 2026-09-19, (c) aritmética o inferencia a partir de los anteriores. Las inferencias se marcan 🟡/🔴 y llevan una verificación concreta.

---

## 3. Resumen ejecutivo

### 3.1 Veredicto

El ecosistema está bien construido como **canal de captura hacia la BD**: upserts idempotentes, lock de instancia, backoff ante 429, circuit breaker, CSV de respaldo, particionado mensual, checksum y auditoría, y escritura en UTC. **Como herramienta de decisión a 15 min, todavía no es utilizable**, por cinco brechas estructurales:

1. **Latencia no medida y probablemente alta:** el feed del heatmap va con 15 min de retraso (confirmado), el del radar probablemente también (sin verificar) y el radar no registra ni `update_mode` ni la hora del dato.
2. **Indicadores de timeframe equivocado:** los campos capturados son de la vela base (probablemente diaria), no de 15 min.
3. **Falta la unidad de trabajo:** no hay barras de 15 min ni calendario de sesiones.
4. **Captura sin conciencia de sesión:** 24 h, con cron en hora local, sin feriados ni horario de verano.
5. **Semántica de activos sin resolver:** no hay mapeo lógico → físico (VIX, DXY…), el universo del radar sesga a tecnología y el del heatmap incluye OTC y preferentes.

### 3.2 Marcador

| Componente | S1 | S2 | S3 | S4 | Total |
| --- | --- | --- | --- | --- | --- |
| Radar (`E-RAD`) | 2 | 5 | 3 | 1 | **11** |
| Heatmap (`E-HM`) | 0 | 4 | 9 | 2 | **15** |
| Calendario (`E-CAL`) | 0 | 3 | 2 | 0 | **5** |
| Base de datos (`E-BD`) | 1 | 3 | 3 | 1 | **8** |
| Operación (`E-OPS`) | 0 | 2 | 2 | 0 | **4** |
| Dashboard (`E-DSH`) | 0 | 3 | 2 | 1 | **6** |
| Documentación (`E-DOC`) | 0 | 1 | 1 | 0 | **2** |
| **Total** | **3** | **21** | **22** | **5** | **51** |

Además: **54 mejoras** (§7), **16 incongruencias** (§8) y **24 hipótesis** (§9). Revisión 1.1 (§16, Anexo G): +3 errores (E-HM-15, E-HM-16, E-HM-17), 1 reclasificado (E-HM-04: S2 → S3) y 4 dudas nuevas (Q18–Q21) tras una segunda pasada de revisión sobre código que no forma parte del material analizado en §2.1.

### 3.3 Los diez hallazgos que más pesan

| # | Hallazgo | Ref. |
| --- | --- | --- |
| 1 | Los indicadores del radar **no son de 15 min** (RSI base 64,25 frente a `RSI|15` 53,06 en AAPL). | E-RAD-01, H2 |
| 2 | El **retraso del feed** del radar no es observable: no se pide `update_mode` y `timestamp_utc` es la hora de la petición. | E-RAD-02, H1 |
| 3 | No existen **barras de 15 min** ni **calendario de sesiones**. | E-BD-01 |
| 4 | Un **ciclo secuencial** de ~2 min con 110 GET hace que los ticks no sean simultáneos y que la cadencia no esté garantizada. | E-RAD-03, H8 |
| 5 | **Pérdida silenciosa** de datos en BD: el flush traga excepciones, `DB_WRITE_ENABLED` es `false` por defecto y no hay auditoría por ciclo. | E-RAD-05 |
| 6 | **Sin gate de sesión:** captura 24 h y cron en hora de Lima (el horario de verano de EE. UU. termina el 1-nov-2026). | E-OPS-01 |
| 7 | **Universo del heatmap contaminado** (459 de 1.005 símbolos OTC, 127 preferentes). | E-HM-01 |
| 8 | **Escala de importancia** probablemente −1/0/1: los 45 eventos con importancia 1 serían los de alto impacto. | E-BD-03, H5 |
| 9 | El **score** no está validado y se calibraría con ~20 sesiones de equity. | E-DSH-01, H13 |
| 10 | **Credenciales y superusuario:** `postgres`/`postgres` en `.env` y reproducidas en el informe de la BD. | E-OPS-02 |

### 3.4 Cadena de latencia de extremo a extremo

```
Mercado
  │  hasta 15 min si update_mode = delayed_streaming_900   (confirmado en heatmap; H1 en radar)
  ▼
Feed de TradingView
  │  GET /symbol × 110, secuencial, pausa 0,4–1,2 s        (~1,8–2,4 min por ciclo; E-RAD-03)
  ▼
timestamp_utc = hora de la PETICIÓN (no la del dato)       (E-RAD-02)
  │
  ▼
CSV por símbolo  ──►  buffer en memoria
  │  flush ÚNICO a BD al terminar el ciclo                 (+0…2,4 min respecto al primer símbolo)
  ▼
fact_market_series  ──►  dashboard (refresh)

Antigüedad del dato ≈ 15 min (si H1) + 0–2,4 min (ciclo) + intervalo de refresco
```

### 3.5 Fortalezas que hay que preservar

- Escritura en **UTC** en los tres scrapers (epoch → `fromtimestamp(..., timezone.utc)`, `datetime.now(timezone.utc)`, ISO con `Z`).
- **Idempotencia** por PK `(asset_id, timestamp_utc)` y `ON CONFLICT`.
- **Lock** `fcntl` que evita ejecuciones solapadas del radar.
- **CSV como respaldo** y rotación de 7 días con histórico mensual.
- **Auditoría** (`audit_sync_run`, `sync_checkpoint`) y **checksums** SHA-256.
- **Particionado** mensual con índices adecuados para lecturas por activo y tiempo.

### 3.6 Decisiones que desbloquean el resto

| Decisión | Por qué desbloquea | Ref. |
| --- | --- | --- |
| ¿Hay una fuente en tiempo real para 5–10 símbolos críticos? | Define si la entrada depende de TradingView anónimo | Q1, D1 |
| ¿Qué instrumentos se operan (solo acciones/ETF de EE. UU. o también futuros y FX)? | Define captura fuera de ventana y universo | Q2 |
| ¿Qué decisión concreta debe apoyar el dashboard? | Define el MVP | Q3 |
| Fuente canónica de VIX y DXY | Define el mapeo lógico → físico y el score de riesgo | D2, D3 |

---

## 4. Modelo de tiempo y ventana operativa

### 4.1 Hechos

- La BD almacena `timestamptz` (internamente UTC). Los `05:00` del informe son la zona de la **sesión SQL** (`America/Lima`), no un desfase de los datos.
- Lima es UTC−5 todo el año. Nueva York es UTC−4 (EDT) hasta el **domingo 1-nov-2026** y UTC−5 (EST) después; vuelve a EDT el **14-mar-2027**.
- El *Fed Interest Rate Decision* figura a las `13:00-05` (= 18:00 UTC = 14:00 ET), la hora real de un anuncio del FOMC: confirma que el UTC del calendario es correcto.
- Dentro de la sesión regular, la fecha UTC coincide con la fecha ET (el cierre cae a las 20:00 o 21:00 UTC), de modo que `timestamp_utc::date` sirve para agrupar la sesión.

### 4.2 Fases de la ventana

| Fase | ET | UTC (hasta 1-nov) | UTC (desde 1-nov) | Lima (hasta 1-nov) | Lectura |
| --- | --- | --- | --- | --- | --- |
| Pre-apertura | 09:00–09:30 | 13:00–13:30 | 14:00–14:30 | 08:00–08:30 | Plan del día: gap, futuros, VIX, eventos de las 08:30 ET |
| Apertura | 09:30–10:30 | 13:30–14:30 | 14:30–15:30 | 08:30–09:30 | Máxima volatilidad; el retraso del feed pesa más |
| Media sesión | 10:30–14:00 | 14:30–18:00 | 15:30–19:00 | 09:30–13:00 | Menor volumen, señales más ruidosas |
| Tarde / FOMC | 14:00–15:00 | 18:00–19:00 | 19:00–20:00 | 13:00–14:00 | Posible catalizador |
| Cierre | 15:00–16:00 | 19:00–20:00 | 20:00–21:00 | 14:00–15:00 | Volumen alto, flujos de cierre |

Desde el 1-nov, Lima y Nueva York coinciden (09:00 ET = 09:00 Lima).

### 4.3 Ventanas de captura recomendadas

| Proceso | Ventana (ET) | Motivo |
| --- | --- | --- |
| Radar y heatmap | 09:00–16:00 | Es el rango en que el dashboard está activo |
| Calendario | **08:00**–16:00 | Los datos de las 08:30 ET (CPI, NFP, empleo semanal) salen **antes** de que abra el dashboard y deben estar cargados con su sorpresa a las 09:00 |
| Fuera de ventana | — | Solo un cierre previo; conservar el rango nocturno de futuros solo si se operan ES/NQ (Q2) |

### 4.4 Consecuencias de diseño

1. Las horas de sesión **nunca** se fijan en UTC ni en un cron de hora local: se derivan del calendario NYSE en `America/New_York` (→ M-DAT-01, M-CAP-01).
2. Los indicadores de 15 min necesitan **calentamiento**: RSI14, ADX14, CCI20 y SMA50 requieren barras de sesiones previas. Se calculan sobre barras de sesión regular encadenadas entre días; el VWAP se reinicia a las 09:30 ET.
3. Para los `|TF` de TradingView rige la regla de **cierre de barra** (H21, M-CAP-03): el valor definitivo de `RSI|15` solo existe tras el cierre de la vela.

---

## 5. Hechos técnicos verificados

### 5.1 Endpoints y frecuencias

| Proceso | Endpoint | Método | Cadencia declarada | Notas |
| --- | --- | --- | --- | --- |
| Radar | `scanner.tradingview.com/symbol` | GET, 1 símbolo por petición | Cron cada 3 min | 110 símbolos (primarios + respaldos únicos); sin `update_mode` |
| Heatmap | `scanner.tradingview.com/america/scan?label-product=heatmap-stock` | POST, ~19.738 símbolos por respuesta | Manual (3 snapshots en BD) | `update_mode = delayed_streaming_900`; se conservan los 1.000 de mayor capitalización |
| Calendario | `economic-calendar.tradingview.com/events` | GET, ventana `now−1 d … now+2 d`, 11 países | Cron cada 15 min | Sin filtro de importancia |

### 5.2 Prueba de campos del 2026-09-19 (`wztest_scraper_timeframes.py`)

Sábado 05:30 UTC, sobre `BINANCE:BTCUSDT` (abierto 24/7), `NASDAQ:AAPL` y `FX:EURUSD` (cerrados).

| Resultado | Evidencia | Estado |
| --- | --- | --- |
| Los sufijos `|5`, `|15`, `|30`, `|60` funcionan en `/symbol` | Valores distintos y coherentes en los tres símbolos | ✅ |
| Los valores base **no coinciden** con los de 5/15/30/60 min | AAPL: RSI 64,25 frente a 44,71 / 53,06 / 54,93 / 56,79 | ✅ |
| `Perf.W|TF` devuelve `None` | Los tres símbolos, todos los TF | ✅ |
| `|1D` devuelve `None` en todos los campos | Los tres símbolos | ✅ |
| `Pivot.M.Camarilla.R3|TF` **no** devuelve `None`: valores distintos del base y agrupados en pares (`|5 = |15`, `|30 = |60`) | BTC 82.287 / 78.051 · AAPL 339,33 / 339,47 · EURUSD 1,14877 / 1,16212 (base: 83.862 · 322,8 · 1,1675) | ✅ (dato) · 🟡 (interpretación) |
| `volume` base = acumulado del día | AAPL 86,6 M con mercado cerrado (total del viernes); BTC sube 2379 → 2382 en 50 s | ✅ |
| `close|TF` **no** es siempre igual a `close` | AAPL: 336,13 (base) frente a 335,58 (`|5…|60`); BTC y EURUSD sí coinciden | ✅ (dato) / 🟡 (causa) |
| `volume|5 = volume|15 = volume|30 = 2,318` en BTC a las 05:30 (las tres velas acaban de abrir) | Sugiere vela **en formación** | 🟡 |
| `change|5 = change|15 = change|30` en BTC | Sugiere cambio **dentro de la vela** y no un retorno móvil | 🟡 |
| El endpoint refresca en 10–20 s **en BTC** | Muestras idénticas en t=0 y t=10 s, distinta en t=20 s | ✅ para BTC · 🔴 para acciones |
| AAPL y EURUSD congelados durante 50 s | Mercado cerrado (fin de semana) | ✅ |

### 5.3 Semántica de los campos

| Campo | Sin sufijo (base) | Con sufijo `|TF` | Uso correcto |
| --- | --- | --- | --- |
| `close` | Último precio; en acciones probablemente el **cierre regular** (H20) | Último precio, posiblemente con operaciones fuera de sesión (H20) | Serie de precios; muestrear también `close|5` en pre-apertura |
| `volume` | **Acumulado del día**; se reinicia con la sesión (00:00 UTC en cripto) | Volumen de la vela actual o última (H19) | Base: diferenciar entre ticks. `|TF`: solo con regla de cierre de barra |
| `RSI`, `CCI20`, `BBPower`, `ADX` | Timeframe base, distinto de 5/15/30/60 (probablemente **1D**) | Calculado sobre la vela en formación (H21) | Base: contexto de régimen. `|15`: señal, solo al cierre de barra |
| `Pivot.M.Camarilla.R3` | Nivel de **rango amplio** (probablemente mensual), no diario (H22) | Devuelve valores propios, **agrupados por pares**: `|5 = |15` y `|30 = |60` en los tres símbolos; compatible con pivotes diarios (5–15 min) y semanales (30–60 min) (H22) | Base: nivel estático de contexto. `|15`: candidato a **pivote diario** para 15 min (validar en T6) |
| `Perf.W` | Rendimiento semanal | No existe (`None`) | Contexto; sin sufijo |
| `change` | % de cambio diario | % de la vela (H19) | Base: régimen del día |

### 5.4 Ciclo del radar (aritmética del código)

- **Símbolos por ciclo:** 110 (primarios y respaldos únicos de `CONFIG_ACTIVOS`), ordenados con `sorted()`, es decir **alfabéticamente por prefijo**: `AMEX → BINANCE → BITSTAMP → CBOE → CBOT → CME → CME_MINI → FX_IDC → ICEUS → NASDAQ → NYMEX → NYSE → OANDA → SAXO → TVC`.
- **Tiempo por símbolo:** pausa `uniform(0.4, 1.2)` s (media 0,8 s, 109 veces ≈ 87 s) + latencia de la petición (0,2–0,5 s) + escritura y rotación del CSV.
- **Duración del ciclo:** ≈ 110–145 s, o sea **1,8–2,4 min**, dentro de una cadencia nominal de 3 min.
- **Corroboración (🟡):** `sync_checkpoint.radar_v4.last_timestamp = 14:20:54-05` y el tick de `TVC:VIX` (último en el orden) a las `14:23:01-05` suman 127 s. El tick de NVDA a las `14:24:52-05` pertenece al ciclo siguiente (NASDAQ queda hacia la posición 45 de 110, unos 58 s después de un inicio de ciclo ≈ 14:23:54).
- **Peor caso por símbolo:** 429 con backoff de 15 + 45 + 120 = 180 s. Tres fallos consecutivos, cada uno con 20 s de pausa, abortan el ciclo (`sys.exit(1)`).
- **Solapes:** si un ciclo supera 3 min, el cron siguiente adquiere el lock, falla (`LOCK_NB`) y sale con código 0 y solo un `warning` en el log.

### 5.5 Volumetría observada y proyectada

| Concepto | Cifra | Base |
| --- | --- | --- |
| Ticks del radar por día | **52.800** (24 h) frente a ~**15.400** dentro de la ventana | 110 activos × 480 ticks (24 h) frente a × 140 (7 h a 3 min) |
| Tamaño de `fact_market_series` | ≈ 316 B/fila → 16,7 MB/día (24 h) frente a ~4,9 MB/día en ventana | 668.437 filas y 211 MB en la partición de septiembre |
| Tamaño de `fact_heatmap_snapshot` | ≈ 1,8 kB/fila (5.456 kB / 3.000 filas) | Incluye el índice GIN sobre `raw_vector` |
| Snapshots del heatmap en ventana (15 min) | 28/día × 1.000 filas ≈ 51 MB/día ≈ **1,1 GB/mes** | 22 sesiones |
| Snapshots del heatmap 24 h (15 min) | 96/día ≈ 173 MB/día ≈ **5,2 GB/mes** | 30 días |

### 5.6 Estado de la BD relevante para este informe

- 110 activos con serie del radar: **70 equity** (desde 2026-08-22) y 40 de otras clases (ETF, futuros, FX, cripto, yields, commodities; desde marzo de 2026).
- `dim_asset`: 1.083 activos; `fact_economic_event`: 579 eventos (2026-08-31 → 2026-09-18).
- `audit_sync_run`: **12 filas** en total (`radar_v4`: 2) → no hay auditoría por ciclo del radar.
- Particiones creadas hasta `2026_12` en `fact_market_series` y `fact_heatmap_snapshot`.
- El asset 1011 (radar "VIX") tiene `volume = null`, coherente con un índice (`TVC:VIX`), no con el futuro `CBOE:VX1!`.

---

## 6. Catálogo de errores y defectos

> Formato de cada ficha: **severidad · evidencia · esfuerzo** → *Hallazgo*, *Evidencia*, *Impacto*, *Corrección* (con el ID de la mejora en §7) y *Aceptación*. Las severidades S3 y S4 se resumen en una tabla (§6.3).
> 

### 6.1 Críticos (S1)

#### E-RAD-01 · Indicadores capturados en el timeframe base (probablemente 1D) para un uso de 15 min

**S1 · ✅ · Esfuerzo M** — Objeto: `CAMPOS` en `scraper_live_tradingview_v5.py`; columnas `rsi`, `cci20`, `bbpower`, `adx`, `pivot_camarilla_r3`, `perf_w`, `change_pct` de `fact_market_series`.

- **Hallazgo.** `CAMPOS = "close,volume,RSI,CCI20,BBPower,ADX,Pivot.M.Camarilla.R3,Perf.W,change"` no lleva sufijo de timeframe.
- **Evidencia.** Prueba del 2026-09-19 (AAPL): `RSI` 64,25 frente a `RSI|15` 53,06; `CCI20` 118,9 frente a 94,99; `ADX` 16,53 frente a 18,89. En BTC, `ADX` y `Pivot.M.Camarilla.R3` base no cambian en 50 s con el precio en movimiento (mientras `RSI`, `CCI20`, `Perf.W` y `change` sí).
- **Impacto.** Cualquier "score de 15 min" construido con estas columnas mide régimen diario. `Perf.W` es semanal. Solo `close` (y `volume` tras diferenciarlo) sirven como señal de 15 min; el resto es contexto válido (régimen y niveles), y el histórico ya capturado se puede reempaquetar (M-VAL-05).
- **Corrección.** M-CAP-03 (`CAMPOS` multi-TF sin `Perf.W|TF` ni `|1D`, que devuelven `None`; `close|TF` se decide tras T3; `Pivot.M.Camarilla.R3|15` se incluye para validarlo como pivote diario en T6; regla de cierre de barra) + M-DAT-03 (formato largo).
- **Aceptación.** `fact_market_indicator_tf` contiene `tf = '15'` para los 110 símbolos en ventana; el dashboard etiqueta siempre `1D` frente a `15m`.

#### E-RAD-02 · El retraso del feed no es observable

**S1 · 🟡 · Esfuerzo S** — Objeto: `fetch_from_scanner()`.

- **Hallazgo.** La petición no incluye `update_mode` y `timestamp_utc` se fija con `datetime.now(timezone.utc)` en el momento de la petición.
- **Evidencia.** El heatmap sí devuelve `delayed_streaming_900` (15 min). NVDA aparece a 219,47 en el radar (14:24:52) y a 219,405 en el heatmap (14:23:36): misma fuente probable. La prueba del 2026-09-19 no pidió `update_mode` y usó BTC (Binance, tiempo real) y dos mercados cerrados.
- **Impacto.** Si H1 es cierta, toda barra construida desde `timestamp_utc` está desplazada hasta 15 min, los backtests tienen look-ahead y el dashboard presentaría precios de hace 15 min como actuales.
- **Corrección.** M-CAP-04 (`update_mode`, `feed_delay_s`, `cycle_id`, `fetched_at`), M-DSH-02 (banner *as-of*), protocolo T1–T2 (Anexo C) y decisión D1.
- **Aceptación.** Cada tick lleva `update_mode`; el dashboard muestra `as_of = timestamp − feed_delay`.

#### E-BD-01 · No existen barras de 15 min ni calendario de sesiones

**S1 · ✅ · Esfuerzo M** — Objeto: esquema (`fact_market_series`, `dim_time`).

- **Hallazgo.** Solo hay ticks de ~3 min con `close` (sin OHLC). No hay tabla de sesiones ni de feriados (E-BD-06).
- **Evidencia.** Esquema del informe; `vw_market_live` devuelve el último tick.
- **Impacto.** SMA20/50 con `AVG() OVER` sobre ticks equivalen a 1 h y 2,5 h, no a 5 h y 12,5 h de barras de 15 min. Sin sesión no se filtran ticks fuera de horario ni se tratan cierres anticipados.
- **Corrección.** M-DAT-01 (`dim_trading_session`) y M-DAT-02 (`fact_market_bar_15m`, con la salvedad de que H/L muestreados cada 3 min subestiman los extremos reales).
- **Aceptación.** 28 barras por día y activo; ≥ 95 % con `n_ticks ≥ 3`.

### 6.2 Altos (S2)

#### E-RAD-03 · Ciclo secuencial lento, sesgo temporal y cadencia no garantizada

**S2 · 🟡 · Esfuerzo M** — Objeto: bucle principal de `main()`.

- **Hallazgo.** 110 `GET` secuenciales con pausa aleatoria (0,4–1,2 s), CSV por símbolo y un único flush a BD al final.
- **Evidencia.** §5.4: ciclo de 1,8–2,4 min; checkpoint 14:20:54 y tick de `TVC:VIX` a las 14:23:01.
- **Impacto.** Los símbolos de OANDA, SAXO y TVC se capturan ~2 min después que AMEX (SPY); las comparaciones entre activos no son simultáneas. Los 429 alargan el ciclo por encima de 3 min y el lock hace que el cron siguiente salga sin dejar rastro. La BD recibe los datos hasta 2,4 min tarde.
- **Corrección.** M-CAP-02 (`POST` único a `/scan` con `symbols.tickers`; validar Q16), M-CAP-04 (`cycle_id`) y agrupar por ciclo.
- **Aceptación.** p95 de duración del ciclo ≤ 15 s; un único timestamp por ciclo; 0 ciclos saltados sin registro.

#### E-RAD-04 · Circuit breaker abortivo con orden alfabético

**S2 · ✅ · Esfuerzo S** — Objeto: `MAX_FALLOS_CONSECUTIVOS`, `sys.exit(1)`.

- **Hallazgo.** Tres fallos consecutivos provocan flush parcial y `sys.exit(1)`. Con `sorted()`, el bloque de futuros (`CBOT`, `CME`, `CME_MINI`, `ICEUS`) se procesa antes que `NASDAQ`, `NYSE`, `OANDA` y `TVC`.
- **Evidencia.** Código; cada fallo suma además `PAUSA_ENFRIAMIENTO_ERROR = 20` s.
- **Impacto.** Un fallo de bloque (por ejemplo, exchanges con datos de pago devolviendo `null`; Q6) deja sin captura a acciones, FX, VIX y US10Y en ese ciclo, tras perder ≥ 60 s. `exit(1)` no deja auditoría.
- **Corrección.** M-CAP-05 (prioridad: SPY, QQQ, VIX, US10Y, DXY, NQ1! primero; breaker por exchange).
- **Aceptación.** Simulando el fallo de un bloque, el resto se captura y el fallo queda auditado.

#### E-RAD-05 · Pérdida silenciosa de datos en BD

**S2 · ✅ · Esfuerzo M** — Objeto: `flush_radar_batch()`, `config.DB_WRITE_ENABLED`, `load_dotenv(override=True)`.

- **Hallazgo.** El silencio ante un fallo de BD es de **tres capas**, no de una: (a) `flush_radar_batch` envuelve la llamada a `process_radar_batch` en un `try/except` que captura toda excepción y devuelve `0`; (b) en `main()`, tanto en el flush de fin de ciclo como en el flush parcial del circuit breaker, el valor de retorno de `flush_radar_batch` **no se lee ni se comprueba** — solo se llama `flush_radar_batch(batch_buffer)` seguido, sin condición, de `batch_buffer.clear()`; (c) `DB_WRITE_ENABLED` vale `false` por defecto y `.env` sobrescribe variables de entorno reales (`load_dotenv(override=True)`), así que sin `.env` el radar corre en modo CSV sin ningún error. Además, `audit_sync_run` tiene solo 2 filas de `radar_v4` y no hay job de reconciliación CSV → BD.
- **Evidencia.** (a) y (b) están confirmadas directamente en `scraper_live_tradingview_v5.py`: ni el flush de cierre de ciclo ni el del circuit breaker capturan el entero devuelto por `flush_radar_batch`, así que aunque la capa (a) devolviera cuántas filas fallaron, esa información no se usaría para decidir si limpiar el buffer. Esto es verificable sin ver `application/market_service.py`. Queda pendiente de confirmar si `process_radar_batch` (dentro de ese módulo, no revisado) también captura sus propias excepciones internamente, lo que añadiría una cuarta capa de silencio antes de llegar al `try/except` de `flush_radar_batch` — de ser así, ese `try/except` sería en la práctica código muerto para fallos de BD, aunque seguiría siendo necesario como red de seguridad ante fallos no previstos por el service (por ejemplo, un error de `import`).
- **Impacto.** Huecos invisibles en BD, sin distinción entre "no hubo fallo" y "el fallo se descartó" (el CSV conserva el dato, pero nada compara ambas fuentes); indicadores y barras con huecos; el dashboard mostraría "sin datos" sin causa identificable.
- **Corrección.** M-CAP-06 (reintento con backoff, modo estricto en producción, reconciliación nocturna) y M-OPS-01 (auditoría por ciclo); `override=False`.
- **Aceptación.** Con la BD caída 10 min, tras reiniciarla no queda ningún hueco en 24 h.

#### E-RAD-06 · Sin mapeo lógico → físico; proxies en VIX, DXY, OIL y PLATA

**S2 · ✅ · Esfuerzo M** — Objeto: `CONFIG_ACTIVOS`, `METADATOS_ACTIVOS`.

- **Hallazgo.** `todos_simbolos` mezcla primario y respaldo sin lógica de fallback. `METADATOS_ACTIVOS` usa claves lógicas (VIX, DXY, TLT, US10Y, ORO, OIL) y la BD guarda símbolos físicos.
- **Evidencia.** VIX = `CBOE:VX1!` (futuro del mes, con roll) / `TVC:VIX`. DXY = `AMEX:UUP` (ETF, solo sesión regular) / `ICEUS:DX1!`; el índice no está. OIL = `AMEX:USO` (ETF sujeto a contango) / `NYMEX:CL1!`. PLATA = `AMEX:SLV` / `TVC:SILVER`. BTC = `BINANCE:BTCUSDT` / `BITSTAMP:BTCUSD`.
- **Impacto.** El score depende de qué `asset_id` se use; los percentiles de VIX mezclarían spot y futuro.
- **Corrección.** M-CAP-07 (`logical_key`, `is_canonical`, `role` en `dim_asset`) y decisiones D2/D3.
- **Aceptación.** Cada clave de `METADATOS_ACTIVOS` resuelve a exactamente un `asset_id` canónico.

#### E-RAD-07 · Universo sesgado a tecnología y con vacíos

**S2 · ✅ · Esfuerzo S** — Objeto: `CONFIG_ACTIVOS`.

- **Hallazgo.** De ~70 acciones, unas 34 son tecnología (11 semiconductores, 9 SaaS, 7 hardware, 7 gigantes), más MSTR y MARA. De los ETF sectoriales solo están XLE y VGT. No hay `ES1!`, IWM ni RSP.
- **Impacto.** El "momentum equity" es en la práctica momentum tecnológico; no hay rotación sectorial ni amplitud; la pre-apertura no tiene futuro del S&P.
- **Corrección.** M-CAP-08 (añadir `CME_MINI:ES1!`, XLK, XLF, XLV, XLY, XLP, XLI, XLU, XLRE, XLB, XLC, IWM, RSP; validar `TVC:DXY`). Ver Anexo E.
- **Aceptación.** Los 13 símbolos nuevos se capturan y hay amplitud sectorial disponible.

#### E-HM-01 · Universo del heatmap con OTC y preferentes

**S2 · ✅ · Esfuerzo S** — Objeto: `filter_top_by_market_cap()`.

- **Hallazgo.** Solo se ordena por `d[11]` (capitalización) y se recorta al top 1.000.
- **Evidencia.** Roadmap 1.0.2: 459 de 1.005 símbolos son OTC y 127 preferentes; OVCHF (+11,32 %) aparece entre los mayores ganadores.
- **Impacto.** Rankings de movers y de amplitud contaminados con instrumentos ilíquidos; ETF, preferentes y unidades entran como `equity`.
- **Corrección.** M-CAP-10 (B.2: `exchange ∈ {NASDAQ, NYSE, AMEX}`, acción común, volumen en USD ≥ umbral).
- **Aceptación.** 0 símbolos OTC en el último snapshot (A12).

#### E-HM-02 · Parseo posicional acoplado a 28 columnas

**S2 · ✅ · Esfuerzo S** — Objeto: `parse_vector()`.

- **Hallazgo.** Usa `d[1]`, `d[11]`, `d[21]`, `d[22]`, `d[23]`, `d[25]`, `d[26]` y `len(d) < 28`. El orden real está declarado en `HEATMAP_COLUMNS` (28 entradas).
- **Impacto.** Cualquier cambio de orden o de columnas produce datos erróneos sin error (así nació la documentación obsoleta, I1).
- **Corrección.** M-CAP-11 (B.2: `dict(zip(HEATMAP_COLUMNS, d))`, validar `len(d) == len(COLS)` y alertar).
- **Aceptación.** Un test unitario falla si cambia el orden de columnas.

#### E-HM-03 · Sin planificación ni ventana; auditoría `FAILED` fuera de sesión

**S2 · ✅ · Esfuerzo S** — Objeto: `main()`, `fetch_from_api()`.

- **Hallazgo.** El script hace una sola pasada. Si no hay vectores `d`, `main` registra `FAILED` y termina con `sys.exit(1)`.
- **Evidencia.** Solo hay 3 snapshots en BD (uno en domingo, 2026-09-13, con precios del viernes).
- **Impacto.** No hay serie temporal de amplitud ni sectores; fuera de sesión se registran fallos falsos.
- **Corrección.** M-CAP-13 (cron con gate, cada 15 min alineado a barras + snapshot de pre-apertura; estado `SKIPPED`).
- **Aceptación.** 28 snapshots por sesión, 0 fuera de ella, 0 `FAILED` espurios.

#### E-HM-17 · `dim_asset` congela ticker, exchange, sector y nombre en el primer valor visto

**S2 · ✅ · Esfuerzo S** — Objeto: `get_or_create_asset()`, cláusula `ON CONFLICT`.

- **Hallazgo.** El upsert usa `COALESCE(dim_asset.col, EXCLUDED.col)` en `ticker`, `exchange`, `asset_class`, `share_class`, `sector`, `company_name` y `logo_id`: si la columna ya tiene un valor no nulo, **nunca** se reemplaza por el nuevo, sin importar si el dato de origen cambió.
- **Evidencia.** Confirmado en el código: las siete columnas del `SET` siguen ese patrón. Es distinto de E-HM-04 (volumen de escrituras): aquí el problema es de **corrección**, no de rendimiento.
- **Impacto.** Un cambio real de ticker (fusión, split de clase de acciones), de sector (reclasificación GICS) o de exchange (deslistado y recontratado) queda invisible para siempre en `dim_asset`, salvo que se borre la fila a mano. Es una fuga de datos silenciosa: no hay error, log ni fila en `audit_sync_run` que lo señale.
- **Corrección.** M-CAP-12 (política explícita: `DO NOTHING` para altas nuevas — no cambia el comportamiento actual sobre existentes — más un job separado de reconciliación que compare `dim_asset` contra el snapshot más reciente y proponga los cambios para revisión, en vez de sobrescribir en silencio).
- **Aceptación.** Existe un reporte periódico de discrepancias `dim_asset` vs. último snapshot; ningún cambio de atributo se aplica sin quedar auditado.

#### E-HM-04 · Upserts por símbolo, un commit por fila y `updated_at` sin significado

**S3 · ✅ · Esfuerzo S** — Objeto: `get_or_create_asset()`, llamada dentro del bucle de `process_heatmap_data()`.

- **Hallazgo.** Se llama una vez por símbolo (1.000 consultas por snapshot) con `ON CONFLICT DO UPDATE SET updated_at = CURRENT_TIMESTAMP` incondicional.
- **Evidencia.** Código. Si `execute_query` confirma en cada llamada (no revisado: `db/postgresql_connection.py` no está en el material analizado), son además 1.000 *round-trips* y posibles commits por snapshot.
- **Impacto.** ~28.000 escrituras/día en `dim_asset` (1.083 filas, varios índices): bloat y presión sobre el WAL. `updated_at` se actualiza en cada snapshot aunque ningún atributo real haya cambiado (ver E-HM-17 para el problema de fondo: los atributos que sí cambiarían no se propagan).
- **Corrección.** M-CAP-12 (cache `symbol → asset_id` precargado, alta masiva con `DO NOTHING`, un solo commit por snapshot).
- **Aceptación.** ≤ 3 sentencias SQL de dimensión por snapshot.

#### E-CAL-01 · Los errores devuelven lista vacía y el checkpoint se sobrescribe con ceros

**S2 · ✅ · Esfuerzo S** — Objeto: `fetch_calendar_events()`, `capturar_eventos()`.

- **Hallazgo.** Un 429 hace `sleep(30)` y `return []`; timeouts y errores HTTP también devuelven `[]`. Si no hay eventos, se ejecuta `guardar_checkpoint(0, 0, 0)`. El cálculo del checkpoint usa `except:` desnudo.
- **Impacto.** No se distingue "sin eventos" de "fallo". Una consulta perdida cerca de una publicación deja el `actual` sin capturar hasta el ciclo siguiente. El checkpoint pierde el último estado válido.
- **Corrección.** M-CAP-15 (reintento con backoff, estado `PARTIAL_FAIL`, checkpoint intacto).
- **Aceptación.** Ante un fallo de API se reintenta y queda auditado; el checkpoint no se sobrescribe.

#### E-CAL-02 · `captured_at` nulo (probable) y upsert que reescribe todo

**S2 · 🟡 · Esfuerzo S** — Objeto: `capturar_eventos()` → `process_calendar_batch(eventos_raw)`.

- **Hallazgo.** A la BD se envía `eventos_raw`; `timestamp_captura` solo se añade en `evento_a_dict` (ruta del CSV). En el pseudocódigo del roadmap 3.1.0, `captured_at = parse_iso(evento.get('timestamp_captura'))` da `None`, y el `ON CONFLICT` fija `last_updated_at = CURRENT_TIMESTAMP` en cada conflicto, con toda la ventana (−1 d … +2 d, 11 países) reenviada en cada corrida.
- **Evidencia.** Código del calendario; el código real de `event_repository.py` no se revisó (H10).
- **Impacto.** No se puede medir la latencia del `actual`; ~600 escrituras por ejecución.
- **Corrección.** M-DAT-08 (B.3: `WHERE payload_checksum IS DISTINCT FROM ...`, `actual_first_seen_at`) y fijar `captured_at = now()`.
- **Aceptación.** A4 sin nulos nuevos; `last_updated_at` cambia solo cuando cambia el payload.

#### E-CAL-03 · Latencia del `actual` y horizonte capado a 2 días

**S2 · 🟡 · Esfuerzo M** — Objeto: cron del calendario, `dias_adelante = min(args.dias, 2)`.

- **Hallazgo.** Cadencia de 15 min y tope fijo de 2 días hacia adelante.
- **Impacto.** Un dato de las 08:30 o 10:00 ET puede tardar hasta 15 min más la latencia de TradingView. Los viernes no se ven los eventos del lunes y un panel semanal es imposible.
- **Corrección.** M-CAP-14 (polling por minuto entre T−1 y T+10 min de cada evento de alto impacto, ventana 08:00–16:00 ET) y M-CAP-16 (llamada semanal aparte).
- **Aceptación.** p95 de `actual_first_seen_at − event_timestamp` ≤ 90 s en eventos de alto impacto.

#### E-BD-02 · Particiones: zona de los límites y vencimiento

**S2 · 🟡 · Esfuerzo S** — Objeto: `fact_market_series_*`, `fact_heatmap_snapshot_*`, `create_partitions.py`.

- **Hallazgo.** El informe indica límites "en hora local"; `scrapper_heatmap_v1.py` crea la partición mensual con `first_day` en UTC; el config del heatmap define `TIMEZONE = America/Lima`. Las particiones existentes terminan en `2026_12`.
- **Evidencia.** El error registrado `no partition of relation "fact_market_series" found for row (2026-08-31 19:00:02-05)` corresponde a 2026-09-01 00:00:02 UTC: ocurre si la partición de septiembre no existía y los límites eran UTC (con límites de Lima esa fila habría caído en agosto). Es un indicio de mezcla de criterios (H11).
- **Impacto.** Posibles solapes o huecos al cambiar de mes; a partir del 2027-01-01 los inserts fallan.
- **Corrección.** M-DAT-07 (A5, límites UTC explícitos, creación anticipada hasta 2027-12, alerta).
- **Aceptación.** A5 muestra límites contiguos a las `00:00+00`; siempre existe la partición del mes siguiente con ≥ 15 días de antelación.

#### E-BD-03 · Escala de importancia mal documentada

**S2 · 🟡 · Esfuerzo S** — Objeto: comentario de `fact_economic_event.importance`, índice `idx_fact_economic_event_importance`.

- **Hallazgo.** Documentado como −1 sin dato, 0 baja, 1 media, 2 alta, 3 muy alta, sin fuente.
- **Evidencia.** Distribución 392 / 142 / 45 para −1 / 0 / 1 y ningún 2 ó 3 en 579 eventos; el *Fed Interest Rate Decision* tiene importancia 1.
- **Impacto.** Si la escala real es −1/0/1 (baja/media/alta), los filtros y etiquetas están mal, la "deuda D8" no existe y el índice parcial `BETWEEN 1 AND 3` funciona por casualidad.
- **Corrección.** Verificar con A3, M-DAT-08 y M-DOC-02.
- **Aceptación.** NFP, CPI y FOMC con la importancia esperada, documentada.

#### E-BD-04 · `dim_asset` declarada SCD2 sin versionado posible

**S2 · ✅ · Esfuerzo S** — Objeto: `dim_asset`.

- **Hallazgo.** Tiene `valid_from`, `valid_to` y `current_version`, pero `symbol` es `UNIQUE` (`dim_asset_symbol_key`). Además existe un índice duplicado `idx_dim_asset_symbol` sobre la misma columna.
- **Impacto.** No puede existir una segunda versión del mismo símbolo; las vistas filtran `current_version` sin necesidad; el índice redundante encarece las escrituras.
- **Corrección.** D7, M-DAT-06 (Tipo 1, o `UNIQUE (symbol) WHERE current_version`) y M-DAT-13.
- **Aceptación.** Decisión documentada y esquema coherente.

#### E-OPS-01 · Sin gate de sesión; cron en hora local; captura 24 h

**S2 · ✅ · Esfuerzo M** — Objeto: los tres scripts y el crontab.

- **Hallazgo.** Ninguno conoce la ventana de mercado. El cron corre de lunes a jueves 24 h y el viernes hasta las 16:59 (roadmap 3.1.0), sin sábado ni domingo.
- **Evidencia.** 480 ticks por activo y día (§5.5).
- **Impacto.** Gran parte de los ticks de acciones cae fuera de la sesión regular (H4) y contamina RSI, ADX y el rolling de volumen. Un cron en hora de Lima no sigue el fin del horario de verano (1-nov-2026), los feriados ni los cierres anticipados. Futuros, FX y cripto quedan sin captura de fin de semana.
- **Corrección.** M-CAP-01 (B.1), M-DAT-01 y M-OPS-04.
- **Aceptación.** Pruebas con 2026-11-26 (Acción de Gracias), 2026-11-27 (cierre anticipado) y 2026-11-02 (primer lunes tras el cambio de horario), según el calendario XNYS.

#### E-OPS-02 · Credenciales y privilegios

**S2 · ✅ · Esfuerzo S** — Objeto: `.env`, `config.py`, informe de la BD.

- **Hallazgo.** El informe reproduce `BD_HEATMAP_USER=postgres` y `BD_HEATMAP_PASSWORD=postgres`. El config del radar usa por defecto `PG_USER = "postgres"` y contraseña vacía. Scrapers y dashboard compartirían el superusuario.
- **Impacto.** Un fallo en cualquier componente tiene privilegios totales; la contraseña está en documentación compartida.
- **Corrección.** M-OPS-03 (roles `scraper_rw` y `dashboard_ro`, rotación de contraseña, retirar el valor del informe).
- **Aceptación.** El dashboard no puede escribir y ningún documento contiene secretos.

#### E-DSH-01 · Score sin validación y calibración al final del plan

**S2 · ✅ · Esfuerzo L** — Objeto: plan del dashboard v2.

- **Hallazgo.** La validación estadística está en la última fase; se prevén zonas COMPRAR/VENDER y direcciones fijas por activo.
- **Evidencia.** ~20 sesiones de equity (desde 2026-08-22), observaciones autocorrelacionadas.
- **Impacto.** Riesgo alto de sobreajuste y de falsa confianza; el retraso del feed no se descuenta en los backtests.
- **Corrección.** M-VAL-02 antes de construir paneles; M-DSH-04 (solo contexto hasta rechazar H13; zonas por fase).
- **Aceptación.** Informe walk-forward con intervalos de confianza y sin look-ahead (señal desplazada por el retraso).

#### E-DSH-02 · Volumen relativo calculado sobre volumen acumulado

**S2 · ✅ · Esfuerzo M** — Objeto: panel 7.8 del plan.

- **Hallazgo.** "Volumen vs media 2 d" divide un acumulado del día por una media.
- **Evidencia.** `volume` base es acumulado (H3 ✅); el snapshot ya trae `average_volume_10d_calc` y `average_volume_30d_calc`; VIX y otros índices tienen `volume = null`.
- **Impacto.** A las 10:00 ET siempre "parece bajo" y al cierre siempre "parece alto"; división por nulos.
- **Corrección.** M-DSH-05 (RVOL por hora del día: acumulado actual / acumulado medio a esa misma hora; tolerante a nulos).
- **Aceptación.** RVOL con mediana ≈ 1,0 a cualquier hora en días normales.

#### E-DSH-03 · Etiquetas de sesión en UTC erróneas

**S2 · ✅ · Esfuerzo S** — Objeto: plan del dashboard (fases y gráficos).

- **Hallazgo.** "Sesión Madura (14:00–16:00 UTC)" y "[09:30–14:25 UTC]".
- **Impacto.** La sesión regular es 13:30–20:00 UTC (EDT) o 14:30–21:00 UTC (EST); las fases quedan mal delimitadas.
- **Corrección.** M-DSH-08 (`session_service` sobre `dim_trading_session`; mostrar ET y Lima).

#### E-DOC-01 · Documentación de campos obsoleta

**S2 · ✅ · Esfuerzo S** — Objeto: `heatmap_stock_documentacion_campos.md`, informe de la BD §9.4.

- **Hallazgo.** El documento (captura antigua de 502 símbolos) da `d[3]` = cambio diario, `d[15]` = capitalización y `d[25]` = precio. El layout real es `d[1]`, `d[11]` y `d[23]`. El informe rotula `change_abs` como "cambio5m?" y `pricescale` como "volumen_relativo".
- **Impacto.** Quien lea `raw_vector` con los índices viejos tomaría `Perf.1M` por cambio diario.
- **Corrección.** M-DOC-01 y M-DOC-02 (Anexo D).

### 6.3 Medios (S3) y bajos (S4)

| ID | Sev. | Hallazgo y evidencia | Corrección |
| --- | --- | --- | --- |
| **E-RAD-08** | S3 | `rotar_datos()` se ejecuta por símbolo y ciclo: lee el CSV completo (~3.400 filas a 7 días) y, desde el día 8, lo reescribe en cada ciclo. Es I/O dentro del ciclo crítico. | M-CAP-17 |
| **E-RAD-09** | S3 | `SCRIPT_NAME_SCRAPER = "radar_v4"` y `VERSION = "3.1.0"` con un script v5: la auditoría atribuye las corridas de v5 a v4. | M-OPS-06 |
| **E-RAD-10** | S3 | `METADATOS_ACTIVOS` fija direcciones (ORO y OIL "invertida", TLT "normal") y sus pesos suman 90; contradice el plan de derivar la dirección por correlación de 60 días. | M-DSH-04 |
| **E-RAD-11** | S4 | Docstring con "fallback automático" inexistente, `DATOS_LIVE_2` frente a `BASE_DIR = "DATOS_LIVE"`, erratas ("CFONFIGURACIÓN", "roadrmaap") y dos llamadas a `now()` para `timestamp_utc` y `fecha_iso`. | M-OPS-06 |
| **E-HM-05** | S3 | `logo_id` queda `NULL` en activos nuevos: `logoid` llega como string (`"nvidia"`) y el código espera un dict (`logo.get('logoid') if isinstance(logo, dict) else None`). Comprobar con A14. | B.2 |
| **E-HM-06** | S3 | `company_name = d[25]` es el ticker (columna `name`); `asset_class` es `equity` para todo (ETF, preferentes, unidades). | M-CAP-11 (`description`, `typespecs`) |
| **E-HM-07** | S3 | El cálculo defectuoso vive **dentro de `log_sync_run()`** (`records_failed = fetched - upserted if fetched and upserted else 0`), no en quien la llama: cualquier invocación futura hereda el bug sin poder evitarlo desde fuera. Con `upserted == 0` y `fetched > 0` informa 0 fallos en vez de `fetched`. | B.7 |
| **E-HM-15** | S4 | `ticker = parsed.get('ticker') or symbol.split(':')[-1] if ':' in symbol else symbol`: por precedencia de operadores en Python (`or` liga más fuerte que el `if/else` de la expresión condicional), se evalúa como `(parsed.get('ticker') or symbol.split(':')[-1]) if ':' in symbol else symbol`. Funciona hoy porque todo símbolo de este proyecto lleva `:`, pero si algún día se captura un símbolo sin exchange, ignora silenciosamente `parsed['ticker']` incluso si tiene valor. Confirmado en `scrapper_heatmap_v1.py` línea 76. | Reescribir con paréntesis explícitos o una función auxiliar |
| **E-HM-16** | S3 | En `main()`, `create_monthly_partitions()` se ejecuta **antes** de `fetch_heatmap_data()`. Si el endpoint falla (fin de semana, mantenimiento, bloqueo), ya se creó la partición del mes y además se registra un `FAILED` en `audit_sync_run` sin haber datos que insertar (mismo síntoma que E-HM-03). Confirmado en el orden de `main()`. | Invertir el orden: `fetch → validar → DDL`; relacionado con E-HM-03 y E-HM-11 |
| **E-HM-08** | S3 | `raw_metadata` duplica `dim_asset`; `raw_vector` JSONB con GIN (~1,8 kB/fila) y sin columnas para lo que se consultará (`volume`, medias de volumen, `Volatility.D`, máx/mín de 52 semanas). | M-DAT-05 |
| **E-HM-09** | S3 | Se descargan ~19.738 símbolos para conservar 1.000, y `filter_top_by_market_cap` reordena lo que el endpoint ya devuelve ordenado (`sort market_cap_basic desc`). | M-CAP-10 (probar `range`) |
| **E-HM-10** | S3 | `timestamp_utc = now()` se toma tras el fetch y el DDL de partición; no se guarda `fetched_at` ni `update_mode` por snapshot. | M-CAP-04, M-DAT-05 |
| **E-HM-11** | S3 | DDL de partición dos veces por corrida (`create_monthly_partitions` en `main` y `create_partition` en `process_heatmap_data`). | M-DAT-07 (comprobar si falta) |
| **E-HM-12** | S4 | `int(os.getenv('BD_HEATMAP_PORT'))` lanza `TypeError` si falta (solo se capturan `ValueError`/`KeyError`); `TIMEZONE = America/Lima` residual; ~60 líneas de fallback comentado. | Limpieza |
| **E-CAL-04** | S3 | Cada ejecución crea un log nuevo (`calendario_YYYYmmdd_HHMMSS.log`): con polling por minuto serían ~420 archivos por día. `except:` desnudo; cabecera `Version: 3.1.0` y `argparse` con "Captura Raw V4". | M-CAP-15 |
| **E-CAL-05** | S3 | Los errores de BD se tragan sin registro en `audit_sync_run`; el CSV se guarda pero no se reconcilia. | M-CAP-06 |
| **E-BD-05** | S3 | `vw_heatmap_event_impact` cruza 1.000 activos con cada evento en ±6 h (no mide impacto) y está vacía. La vista "relajada" (D7) no lo corrige: el propio roadmap admite que seguirá vacía. | M-DAT-10 |
| **E-BD-06** | S3 | `dim_time.is_holiday` con `false` por defecto y `trading_session` genérico `US`: sin feriados ni cierres anticipados. | M-DAT-01 |
| **E-BD-07** | S3 | Convención de FK inconsistente (roadmap 1.0.2 quita FK físicas; el plan del dashboard añade `REFERENCES dim_asset`) y `fact_market_score` mezcla granularidades: score por activo y agregados de mercado repetidos 110 veces por tick. | M-DAT-09 |
| **E-BD-08** | S4 | `raw_payload` 100 % nulo en `fact_market_series`; posibles índices sin uso; `vw_heatmap_enriched.last_rsi` con subconsulta por fila (solo 110 de 1.000 activos tienen serie). | M-DAT-13, A13 |
| **E-OPS-03** | S3 | Sin monitoreo de frescura ni de esquema del endpoint (H18); solo 12 filas en `audit_sync_run`. | M-OPS-02 |
| **E-OPS-04** | S3 | Dos `config.py` distintos (radar 3.1.0 y heatmap 1.0.2) con la misma API parcial (`PG_*`); chocarán si se combinan en un mismo entorno (por ejemplo, el dashboard). | M-OPS-06 |
| **E-DSH-04** | S3 | SMA20/50 con `AVG() OVER` sobre ticks; `psycopg2` síncrono dentro de FastAPI `async`; refresco automático de 15–30 s con datos nuevos cada 3 min; nueve paneles antes de validar nada. | M-DSH-03, M-DSH-07 |
| **E-DSH-05** | S3 | Sorpresa `(actual − forecast)/forecast`: inestable cerca de 0 y con negativos (ejemplo −66 %); sin polaridad por indicador (más desempleo es negativo). | M-DAT-10, M-DSH-09 |
| **E-DSH-06** | S4 | Ejemplos ASCII con valores que parecen reales y no lo son (NVDA con RSI 65,4 y "ya pasó R3", frente a RSI 51,83 y R3 por encima del cierre; `DXY xx.xx`). | Reemplazar por datos reales |
| **E-DOC-02** | S3 | Versionado y nombres (I13, I14): `Version: 3.1.0` en un script v5; `scrapper_heatmap.py` frente a `scrapper_heatmap_v1.py`; el ejemplo de `CONFIG_ACTIVOS` del roadmap 1.0.2 no es el volcado real. | M-DOC-02, M-OPS-06 |

---

## 7. Catálogo de mejoras

> **Prioridad** P0–P3 según §1.3. La columna *Resuelve* remite a errores (E-), hipótesis (H) o preguntas (Q). Los criterios de aceptación son verificables con las consultas del Anexo A o las pruebas del Anexo C.
> 

### 7.1 Captura (`M-CAP`)

| ID | Mejora | Resuelve | Prio. | Esf. | Depende de | Criterio de aceptación |
| --- | --- | --- | --- | --- | --- | --- |
| **M-CAP-01** | Gate de sesión por calendario NYSE dentro del código (B.1); el cron queda cada 3 min sin lógica horaria. | E-OPS-01, E-HM-03 | P0 | S | M-DAT-01 | Pruebas de feriado, cierre anticipado y DST pasan; 0 ticks del radar fuera de 09:00–16:00 ET |
| **M-CAP-02** | `POST` único a `/scan` con `symbols.tickers` para los 110 símbolos, con fallback a `GET`. | E-RAD-03 | P0 | M | Q16 (T5) | Ciclo ≤ 15 s; un timestamp por ciclo |
| **M-CAP-03** | `CAMPOS` multi-TF (B.4) y regla de cierre de barra: el valor definitivo de cada barra de 15 min es el último tick previo a su cierre; el primer tick tras la frontera se marca `provisional`. | E-RAD-01 | P0 | M | H19–H21 (T4) | Cada barra cerrada tiene indicadores `tf = 15` definitivos |
| **M-CAP-04** | Trazabilidad temporal: `cycle_id`, `fetched_at`, `update_mode` y `feed_delay_s` por tick y en `audit_sync_run.source_params`. | E-RAD-02, E-HM-10 | P0 | S | T1 | 100 % de los ticks con `update_mode` |
| **M-CAP-05** | Prioridad de símbolos (SPY, QQQ, VIX, US10Y, DXY, NQ1! primero) y circuit breaker por exchange o bloque. | E-RAD-04 | P1 | S | Q6 | Fallo simulado de un bloque no afecta al resto |
| **M-CAP-06** | Reintento del flush con backoff, modo estricto (`DB_WRITE_ENABLED` obligatorio en producción, `override=False`) y reconciliación nocturna CSV → BD. | E-RAD-05, E-CAL-05 | P1 | M | — | Con la BD caída 10 min no queda ningún hueco tras 24 h |
| **M-CAP-07** | Mapeo canónico lógico → físico y metadatos de feed en `dim_asset`. | E-RAD-06 | P1 | M | D2, D3, M-DAT-06 | Cada clave de `METADATOS_ACTIVOS` resuelve a un `asset_id` |
| **M-CAP-08** | Ampliar el universo del radar (Anexo E). | E-RAD-07 | P1 | S | H7b | 13 símbolos nuevos capturados |
| **M-CAP-09** | Columnas de pre-market (`premarket_close`, `premarket_change`, `gap`) en radar y heatmap. | H6, H20 | P1 | M | T3 | Precio de pre-apertura disponible desde las 09:00 ET |
| **M-CAP-10** | Heatmap: filtro tradeable, top-N configurable y prueba de `range`. | E-HM-01, E-HM-09 | P1 | S | D6 | 0 OTC en el último snapshot |
| **M-CAP-11** | Heatmap: parseo por nombre, `description`, corrección de `logo_id` y `asset_class` desde `typespecs`. | E-HM-02, E-HM-05, E-HM-06 | P1 | S | — | Test unitario del orden de columnas |
| **M-CAP-12** | Heatmap: cache `symbol → asset_id`, alta masiva `DO NOTHING`, un commit y corrección de `records_failed`. | E-HM-04, E-HM-07 | P2 | S | — | ≤ 3 sentencias de dimensión por snapshot |
| **M-CAP-13** | Heatmap: cron con gate, cadencia de 15 min alineada (:00/:15/:30/:45 + ~20 s) y snapshot de pre-apertura (~09:25 ET). | E-HM-03 | P1 | S | M-CAP-01 | 28 snapshots por sesión |
| **M-CAP-14** | Calendario: polling por minuto entre T−1 y T+10 min de cada evento de alto impacto de EE. UU.; ventana 08:00–16:00 ET. | E-CAL-03 | P1 | M | H5 | p95 de latencia del `actual` ≤ 90 s |
| **M-CAP-15** | Calendario: reintento, distinguir error de vacío, checkpoint intacto, `RotatingFileHandler` y `except` explícito. | E-CAL-01, E-CAL-04 | P2 | S | — | Un fallo de API queda auditado y reintentado |
| **M-CAP-16** | Calendario: llamada semanal separada (7 días) para el panel de semana. | E-CAL-03 | P3 | S | — | Eventos de los próximos 7 días disponibles |
| **M-CAP-17** | Rotación de CSV diaria y fuera del ciclo. | E-RAD-08 | P3 | S | — | 0 lecturas de CSV dentro del ciclo |

### 7.2 Modelo de datos (`M-DAT`)

| ID | Mejora | Resuelve | Prio. | Esf. | Depende de | Criterio de aceptación |
| --- | --- | --- | --- | --- | --- | --- |
| **M-DAT-01** | `dim_trading_session` (B.5) poblada con `exchange_calendars` (XNYS) para 2026–2027. | E-BD-01, E-BD-06, E-OPS-01 | P0 | S | D11 | Feriados y cierres anticipados presentes |
| **M-DAT-02** | `fact_market_bar_15m` (B.5) con `n_ticks`, `is_regular` y volumen por diferencia. | E-BD-01 | P0 | M | M-DAT-01 | 28 barras/día/activo; ≥ 95 % con `n_ticks ≥ 3` |
| **M-DAT-03** | `fact_market_indicator_tf` en formato largo (B.5). | E-RAD-01 | P1 | M | D4, D12 | Añadir un TF no exige cambiar el esquema |
| **M-DAT-04** | `latest_market_tick`: una fila por activo actualizada por upsert en cada ciclo. | E-DSH-04 | P1 | S | — | Lectura del dashboard sobre 110 filas |
| **M-DAT-05** | Snapshots: columnas explícitas (`volume`, `avg_vol_10d`, `avg_vol_30d`, `volatility_d`, `change_abs`, `high_52w`, `low_52w`, `update_mode`, `fetched_at`), eliminar `raw_metadata`, evaluar el GIN. | E-HM-08, E-HM-10 | P1 | M | — | Tamaño por fila < 1 kB |
| **M-DAT-06** | `dim_asset`: `logical_key`, `is_canonical`, `role`, `feed_delay_s`; resolver SCD2. | E-BD-04, E-RAD-06 | P1 | M | D7 | Esquema coherente y documentado |
| **M-DAT-07** | Particiones con límites UTC explícitos, verificación A5, creación hasta 2027-12 y alerta de antelación. | E-BD-02, E-HM-11 | P0 | S | — | A5 contiguo a las `00:00+00` |
| **M-DAT-08** | Eventos: upsert condicional por checksum (B.3), `actual_first_seen_at`, `captured_at` y semántica de importancia. | E-CAL-02, E-BD-03 | P1 | S | H5 | A4 sin nulos nuevos |
| **M-DAT-09** | `fact_symbol_score` (por activo) y `fact_market_context` (por timestamp). | E-BD-07 | P2 | M | M-VAL-02 | Sin agregados repetidos por activo |
| **M-DAT-10** | `fact_event_reaction` (+ `dim_indicator_polarity`, sorpresa estandarizada) que sustituye a `vw_heatmap_event_impact`. | E-BD-05, E-DSH-05 | P2 | L | M-DAT-02 | Reacción a +3/+15/+30/+60 min por evento |
| **M-DAT-11** | `fact_sector_snapshot`: amplitud y cambio ponderado por sector en cada snapshot. | H16 | P2 | M | M-CAP-13 | Serie de amplitud por sector |
| **M-DAT-12** | Retención: ticks 6 meses, barras de 15 min indefinidas, `raw_payload` solo si hace falta. | Q10, Q14 | P3 | M | D8 | Política aplicada y documentada |
| **M-DAT-13** | Limpieza: índice duplicado de `dim_asset`, índices sin uso (A13) y `vw_heatmap_enriched`. | E-BD-04, E-BD-08 | P3 | S | A13 | Sin índices redundantes |

### 7.3 Validación y calidad (`M-VAL`)

| ID | Mejora | Resuelve | Prio. | Esf. | Depende de | Criterio de aceptación |
| --- | --- | --- | --- | --- | --- | --- |
| **M-VAL-01** | Suite nocturna de calidad: duplicados, huecos, nulos, ticks planos fuera de sesión, `n_ticks` por barra, continuidad de particiones. | E-RAD-05 | P1 | M | M-DAT-02 | Informe diario sin alertas abiertas |
| **M-VAL-02** | Estudio de forward-return del score y de cada componente (walk-forward, retornos a +15/+30/+60 min, señal desplazada por el retraso del feed). | E-DSH-01, H13 | P1 | L | M-DAT-02 | Informe con intervalos de confianza y sin look-ahead |
| **M-VAL-03** | Estudio de eventos sobre ticks de 3 min (QQQ, SPY, US10Y, XAUUSD). | H14 | P2 | L | Q8 | Reacción media por importancia y por sorpresa |
| **M-VAL-04** | Validación cruzada de `RSI|15`, `ADX|15`, `CCI20|15` de TradingView frente a cálculo propio en 5–10 sesiones. | D4 | P2 | M | M-DAT-02, M-DAT-03 | Diferencias documentadas y decisión D4 cerrada |
| **M-VAL-05** | Reempaquetado del histórico: `fact_daily_context` (último valor por día ET) y barras de 15 min retroactivas. Salvedades: `timestamp_utc` es hora de captura, posible retraso de 15 min, captura 24 h, equity solo desde 2026-08-22. | E-RAD-01 | P2 | M | M-DAT-01, M-DAT-02 | Backtest reproducible sobre barras y contexto diario |

### 7.4 Dashboard (`M-DSH`)

| ID | Mejora | Resuelve | Prio. | Esf. | Depende de | Criterio de aceptación |
| --- | --- | --- | --- | --- | --- | --- |
| **M-DSH-01** | Modos PRE (09:00–09:30), LIVE y CLOSED gobernados por `dim_trading_session`. | E-DSH-03 | P0 | M | M-DAT-01 | Fuera de ventana muestra resumen del día y cuenta regresiva |
| **M-DSH-02** | Banner de frescura por panel (`as_of`, `feed_delay`, `ingest_lag`). | E-RAD-02 | P0 | S | M-CAP-04 | Todo panel muestra su antigüedad |
| **M-DSH-03** | MVP de 4 paneles: pre-apertura y régimen (VIX, DXY, US10Y, NQ/ES, BTC), QQQ/SPY/ORO en 15 min con SMA, VWAP y pivotes, próximos eventos con cuenta regresiva, termómetro de riesgo. | E-DSH-04 | P0 | L | M-DAT-02, M-DAT-04 | Los 4 paneles con datos reales en sesión |
| **M-DSH-04** | Score como contexto (valor, percentil y fase), zonas por fase y dirección por correlación de 60 días. | E-DSH-01, E-RAD-10 | P1 | M | M-VAL-02 | Sin etiquetas COMPRAR/VENDER hasta rechazar H13 |
| **M-DSH-05** | RVOL por hora del día tolerante a nulos. | E-DSH-02 | P2 | M | M-DAT-02 | Mediana ≈ 1,0 a cualquier hora |
| **M-DSH-06** | Amplitud y sectores (heatmap filtrado + ETF sectoriales). | E-HM-01, E-RAD-07 | P2 | M | M-CAP-08, M-CAP-10 | Panel con % de avance y cambio por sector |
| **M-DSH-07** | Stack: endpoints `def` o `psycopg` v3 con pool; refresco por `LISTEN/NOTIFY` o poll de 60–180 s alineado al cierre de barra. | E-DSH-04 | P2 | S | — | Sin bloqueo del event loop |
| **M-DSH-08** | `session_service` en `America/New_York`, mostrando ET y Lima. | E-DSH-03 | P1 | S | M-DAT-01 | Fases correctas antes y después de DST |
| **M-DSH-09** | Panel de eventos: cuenta regresiva, ventana de silencio y sorpresa estandarizada con polaridad. | E-DSH-05 | P1 | M | M-DAT-10 | Sorpresa correcta en NFP y CPI |

### 7.5 Operación (`M-OPS`)

| ID | Mejora | Resuelve | Prio. | Esf. | Depende de | Criterio de aceptación |
| --- | --- | --- | --- | --- | --- | --- |
| **M-OPS-01** | Wrapper de ejecución: lock, gate, auditoría por ciclo (`RUNNING → SUCCESS / PARTIAL_FAIL / SKIPPED`), duración y símbolos fallidos. | E-RAD-05, E-OPS-03 | P0 | M | M-CAP-01 | 1 fila de auditoría por ciclo, incluidos los saltados |
| **M-OPS-02** | Monitoreo y alertas: frescura en ventana, ciclos saltados, 429, cambio de esquema del endpoint (H18), `DB_WRITE = OFF`. | E-OPS-03 | P1 | M | M-OPS-01 | Alerta en < 5 min ante un dato viejo |
| **M-OPS-03** | Roles `scraper_rw` y `dashboard_ro`, rotación de contraseña y secretos fuera de documentos. | E-OPS-02 | P1 | S | — | El dashboard no puede escribir |
| **M-OPS-04** | Pruebas automáticas del gate: feriado, cierre anticipado y DST (2026-11-02, 2027-03-15). | E-OPS-01 | P1 | S | M-CAP-01 | Suite en verde |
| **M-OPS-05** | Backups y política de retención. | — | P2 | S | D8 | Restauración probada |
| **M-OPS-06** | Unificar o renombrar `config.py`, `SCRIPT_NAME_SCRAPER`, versiones y nombres de archivo. | E-OPS-04, E-RAD-09, E-DOC-02 | P3 | S | — | Sin colisiones de módulo |

### 7.6 Documentación (`M-DOC`)

| ID | Mejora | Resuelve | Prio. | Esf. | Depende de | Criterio de aceptación |
| --- | --- | --- | --- | --- | --- | --- |
| **M-DOC-01** | Documento de campos v3 generado desde `HEATMAP_COLUMNS` (Anexo D); archivar el antiguo. | E-DOC-01 | P1 | S | — | Sin referencias a índices obsoletos |
| **M-DOC-02** | Correcciones al informe de la BD (§9.4, escala de importancia, conteos con fecha). | E-DOC-01, E-BD-03 | P2 | S | H5 | Informe sin contradicciones con el código |
| **M-DOC-03** | Registro de decisiones (ADR) con D1–D12. | — | P2 | S | — | Cada decisión con fecha y motivo |
| **M-DOC-04** | Separar la auditoría (congelada) del plan vivo. | — | P3 | S | — | Dos documentos con propósito distinto |

---

## 8. Incongruencias entre fuentes

| ID | Fuente A dice… | Fuente B dice… | Riesgo | Resolución |
| --- | --- | --- | --- | --- |
| **I1** | `heatmap_stock_documentacion_campos.md` (captura de 502 símbolos): `d[3]` = cambio diario, `d[15]` = capitalización, `d[25]` = precio. | Endpoint v3, `HEATMAP_COLUMNS`, `parse_vector` y el `raw_vector` de la BD: `d[1]` = cambio, `d[3]` = `Perf.1M`, `d[11]` = capitalización, `d[23]` = precio (universo de 19.738 símbolos). | Alto | M-DOC-01 (Anexo D) |
| **I2** | Informe de la BD §9.4: posiciones "cambio5m?" y "volumen_relativo". | Layout v3: `d[2]` = `change_abs`, `d[24]` = `pricescale` (100). | Medio | M-DOC-02 |
| **I3** | Plan del dashboard: NVDA con RSI 65,4 y "ya pasó R3 +0,9 %"; NFP/CPI/GDP con sorpresas; `DXY xx.xx`. | BD real: NVDA RSI 51,83 y R3 (230,03) por encima del cierre (219,47); esos eventos no constan; el índice DXY no existe. | Bajo | E-DSH-06 |
| **I4** | `dim_asset` declarada SCD Tipo 2. | `symbol` es `UNIQUE`: no admite dos versiones del mismo símbolo. | Medio | D7, M-DAT-06 |
| **I5** | Roadmap 1.0.2: sin FK físicas de los hechos hacia `dim_asset`. | Plan del dashboard: `fact_market_score ... REFERENCES dim_asset`; informe §10.1: "opcional añadir FK". | Bajo | M-DAT-09 |
| **I6** | Esquema, roadmaps e informe: importancia −1..3 con "−1 = sin dato". | Datos: solo −1/0/1; el FOMC tiene 1; el 67 % de los eventos con −1 sería "baja", no "sin dato". | Alto | E-BD-03, M-DAT-08 |
| **I7** | Docstring del radar: "Fallback automático entre Primarios y Respaldos". | El código recorre todos los símbolos sin lógica de fallback. | Medio | E-RAD-06, M-CAP-07 |
| **I8** | `dim_asset.company_name` = nombre de la empresa. | `parse_vector` asigna `company_name = d[25]` = ticker. | Bajo | M-CAP-11 |
| **I9** | `dim_asset.sector_es`: "traducción pendiente". | El endpoint ya no devuelve `sectorTranslated`; nunca se poblará desde la fuente. | Bajo | Diccionario local de ~20 sectores |
| **I10** | Informe §4: límites de partición "en hora local del servidor". | Decisión vigente: todo en UTC; `scrapper_heatmap_v1.py` crea particiones con límites UTC; el config del heatmap define `TIMEZONE = America/Lima`. | Medio | E-BD-02, M-DAT-07 |
| **I11** | Plan del dashboard: "Sesión Madura (14:00–16:00 UTC)", "[09:30–14:25 UTC]". | La sesión regular NYSE es 13:30–20:00 UTC (EDT) o 14:30–21:00 UTC (EST). | Medio | E-DSH-03 |
| **I12** | Plan del dashboard (D7): crear `vw_heatmap_event_impact_relaxed` para resolver la vista vacía. | El propio plan admite que "seguirá vacía"; además el cruce snapshot × evento no mide impacto. | Medio | E-BD-05, M-DAT-10 |
| **I13** | El script del calendario declara `Version: 3.1.0` y su `argparse` dice "Captura Raw V4"; el radar menciona `DATOS_LIVE_2` pero usa `DATOS_LIVE`; el heatmap se autodenomina `scrapper_heatmap.py`; `SCRIPT_NAME_SCRAPER = "radar_v4"` con un script v5. | El roadmap 3.1.0 ya da por corregida la discrepancia `.env` (`BD_HEATMAP_SERVER`) frente a `config.py` (`BD_HEATMAP_HOST`) y ambos `config.py` leen `HOST`. | Bajo | M-OPS-06 |
| **I14** | Roadmap 1.0.2: `CONFIG_ACTIVOS` con claves numéricas, campo `indicadores`, `CBOE:VIX` como primario y `OANDA:EURUSD` como primario de EURUSD. | Config real: claves con nombre (`"VIX"`), sin `indicadores`, VIX primario `CBOE:VX1!`, EURUSD primario `FX_IDC:EURUSD`. | Bajo | E-DOC-02 |
| **I15** | `sync_checkpoint.calendario.last_timestamp = 2026-09-18 20:15:28-05` y el radar `14:20:54-05`. | El checkpoint local del calendario guarda la **fecha máxima de evento** (`max_ts`); el pseudocódigo de la BD usa `run_start`. El rango de eventos en BD llega solo hasta las 12:00 (−05). | Bajo | Unificar la semántica (M-CAP-15) |
| **I16** | Conteos de activos: 1.060 (2026-09-13) y 1.083 (2026-09-18); 1.005 símbolos en el CSV semilla; 502 símbolos en la documentación antigua. | 1.000 por ventana de snapshot (`HEATMAP_MAX_SYMBOLS`); 19.738 símbolos devueltos por el endpoint. | Bajo | M-DOC-02 (fechar cada conteo) |

---

## 9. Hipótesis y estado de la evidencia

| ID | Hipótesis | Evidencia | Estado | Verificación | Impacto según el resultado |
| --- | --- | --- | --- | --- | --- |
| **H1** | El feed del **radar** va retrasado ~15 min (`delayed_streaming_900`). | Confirmado en el heatmap; el radar no pide `update_mode`; NVDA casi idéntico en radar (219,47) y heatmap (219,405); la prueba del 2026-09-19 usó BTC y mercados cerrados. | 🟡 | T1, T2 | **Si cierta:** la entrada no puede depender de este feed (D1). **Si falsa:** el retraso se limita al heatmap. |
| **H2** | Los indicadores base **no son de 15 min** (probablemente 1D). | AAPL: RSI base 64,25 frente a `RSI|15` 53,06; `|1D` devolvió `None`; ADX y R3 estables. | ✅ (no 15 min) · 🟡 (1D) | Comparar con RSI14 diario propio | Válidos como contexto, no como señal de 15 min. |
| **H3** | `volume` base es el **acumulado del día**. | AAPL 86,6 M con mercado cerrado; BTC crece 2379 → 2382; NVDA 73,65 M → 73,85 M en 76 s. | ✅ | A2 | Diferenciar para barras; RVOL por hora del día. |
| **H4** | La mayoría de los ticks de acciones fuera de sesión (días hábiles) son **repeticiones** del último precio. | 480 ticks/activo/día (24 h); AAPL y EURUSD congelados en fin de semana. El fin de semana no prueba lo que ocurre entre semana, y EURUSD, BTC y oro sí se mueven 24 h. | 🟡 | A1 | Filtrar por sesión; apagar la captura densa fuera de ventana. |
| **H5** | La escala de `importance` de TradingView es **−1 / 0 / 1** (baja / media / alta). | FOMC con 1; distribución 392 / 142 / 45; nunca 2 ó 3; escala −1..3 sin fuente. | 🟡 | A3 | Corregir etiquetas y comentarios; D8 deja de ser un gap. |
| **H6** | El `close` base de acciones en pre-market es el **cierre regular previo**. | Indicio: AAPL `close` 336,13 frente a `close|5` 335,58 (H20). | 🟡 | T3 | El radar no ve pre-market en acciones; usar `premarket_*`, `close|5` y futuros. |
| **H7** | (a) Los sufijos TF funcionan en `/symbol`. (b) `premarket_*`, `gap`, `VWAP`, `ATR`, `description`, `update_mode` y `symbols.tickers` con TF en `/scan` también funcionan. | (a) Prueba del 2026-09-19. (b) Solo memoria. | (a) ✅ · (b) 🔴 | T3, T5 | Habilita M-CAP-02, -03, -09. Si (b) falla: cálculo propio. |
| **H8** | El ciclo del radar dura **1,8–2,4 min** y puede saltarse ciclos. | Aritmética del código (§5.4); checkpoint 14:20:54 → `TVC:VIX` 14:23:01. | 🟡 | A6, A7, T9 | Agrupar por ciclo; pasar al `POST` único. |
| **H9** | Los cierres de VIX = 15,00 y US10Y = 5,00 son **artefactos**. | VIX cotiza con 2 decimales y `change_pct = −2,91262136` es exactamente (15,00 − 15,45)/15,45: coherente. US10Y sin verificar. | 🔴 (debilitada; descartada para VIX) | A8 | Baja prioridad. |
| **H10** | Los eventos capturados en vivo quedan con `captured_at` nulo. | El código pasa `eventos_raw` sin `timestamp_captura`; el repositorio real no se revisó. | 🟡 | A4 y leer `event_repository.py` | Sin `captured_at` no se mide la latencia del `actual`. |
| **H11** | Los límites de partición **mezclan UTC y hora local**. | El informe dice "hora local"; el heatmap crea límites UTC; el error `no partition ... (2026-08-31 19:00:02-05)` es compatible con límites UTC. | 🟡 | A5 | Solapes o huecos al cambiar de mes. |
| **H12** | El `actual` llega hasta **15 min tarde** por el cron de 15 min. | Cadencia del cron; `last_updated_at` no permite medirlo hoy. | 🟡 | Tras M-DAT-08 | Justifica el polling por evento. |
| **H13** | (Hipótesis nula) El score **no tiene poder predictivo** a 15–60 min. | Sin evidencia; ~20 sesiones de equity y datos autocorrelacionados. | 🔴 | M-VAL-02 | Si no se rechaza: solo contexto. |
| **H14** | Los eventos de alto impacto generan **reacción medible** en QQQ, SPY, US10Y y oro. | 45 eventos con importancia 1 en 18 días; sorpresas computables desconocidas. | 🔴 | M-VAL-03, A9 | Justifica `fact_event_reaction`. |
| **H15** | El UTC de los datos **cargados** es correcto. | Radar: epoch UTC y `fromtimestamp(..., timezone.utc)`. Heatmap: `datetime.now(timezone.utc)`. Calendario: ISO con `Z`; el FOMC a las 14:00 ET lo confirma. Falta comprobar la carga histórica de calendario y snapshots. | 🟡 | A10 | Una segunda concentración desplazada 5 h indicaría duplicados. |
| **H16** | El "momentum equity" está **sesgado a tecnología**. | ~34 de ~70 acciones, más MSTR y MARA; solo XLE y VGT como ETF sectoriales. | ✅ | — | Requiere ETF sectoriales y amplitud. |
| **H17** | Una cadencia de 3 min basta para **barras de 15 min** (~5 ticks). | Nominal; H8 sugiere ciclos irregulares. | 🟡 | `n_ticks` por barra | Marcar barras con < 3 ticks. |
| **H18** | Los **endpoints no oficiales** pueden cambiar sin aviso. | Precedentes: `Content-Type` incorrecto daba `d[]` vacío, el payload completo daba 400 y `sectorTranslated` desapareció. | ✅ (riesgo) | M-OPS-02 | Validar forma de cada respuesta y alertar. |
| **H19** | `volume|TF` y `change|TF` describen la **vela en formación**. | BTC a las 05:30: `volume|5 = |15 = |30 = 2,318` (las tres velas acaban de abrir) y `change|5 = |15 = |30`. | 🟡 | T4 | Solo se pueden usar con la regla de cierre de barra. |
| **H20** | `close|TF` incluye operaciones **fuera de sesión** y `close` base no. | AAPL: 336,13 frente a 335,58; BTC y EURUSD coinciden. | 🟡 | T3 | Camino para obtener precio de pre-apertura sin `premarket_*`. |
| **H21** | Los indicadores `|TF` se **repintan** hasta el cierre de la vela. | Comportamiento estándar de TradingView; RSI base de BTC cambia con el precio. | 🟡 | T4 | Regla de cierre de barra obligatoria (M-CAP-03). |
| **H22** | `Pivot.M.Camarilla.R3` base es un nivel de **rango amplio** (probablemente mensual); con sufijo, `|5/|15` serían pivotes **diarios** y `|30/|60` **semanales**. | Con `R3 = C + 1,1·(H−L)/4`, NVDA (R3 − cierre = 10,56) implica H−L ≈ 38 (~17,5 % del precio) y BTC ≈ 12,6 %: improbables para un día (tomando C ≈ precio actual). Con sufijo, los valores se agrupan en pares idénticos (`|5 = |15`, `|30 = |60`) en BTC, AAPL y EURUSD, compatible con una selección automática de período según el timeframe. | 🟡 | T6 | Si se confirma, los pivotes diarios de TradingView estarían disponibles en `|15` sin calcularlos; el base sirve de contexto mensual. |
| **H23** | `ADX` base no se recalcula dentro de la sesión. | BTC: estable en 5 muestras de 50 s con el precio moviéndose (un solo símbolo). | 🟡 | T4 con `ADX|15` | Evita esperar variaciones intradía en `ADX` base. |
| **H24** | El endpoint refresca **acciones en horario** cada 10–30 s. | Solo medido en BTC (tiempo real); AAPL y EURUSD estaban cerrados. | 🔴 | T7 | Define la cadencia útil del radar (ver E-RAD-03). |

---

## 10. Dudas abiertas y decisiones pendientes

### 10.1 Dudas

| ID | Duda | Por qué importa | Cómo resolverla |
| --- | --- | --- | --- |
| **Q1** | ¿Hay una **fuente en tiempo real** (API de broker o de datos de mercado) para 5–10 símbolos críticos (SPY, QQQ, VIX, NQ/ES, US10Y)? | Decide si la entrada depende solo de TradingView (D1). | Decisión del usuario |
| **Q2** | ¿Se operan solo acciones y ETF de EE. UU. o también futuros (ES/NQ) y FX? | Define captura fuera de ventana y universo. | Decisión del usuario |
| **Q3** | ¿Qué decisión concreta debe apoyar el dashboard y con qué horizonte? | Define el MVP (M-DSH-03). | Decisión del usuario |
| **Q4** | ¿El cambio a UTC se aplicó también al histórico (2,4 M de filas, 579 eventos, snapshots)? | Evita duplicados desplazados 5 h. | A10 y revisar los cargadores `load_*_csv_to_db` |
| **Q5** | ¿Cómo es el **crontab real** (horarios, `TZ`) y quién ejecuta `scrapper_heatmap_v1.py`? | Solo hay 3 snapshots: el heatmap parece manual. | `crontab -l`, `echo $TZ` |
| **Q6** | ¿Qué símbolos devuelven campos nulos o rezagados (`CBOE`, `ICEUS`, `SAXO`, `CME_MINI`)? | Exchanges con datos de pago pueden dar `null` o mayor retraso. | A11 |
| **Q7** | ¿Existen ticks del radar posteriores a las 14:25 (Lima) del 2026-09-18? ¿Qué mide `sync_checkpoint.last_timestamp`? | El cron declara viernes hasta las 16:59. | `max(timestamp_utc)` por día; leer el código |
| **Q8** | ¿Cuántos eventos con importancia 1 tienen `actual` y `forecast` (sorpresa computable)? | Tamaño de muestra de M-VAL-03. | A9 |
| **Q9** | ¿El `event_repository.py` real rellena `captured_at` en eventos en vivo? | H10, H12. | Leer el código y A4 |
| **Q10** | ¿Cuánto histórico de ticks conservar? (ticks ≈ 0,35–0,5 GB/mes; snapshots ≈ 1,1 GB/mes en ventana o ≈ 5,2 GB/mes 24 h). | Retención y costo. | D8 |
| **Q11** | ¿Se mantiene el Streamlit de `proy_heatmap` junto al dashboard v2? | Evita duplicar lógica. | D9 |
| **Q12** | ¿Se expondrá el dashboard fuera de `localhost` (puerto 8100)? | Autenticación y rol de solo lectura. | Decisión de despliegue |
| **Q13** | ¿Es aceptable depender de endpoints no oficiales de TradingView para una herramienta de trading? Conviene revisar sus términos de uso y definir un plan B. | Riesgo operativo y legal de la fuente única (H18). | Revisión propia |
| **Q14** | ¿Debe reactivarse `fact_market_series.raw_payload` (hoy 100 % nulo)? | Reproducibilidad frente a ~366 MB/mes (roadmap 3.1.0). | D8 |
| **Q15** | ¿Qué devuelven exactamente `volume|TF` y `change|TF` (vela en formación o cerrada)? | H19. | T4 |
| **Q16** | ¿El `POST` a `/scan` acepta sufijos de TF en `columns` y `symbols.tickers`? | Permite combinar M-CAP-02 y M-CAP-03 en una sola petición. | T5 |
| **Q17** | ¿Qué período usa cada variante de `Pivot.M.Camarilla.R3` (base, `|5/|15`, `|30/|60`) y existen columnas `Pivot.D.*` y `Pivot.W.*`? | H22. | T6 |
| **Q18** | ¿`get_heatmap_last_hour()` (o equivalente del servicio del heatmap) filtra con una ventana fija de 1 hora? | Con snapshots hoy espaciados > 1 h (§5.6), la consulta devolvería 0 filas la mayor parte del tiempo y el panel quedaría vacío sin causa visible, incluso después de resolver E-HM-03 (Anexo G.4, punto 1). | Leer `heatmap_service.py` (no incluido en §2.1) |
| **Q19** | ¿`fetch_price_evolution()` (o equivalente) arma las columnas de la serie con una clave `HH:MM` sin la fecha? | Si es así, dos snapshots de días distintos a la misma hora se sobrescribirían al agregarse en la misma tabla (Anexo G.4, punto 2) | Leer el código del servicio de evolución de precio (no incluido en §2.1) |
| **Q20** | ¿Existe una ruta de cálculo (por ejemplo `safe_int` sobre un `event_id`) que pueda hacer que `max(...)` reciba un `None` y lance `TypeError`? | El cálculo de checkpoint que sí está en `calendario_tradingview_live_v5.py` ya usa `max()` sobre fechas dentro de un `except:` desnudo (E-CAL-01), así que ahí un `TypeError` quedaría silenciado, no propagado; la ruta descrita en Anexo G.4 (punto 3) parece referirse a otro módulo | Leer `application/event_service.py` (no incluido en §2.1) |
| **Q21** | ¿`event_service.process_calendar_batch()` vuelve a llamar a `guardar_checkpoint()` de forma independiente al que ya se ejecuta al final de `capturar_eventos()`? | En el código disponible, `capturar_eventos()` llama a `guardar_checkpoint()` **una sola vez** por ejecución (rama vacía en la línea 409 o cierre normal en la línea 446), nunca dos veces; si la doble escritura existe, se origina en `event_service.py`, que no forma parte de §2.1 (Anexo G.4, punto 4) | Leer `application/event_service.py` |

### 10.2 Decisiones

| ID | Decisión | Opciones | Recomendación | Depende de |
| --- | --- | --- | --- | --- |
| **D1** | Fuente de datos para la **decisión de entrada** | (a) Solo TradingView anónimo · (b) TradingView para contexto + fuente en tiempo real para 5–10 símbolos | **(b)** si H1 se confirma: el contexto tolera 15 min de retraso; la entrada no | Q1, H1 |
| **D2** | Fuente canónica de **VIX** | `TVC:VIX` (spot) · `CBOE:VX1!` (futuro con roll) | **Ambas con roles distintos:** spot para nivel y percentil; futuro para pre-apertura | Q6 |
| **D3** | Fuente canónica de **DXY** | `TVC:DXY` (validar) · `ICEUS:DX1!` · `AMEX:UUP` | Índice o futuro para pre-apertura; `UUP` solo como respaldo en sesión | H7 |
| **D4** | **Indicadores de 15 min** | (a) TradingView `|TF` · (b) cálculo propio · (c) híbrido | **(c)** durante 5–10 sesiones (M-VAL-04), siempre con la regla de cierre de barra | H2, H19–H21 |
| **D5** | **Cadencia del heatmap** | 5 · 15 min | 15 min alineado al cierre de barra, más un snapshot de pre-apertura | M-CAP-13 |
| **D6** | **Universo del heatmap** | Top-N por capitalización con filtro de liquidez | NASDAQ/NYSE/AMEX, acciones comunes, volumen en USD ≥ 20 M, N entre 600 y 800 | E-HM-01 |
| **D7** | `dim_asset`: **SCD2 real o Tipo 1** | Tipo 1 · SCD2 con unicidad parcial | Tipo 1 si no hay necesidad real de historial de atributos | I4 |
| **D8** | **Retención** de ticks y `raw_payload` | Todo a 3 min · agregar a barras de 15 min tras N meses | Ticks 6 meses; barras de 15 min indefinidas; `raw_payload` solo si hace falta | Q10, Q14 |
| **D9** | **Streamlit** existente | Coexistir · absorber en el dashboard v2 | Reutilizar los endpoints y retirar paneles duplicados | Q11 |
| **D10** | Presentación del **score** | Zonas COMPRAR/VENDER · solo contexto | **Solo contexto** hasta rechazar H13 | M-VAL-02 |
| **D11** | Librería de **calendario de sesiones** | `exchange_calendars` · `pandas_market_calendars` | `exchange_calendars` (XNYS) | M-DAT-01 |
| **D12** | **Ancho** de la captura multi-TF | Tabla ancha (`_1d`, `_5m`, `_15m`, `_30m`, `_1h`) · tabla larga con `tf` | **Tabla larga** (M-DAT-03), empezando por `15` y `5`; añadir `30`/`60` solo si M-VAL-02 los usa | D4 |

---

## 11. Plan por fases e hitos

### 11.1 Fases

| Fase | Objetivo | Mejoras incluidas | Salida (criterio) |
| --- | --- | --- | --- |
| **0a · Verificación por SQL** (domingo 2026-09-20) | Cerrar o reclasificar hipótesis que solo necesitan la BD | Consultas A1–A16 | H3, H4, H8, H9, H10, H11, H15 y Q4, Q6–Q8 actualizadas en §9 y §10 |
| **0b · Pruebas con mercado abierto** (lunes 2026-09-21) | Resolver lo que exige datos en vivo | Protocolo T1–T9 (Anexo C) | H1 (con referencia en tiempo real), H6, H7b, H19–H24, Q15–Q17; `CAMPOS` definitivo |
| **0c · Decisiones** | Fijar D1–D4 y responder Q1–Q3 | M-DOC-03 (ADR) | Registro de decisiones con fecha y motivo |
| **1 · Tiempo y operación** | Base temporal y operativa segura | M-DAT-01, M-DAT-07, M-CAP-01, M-CAP-04, M-OPS-01, M-OPS-03, M-OPS-04, M-DOC-01 | Gate probado con feriado, cierre anticipado y DST; auditoría por ciclo; roles separados |
| **2 · Captura fiable** | Ciclo corto, simultáneo y trazable | M-CAP-02, -03, -05 a -15; M-DAT-08; M-OPS-02 | Ciclo p95 ≤ 15 s; `update_mode` en 100 % de ticks; alertas de frescura activas |
| **3 · Modelo de 15 min** | Barras, indicadores por TF y calidad | M-DAT-02 a -06; M-VAL-01; M-VAL-05 | 28 barras/día/activo con ≥ 95 % de `n_ticks ≥ 3`; histórico reempaquetado |
| **4 · MVP del dashboard** | Cuatro paneles utilizables en sesión | M-DSH-01, -02, -03, -07, -08, -09 | Paneles con datos reales y banner de frescura |
| **5 · Validación y score** (en paralelo con 4) | Saber si el score aporta | M-VAL-02, -03, -04; M-DSH-04, -05, -06; M-DAT-09, -10, -11 | Informe walk-forward; decisión D4 y D10 cerradas |
| **6 · Calidad, seguridad y retención** | Cerrar deuda y proteger | M-CAP-16, -17; M-DAT-12, -13; M-OPS-05, -06; M-DOC-02, -04 | Retención aplicada, backups probados, documentación alineada |

### 11.2 Hitos con fecha

| Fecha | Acción | Criterio de aceptación |
| --- | --- | --- |
| **2026-09-20 (dom)** | Ejecutar A1–A16 | Tabla de §9 actualizada con los resultados |
| **2026-09-21 (lun)** | Protocolo del Anexo C durante la sesión (13:00–20:00 UTC) | H1, H6, H7b, H19–H24 y Q15–Q17 cerradas; `CAMPOS` definitivo |
| **2026-09-25 (vie)** | Registrar D1–D4 | ADR publicado |
| **2026-09-30** | **Chequeo A5 obligatorio** antes del cierre de mes | Límites de partición contiguos, sin solapes |
| **2026-10-16** (orientativa) | Fin de la Fase 1 | Gate probado; auditoría por ciclo; roles separados |
| **2026-10-31** | Gate por calendario NYSE en producción y probado con fecha simulada 2026-11-02 | Suite de M-OPS-04 en verde |
| **2026-12-31** | Crear particiones 2027 | Existen hasta `2027_12` |
| **2027-03-13** | Revalidar el gate ante el inicio del horario de verano (2027-03-14) | Suite de M-OPS-04 en verde |

---

## 12. Trazabilidad

| Hipótesis | Decisión | Errores | Mejoras |
| --- | --- | --- | --- |
| H1 | D1 | E-RAD-02 | M-CAP-04, M-DSH-02 |
| H2 | D4 | E-RAD-01 | M-CAP-03, M-DAT-03, M-VAL-04 |
| H3 | — | E-DSH-02 | M-DSH-05, M-DAT-02 |
| H4 | — | E-OPS-01 | M-CAP-01, M-DAT-01 |
| H5 | — | E-BD-03 | M-DAT-08, M-CAP-14, M-DOC-02 |
| H6, H20 | — | E-RAD-01 | M-CAP-09 |
| H7 | D3, D4 | E-RAD-03 | M-CAP-02, M-CAP-08, M-CAP-09 |
| H8 | — | E-RAD-03, E-RAD-04 | M-CAP-02, M-CAP-05 |
| H9 | — | — | A8 |
| H10 | — | E-CAL-02 | M-DAT-08 |
| H11 | — | E-BD-02 | M-DAT-07 |
| H12 | — | E-CAL-03 | M-CAP-14 |
| H13 | D10 | E-DSH-01 | M-VAL-02, M-DSH-04 |
| H14 | — | E-BD-05 | M-VAL-03, M-DAT-10 |
| H15 | — | (Q4) | M-VAL-01 |
| H16 | — | E-RAD-07 | M-CAP-08, M-DSH-06 |
| H17 | — | E-BD-01 | M-DAT-02, M-VAL-01 |
| H18 | — | E-OPS-03 | M-OPS-02 |
| H19, H21, H23 | D4, D12 | E-RAD-01 | M-CAP-03 |
| H22 | — | E-RAD-01 | M-DAT-02 (pivotes propios) |
| H24 | — | E-RAD-03 | M-CAP-02 |

---

## 13. Riesgos

| ID | Riesgo | Prob. | Impacto | Mitigación |
| --- | --- | --- | --- | --- |
| **R1** | El retraso del feed no se puede resolver con TradingView anónimo y la entrada usa datos viejos | Alta | Alto | D1 (b); banner *as-of*; no operar con señales provisionales |
| **R2** | El endpoint no oficial cambia sin aviso y la captura se rompe en silencio | Media | Alto | Validar la forma de cada respuesta, alertas, tests de contrato y plan B (Q13) |
| **R3** | Sobreajuste del score | Alta | Alto | M-VAL-02, D10 (solo contexto) |
| **R4** | Bloqueo por rate limit al aumentar peticiones (calendario cada minuto, `/scan`) | Media | Alto | El `POST` único reduce 110 peticiones a 1; jitter, backoff y monitoreo de 429 |
| **R5** | El cambio de horario del 1-nov desalinea las ventanas si el gate no está desplegado | Alta si no se actúa | Medio | M-CAP-01, M-OPS-04 (hito 2026-10-31) |
| **R6** | Inserts sin partición en el cambio de mes o desde 2027-01-01 | Media | Alto | M-DAT-07, hitos del 30-sep y 31-dic |
| **R7** | Crecimiento del almacenamiento (snapshots ≈ 5,2 GB/mes a 24 h) | Media | Medio | Gate, columnas explícitas, retención (D8) |
| **R8** | Muestras pequeñas (≈ 20 sesiones de equity, 45 eventos): conclusiones frágiles | Alta | Medio | Intervalos de confianza, ampliar historial, no calibrar zonas |
| **R9** | Alcance excesivo del dashboard (nueve paneles) | Media | Medio | MVP de cuatro paneles (M-DSH-03) |
| **R10** | Exposición de credenciales y uso de superusuario | Media | Alto | M-OPS-03 |
| **R11** | Barras con H/L muestreados cada 3 min subestiman los extremos y dimensionan mal los stops | Alta | Medio | Documentarlo; valorar ATR y OHLC de TradingView (`|15`) para stops |
| **R12** | Señales falsas por indicadores `|TF` repintados dentro de la vela | Alta | Alto | Regla de cierre de barra (M-CAP-03) |

## 14. Criterios de aceptación y KPIs

| KPI | Definición | Objetivo | Fuente |
| --- | --- | --- | --- |
| Frescura de ingesta | `now() − max(ingested_at)` durante la ventana | p95 ≤ 60 s | Monitoreo (M-OPS-02) |
| Antigüedad efectiva del dato | `ingested_at − (timestamp_utc − feed_delay_s)` | Visible en el dashboard | M-CAP-04, M-DSH-02 |
| Duración del ciclo del radar | Fin − inicio por `cycle_id` | p95 ≤ 15 s (`POST`); ≤ 150 s (`GET`) | `audit_sync_run` |
| Ciclos saltados sin registro | Ciclos con lock ocupado sin fila de auditoría | 0 | M-OPS-01 |
| Completitud en ventana | Ticks recibidos / esperados (110 × 140) | ≥ 98 % | M-VAL-01 |
| Barras válidas | Barras con `n_ticks ≥ 3` | ≥ 95 % | M-DAT-02 |
| Duplicados | Filas repetidas por `(asset_id, timestamp_utc)` | 0 | M-VAL-01 |
| Éxito de escritura en BD | Ciclos escritos o reconciliados en ≤ 24 h | 100 % | M-CAP-06 |
| Snapshots del heatmap | Por sesión / fuera de sesión | 28 / 0 | M-CAP-13 |
| Universo del heatmap | Símbolos OTC en el último snapshot | 0 | A12 |
| Latencia del `actual` | `actual_first_seen_at − event_timestamp` en eventos de alto impacto | p95 ≤ 90 s | M-DAT-08 |
| Gate de sesión | Casos de prueba superados (feriado, cierre anticipado, DST) | 100 % | M-OPS-04 |
| Particiones | Antelación de la partición del mes siguiente | ≥ 15 días | M-DAT-07 |
| Transparencia del dashboard | Paneles que muestran `as_of` | 100 % | M-DSH-02 |
| Seguridad | Secretos en documentos; permisos de escritura del dashboard | 0; ninguno | M-OPS-03 |

---

## 15. Anexos

## Anexo A · Consultas de verificación

> Las consultas **no se han ejecutado**: están escritas contra los nombres de tabla y columna del informe de la BD (2026-09-18). Ajusta símbolos y fechas si difieren. Conviene versionarlas como un archivo `.sql` en el repositorio.
> 

**A1 · Ticks fuera de sesión (H4, E-OPS-01).** Ticks y precios distintos por hora ET; fuera de sesión los `closes_distintos` deberían ser 1.

sql

```sql
SELECT date_trunc('hour', s.timestamp_utc AT TIME ZONE 'America/New_York') AS hora_et,
       count(*) AS ticks, count(DISTINCT s.close) AS closes_distintos
FROM fact_market_series s JOIN dim_asset a USING (asset_id)
WHERE a.symbol = 'NASDAQ:NVDA'
  AND s.timestamp_utc >= '2026-09-17 04:00+00' AND s.timestamp_utc < '2026-09-18 04:00+00'
GROUP BY 1 ORDER BY 1;
```

**A2 · Volumen acumulado (H3).** Debe crecer durante la sesión y reiniciarse; busca deltas negativos.

sql

```sql
SELECT s.timestamp_utc AT TIME ZONE 'America/New_York' AS ts_et, s.volume,
       s.volume - lag(s.volume) OVER (ORDER BY s.timestamp_utc) AS delta
FROM fact_market_series s JOIN dim_asset a USING (asset_id)
WHERE a.symbol = 'NASDAQ:NVDA'
  AND s.timestamp_utc >= '2026-09-17 12:00+00' AND s.timestamp_utc < '2026-09-18 02:00+00'
ORDER BY s.timestamp_utc;
```

**A3 · Escala de importancia (H5, E-BD-03).**

sql

```sql
SELECT importance, count(*) AS n,
       array_agg(DISTINCT title) FILTER (WHERE title ~* 'non.?farm|cpi|fed interest|gdp|core pce|unemployment') AS ejemplos
FROM fact_economic_event
WHERE country = 'US'
GROUP BY 1 ORDER BY 1;
```

**A4 · `captured_at` nulo en eventos en vivo (H10, E-CAL-02).**

sql

```sql
SELECT date_trunc('day', first_seen_at) AS dia, count(*) AS eventos,
       count(*) FILTER (WHERE captured_at IS NULL) AS sin_captured_at
FROM fact_economic_event
GROUP BY 1 ORDER BY 1 DESC LIMIT 14;
```

**A5 · Límites de partición (H11, E-BD-02).** Ejecútala dos veces: con `SET TIME ZONE 'America/Lima';` y con `SET TIME ZONE 'UTC';`. Límites a las `00:00:00+00` indican criterio UTC; a las `05:00:00+00`, criterio de Lima.

sql

```sql
SELECT i.inhparent::regclass AS tabla, c.relname AS particion,
       pg_get_expr(c.relpartbound, c.oid) AS limites
FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
ORDER BY 1, 2;
```

**A6 · Duración del ciclo (H8).** Desfase entre cada tick de SPY (`AMEX`, de los primeros) y el siguiente tick de VIX (`TVC`, de los últimos). La mediana aproxima la duración del ciclo.

sql

```sql
WITH t AS (
  SELECT a.symbol, s.timestamp_utc
  FROM fact_market_series s JOIN dim_asset a USING (asset_id)
  WHERE a.symbol IN ('AMEX:SPY', 'TVC:VIX')
    AND s.timestamp_utc >= '2026-09-17 14:00+00' AND s.timestamp_utc < '2026-09-17 15:00+00')
SELECT p.timestamp_utc AS spy,
       min(v.timestamp_utc) - p.timestamp_utc AS desfase
FROM t p JOIN t v ON v.symbol = 'TVC:VIX' AND v.timestamp_utc >= p.timestamp_utc
WHERE p.symbol = 'AMEX:SPY'
GROUP BY p.timestamp_utc ORDER BY 1;
```

**A7 · Huecos entre ticks (H8, H17).**

sql

```sql
WITH g AS (
  SELECT s.timestamp_utc - lag(s.timestamp_utc) OVER (ORDER BY s.timestamp_utc) AS gap
  FROM fact_market_series s JOIN dim_asset a USING (asset_id)
  WHERE a.symbol = 'AMEX:SPY'
    AND s.timestamp_utc >= '2026-09-14 13:00+00' AND s.timestamp_utc < '2026-09-18 21:00+00')
SELECT percentile_cont(ARRAY[0.5, 0.9, 0.99]) WITHIN GROUP (ORDER BY gap) AS p50_p90_p99,
       max(gap) AS gap_max,
       count(*) FILTER (WHERE gap > interval '4 minutes') AS huecos_mayores_4_min
FROM g;
```

**A8 · Cierres redondos y nulos (H9).**

sql

```sql
SELECT a.symbol, count(*) AS n, count(DISTINCT s.close) AS distintos,
       count(*) FILTER (WHERE s.close = round(s.close)) AS enteros,
       count(*) FILTER (WHERE s.close IS NULL) AS nulos
FROM fact_market_series s JOIN dim_asset a USING (asset_id)
WHERE a.symbol IN ('TVC:VIX', 'CBOE:VX1!', 'TVC:US10Y', 'TVC:US02Y')
  AND s.timestamp_utc >= now() - interval '7 days'
GROUP BY 1;
```

**A9 · Sorpresas computables (Q8, H14).**

sql

```sql
SELECT importance, count(*) AS total,
       count(*) FILTER (WHERE actual_raw IS NOT NULL AND forecast_raw IS NOT NULL) AS con_sorpresa
FROM fact_economic_event
GROUP BY 1 ORDER BY 1;
```

**A10 · UTC del histórico (H15, Q4).** Los `closes_distintos` deben concentrarse entre las 13:00 y las 21:00 UTC; una segunda concentración desplazada 5 h indicaría datos duplicados o mal etiquetados.

sql

```sql
SELECT date_trunc('hour', s.timestamp_utc AT TIME ZONE 'UTC') AS hora_utc,
       count(*) AS ticks, count(DISTINCT s.close) AS closes_distintos
FROM fact_market_series s JOIN dim_asset a USING (asset_id)
WHERE a.symbol = 'NASDAQ:NVDA'
  AND s.timestamp_utc >= '2026-09-17 00:00+00' AND s.timestamp_utc < '2026-09-19 00:00+00'
GROUP BY 1 ORDER BY 1;
```

**A11 · Nulos por símbolo (Q6, E-RAD-04).**

sql

```sql
SELECT a.symbol, count(*) AS n,
       round(100.0 * count(*) FILTER (WHERE s.close  IS NULL) / count(*), 2) AS pct_close_nulo,
       round(100.0 * count(*) FILTER (WHERE s.rsi    IS NULL) / count(*), 2) AS pct_rsi_nulo,
       round(100.0 * count(*) FILTER (WHERE s.volume IS NULL) / count(*), 2) AS pct_volumen_nulo
FROM fact_market_series s JOIN dim_asset a USING (asset_id)
WHERE s.timestamp_utc >= now() - interval '7 days'
GROUP BY 1
HAVING count(*) FILTER (WHERE s.close IS NULL OR s.rsi IS NULL) > 0
ORDER BY pct_close_nulo DESC, pct_rsi_nulo DESC;
```

**A12 · Composición del último snapshot (E-HM-01).**

sql

```sql
SELECT a.exchange, a.share_class, count(*) AS n
FROM fact_heatmap_snapshot h JOIN dim_asset a USING (asset_id)
WHERE h.timestamp_utc = (SELECT max(timestamp_utc) FROM fact_heatmap_snapshot)
GROUP BY 1, 2 ORDER BY n DESC;
```

**A13 · Índices sin uso (E-BD-08).**

sql

```sql
SELECT relname AS tabla, indexrelname AS indice, idx_scan,
       pg_size_pretty(pg_relation_size(indexrelid)) AS tamano
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC
LIMIT 30;
```

**A14 · `logo_id` nulo por origen (E-HM-05).**

sql

```sql
SELECT source_discovered_by, count(*) AS n, count(*) FILTER (WHERE logo_id IS NULL) AS sin_logo
FROM dim_asset GROUP BY 1;
```

**A15 · Auditoría por script y estado (E-RAD-05, E-OPS-03).**

sql

```sql
SELECT script_name, status, count(*) AS corridas, min(run_start) AS primera, max(run_start) AS ultima
FROM audit_sync_run GROUP BY 1, 2 ORDER BY 1, 2;
```

**A16 · Índices de `dim_asset` (E-BD-04).**

sql

```sql
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'dim_asset' ORDER BY indexname;
```

---

## Anexo B · Fragmentos de corrección

> Fragmentos de referencia, no probados contra el repositorio. Las dependencias son `exchange_calendars`, `pandas` y las ya usadas por los scripts.
> 

### B.1 Gate de sesión (M-CAP-01)

python

```python
import sys
import pandas as pd
import exchange_calendars as xcals

XNYS = xcals.get_calendar("XNYS")

def en_ventana(pre_min: int = 30, ahora: pd.Timestamp | None = None) -> bool:
    """True si `ahora` está entre (apertura − pre_min) y el cierre de una sesión NYSE."""
    ahora = ahora or pd.Timestamp.now(tz="UTC")
    dia_et = ahora.tz_convert("America/New_York").normalize().tz_localize(None)
    if not XNYS.is_session(dia_et):
        return False                                  # fin de semana o feriado
    abre = XNYS.session_open(dia_et)                  # UTC, tz-aware
    cierra = XNYS.session_close(dia_et)               # respeta cierres anticipados
    return abre - pd.Timedelta(minutes=pre_min) <= ahora <= cierra

# Al inicio de main() del radar y del heatmap:
if not en_ventana():
    sys.exit(0)
# El calendario usa en_ventana(pre_min=90) para arrancar a las 08:00 ET.
```

Casos de prueba (M-OPS-04):

python

```python
import pytest, pandas as pd

@pytest.mark.parametrize("ts, esperado", [
    ("2026-09-21 12:59:00+00:00", False),  # 08:59 ET (EDT)
    ("2026-09-21 13:00:00+00:00", True),   # 09:00 ET
    ("2026-09-21 20:00:00+00:00", True),   # 16:00 ET, cierre
    ("2026-09-21 20:01:00+00:00", False),
    ("2026-11-02 13:59:00+00:00", False),  # 08:59 ET (EST, tras el cambio de horario)
    ("2026-11-02 14:00:00+00:00", True),   # 09:00 ET (EST)
    ("2026-11-26 15:00:00+00:00", False),  # Acción de Gracias
    ("2026-11-27 17:30:00+00:00", True),   # 12:30 ET, antes del cierre anticipado
    ("2026-11-27 18:01:00+00:00", False),  # tras el cierre anticipado de las 13:00 ET
])
def test_en_ventana(ts, esperado):
    assert en_ventana(ahora=pd.Timestamp(ts)) is esperado
```

### B.2 Heatmap: parseo por nombre y filtro de universo (M-CAP-10, M-CAP-11)

python

```python
COLS = config.HEATMAP_COLUMNS
ALLOWED_EXCHANGES = {"NASDAQ", "NYSE", "AMEX"}

def _tipo(r):
    t = r["typespecs"]
    return t[0] if isinstance(t, list) and t else (t or "")

def parse_vector(d):
    if not isinstance(d, list) or len(d) != len(COLS):
        return None                       # registrar: el layout de la fuente cambió
    r = dict(zip(COLS, d))
    return {
        "share_class": _tipo(r),
        "daily_change_pct": round_value(r["change"]),
        "market_cap": round_value(r["market_cap_basic"], 2),
        "sector": r["sector"],
        "logo_id": r["logoid"] if isinstance(r["logoid"], str) else None,   # corrige E-HM-05
        "price_heatmap": round_value(r["close"]),
        "ticker": r["name"],
        "stream_status": r["update_mode"],
        "raw_vector": [round_value(v) if isinstance(v, float) else v for v in d],
    }

def is_tradeable(item, min_dollar_vol=20_000_000):
    d = item.get("d") or []
    if len(d) != len(COLS):
        return False
    r = dict(zip(COLS, d))
    dollar_vol = (r["average_volume_30d_calc"] or 0) * (r["close"] or 0)
    return (item["s"].split(":")[0] in ALLOWED_EXCHANGES
            and _tipo(r) == "common"
            and dollar_vol >= min_dollar_vol)

# En fetch_heatmap_data(): filtrar primero y recortar después
# candidatos = [i for i in rows if is_tradeable(i)]
# top = filter_top_by_market_cap(candidatos, config.HEATMAP_MAX_SYMBOLS)
```

### B.3 Eventos: upsert condicional (M-DAT-08)

sql

```sql
ALTER TABLE fact_economic_event ADD COLUMN IF NOT EXISTS actual_first_seen_at timestamptz;

INSERT INTO fact_economic_event (event_id, /* ...columnas... */ payload_checksum, captured_at)
VALUES %s
ON CONFLICT (event_id) DO UPDATE SET
    actual         = COALESCE(EXCLUDED.actual,         fact_economic_event.actual),
    actual_raw     = COALESCE(EXCLUDED.actual_raw,     fact_economic_event.actual_raw),
    actual_display = COALESCE(EXCLUDED.actual_display, fact_economic_event.actual_display),
    forecast_raw   = COALESCE(EXCLUDED.forecast_raw,   fact_economic_event.forecast_raw),
    /* ...resto de columnas... */
    actual_first_seen_at = CASE
        WHEN fact_economic_event.actual_raw IS NULL AND EXCLUDED.actual_raw IS NOT NULL
        THEN CURRENT_TIMESTAMP ELSE fact_economic_event.actual_first_seen_at END,
    payload_checksum = EXCLUDED.payload_checksum,
    last_updated_at  = CURRENT_TIMESTAMP
WHERE fact_economic_event.payload_checksum IS DISTINCT FROM EXCLUDED.payload_checksum;
```

Además, `captured_at = now()` en el servicio, ya que el evento crudo no trae `timestamp_captura`.

### B.4 `CAMPOS` multi-TF (M-CAP-03)

python

```python
BASE = "close,volume,RSI,CCI20,BBPower,ADX,Pivot.M.Camarilla.R3,Perf.W,change"

def _bloque(tf: str) -> str:
    # Excluidos: Perf.W|TF y |1D (devuelven None) y close|TF (se decide tras T3; H20).
    # Pivot.M.Camarilla.R3|TF sí responde: |5 y |15 coinciden entre sí, y |30 y |60 también (H22, T6).
    campos = ("volume", "RSI", "CCI20", "BBPower", "ADX", "change", "Pivot.M.Camarilla.R3")
    return ",".join(f"{c}|{tf}" for c in campos)

CAMPOS = ",".join([BASE, _bloque("5"), _bloque("15")])   # añadir "30" y "60" solo si M-VAL-02 los usa
# CAMPOS += ",update_mode"        # validar en T1 (H7b)
```

Antes de descartar `close|TF`, ejecutar T3: en AAPL difiere del `close` base (H20).

### B.5 Modelo de 15 min (M-DAT-01, M-DAT-02, M-DAT-03)

sql

```sql
-- Sesiones NYSE
CREATE TABLE dim_trading_session (
    session_date   date        PRIMARY KEY,          -- fecha ET
    open_utc       timestamptz NOT NULL,
    close_utc      timestamptz NOT NULL,
    is_early_close boolean     NOT NULL DEFAULT false,
    calendar       text        NOT NULL DEFAULT 'XNYS'
);
```

python

```python
# Carga (una vez al año y en el arranque de M-OPS-01)
cal = xcals.get_calendar("XNYS")
sch = cal.schedule.loc["2026-01-01":"2027-12-31"]           # columnas open / close en UTC
early = set(cal.early_closes.strftime("%Y-%m-%d"))
rows = [(d.date(), r["open"].to_pydatetime(), r["close"].to_pydatetime(),
         d.strftime("%Y-%m-%d") in early) for d, r in sch.iterrows()]
# INSERT ... ON CONFLICT (session_date) DO UPDATE SET open_utc = EXCLUDED.open_utc, ...
```

sql

```sql
-- Barras de 15 min
CREATE TABLE fact_market_bar_15m (
    asset_id      integer      NOT NULL,
    bar_start_utc timestamptz  NOT NULL,
    session_date  date         NOT NULL,
    open numeric(20,8), high numeric(20,8), low numeric(20,8), close numeric(20,8),
    volume_delta  numeric(30,8),
    n_ticks       smallint     NOT NULL,
    is_regular    boolean      NOT NULL,
    PRIMARY KEY (asset_id, bar_start_utc)
) PARTITION BY RANGE (bar_start_utc);

-- Agregación incremental (:desde / :hasta en UTC). Los H/L salen de muestras de 3 min y subestiman los extremos.
WITH t AS (
    SELECT s.asset_id, s.timestamp_utc, s.close, s.volume,
           date_bin('15 minutes', s.timestamp_utc, TIMESTAMPTZ '2001-01-01 00:00:00+00') AS bar_start,
           (d.session_date IS NOT NULL) AS is_regular
    FROM fact_market_series s
    LEFT JOIN dim_trading_session d
           ON s.timestamp_utc >= d.open_utc AND s.timestamp_utc < d.close_utc
    WHERE s.timestamp_utc >= :desde AND s.timestamp_utc < :hasta
), b AS (
    SELECT asset_id, bar_start, bool_and(is_regular) AS is_regular,
           (array_agg(close  ORDER BY timestamp_utc ASC ))[1] AS open,
           max(close) AS high, min(close) AS low,
           (array_agg(close  ORDER BY timestamp_utc DESC))[1] AS close,
           (array_agg(volume ORDER BY timestamp_utc DESC))[1] AS vol_cum_end,
           count(*)::smallint AS n_ticks
    FROM t GROUP BY asset_id, bar_start
)
SELECT asset_id, bar_start AS bar_start_utc,
       (bar_start AT TIME ZONE 'America/New_York')::date AS session_date,
       open, high, low, close,
       COALESCE(vol_cum_end - lag(vol_cum_end) OVER (
                    PARTITION BY asset_id, (bar_start AT TIME ZONE 'America/New_York')::date
                    ORDER BY bar_start), vol_cum_end) AS volume_delta,
       n_ticks, is_regular
FROM b;
```

sql

```sql
-- Indicadores por timeframe en formato largo
CREATE TABLE fact_market_indicator_tf (
    asset_id       integer     NOT NULL,
    timestamp_utc  timestamptz NOT NULL,
    tf             varchar(3)  NOT NULL,             -- '5' | '15' | '30' | '60'
    rsi numeric(12,6), cci20 numeric(14,6), bbpower numeric(20,8),
    adx numeric(12,6), change_pct numeric(12,8), volume numeric(30,8),
    pivot_r3 numeric(20,8),
    PRIMARY KEY (asset_id, timestamp_utc, tf)
) PARTITION BY RANGE (timestamp_utc);
```

**Regla de cierre de barra (H21).** El valor de `RSI|15` en un tick corresponde a la vela en formación. Para aproximar el valor definitivo de una barra se toma el **último tick anterior a su frontera**, que con cadencia de 3 min queda hasta ~3 min antes del cierre. Para un valor más fiel, añadir un muestreo dedicado a T−10 s de cada cuarto de hora (`:14:50`, `:29:50`, `:44:50`, `:59:50`). Con un retraso de exactamente 900 s la alineación con la frontera se conserva, pero el dato corresponde a la barra anterior.

sql

```sql
SELECT DISTINCT ON (asset_id, date_bin('15 minutes', timestamp_utc, TIMESTAMPTZ '2001-01-01 00:00+00'))
       asset_id, timestamp_utc, rsi, adx, cci20, bbpower
FROM fact_market_indicator_tf
WHERE tf = '15'
ORDER BY asset_id, date_bin('15 minutes', timestamp_utc, TIMESTAMPTZ '2001-01-01 00:00+00'), timestamp_utc DESC;
```

### B.6 `POST` a `/scan` para el radar (M-CAP-02; validar en T5, Q16)

json

```json
{
  "symbols": { "tickers": ["AMEX:SPY", "NASDAQ:QQQ", "TVC:VIX", "CME_MINI:NQ1!"] },
  "columns": ["close", "volume", "RSI", "RSI|15", "ADX|15", "CCI20|15", "BBPower|15",
              "change|15", "volume|15", "Pivot.M.Camarilla.R3", "Pivot.M.Camarilla.R3|15", "Perf.W", "update_mode"]
}
```

La respuesta trae `{"s": símbolo, "d": [...]}` en el orden de `columns`: mapear por nombre, igual que en B.2.

### B.7 Heatmap: dimensión y auditoría (M-CAP-12)

python

```python
# Cache de asset_id, una vez por corrida
def load_asset_cache(conn) -> dict:
    rows = conn.execute_query("SELECT symbol, asset_id FROM dim_asset")
    return {r["symbol"]: r["asset_id"] for r in rows}

# Alta masiva de símbolos nuevos (una sentencia), luego recargar el cache
# INSERT INTO dim_asset (symbol, ticker, exchange, asset_class, share_class, sector,
#                        company_name, logo_id, source_discovered_by)
# VALUES %s ON CONFLICT (symbol) DO NOTHING;

# Corrección de records_failed (E-HM-07)
records_failed = max((records_fetched or 0) - (records_upserted or 0), 0)
```

---

## Anexo C · Protocolo de pruebas con mercado abierto (lunes 2026-09-21)

> Horas del lunes 2026-09-21 (EDT = UTC−4; Lima = UTC−5): 09:00 ET = 13:00 UTC = 08:00 Lima; 09:30 ET = 13:30 UTC = 08:30 Lima. Extiende `wztest_scraper_timeframes.py` y registra cada muestra en un CSV con marca de tiempo UTC (segundos), símbolo, campo y valor.
> 

| # | Objetivo | Cuándo (ET · UTC · Lima) | Procedimiento | Criterio de decisión |
| --- | --- | --- | --- | --- |
| **T1** | `update_mode` de cada símbolo crítico (H1) | 09:35 · 13:35 · 08:35 | `GET /symbol` con `fields=close,update_mode` para `NASDAQ:NVDA`, `NASDAQ:AAPL`, `AMEX:SPY`, `NASDAQ:QQQ`, `CME_MINI:NQ1!`, `CME_MINI:ES1!`, `TVC:VIX`, `CBOE:VX1!`, `BINANCE:BTCUSDT`, `OANDA:XAUUSD` | Cualquier `delayed_streaming_*` confirma H1 para ese símbolo; `streaming` la descarta |
| **T2** | Retraso real frente a una referencia en tiempo real (H1) | 09:35–09:40 · 13:35–13:40 · 08:35–08:40 | 5 lecturas de `close` de SPY y NVDA, una por minuto, con su segundo exacto; buscar en la serie de 1 min de una fuente en tiempo real el minuto en que aparece ese precio | ≈ 900 s confirma H1; ≈ 0–30 s la descarta. Requiere una referencia (Q1); sin ella, decidir D1 por prudencia |
| **T3** | Precio de pre-apertura (H6, H20, H7b) | 09:00, 09:15 y 09:29 · 13:00, 13:15, 13:29 · 08:00, 08:15, 08:29 | Para NVDA, AAPL y SPY: `close`, `close|5`, `close|15`, `premarket_close`, `premarket_change`, `gap`, `update_mode` (los que existan) | Si `close` se mantiene en el cierre previo mientras `close|5` o `premarket_close` se mueven, H6 y H20 quedan confirmadas |
| **T4** | Repintado y frontera de barra (H19, H21, H23) | 09:44:30–09:46:00 · 13:44:30–13:46:00 · 08:44:30–08:46:00 | Cada 15–30 s sobre SPY: `RSI|15`, `ADX|15`, `CCI20|15`, `BBPower|15`, `volume|15`, `change|15`, más `RSI` y `ADX` base | `volume|15` cae a un valor pequeño a las 09:45 y `RSI|15` salta: H19 y H21 confirmadas. `ADX` base constante: H23 |
| **T5** | `/scan` por lotes con sufijos (Q16, H7b) | 09:50 · 13:50 · 08:50 | `POST` con el cuerpo de B.6 (10 tickers, columnas con sufijo) | HTTP 200 con `d` de la longitud de `columns` y sin `null` en los sufijos; latencia total < 5 s |
| **T6** | Período de cada variante de pivote (H22, Q17) | Cualquier hora | `Pivot.M.Camarilla.R3` base, `|5`, `|15`, `|30`, `|60` y variantes `Pivot.W.*` y `Pivot.D.*` (nombres por validar) en NVDA, AAPL y BTC; calcular a mano R3 con H/L/C del día, semana y mes previos | La coincidencia con el pivote diario, semanal o mensual identifica el período de cada variante |
| **T7** | Refresco del endpoint en acciones (H24) | 10:00–10:05 · 14:00–14:05 · 09:00–09:05 | `GET /symbol` de NVDA y AAPL con `fields=close,volume` cada 10 s (30 muestras) | Número de valores distintos y su separación definen la cadencia útil |
| **T8** | Fallos por exchange (Q6, E-RAD-04) | Todo el día | Agrupar por prefijo de exchange las líneas `FALLO` y `BLOQUEO 429` del log del radar | Exchanges con fallos recurrentes: prioridad y breaker por bloque |
| **T9** | Duración real del ciclo (H8) | Todo el día | Del log, tiempo entre `[1/110]` y `PROCESO FINALIZADO` en 20 ciclos | Confirma 1,8–2,4 min y fija la línea base del KPI |

---

## Anexo D · Layout del vector `d[]` del heatmap (v3)

Fuente: `HEATMAP_COLUMNS` (`config.py` del heatmap, `VERSION 1.0.2`). Es el layout que usa `parse_vector` y el que guarda `fact_heatmap_snapshot.raw_vector`. **Sustituye a `heatmap_stock_documentacion_campos.md`.**

| Índice | Columna del scanner | Contenido y observaciones | Se guarda en |
| --- | --- | --- | --- |
| 0 | `typespecs` | Lista o string (`common`, `preferred`…) | `share_class` |
| 1 | `change` | % de cambio diario | `daily_change_pct` |
| 2 | `change_abs` | Cambio absoluto | `raw_vector` |
| 3 | `Perf.1M` | Rendimiento 1 mes | `raw_vector` |
| 4 | `Perf.3M` | Rendimiento 3 meses | `raw_vector` |
| 5 | `Perf.6M` | Rendimiento 6 meses | `raw_vector` |
| 6 | `Perf.Y` | Rendimiento 1 año | `raw_vector` |
| 7 | `Perf.YTD` | Rendimiento en el año | `raw_vector` |
| 8 | `Volatility.D` | Volatilidad diaria | `raw_vector` |
| 9 | `price_52_week_high` | Máximo de 52 semanas | `raw_vector` |
| 10 | `price_52_week_low` | Mínimo de 52 semanas | `raw_vector` |
| 11 | `market_cap_basic` | Capitalización de mercado | `market_cap` |
| 12 | `average_volume_30d_calc` | Volumen medio de 30 días | `raw_vector` |
| 13 | `average_volume_10d_calc` | Volumen medio de 10 días | `raw_vector` |
| 14 | `volume` | **Acumulado del día** | `raw_vector` |
| 15 | `total_shares_outstanding` | Acciones en circulación | `raw_vector` |
| 16 | `total_shares_outstanding_fundamental` | Ídem, fuente fundamental | `raw_vector` |
| 17 | `number_of_employees` | Empleados | `raw_vector` |
| 18 | `earnings_per_share_basic_ttm` | BPA básico (12 meses) | `raw_vector` |
| 19 | `revenue_per_employee_ttm` | Ingresos por empleado | `raw_vector` |
| 20 | `gross_profit_1Y_growth_fq` | Crecimiento del beneficio bruto a 1 año | `raw_vector` |
| 21 | `sector` | Sector (en inglés; ya no llega traducido) | `sector` |
| 22 | `logoid` | **String** (`"nvidia"`), no dict | `logo_id` (hoy queda `NULL`; E-HM-05) |
| 23 | `close` | Precio | `price_heatmap` |
| 24 | `pricescale` | Factor de escala de precio (100) | `raw_vector` |
| 25 | `name` | Ticker (no el nombre de la empresa) | `ticker`, `company_name` |
| 26 | `update_mode` | `delayed_streaming_900` | `stream_status` |
| 27 | `currency` | Moneda | `raw_vector` |

---

## Anexo E · Universo propuesto para el radar

| Símbolo | Rol | Motivo | Validación |
| --- | --- | --- | --- |
| `CME_MINI:ES1!` | Futuro S&P 500 | Gap y pre-apertura del S&P; hoy solo está `NQ1!` | 🔴 disponibilidad y `update_mode` |
| `AMEX:XLK`, `XLF`, `XLV`, `XLY`, `XLP`, `XLI`, `XLU`, `XLRE`, `XLB`, `XLC` | ETF sectoriales SPDR | Rotación sectorial de 15 min (XLE ya existe) | 🟡 tickers de NYSE Arca (prefijo `AMEX` como el resto de ETF de la config) |
| `AMEX:IWM` | Small caps | Apetito de riesgo y amplitud | 🟡 |
| `AMEX:RSP` | S&P 500 equiponderado | Amplitud (RSP frente a SPY) | 🟡 |
| `TVC:DXY` | Índice del dólar | Referencia directa en lugar del proxy `UUP` | 🔴 (D3) |

---

## Anexo F · Errata y contrastes

### F.1 Correcciones al borrador `Roadmap_Integral_de_Mejoras___Ecosistema.md`

| # | Punto del borrador | Corrección |
| --- | --- | --- |
| 1 | Índice con 13 secciones; solo existían la 0 a la 7 | 36 IDs colgantes (`RAD`, `BD`, `HM`, `CAL`, `DSH`, `VAL`, `OPS`, `DOC`), consultas A1–A11 y Anexo D ausentes y enlace roto. Este informe los define todos |
| 2 | H8: "VIX (14:23:01) y NVDA (14:24:52) difieren ~1 min 50 s" como prueba de sesgo dentro del ciclo | Evidencia inválida: NVDA (`NASDAQ`) se captura antes que `TVC:VIX` en el mismo ciclo, así que son ciclos distintos. Se sustituye por la corroboración del checkpoint (§5.4) |
| 3 | H2 incluía `Pivot.M.Camarilla.R3` entre los indicadores "diarios" | Ese campo parece de rango amplio (probablemente mensual) y sus variantes con sufijo se agrupan por pares (H22) |
| 4 | H9: cierres exactos de VIX y US10Y como posible artefacto | Debilitada: VIX cotiza con 2 decimales y su `change_pct` es coherente con 15,45 → 15,00 |
| 5 | H3 en 🟡 | ✅ (AAPL 86,6 M con mercado cerrado) |
| 6 | H15 con dos estados en una celda | Un solo estado (🟡) con la nota del radar |
| 7 | I13: `.env` con `BD_HEATMAP_SERVER` frente a `HOST` | Obsoleta: el roadmap 3.1.0 la da por corregida y ambos `config.py` leen `HOST` |
| 8 | §3.3 asumía captura solo dentro de la ventana | Depende de Q2 (futuros, FX y cripto operan 24 h) |

### F.2 Contrastes con la evaluación incluida en `diagnostico_scrapper_v5_al_2026-09-19.md`

| Afirmación de la evaluación | Contraste | Evidencia |
| --- | --- | --- |
| "`close|TF` es invariante (H20 ✅)" | Falso para AAPL; se mantiene como H20 🟡 y se prueba en T3 antes de excluirlo de `CAMPOS` | AAPL: 336,13 (base) frente a 335,58 (`|5…|60`) |
| "H4 ✅, reforzada por AAPL y EURUSD congelados" | Un fin de semana no prueba lo que ocurre entre semana | EURUSD, BTC y oro operan 24 h en días hábiles |
| "La cadencia de 1×/min está bien dimensionada" | El cron real es cada 3 min y 110 `GET` secuenciales no caben en 1 min; el refresco de 10–30 s se midió solo en BTC | Pausas ≈ 87 s por ciclo; H24 |
| "`volume|TF` = última vela cerrada" | Indicios de vela en formación (H19) | BTC: `volume|5 = |15 = |30` a las 05:30 |
| "`Pivot.M…` es un pivote mensual" y "`Pivot.M.*|TF` tiene semántica ambigua: sacarlo del alcance" | Lo primero es plausible pero no probado. Lo segundo no se sostiene: las variantes con sufijo responden y se agrupan por pares, lo que sugiere pivotes diarios y semanales útiles para 15 min; se decide en T6 (H22) | `|5 = |15` y `|30 = |60` en BTC, AAPL y EURUSD |
| "H23 ✅ (ADX no se recalcula)" | 🟡: cinco muestras de 50 s en un solo símbolo | BTC |
| "H6, H7, H10, H11, H13 y H14 se resuelven en una jornada" | H10 y H11 se resuelven con SQL hoy; H13 y H14 exigen semanas de datos | Fases 0a y 5 |
| "Migrar a columnas `_1d/_5m/_15m/_30m/_1h`" | Formato largo con `tf` como clave (D12) | M-DAT-03 |
| "El histórico se reempaqueta sin perder nada" | Con salvedades: timestamp de captura, posible retraso, captura 24 h y equity solo desde 2026-08-22 | M-VAL-05 |

**Aportes adoptados de la evaluación:** `Perf.W\|TF` y `\|1D` no existen; incluir `\|30` como opción; tabla de trazabilidad H → D → mejora; Anexo A como `.sql` versionado; hitos con formato "fecha → acción → criterio"; separar la auditoría del plan vivo.

---

## Anexo G · Evaluación de la segunda revisión externa (2026-09-21)

> Se recibió una revisión de este informe con 8 hallazgos nuevos y 5 correcciones puntuales. Antes de incorporarlos se contrastó cada uno contra el **material realmente disponible** (§2.1). El resultado se resume aquí, por honestidad con lo que se pudo y no se pudo verificar: gran parte de los hallazgos nuevos se refieren a `application/market_service.py`, `application/event_service.py` y al servicio/Streamlit del heatmap, **ninguno de los cuales forma parte del material analizado** (§2.2). Sobre esos archivos solo puedo evaluar la plausibilidad lógica de la afirmación, no confirmarla.
> 

### G.1 · Matices aceptados y ya incorporados al cuerpo del informe

| Punto de la revisión | Veredicto | Evidencia propia | Dónde quedó |
| --- | --- | --- | --- |
| E-RAD-05 "el silencio es doble/triple" | **Aceptado, con precisión.** El código que sí tengo (`scraper_live_tradingview_v5.py`) confirma por sí solo dos de las tres capas: el `try/except` de `flush_radar_batch` y el hecho de que **su valor de retorno nunca se lee** antes de `batch_buffer.clear()`, tanto en el flush de cierre de ciclo como en el del circuit breaker. La tercera capa (que `process_radar_batch` ya capture sus propias excepciones, según cita un docstring que no tengo) queda como **no confirmada por mí**, aunque es plausible y no cambia la conclusión. | Código propio + cita del docstring (no verificable) | E-RAD-05, reescrita |
| E-HM-04 "subir de S3 a S2" | **Aceptado, pero reestructurado.** Ya estaba en S2 en la versión 1.0 (la revisión asumió que estaba en S3, error suyo — ver G.3). Se separó en dos hallazgos distintos porque mezclaban dos problemas de naturaleza diferente: E-HM-17 (S2, corrección: atributos que se congelan para siempre) y E-HM-04 (S3, rendimiento: volumen de escrituras y `updated_at` sin significado). | Código propio (`ON CONFLICT ... COALESCE`) | E-HM-17 (nueva), E-HM-04 (reescrita) |
| E-HM-07 "el bug está en `log_sync_run`, no en el llamador" | **Confirmado y corregido.** El código que tengo muestra `records_failed = ...` calculado dentro del cuerpo de `log_sync_run()`. | Código propio | Tabla §6.3, fila `E-HM-07` |
| E-HM-15 "`ticker = ... or ... if ... else ...`" | **Confirmado.** Verificado línea por línea contra `scrapper_heatmap_v1.py`; la precedencia de operadores es la descrita. | Código propio | Tabla §6.3, nueva fila `E-HM-15` |
| E-HM-16 "DDL antes de validar la API" | **Confirmado.** El orden `create_monthly_partitions() → fetch_heatmap_data() → validar` está tal cual en `main()`. | Código propio | Tabla §6.3, nueva fila `E-HM-16` |
| E-RAD-12 "`prepare_bd_row` no incluye `source_checksum`" | **Parcialmente contrastable.** No tengo `market_service.py`, pero el informe de la BD sí confirma que `source_checksum` está 100 % poblado en `fact_market_series` (vía el parámetro `p_source_checksum` de `upsert_market_series`), así que el cálculo ocurre en algún punto del pipeline. Que ese punto no sea `prepare_bd_row` es plausible pero no verificable con lo que tengo. Se trata como nota de trazabilidad, no como error. | Informe de BD (parcial) | Nota en G.4 |

### G.2 · Incorporado como duda, no como error confirmado

Los siguientes puntos se mueven a §10.1 (**Q18–Q21**) en vez de entrar al catálogo de errores, porque afirman el contenido de código que no está en el material analizado y que, en un caso, la evidencia disponible **contradice parcialmente**:

- **E-HM-13** (ventana de 1 h en el heatmap service) → **Q18**.
- **E-HM-14** (colisión de etiquetas `HH:MM` entre días) → **Q19**.
- **E-CAL-06** (`max(safe_int(...))` puede lanzar `TypeError`) → **Q20**. El texto de `calendario_tradingview_live_v5.py` que sí tengo no contiene ninguna variable `safe_int` ni `max_event_id`; el único `max()` del archivo (sobre fechas, para el checkpoint) ya está envuelto en un `except:` desnudo que silenciaría un `TypeError` en vez de dejarlo romper el ciclo. Si el problema descrito existe, está en un módulo distinto (`event_service.py` o el repositorio de eventos), no en el script capturado.
- **E-CAL-07** (`guardar_checkpoint` se llama dos veces por ciclo) → **Q21**. Esto **no coincide** con el código disponible: `capturar_eventos()` en `calendario_tradingview_live_v5.py` llama a `guardar_checkpoint()` en un único punto de salida por ejecución (línea 409 si no hay eventos, o línea 446 al cerrar el flujo normal), nunca ambos. Si `event_service.py` reimporta y vuelve a llamar a esa función, sería una decisión de ese módulo que no puedo confirmar ni descartar sin leerlo.

### G.3 · Correcciones a la propia revisión

| Punto de la revisión | Por qué no se acepta tal cual |
| --- | --- |
| "El informe lo menciona [E-HM-04] de pasada pero no le da severidad" | Incorrecto: en la versión 1.0, E-HM-04 ya estaba clasificado como **S2**, con ficha completa en la sección "Altos". No fue necesario "subirlo": ya estaba ahí. Lo que sí aporta la revisión es una razón válida para separarlo en dos hallazgos (G.1). |
| "El script principal la llama al final de `capturar_eventos`, y `event_service.process_calendar_batch` la vuelve a llamar" (sobre `guardar_checkpoint`) | Afirmado como hecho verificado; en realidad es una hipótesis sobre un archivo no disponible, y la parte que sí es verificable (el propio `capturar_eventos`) muestra un único punto de escritura. Reclasificado como duda (Q21), no como error confirmado. |
| Numeración `E-CAL-06` citando `safe_int`/`max_event_id` como si perteneciera al script ya auditado | Ese identificador y esas variables no existen en `calendario_tradingview_live_v5.py`; si el hallazgo es real, pertenece a un módulo fuera del alcance de este informe (§2.2). Reclasificado como Q20. |

### G.4 · Qué falta para cerrar los puntos pendientes

Para verificar Q18–Q21 y precisar E-RAD-12 con evidencia directa (no por inferencia desde el informe de la BD), hacen falta los archivos que §2.2 ya señalaba como no revisados: `application/market_service.py`, `application/event_service.py`, `db/market_repository.py`, `db/event_repository.py` y el código del heatmap service / Streamlit (`heatmap_service.py` o equivalente, incluyendo la consulta de "última hora" y la de evolución de precio). Si se comparten, la siguiente revisión puede mover Q18–Q21 al catálogo de errores con la misma evidencia directa que ya se usó para E-HM-15, E-HM-16 y E-RAD-05.

---

## Changelog

| Versión | Fecha | Cambios |
| --- | --- | --- |
| 1.0 | 2026-09-20 | Primera versión. Sustituye al borrador del 2026-09-19, incorpora el diagnóstico de campos del 2026-09-19 y los dos `config.py`, y define todos los IDs |
| 1.1 | 2026-09-21 | Evalúa una segunda revisión externa (Anexo G). Confirma con código propio y añade E-HM-15, E-HM-16, E-HM-17; reclasifica E-HM-04 (S2 → S3) separándolo de E-HM-17; precisa la ubicación de E-HM-07; refuerza E-RAD-05 con evidencia directa sobre `batch_buffer.clear()`. Traslada a dudas (Q18–Q21), en vez de aceptar como errores confirmados, los puntos que dependen de código no incluido en §2.1 (`market_service.py`, `event_service.py`, servicio del heatmap); una de esas dudas (Q21) contradice parcialmente lo observado en `calendario_tradingview_live_v5.py` |
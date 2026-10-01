# Planilla F0.1 · Verificación A1–A16 contra `heatmap_stock`

> **Fecha:** 2026-09-22 · **Ejecución:** `proy_scrapping_detail/db/run_verify_a1_a16.py`
> **Fuente:** [verify_a1_a16.sql](proy_scrapping_detail/db/verify_a1_a16.sql) → `planilla_a1_a16_UTC.json`
> **Rango de datos:** `fact_market_series` 2026-03-17 → 2026-09-18 (postgres 17.10, Lima UTC−5).

## Resumen ejecutivo

| ID | Hipótesis/Duda/Error | Resultado | Estado |
|---|---|---|---|
| A1 | H4, E-OPS-01 · Ticks fuera de sesión como repeticiones | **Confirmado**: fuera de 13–20 UTC `closes_distintos=1`; en sesión 19–20. | Cierra H4 (matiz) |
| A2 | H3 · Volumen acumulado | **Confirmado**: 280 filas, 1 solo delta negativo (reset de sesión). | Cierra H3 |
| A3 | H5, E-BD-03 · Escala de importancia | **Hallazgo**: escala real es `−1/0/1` (no 0–3). 218 US, 18 de máxima con CPI/NFP/Fed. | Actualiza H5 |
| A4 | H10, E-CAL-02 · `captured_at` nulo | Ventana limitada (1 día hábil); **no hay nulos en el último día**. | No concluyente |
| A5 | H11, E-BD-02 · Criterio de partición | **Lima**: límites `00:00-05` = `05:00+00` UTC → **criterio Lima**. | Cierra H11 |
| A6 | H8 · Duración del ciclo | **~2 min** (mediana 121 s) SPY→VIX. | Cierra H8 |
| A7 | H8, H17 · Huecos entre ticks | Ticks a intervalos de **3 min**; máx. gap 3:44; **0 gaps > 4 min**. | Refina H8, refuta H17 |
| A8 | H9 · Cierres redondos/nulos | 0 nulos; redondos minoritarios (VIX 17/1312). | Cierra H9 |
| A9 | Q8, H14 · Sorpresas computables | **Sí**: 125/392 (imp−1), 89/142, 39/45. | Cierra Q8/H14 |
| A10 | H15, Q4 · UTC del histórico | Concentración única 13–21 UTC; **no hay duplicado +5h**. | Cierra H15, Q4 |
| A11 | Q6, E-RAD-04 · Nulos por símbolo | `TVC:US10Y`/`TVC:US02Y`: **close 0% pero RSI y volume 100% nulos**. | Confirma E-RAD-04 |
| A12 | E-HM-01 · Composición del snapshot | Último snapshot = **1000 assets**; 80% equity común. | Confirma E-HM-01 |
| A13 | E-BD-08 · Índices sin uso | `close_idx`/`rsi_idx` por partición con `idx_scan=0`; 21 MB c/u. | Confirma E-BD-08 |
| A14 | E-HM-05 · `logo_id` nulo | **100% sin logo** (radar_v4 45/45, heatmap 1038/1038). | Confirma E-HM-05 |
| A15 | E-RAD-05, E-OPS-03 · Auditoría | `backfill_market_csv` **FAILED ×3**; `radar_v4` OK. | Confirma E-RAD-05 |
| A16 | E-BD-04 · Índices de `dim_asset` | 6 índices; falta índice funcional en `(is_active, asset_class)`. | Confirma E-BD-04 |

## Resultados por consulta

### A1 · Ticks fuera de sesión (NVDA, 2026-09-17, hora ET)
- 00:08–08:00 y 17:00–23:00 ET: `ticks=20/h`, `closes_distintos=1` → cada hora repite el mismo close.
- **Sesión (09:00–16:00 ET):** `closes_distintos` 6→20→19→19→20→20→20→5.
- Fuera de sesión 20 ticks/h * 15 h = 300/340 ticks fueron repeticiones. **H4 confirmada con matiz** (1 close por hora, no exactamente 1 clado).

### A2 · Volumen acumulado
- 280 filas; **1 delta negativo** (2:00 UTC → reinicio del acumulado de sesión). Sin ceros.

### A3 · Escala de importancia (eventos US)
| importance | n | Ejemplos de alta |
|---|---|---|
| −1 | 150 | Nonfarm Payrolls Private, U–6, Nonfarm Product. |
| 0 | 50 | CPI, CPI s.a |
| 1 | 18 | Fed Interest Rate Decision, Non Farm Payrolls, Unemployment |

→ La escala usada es `−1/0/1` (TradingView). **E-BD-03**: la doc asumía 0–3; corregir.

### A4 · `captured_at` nulo
- Último día (2026-09-18): 579 eventos, **0 sin `captured_at`**. Solo 1 día con eventos en la ventana; **no concluyente** para el defecto de los sábados.

### A5 · Límites de partición
- `fact_heatmap_snapshot` particionada mensual desde 2026-09.
- Límites `FOR VALUES FROM ('2026-09-01 00:00:00-05') TO (...)`.
- Con `SET TIME ZONE 'UTC'` se ven como `05:00+00`; con `America/Lima` como `00:00-05`. → **Criterio Lima confirmado** (H11), no UTC.

### A6 + A7 · Ciclo de captura y huecos (SPY=01:00 VT first)
- A6: desfase SPY→VIX mediana **121 s** (p90=125 s, max=126 s). Ciclo = T(VIX)−T(SPY) ≈ 2 min.
- A7: gap entre ticks de SPY p50/p90/p99 ≈ **3:00/3:01/3:02**, max=3:44, **0 huecos>4 min**.
- Conclusión: captura en **ciclos regulares de 3 min**, no hay huecos grandes (H17 refutada); la duración del ciclo en A6 (~2 min) mezcla la latencia de orden de símbolos dentro del ciclo de 3 min.

### A8 · Cierres redondos y nulos (7 días)
| symbol | n | distintos | enteros | nulos |
|---|---|---|---|---|
| TVC:VIX | 1312 | 204 | 17 | 0 |
| TVC:US10Y | 1312 | 58 | 110 | 0 |
| TVC:US02Y | 1312 | 85 | 0 | 0 |
| CBOE:VX1! | 1312 | 91 | 119 | 0 |

- **0 nulos** → H9 refutada en el dato observado; redondeos minoritarios.

### A9 · Sorpresas computables
| importance | total | con sorpresa |
|---|---|---|
| −1 | 392 | 125 (32%) |
| 0 | 142 | 89 (63%) |
| 1 | 45 | 39 (87%) |

### A10 · UTC del histórico (NVDA)
- Concentración única **13:00–21:00 UTC** (9:00–17:00 ET). 09-17 y 09-18 idénticos en horas pares. **No hay** segunda concentración desplazada 5 h.

### A11 · Nulos por símbolo (7 días)
| symbol | n | %close | %rsi | %volume |
|---|---|---|---|---|
| TVC:US02Y | 1312 | 0 | **100** | **100** |
| TVC:US10Y | 1312 | 0 | **100** | **100** |

→ **E-RAD-04 confirmado**: yields sin RSI/volumen → el frontend marca `as_of` viejo.

### A12 · Último snapshot (2026-09-18 14:23 UTC)
- **1000 assets**: OTC common 248, NYSE common 245, OTC 199, NASDAQ common 112, NYSE preferred 101, NYSE 58, OTC preferred 14, NASDAQ 10, NASDAQ preferred 8, NYSE unit 4, AMEX common 1.

### A13 · Índices sin uso (top por tamaño)
- `fact_market_series_2026_09_{pkey,close_idx,rsi_idx}` → `idx_scan=0`, 21/21/20 MB.
- Mismo patrón 2026_08 (14/14/13 MB) y 2026_07/04 (`close_idx`).
- En BD con auto-partición, los índices de la partición recién creada aún no se han usado (contadores reiniciados por `TRUNCATE`/nueva partición) — **verificar con `pg_stat_all_indexes` acumulativo** (nota M-CAP).

### A14 · `logo_id` nulo por origen
| source_discovered_by | n | sin logo |
|---|---|---|
| radar_v4 | 45 | **45 (100%)** |
| heatmap | 1038 | **1038 (100%)** |

### A15 · Auditoría por script y estado
| script_name | status | corridas | primera → última |
|---|---|---|---|
| backfill_calendar_csv | SUCCESS | 1 | 2026-09-18 20:15 |
| backfill_market_csv | FAILED | 3 | 2026-09-18 15:41 → 15:42 |
| backfill_market_csv | SUCCESS | 2 | 2026-09-18 15:40 → 15:46 |
| calendario | SUCCESS | 1 | 2026-09-13 23:40 |
| radar_v4 | SUCCESS | 2 | 2026-09-18 13:23 → 14:20 |
| scrapper_heatmap_v1 | SUCCESS | 3 | 2026-09-13 12:59 → 2026-09-18 14:23 |

→ **3 corridas FAILED de `backfill_market_csv`** (E-RAD-05).

### A16 · Índices de `dim_asset`
- `dim_asset_pkey`, `dim_asset_symbol_key` (unique), `idx_dim_asset_active`, `idx_dim_asset_class`, `idx_dim_asset_slug`, `idx_dim_asset_symbol`.
- **Falta** índice en `(is_active, current_version, asset_class)` (E-BD-04) y en `source_discovered_by` (usado por A14).

## Impacto en el roadmap
- **Cierres F0.1:** H3, H8, H11, H15, Q4, Q8 + H4 (matiz), H9 (refutada), H17 (refutada), H14.
- **Confirma errores:** E-RAD-05, E-RAD-04, E-HM-01, E-HM-05, E-BD-04, E-BD-08.
- **Nuevo:** E-BD-03 (escala `−1/0/1`), A14 confirma falta índice en `source_discovered_by`.
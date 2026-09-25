# Roadmap Integral de Ejecución v2.3 — Explicación analógica

Documento complementario al roadmap técnico. Aquí cada fase y cada cambio se explica **con analogías**, para entender el "qué" y el "por qué" de memoria, sin entrar al detalle SQL/Python (que vive en el roadmap fuente).

---

## Analogía maestra del ecosistema

Imagina este proyecto como **un restaurante que cocina datos del mercado**:

- **`scraper_live_tradingview_v5.py` (radar)** = el mesero que recorre las mesas (símbolos) pidiendo precios.
- **`scrapper_heatmap_v1.py` (heatmap)** = el fotógrafo que cada 15 min toma una instantánea de toda la sala.
- **`calendario_tradingview_live_v5.py` (calendario)** = el encargado de avisar "en 10 min llega una noticia importante" (NFP, CPI, FOMC).
- **PostgreSQL `heatmap_stock`** = el libro mayor donde se guarda todo lo servido.
- **`dim_trading_session`** = el reloj de la cocina: el horario en que la bolsa abre, cierra y descansa.
- **Dashboard (Fase 5)** = la vitrina donde el comensal ve el menú, los platos y su frescura.

El resto del documento recorre cada fase como si fuera **una remodelación de este restaurante**.

---

## FASE 0 · Verificación empírica

> **Frase**: "Antes de remodelar, medimos la mesa, el fuego y el menú."

**Analogía general:** Es la **inspección técnica** previa a una obra. No se toca nada: solo se comprueba qué funciona, qué hipótesis eran falsas y qué hay que arreglar. Es el "reconocimiento del terreno" — como medir los muros antes de pintar.

### F0.1 · Ejecutar A1–A16 (SQL)
**Analogía:** Recorrer la bodega con una **checklist de 16 puntos**: "¿la puerta cierra? ¿hay luz? ¿cuántas cajas hay?". Al final tienes una planilla con las respuestas y varias hipótesis (H3, H4, H5, H8, H11, H15) quedan cerradas con evidencia, no con suposiciones.

### F0.2 · Protocolo empírico (T1–T13)
**Analogía:** La **fase de pruebas del chef**: en vez de creerle al proveedor, pruebas cada ingrediente.

- T1/T3/T4/T6/T10/T11/T12 ✅ = ingredientes verificados (precio en vivo, pre-market, repintado, pivotes, volumen FX idéntico, gate por clase, batch).
- **T5 (hallazgo clave):** se creía que `/scan` no funcionaba (devuelve 404), pero el reporte v3 descubrió que **la dirección era incorrecta**: `POST /america/scan` responde 200. Es como descubrir que el restaurante sí tenía carrito de servicio, pero estaba en el pasillo equivocado. **Este hallazgo desbloquea la Fase 3 (captura en lote).**
- **Pendientes:** T3.1/T13 (semántica de `gap`) y T2/T8/T9 (requieren mercado en vivo o logs de producción).

### F0.3 · ADR 0001 (D1–D14)
**Analogía:** Escribir las **decisiones de arquitectura en un acta firmada**: "a partir de hoy, el pan viene de esta panadería, y si falla, de esta otra". Cada `D` es una decisión oficial que evita volver a preguntarse "¿por qué usamos esto?".

---

## FASE 1 · Bugs latentes + E-RAD-14 (quick wins)

> **Frase**: "Arreglamos los hilos sueltos antes de que el restaurante abra a plena capacidad."

**Analogía general:** Es la **ronda de mantenimiento rápido**: el horno pierde calor, un grifo gotea y la puerta del congelador no cierra. Cada fix es pequeño, pero todos juntos evitan catástrofes cuando el cron se llene de trabajo.

### F1.1 · Arreglar `heatmap_service` / `heatmap_repository`
**Analogía:** El menú del día mostraba la foto de **una hora muerta** (ventana de 1 h vacía) y dos platos del mismo día colisionaban en el historial (etiquetas `HH:MM` sin fecha). Se corrige para que siempre muestre algo reciente (últimos 15 min) y cada plato lleve su fecha completa (`%m-%d %H:%M`). **Verificado: 1000 filas y etiquetas de días distintos.**

### F1.2 · Arreglar `event_service`
**Analogía:** El avisador de noticias **se bloqueaba cuando un evento llegaba sin ID** (`max([])` → TypeError) y además **apuntaba dos veces en el cuaderno** la última noticia vista (doble checkpoint). Se filtra el ID vacío y se deja un solo apunte. **Verificado: `safe_int` filtrado, `max([]) → 0`.**

### F1.3 · Invertir orden en `scrapper_heatmap_v1.main()`
**Analogía:** El fotógrafo **construía el estudio (DDL) antes de ver si había sujetos** (validar la API). Si el restaurante está cerrado, igual montaba el set y registraba `FAILED`. Tras el fix: primero comprueba que hay algo que fotografiar y, si no, registra `SKIPPED` (no es un fracaso, es que no tocaba). **Verificado: estado `closed` → `SKIPPED`, exit 0.**

### F1.4 · Contrato con estado en `market_service`
**Analogía:** El mesero **tiraba la bandeja tuviera o no los platos** (`batch_buffer.clear()` incondicional) y si algo fallaba lo tragaba en silencio (errores capturados y no propagados). Ahora la cocina devuelve un ticket (`{'inserted','status','error'}`) y la bandeja solo se limpia cuando la entrega fue `SUCCESS`. **Verificado: con BD apagada el log dice `FAILED` y el buffer conserva filas.**

### F1.5 · Corregir `records_failed`
**Analogía:** La caja registradora **imprimía "0 fallos" aun sin vender nada** (`records_failed` siempre 0). Ahora los fallos = pedidos tomados − platos servidos (con mínimo 0). **Verificado: 1000→1000; 1000/950→50.**

### F1.6 · Documentar `source_checksum`
**Analogía:** Poner **una etiqueta en la despensa** diciendo "la huella digital de este ingrediente se calcula en `market_repository.py:118`". Un cocinero nuevo sabe dónde buscar. **Verificado: comentario añadido.**

### F1.7 · Corregir primario de EURUSD
**Analogía:** El proveedor de datos de EURUSD (`FX_IDC`) **entregaba el precio pero marcaba el peso en 0** (volumen = 0), mientras que otros proveedores (OANDA, FX) sí pesaban. Cambiamos de proveedor principal a `OANDA:EURUSD` (con respaldo `FX:EURUSD`) — como cambiar de panadero porque uno corta el pan en ceros. **Evidencia retroactiva: `OANDA` ya registraba volumen 97767 vs `FX_IDC` en 0.**

### F1.8 · Refactorizar `main()` del heatmap
**Analogía:** El estudio se **montaba dos veces** (duplicado de DDL: en `main()` línea 370 y en `process_heatmap_data` línea 131). Se deja **una sola ruta de montaje**, tras validar la API. Como decidir: el set lo arma solo el jefe de piso, nadie más.

---

## FASE 2 · Tiempo y ventana

> **Frase**: "Instalamos el reloj de la cocina antes del cambio de horario."

**Analogía general:** El 1-nov-2026 hay **cambio de horario (DST)**. Si no sabemos cuándo abre NYSE, todo lo demás vive desalineado. Esta fase construye el **reloj y los permisos** del restaurante. (Metáfora: como si el restaurante estuviera por cambiar de huso y necesitamos un único reloj maestro.)

### F2.1 · `dim_trading_session`
**Analogía:** Crear **el calendario oficial de la cocina**: los días que se trabaja (432 sesiones de NYSE), los que se descansa (feriados como Acción de Gracias 26-nov) y los días de cierre temprano (27-nov, cierra 13:00 ET). Se construye con la librería `exchange_calendars` (XNYS) y cubre 2026–2027 (630 días). **Verificado: 26/11 no es sesión; 27/11 cierra temprano.**

### F2.2 · Gate por clase de activo
**Analogía:** Cada tipo de alimento tiene **su horario de bodega**:

- Acciones/ETF → solo cuando NYSE está abierto.
- FX → de lunes a viernes casi 24 h.
- Cripto → 24/7, nunca cierra.
- Futuros → siguen a NYSE.

Antes, el mesero repartía estuviera o no la sala abierta. Ahora se filtra símbolo por símbolo (`continue` en el radar) sin abortar el ciclo. **Verificado: 9 tests de sesión (feriado, cierre anticipado, DST) PASS.** Pendiente: confirmación con ciclo en vivo.

### F2.3 · Particiones UTC explícitas
**Analogía:** Las cajas del almacén estaban **rotuladas con hora de Lima** (límites `-05`, medianoche local), lo que en UTC quedaba a las `05:00`. El correcto es rotular **en UTC (`00:00+00`), el idioma universal**. El cambio (38 particiones UTC, 14 legacy migradas) está **preparado**: backup hecho (`heatmap_stock_pre_F2.3_20260922_224433.dump`, 103 MB) y SQL generado, pero la migración **queda pospuesta** hasta confirmación. ~20.300 filas del día 1 (00–05 h UTC) cambiarán de caja al ejecutar.

### F2.4 · Roles y credenciales
**Analogía:** No todos los empleados tienen **la llave de la bóveda**. Se crean dos perfiles: `scraper_rw` (puede escribir en las tablas de datos) y `dashboard_ro` (solo lee), y se rota la contraseña maestra de `postgres`. **Pendiente por decisión del usuario.**

### F2.5 · Mapeo canónico lógico → físico
**Analogía:** Algunos activos tienen **dos proveedores** (p. ej., `VIX` puede venir de `TVC:VIX` o de `CBOE:VX1!`). Este cambio crea una **ficha maestra** en `dim_asset` que dice cuál es el proveedor principal y cuál el de respaldo, cuánto retraso tiene cada uno (0/600/900 s). **Pendiente por decisión del usuario.**

---

## FASE 3 · Captura fiable

> **Frase**: "El grifo de datos debe servir rápido, junto, con ticket y sin gotear."

**Analogía general:** Es remodelar **la cocina para servir toda la mesa de una vez**: hoy se hace una llamada por símbolo (servicio lento); el objetivo es captura **en lote**, **simultánea**, **trazable** y **con pre-market**. Criterio de salida: `p95 ciclo ≤ 15 s`, `update_mode` al 100%, `premarket_*` al 100%.

### F3.1 · Estrategia de captura batch
**Analogía:** El hallazgo de F0/T5 nos regala **el carrito de servicio**: una sola llamada `POST /america/scan` trae los 110 símbolos, con columnas y hasta filtro (`RSI|60 > 60`), en ~1,5 s (incluida la pausa anti-429). Antes el mesero cruzaba 110 veces con un plato; ahora cruza una vez con todos. Se implementa el **Plan A** y se descarta el Plan B. Para no tocar el límite de visitas (429): pausa de 1,2 s y hasta 3 reintentos con backoff.

### F3.2 · `CAMPOS` extendido
**Analogía:** Ampliamos **la orden que se pide al carrito**: además de los datos base (diario), se piden bloques `|5`, `|15` y el nuevo `|60` (como pedir la ración en tres tamaños) más el pivote diario `Pivot.M.Camarilla.R3|15`. El catálogo válido de tamaños (TF): `1,5,15,30,60,120,240,1W,1M`. Se omite `close|TF` porque el cierre es idéntico en todos los tamaños (el `close` base + `premarket_close` bastan).

### F3.3 · Trazabilidad temporal
**Analogía:** Cada plato sale ahora **con el ticket del horno**: `update_mode` (en vivo o con 600/900 s de retraso), `cycle_id` (número de vuelta), `fetched_at` (hora de entrega), `feed_delay_s` (minutos que se enfrió) y los datos de pre-apertura (`premarket_*`, `gap`). Así, cuando un dato parece "de hace 15 min", sabemos quién lo dejó esperando.

### F3.4 · Prioridad y circuit breaker por exchange
**Analogía:** El mesero ya no visita las mesas **en orden alfabético** (una mesa lejana primero) ni **abandona el restaurante entero** si una mesa da problemas (antes: `sys.exit(1)` tras 3 fallos). Ahora: primero las mesas importantes (SPY, QQQ, VIX, US10Y, DXY, NQ1!) y, si el sector CBOE se incendia, **se apaga ese sector y se sigue sirviendo en NASDAQ**.

### F3.5 · Reintento + modo estricto + reconciliación
**Analogía:** Tres reglas: 1) **no se puede abrir sin el libro mayor** (`DB_WRITE_ENABLED` obligatorio en prod); 2) **el `.env` manda** (`override=False`, nadie le pisa la receta); 3) **cuaderno de respaldo**: los CSV se pasan a limpio en el libro mayor con un job nocturno de reconciliación, así un corte de luz de 10 min no deja huecos.

### F3.6 · Calendario: polling por evento + reintento
**Analogía:** El avisador de noticias **ya no vigila todo el día**: solo atiende en la ventana crítica (08:00–16:00 ET, alrededor de cada evento de alto impacto, `T−1` a `T+10 min`). Y si el teléfono falla, **vuelve a marcar** (reintento con backoff) distinguiendo "no hay eventos" (checkpoint intacto) de "error de API" (reintentar). Los logs rotan (10 MB × 7) como un historial acotado.

### F3.7 · Heatmap: filtros y parseo
**Analogía:** El portero del heatmap **ahora pide carné y recibo**: solo entran exchanges {NASDAQ, NYSE, AMEX} con dólar-volumen ≥ 20 M, y la fotografía se lee **por nombre de columna**, no por posición (frágil si cambia el orden). Además, el filtro se puede aplicar **en el endpoint** (`/america/scan` acepta `filter` simple): como pedir al carrito solo los platos que pasan control de calidad.

### F3.8 · Heatmap: cache de `asset_id`
**Analogía:** El empleado **se aprendió los códigos de los platos** (cache en memoria `symbol → asset_id`). Antes buscaba la ficha de cada plato en cada mesa; ahora solo consulta los pocos que no conoce (`ON CONFLICT DO NOTHING`). Objetivo: ≤ 3 consultas SQL de dimensión por snapshot.

### F3.9 · Heatmap: cron con gate
**Analogía:** Las fotos de la bóveda se toman **a hora fija** (cada 15 min alineado a `:00/:15/:30/:45` + ~20 s) para evitar el momento ambiguo del cierre de barra. Criterio: 28 snapshots por sesión.

### F3.10 · Auditoría por ciclo
**Analogía:** Cada vuelta del mesero queda **anotada en el parte de servicio** (`RUNNING → SUCCESS / PARTIAL_FAIL / SKIPPED`, duración y símbolos fallidos), **incluso los saltados**. Antes, las vueltas que no servían no dejaban rastro: imposible saber qué pasó.

### F3.11 · Monitoreo y alertas
**Analogía:** El **detector de humo de la cocina**: suena si (a) llevamos más de 5 min sin servir en ventana, (b) hay bloqueos 429 repetidos, o (c) el libro mayor está apagado (`DB_WRITE=OFF`). No hay que mirar para enterarse.

### F3.12 · Ampliar universo del radar
**Analogía:** El menú crece de 110 a **123 símbolos**: el futuro de S&P (`CME_MINI:ES1!`), los 10 **ETF sectoriales** SPDR (XLK…XLC), IWM (small caps), RSP (S&P equiponderado) y validar `TVC:DXY`/`ICEUS:DX1!`. Regla de oro: cada plato nuevo debe **verificar su cadena de frío** (update_mode predicho por Test D: sectoriales 900 s, ES1! 600 s, DXY 0 s). Con el batch de F3.1, el ciclo sigue ≤ 15 s.

---

## FASE 4 · Modelo 15 min

> **Frase**: "Convertimos el torrente de datos en barras consultables, con el termómetro de la calidad en la mano."

**Analogía general:** Si F3 es la captura, F4 es **el procesamiento en cocina**: agrupar los ticks sueltos en **barras de 15 min** (como cortar las verduras en porciones), etiquetar cada barra con su calidad (¿el cierre es definitivo o provisional?) y dejar todo listo para el comensal (dashboard). **Criterio: 28 barras/día/activo, ≥95% con `n_ticks ≥ 3`, ≥95% `definitive`.**

### F4.1 · `fact_market_bar_15m`
**Analogía:** Crear **la bandeja de porciones**: una tabla donde cada activo tiene su barra OHLCV de 15 min por sesión, con `n_ticks` (cuántos bocados componen esa porción) y `close_quality` (etiqueta de frescura del cierre: `definitive` / `provisional` / `unknown`). Hipótesis ya validada: la frontera de barra en `|15` es limpia (el `volume|15` se reinicia de verdad).

### F4.1b · Regla de cierre de barra
**Analogía:** El endpoint tarda 7–12 s en mostrar la vela nueva y la caché añade 15–40 s: **en `[T_cierre − 5 s, T_cierre + 15 s]` el dato es ambiguo** (como ver el plato mientras el horno aún lo está terminando). Regla: si el último tick cayó justo antes del cierre (−20 a −5 s) → `definitive`; si cayó en la zona ambigua (−5 a +15 s) → `provisional`; si fuera → `unknown`. **Objetivo: 0% de barras `provisional` tras un ciclo completo.**

### F4.1c · Cron desfasado + muestreo T−10 s
**Analogía:** El fotógrafo se desfasa **1 minuto** (cron `1-59/3` en vez de `/3` para no chocar con los baches) y además envía un **ayudante a disparar 10 segundos antes** de cada cuarto de hora (`:14:50`, `:29:50`...). Así se captura el cierre justo antes de la bruma del cambio de vela. **Objetivo: 95% de barras `definitive`.**

### F4.2 · `fact_market_indicator_tf` (formato largo)
**Analogía:** Los indicadores (RSI, CCI20, BBPower, ADX, change%, volumen, pivote R3) viven **en formato largo** (una fila por activo × timestamp × TF): como un contenedor con estantes fijos, fácil de consultar. **Hecho cuando: `RSI|15` de la tabla coincide con el de `/america/scan`.**

### F4.3 · `latest_market_tick`
**Analogía:** Un **corcho de última hora** en la pizarra: una fila por activo con el último precio conocido (upsert en cada ciclo). El dashboard lee 110 filas en segundos en vez de escanear millones de filas históricas.

### F4.4 · Snapshots con columnas explícitas
**Analogía:** La fotografía del menú ya no es **un blob ilegible** (`raw_vector`): se separa en columnas claras (volumen, promedio 10 días, volatilidad, máximos/mínimos 52 semanas, `update_mode`, `fetched_at`). Cada fila pasa a ser < 1 kB.

### F4.5 / F4.5b · Resolver SCD2 en `dim_asset`
**Analogía:** Se aplica la decisión D7 (**Tipo 1: sin versionado**). La ficha de cada activo es **una sola página vigente**, no un archivo histórico de versiones. Se consolidan las columnas del mapeo canónico de F2.5 (`logical_key`, `is_canonical`, `role`, `feed_delay_s`) y se deja **un solo índice único** sobre `symbol` (se elimina el índice duplicado).

**✅ Completa (2026-09-23, changelog v2.3.8):** migración Alembic **`0006`** aplicada en vivo — `dim_asset` a **Tipo 1** (drogadas `valid_from`/`valid_to`/`current_version`) + **mapeo canónico** de las 6 claves (VIX|DXY|TLT|US10Y|ORO|OIL) con alta de `TVC:DXY`, índice único parcial por clave (1 canónico) y `feed_delay_s` sin NULL. `dim_asset`=1.669, secuencia 4.701, BD en `0006 (head)`. Consumidores corregidos (seed_symbols/repos/scrappers/heatmap). 75 tests en verde.

### F4.6 · Eventos: upsert condicional
**Analogía:** La agenda de eventos **solo se reescribe si el contenido cambió** (`captured_at = now()` y `last_updated_at` solo se toca si cambia el payload). Como actualizar la pizarra de noticias solo cuando hay noticia nueva, no cada minuto.

### F4.7 · Reempaquetado del histórico
**Analogía:** Un **taller nocturno** lee los CSV viejos (el cuaderno de respaldo) y genera las barras de 15 min retroactivas (desde 2026-08-22 para equity) y el contexto diario. Con **salvedades documentadas**: la hora es de captura, no del dato; puede haber retrasos de 15 min; hay 24 h de captura fuera de sesión.

### F4.8 · Suite nocturna de calidad
**Analogía:** El **control de calidad nocturno** (02:00 UTC) revisa: duplicados, huecos, nulos, ticks planos fuera de sesión, `n_ticks` por barra, `close_quality` y contigüidad de particiones; y deja **un informe diario**. Como el supervisor que pasa de noche con su checklist y deja el parte impreso.

---

## FASE 5 · MVP Dashboard

> **Frase**: "La vitrina abre con 4 paneles que se ven frescos de verdad."

**Analogía general:** Construir **la sala del comensal** (web) sobre la cocina ya limpia: un MVP con 4 paneles, modo PRE/LIVE/CLOSED, y un **banner de frescura por activo** (la fecha de caducidad visible de cada dato).

### F5.1 · Esqueleto FastAPI
**Analogía:** Montar **el esqueleto del restaurante**: estructura de carpetas (core, domain, db, repositories, services, api, web), patrón copiado de `postgresql_connection`, y el "está abierto" (`/api/health`) respondiendo en el puerto 8100.

### F5.2 · Modos PRE / LIVE / CLOSED
**Analogía:** La vitrina sabe **en qué momento del día está** gracias a `session_service` (que lee `dim_trading_session`): antes de abrir muestra el resumen del día y la cuenta regresiva; en vivo, los datos; cerrado, el parte del día.

### F5.3 · Banner de frescura por panel
**Analogía:** Cada panel muestra **su antigüedad real por activo** (`as_of`, `feed_delay`, `ingest_lag`): no un "fresco" global, porque unas mesas se sirven en vivo (0 s) y otras con retraso de 600/900 s (Test D). Como la etiqueta de "listo para servir" por plato, no por sala.

### F5.4 · Los 4 paneles del MVP
**Analogía:** Las 4 vitrinas principales:

1. **Pre-apertura y régimen** — VIX, DXY, US10Y, NQ/ES, BTC, con `gap` y `premarket_*` (el menú de la mañana antes de que abra la bolsa). Depende de F2.5 (D2/D3).
2. **QQQ/SPY/ORO en 15 min** — SMA20/50, VWAP y pivotes (usando `Pivot.M.Camarilla.R3|15`).
3. **Próximos eventos** — cuenta regresiva + sorpresa con polaridad.
4. **Termómetro de riesgo** — percentil 60d de VIX, US10Y, TLT.

### F5.5 · `session_service` con ET y Lima
**Analogía:** El reloj de la vitrina **habla dos idiomas**: hora de Nueva York (la de la bolsa) y hora de Lima (la local). Verificación: que al cruzar el 1-nov (DST) muestre las horas correctas antes y después.

### F5.6 · Panel de eventos
**Analogía:** La vitrina de noticias incluye **cuenta regresiva, ventana de silencio** (no operar justo antes/durante) y **sorpresa con polaridad** (¿salió mejor o peor de lo esperado?). Verificación: NFP y CPI con sorpresa correcta.

---

## FASE 6 · Validación y score

> **Frase**: "Antes de vender la receta, medimos si de verdad rinde."

**Analogía general:** Es el **chef científico**: se pone a prueba si el score/los indicadores **predicen algo real** (H13, H14, H17). Si no, el score solo se muestra como contexto, nunca como señal de compra/venta. Criterio: informe *walk-forward* con IC.

### F6.1 · Estudio forward-return
**Analogía:** El plato estrella se prueba en **degustación controlada**: se mide cuánto se movió el mercado +15/+30/+60 min tras la señal, desplazando la señal por el retraso real del dato (**por clase**: 0/600/900 s). Resultado: informe con IC para aceptar o echar abajo la hipótesis H13.

### F6.2 · Estudio de eventos
**Analogía:** Registrar la **reacción promedio del mercado ante cada noticia** (por importancia y sorpresa) con ≥30 eventos que tengan valor esperado y real. Como llevar el libro de "cuando llueve, vende paraguas".

### F6.3 · Validación cruzada TV vs propio
**Analogía:** Comprobar si el indicador del proveedor (RSI, ADX, CCI20, pivote R3) **coincide con el cálculo propio** en 5–10 sesiones; las diferencias se documentan y se decide (D4) si se mantiene la fuente de TradingView o se calcula en casa.

### F6.4 · Score como contexto
**Analogía:** El score se muestra **como termómetro, no como brújula**: valor + percentil + fase, **sin zonas COMPRAR/VENDER** hasta que H13 pase el examen. Siguiendo D10: no prometer lo que aún no se demostró.

### F6.5 · RVOL por hora del día
**Analogía:** El volumen relativo se calcula **solo para acciones/ETF** (el FX no tiene volumen nocional y el primario FX_IDC lo corrompía). Verificación: la mediana del RVOL ≈ 1.0 a cualquier hora (la escala está calibrada).

### F6.6 · Amplitud sectorial
**Analogía:** Medir **cuántos sectores están arriba/abajo** usando los ETF sectoriales de F3.12 + el heatmap filtrado: la foto de "¿el mercado es ancho o concentrado?".

### F6.7 · `fact_symbol_score` / `fact_market_context` / F6.8 · `fact_event_reaction` / F6.9 · `fact_sector_snapshot`
**Analogía:** Las **tablas del laboratorio**: lugar donde se guardan el score por símbolo, el contexto de mercado, la reacción a eventos y la foto sectorial — todo con su esquema y particionado, listos para el informe final.

---

## FASE 7 · Calidad, seguridad y retención

> **Frase**: "Cerramos la deuda técnica: dejamos de acumular y empezamos a mantener."

**Analogía general:** Es la **limpieza y puesta a punto de fin de temporada**: se retiene lo útil, se destruye lo caduco, se respaldan los libros y se alinean todos los documentos.

### F7.1 · Calendario: llamada semanal (M-CAP-16) + F7.2 · Rotación CSV fuera del ciclo
**Analogía:** El avisador consulta la agenda **una vez por semana** (no cada minuto) y la rotación de los CSV ya **no gotea dentro del ciclo de servicio** (mueve el I/O pesado fuera, para no ralentizar el servicio). Como cambiar el aceite del horno fuera de la hora punta.

### F7.3 · Retención (D8)
**Analogía:** Política de vencimiento del inventario: **ticks 6 meses**, barras indefinidas y `raw_payload` apagado. Como decidir qué se congela y qué se tira — sin acumular hielo viejo en la cámara.

### F7.4 · Limpieza de índices (M-DAT-13, A13)
**Analogía:** Podar los **índices que ya no sirven** (huérfanos/duplicados) para que las escrituras no paguen mantenimiento inútil.

### F7.5 · Backups (M-OPS-05)
**Analogía:** **Copias de seguridad probadas** del libro mayor (como el backup ya hecho en F2.3 con `pg_dump` dentro del contenedor `pg_db`), y además **se comprueba que se restauran**, no solo que se generan.

### F7.6 · Unificar configs y versiones (M-OPS-06)
**Analogía:** Que **todas las cocinas usen la misma receta impresa**: una sola fuente de configuración/versión, sin divergencias entre `.env`, JSON de config y código.

### F7.7 · Documentación de campos / F7.7b · Correcciones al informe de BD / F7.8 · Separar auditoría del plan vivo
**Analogía:** Alinear **el libro de recetas con lo que realmente se cocina**: documentar la semántica final de `premarket_*`/`gap` y los TF válidos (una vez cerrado T3.1); corregir los índices del informe BD (`d[1]`, `d[11]`, `d[23]`, no `d[3]`...) y los conteos reales post-F3.12 (110 → 123). El criterio: **el informe coincide con el código**.

---

## Estados actuales (recordatorio 2026-09-22)

- **FASE 0:** Verificación empírica, protocolo T1–T12 ✅ (pendientes T3.1/T13 mañana 09:29 ET). **F0.1 (A1–A16) ✅ y F0.3 (ADR 0001) ✅.**
- **FASE 1:** ✅ **Completada** — F1.1–F1.8 aplicados y verificados (changelog v2.3.2).
- **FASE 2:** F2.1 ✅, F2.2 ✅; **F2.3 preparada (backup + SQL, ejecución pospuesta)**; F2.4/F2.5 pendientes.
- **FASE 3 a 7:** por implementar (orden y duración en la Sección 2 / calendario consolidado del roadmap fuente).
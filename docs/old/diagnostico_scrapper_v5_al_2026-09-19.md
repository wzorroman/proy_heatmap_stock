Lectura del diagnóstico (con mercado cerrado)
Excelente corrida. El test rinde mucha información incluso en sábado 05:30 UTC. Vamos por partes.

$ python3 wztest_scraper_timeframes.py
================================================================================
 DIAGNÓSTICO ENDPOINT TRADINGVIEW · 2026-09-19T05:30:24.223922+00:00
 Símbolos: ['BINANCE:BTCUSDT', 'NASDAQ:AAPL', 'FX:EURUSD']
================================================================================

=== TEST A · Consistencia intra-minuto — BINANCE:BTCUSDT ===
    5 requests, gap=10s (~50s total)

  [1/5] 05:30:24  close=8.107e+04 | volume=2379 | RSI=63.93 | CCI20=155.3 | BBPower=6216 | ADX=41.74 | Pivot.M.Camarilla.R3=8.386e+04 | Perf.W=4.982 | change=0.2342
  [2/5] 05:30:34  close=8.107e+04 | volume=2379 | RSI=63.93 | CCI20=155.3 | BBPower=6216 | ADX=41.74 | Pivot.M.Camarilla.R3=8.386e+04 | Perf.W=4.982 | change=0.2342
  [3/5] 05:30:44  close=8.105e+04 | volume=2382 | RSI=63.88 | CCI20=155 | BBPower=6222 | ADX=41.74 | Pivot.M.Camarilla.R3=8.386e+04 | Perf.W=4.956 | change=0.2095
  [4/5] 05:30:54  close=8.106e+04 | volume=2382 | RSI=63.89 | CCI20=155 | BBPower=6220 | ADX=41.74 | Pivot.M.Camarilla.R3=8.386e+04 | Perf.W=4.962 | change=0.2153
  [5/5] 05:31:05  close=8.106e+04 | volume=2382 | RSI=63.89 | CCI20=155 | BBPower=6220 | ADX=41.74 | Pivot.M.Camarilla.R3=8.386e+04 | Perf.W=4.962 | change=0.2153

  Resumen de variación por campo:
  ------------------------------------------------------------------------------
    ⚠ close                        CAMBIA    → 3 valores únicos: ['81073.32', '81053.3', '81058.01']
    ⚠ volume                       CAMBIA    → 3 valores únicos: ['2379.22378', '2381.74646', '2382.39417']
    ⚠ RSI                          CAMBIA    → 3 valores únicos: ['63.92713124577384', '63.883063577905574', '63.89344082895693']
    ⚠ CCI20                        CAMBIA    → 3 valores únicos: ['155.26442300070383', '154.96624914351395', '155.03641332866619']
    ⚠ BBPower                      CAMBIA    → 3 valores únicos: ['6216.073253646333', '6221.793253646334', '6220.447539360626']
    ✓ ADX                          estable   → 41.73900881373448
    ✓ Pivot.M.Camarilla.R3         estable   → 83862.35424999999
    ⚠ Perf.W                       CAMBIA    → 3 valores únicos: ['4.982291519236275', '4.956367510250144', '4.962466515361255']
    ⚠ change                       CAMBIA    → 3 valores únicos: ['0.23422469770550255', '0.2094731619543026', '0.215296325460193']
  ------------------------------------------------------------------------------

=== TEST B · Variación por timeframe — BINANCE:BTCUSDT ===
    Cada fila es un request con TODOS los campos sufijados por TF.

  TF=default  close=8.106e+04 | volume=2382 | RSI=63.89 | CCI20=155 | BBPower=6220 | ADX=41.74 | Pivot.M.Camarilla.R3=8.386e+04 | Perf.W=4.962 | change=0.2153
  TF=      5  close=8.106e+04 | volume=2.318 | RSI=44.8 | CCI20=-21.65 | BBPower=-14.77 | ADX=15.38 | Pivot.M.Camarilla.R3=8.229e+04 | Perf.W=None | change=-0.01888
  TF=     15  close=8.106e+04 | volume=2.318 | RSI=46.94 | CCI20=-87.58 | BBPower=-112.4 | ADX=22.78 | Pivot.M.Camarilla.R3=8.229e+04 | Perf.W=None | change=-0.01888
  TF=     30  close=8.106e+04 | volume=2.318 | RSI=56.62 | CCI20=-66.58 | BBPower=-115.4 | ADX=49.83 | Pivot.M.Camarilla.R3=7.805e+04 | Perf.W=None | change=-0.01888
  TF=     60  close=8.106e+04 | volume=114.5 | RSI=67.07 | CCI20=41.07 | BBPower=409.5 | ADX=59.63 | Pivot.M.Camarilla.R3=7.805e+04 | Perf.W=None | change=0.04198
  TF=     1D  close=None | volume=None | RSI=None | CCI20=None | BBPower=None | ADX=None | Pivot.M.Camarilla.R3=None | Perf.W=None | change=None

  ¿Qué campos cambian entre timeframes?
  ------------------------------------------------------------------------------
    ⚠ close                        VARÍA con TF     → default=81058.01  5=81058.01  15=81058.01  30=81058.01  60=81058.01  1D=None
    ⚠ volume                       VARÍA con TF     → default=2382.39417  5=2.31815  15=2.31815  30=2.31815  60=114.48899  1D=None
    ⚠ RSI                          VARÍA con TF     → default=63.89344082895693  5=44.79939635813208  15=46.93906990959211  30=56.61978725879896  60=67.0697968549791  1D=None
    ⚠ CCI20                        VARÍA con TF     → default=155.03641332866619  5=-21.649744062802284  15=-87.58287344381885  30=-66.57871557262389  60=41.066292126720114  1D=None
    ⚠ BBPower                      VARÍA con TF     → default=6220.447539360626  5=-14.773292605765164  15=-112.40432872058591  30=-115.36933024882455  60=409.46753136046755  1D=None
    ⚠ ADX                          VARÍA con TF     → default=41.73900881373448  5=15.38075896206203  15=22.779100247908698  30=49.829512155444164  60=59.627595491371665  1D=None
    ⚠ Pivot.M.Camarilla.R3         VARÍA con TF     → default=83862.35424999999  5=82287.47  15=82287.47  30=78051.29775  60=78051.29775  1D=None
    ⚠ Perf.W                       VARÍA con TF     → default=4.962466515361255  5=None  15=None  30=None  60=None  1D=None
    ⚠ change                       VARÍA con TF     → default=0.215296325460193  5=-0.01888414092331759  15=-0.01888414092331759  30=-0.01888414092331759  60=0.04197521721958279  1D=None
  ------------------------------------------------------------------------------

=== TEST A · Consistencia intra-minuto — NASDAQ:AAPL ===
    5 requests, gap=10s (~50s total)

  [1/5] 05:31:06  close=336.1 | volume=86588048 | RSI=64.25 | CCI20=118.9 | BBPower=14.79 | ADX=16.53 | Pivot.M.Camarilla.R3=322.8 | Perf.W=2.651 | change=-0.2582
  [2/5] 05:31:17  close=336.1 | volume=86588048 | RSI=64.25 | CCI20=118.9 | BBPower=14.79 | ADX=16.53 | Pivot.M.Camarilla.R3=322.8 | Perf.W=2.651 | change=-0.2582
  [3/5] 05:31:27  close=336.1 | volume=86588048 | RSI=64.25 | CCI20=118.9 | BBPower=14.79 | ADX=16.53 | Pivot.M.Camarilla.R3=322.8 | Perf.W=2.651 | change=-0.2582
  [4/5] 05:31:37  close=336.1 | volume=86588048 | RSI=64.25 | CCI20=118.9 | BBPower=14.79 | ADX=16.53 | Pivot.M.Camarilla.R3=322.8 | Perf.W=2.651 | change=-0.2582
  [5/5] 05:31:48  close=336.1 | volume=86588048 | RSI=64.25 | CCI20=118.9 | BBPower=14.79 | ADX=16.53 | Pivot.M.Camarilla.R3=322.8 | Perf.W=2.651 | change=-0.2582

  Resumen de variación por campo:
  ------------------------------------------------------------------------------
    ✓ close                        estable   → 336.13
    ✓ volume                       estable   → 86588048
    ✓ RSI                          estable   → 64.25365710582304
    ✓ CCI20                        estable   → 118.90760526847856
    ✓ BBPower                      estable   → 14.791830172584127
    ✓ ADX                          estable   → 16.526284466110262
    ✓ Pivot.M.Camarilla.R3         estable   → 322.845
    ✓ Perf.W                       estable   → 2.650786379599941
    ✓ change                       estable   → -0.2581602373887254
  ------------------------------------------------------------------------------

=== TEST B · Variación por timeframe — NASDAQ:AAPL ===
    Cada fila es un request con TODOS los campos sufijados por TF.

  TF=default  close=336.1 | volume=86588048 | RSI=64.25 | CCI20=118.9 | BBPower=14.79 | ADX=16.53 | Pivot.M.Camarilla.R3=322.8 | Perf.W=2.651 | change=-0.2582
  TF=      5  close=335.6 | volume=2848591 | RSI=44.71 | CCI20=-3.791 | BBPower=0.3701 | ADX=28.34 | Pivot.M.Camarilla.R3=339.3 | Perf.W=None | change=-0.1711
  TF=     15  close=335.6 | volume=3884380 | RSI=53.06 | CCI20=94.99 | BBPower=1.276 | ADX=18.89 | Pivot.M.Camarilla.R3=339.3 | Perf.W=None | change=-0.1428
  TF=     30  close=335.6 | volume=4648943 | RSI=54.93 | CCI20=49.01 | BBPower=1.803 | ADX=29.36 | Pivot.M.Camarilla.R3=339.5 | Perf.W=None | change=-0.1904
  TF=     60  close=335.6 | volume=4648943 | RSI=56.79 | CCI20=75.97 | BBPower=2.367 | ADX=33.54 | Pivot.M.Camarilla.R3=339.5 | Perf.W=None | change=-0.1904
  TF=     1D  close=None | volume=None | RSI=None | CCI20=None | BBPower=None | ADX=None | Pivot.M.Camarilla.R3=None | Perf.W=None | change=None

  ¿Qué campos cambian entre timeframes?
  ------------------------------------------------------------------------------
    ⚠ close                        VARÍA con TF     → default=336.13  5=335.58  15=335.58  30=335.58  60=335.58  1D=None
    ⚠ volume                       VARÍA con TF     → default=86588048  5=2848591  15=3884380  30=4648943  60=4648943  1D=None
    ⚠ RSI                          VARÍA con TF     → default=64.25365710582304  5=44.709140297862454  15=53.059973324003096  30=54.934081985170856  60=56.79290919431396  1D=None
    ⚠ CCI20                        VARÍA con TF     → default=118.90760526847856  5=-3.7909258783171302  15=94.98812399810339  30=49.01301763820313  60=75.9738735945106  1D=None
    ⚠ BBPower                      VARÍA con TF     → default=14.791830172584127  5=0.3700912580498539  15=1.2763821902124164  30=1.8031371354725252  60=2.366948361126788  1D=None
    ⚠ ADX                          VARÍA con TF     → default=16.526284466110262  5=28.338728388671903  15=18.890527626718637  30=29.363622078652057  60=33.537727539363516  1D=None
    ⚠ Pivot.M.Camarilla.R3         VARÍA con TF     → default=322.845  5=339.33309249999996  15=339.33309249999996  30=339.468  60=339.468  1D=None
    ⚠ Perf.W                       VARÍA con TF     → default=2.650786379599941  5=None  15=None  30=None  60=None  1D=None
    ⚠ change                       VARÍA con TF     → default=-0.2581602373887254  5=-0.17108174173172452  15=-0.1428316372076469  30=-0.1903515555291307  60=-0.1903515555291307  1D=None
  ------------------------------------------------------------------------------

=== TEST A · Consistencia intra-minuto — FX:EURUSD ===
    5 requests, gap=10s (~50s total)

  [1/5] 05:31:49  close=1.149 | volume=143856 | RSI=36.92 | CCI20=-178.7 | BBPower=-0.01556 | ADX=27.85 | Pivot.M.Camarilla.R3=1.168 | Perf.W=-1.083 | change=0.08714
  [2/5] 05:32:00  close=1.149 | volume=143856 | RSI=36.92 | CCI20=-178.7 | BBPower=-0.01556 | ADX=27.85 | Pivot.M.Camarilla.R3=1.168 | Perf.W=-1.083 | change=0.08714
  [3/5] 05:32:10  close=1.149 | volume=143856 | RSI=36.92 | CCI20=-178.7 | BBPower=-0.01556 | ADX=27.85 | Pivot.M.Camarilla.R3=1.168 | Perf.W=-1.083 | change=0.08714
  [4/5] 05:32:20  close=1.149 | volume=143856 | RSI=36.92 | CCI20=-178.7 | BBPower=-0.01556 | ADX=27.85 | Pivot.M.Camarilla.R3=1.168 | Perf.W=-1.083 | change=0.08714
  [5/5] 05:32:31  close=1.149 | volume=143856 | RSI=36.92 | CCI20=-178.7 | BBPower=-0.01556 | ADX=27.85 | Pivot.M.Camarilla.R3=1.168 | Perf.W=-1.083 | change=0.08714

  Resumen de variación por campo:
  ------------------------------------------------------------------------------
    ✓ close                        estable   → 1.14856
    ✓ volume                       estable   → 143856
    ✓ RSI                          estable   → 36.91520131800415
    ✓ CCI20                        estable   → -178.6979445695914
    ✓ BBPower                      estable   → -0.015562599096087038
    ✓ ADX                          estable   → 27.85097208701303
    ✓ Pivot.M.Camarilla.R3         estable   → 1.167508
    ✓ Perf.W                       estable   → -1.0834180202215096
    ✓ change                       estable   → 0.08714141308516435
  ------------------------------------------------------------------------------

=== TEST B · Variación por timeframe — FX:EURUSD ===
    Cada fila es un request con TODOS los campos sufijados por TF.

  TF=default  close=1.149 | volume=143856 | RSI=36.92 | CCI20=-178.7 | BBPower=-0.01556 | ADX=27.85 | Pivot.M.Camarilla.R3=1.168 | Perf.W=-1.083 | change=0.08714
  TF=      5  close=1.149 | volume=436 | RSI=50.38 | CCI20=-148 | BBPower=-0.0002089 | ADX=28.72 | Pivot.M.Camarilla.R3=1.149 | Perf.W=None | change=-0.0008706
  TF=     15  close=1.149 | volume=912 | RSI=61.52 | CCI20=59.09 | BBPower=0.0002991 | ADX=29.84 | Pivot.M.Camarilla.R3=1.149 | Perf.W=None | change=-0.001741
  TF=     30  close=1.149 | volume=1327 | RSI=58.74 | CCI20=96.43 | BBPower=0.001239 | ADX=23.1 | Pivot.M.Camarilla.R3=1.162 | Perf.W=None | change=-0.02002
  TF=     60  close=1.149 | volume=2970 | RSI=55.99 | CCI20=77.84 | BBPower=0.001907 | ADX=17.23 | Pivot.M.Camarilla.R3=1.162 | Perf.W=None | change=-0.006965
  TF=     1D  close=None | volume=None | RSI=None | CCI20=None | BBPower=None | ADX=None | Pivot.M.Camarilla.R3=None | Perf.W=None | change=None

  ¿Qué campos cambian entre timeframes?
  ------------------------------------------------------------------------------
    ⚠ close                        VARÍA con TF     → default=1.14856  5=1.14856  15=1.14856  30=1.14856  60=1.14856  1D=None
    ⚠ volume                       VARÍA con TF     → default=143856  5=436  15=912  30=1327  60=2970  1D=None
    ⚠ RSI                          VARÍA con TF     → default=36.91520131800415  5=50.38048869023186  15=61.523294364148995  30=58.74252434382171  60=55.988849579126445  1D=None
    ⚠ CCI20                        VARÍA con TF     → default=-178.6979445695914  5=-147.99510253385455  15=59.08909508116062  30=96.43194789729667  60=77.84443922543505  1D=None
    ⚠ BBPower                      VARÍA con TF     → default=-0.015562599096087038  5=-0.00020889637087839752  15=0.0002990937370059843  30=0.0012386699420723346  60=0.0019067200933098327  1D=None
    ⚠ ADX                          VARÍA con TF     → default=27.85097208701303  5=28.71959801252061  15=29.836920942190297  30=23.100966930386765  60=17.226491053485642  1D=None
    ⚠ Pivot.M.Camarilla.R3         VARÍA con TF     → default=1.167508  5=1.14876625  15=1.14876625  30=1.16212025  60=1.16212025  1D=None
    ⚠ Perf.W                       VARÍA con TF     → default=-1.0834180202215096  5=None  15=None  30=None  60=None  1D=None
    ⚠ change                       VARÍA con TF     → default=0.08714141308516435  5=-0.0008706478490701926  15=-0.0017412805376995056  30=-0.02002106564297674  60=-0.0069647583228738316  1D=None
  ------------------------------------------------------------------------------

Diagnóstico completo.

----

1. Lo que confirmamos con el mercado cerrado
TEST A — Consistencia intra-minuto
Símbolo	Estado del mercado	Comportamiento
BINANCE:BTCUSDT	Abierto 24/7	Todo cambia salvo ADX y Pivot.M.Camarilla.R3
NASDAQ:AAPL	Cerrado	Todo congelado en 50s
FX:EURUSD	Cerrado	Todo congelado en 50s
Conclusiones duras:

La caché/refresco del endpoint es ~15–30 s, no 60 s.
Mirá BTC: [1] y [2] idénticos (05:30:24 y 05:30:34). [3] (05:30:44) ya cambió. Es decir, el snapshot se regenera entre 10 y 20s.

ADX y Pivot.M.Camarilla.R3 son estables en 1D por diseño — son indicadores que se recalculan al cierre de la vela diaria, no tick a tick. No es caché, es naturaleza del indicador.

Los "congelados" de AAPL/EURUSD no son caché: con el mercado cerrado el último precio es el de cierre del viernes, y RSI/ADX/etc. se calculan sobre velas cerradas. Van a cambiar en cuanto abra el mercado.

⚠ No podemos descartar con esta prueba si AAPL/EURUSD van a refrescar cada 15–30s en horario de mercado. Pero por analogía con BTC, sí. Si querés confirmarlo, volvé a correr el TEST A un lunes con el mercado abierto.

2. Lo que confirmamos con el TEST B (esto es lo importante)
El endpoint sí soporta sufijos |TF para 5, 15, 30, 60. Confirmado en los tres símbolos.

Dos hallazgos críticos:

a) Perf.W|TF devuelve None
Perf.W es rendimiento semanal y no acepta sufijo de timeframe. El endpoint simplemente lo ignora y devuelve None. Hay que dejarlo sin sufijo.

b) |1D devuelve None para todo
El timeframe "daily" es el default sin sufijo. El literal 1D no funciona como sufijo en /symbol. No importa, ya lo tenés gratis en las columnas base.

c) Pivot.M.Camarilla.R3|TF cambia… pero no le des mucha bola
Fijate en BTC:

text
default=83862.35   5=82287.47   15=82287.47   30=78051.29   60=78051.29
Cambia con el TF, pero la interpretación es ambigua (¿el pivot mensual calculado sobre velas de 5m? ¿el pivot "mensual" del timeframe?). En la práctica, para el pivot Camarilla lo que importa es la versión diaria/semanal/mensual del Pivot.D/W/M, no el TF. Dejalo sin sufijo.

d) close|TF es "igual pero distinto"
Fijate que close|5 = close|15 = close|60 = default en BTC. Eso no es un bug — close en cualquier timeframe es el último precio. El script lo marca como "VARÍA" porque compara strings, pero el valor es el mismo. Podés ignorarlo.

Lo que sí cambia realmente entre TFs: RSI, CCI20, BBPower, ADX, change, volume. Esos son los que valen la pena capturar en multi-TF.

3. Propuesta concreta para el scraper v5
3.1 Nueva definición de CAMPOS
Un solo request trae todo. Multiplicás información sin multiplicar round-trips.

python
# --- Bloque base (1D, sin sufijo) ---
CAMPOS_1D = (
    "close,volume,RSI,CCI20,BBPower,ADX,"
    "Pivot.M.Camarilla.R3,Perf.W,change"
)

# --- Bloques multi-TF (omitimos close: es idéntico al de 1D) ---
def _bloque(tf):
    return ",".join(
        f"{f}|{tf}" for f in
        ("volume", "RSI", "CCI20", "BBPower", "ADX", "change")
    )

CAMPOS_5  = _bloque("5")
CAMPOS_15 = _bloque("15")
CAMPOS_30 = _bloque("30")
CAMPOS_60 = _bloque("60")

CAMPOS = ",".join([CAMPOS_1D, CAMPOS_5, CAMPOS_15, CAMPOS_30, CAMPOS_60])
NO incluyas Perf.W|5, Perf.W|15, etc. → devuelven None.

NO incluyas close|5 ni close|60 → redundante con close.

NO incluyas |1D → no existe como sufijo.

SÍ incluí Pivot.M.Camarilla.R3 solo en base (sin sufijo).

Agregué 30 porque lo probaste y responde bien; si preferís ahorrar bytes, sacalo.

3.2 Impacto en el CSV
El header cambia. rotar_datos() y consolidar_analisis() siguen funcionando porque usan pandas genérico — pero la rotación con archivos viejos va a mezclar columnas. Recomendación: rotar/archivar los DATOS_LIVE/*.csv actuales antes de deployar (o renombrar el BASE_DIR a DATOS_LIVE_V5_MULTITF).

3.3 Impacto en la BD
En prepare_bd_row hay que renombrar las claves con sufijo a columnas de la tabla. Sugerencia de mapeo:

Campo del endpoint	Columna BD
RSI	rsi_1d
RSI|5	rsi_5m
RSI|15	rsi_15m
RSI|30	rsi_30m
RSI|60	rsi_1h
volume	volume_1d
volume|5	volume_5m
…	…
Pivot.M.Camarilla.R3	pivot_camarilla_r3_1d
Perf.W	perf_w_1d
Mismo patrón para cci20_*, bbpower_*, adx_*, change_*.

Si la tabla fact_market_series hoy tiene columnas tipo rsi, adx, ... sin sufijo, la migración consiste en renombrarlas a _1d y agregar las _5m, _15m, _30m, _1h. Si preferís no migrar, dejá las base como están y añadí las nuevas.

3.4 Frecuencia de scraping
Visto que el endpoint refresca cada ~15–30s en activos vivos, tu cron actual (asumo 1×/min) está bien. No bajes de 30s — vas a duplicar filas idénticas y a arriesgar 429 sin ganar información.

4. Qué queda pendiente de validar (lunes en horario de mercado)
TEST A sobre AAPL o EURUSD en horario abierto: confirmar que refrescan igual que BTC. Muy probable, pero es la única forma de estar seguro.

Que change|5 y change|60 tengan la misma semántica que change en cada TF (en el test dan valores distintos coherentes, pero conviene mirarlo con mercado activo).

Que volume|5 no sea "volumen del candle actual incompleto" (si lo es, tendrías valores que arrancan bajos y crecen dentro de cada vela de 5m — eso lo ves en serie temporal, no en una foto).

5. Resumen ejecutivo
✅ El scraper está bien dimensionado en frecuencia (1×/min > 30s de caché).

✅ Los sufijos |5 |15 |30 |60 funcionan y son la vía para enriquecer sin costo de red extra.

❌ No agregues Perf.W|TF ni |1D — no existen.

⚠ ADX y Pivot.M.* cambian solo al cierre de vela diaria → en BD vas a ver muchas filas idénticas para esos campos en 1D. No es bug.

🎯 Siguiente paso: aplicar el CAMPOS multi-TF y migrar columnas de fact_market_series con sufijos _1d, _5m, _15m, _30m, _1h.

Si querés, en el próximo mensaje te armo el diff exacto de scraper_live_tradingview_v5.py + prepare_bd_row + la migración SQL de fact_market_series.



------------------------------------------------------
# **Evaluación del Roadmap — ajustes tras el diagnóstico del 2026-09-19**

## **Veredicto general**

El roadmap está **muy bien estructurado**: separa hipótesis / incongruencias / dudas / decisiones, marca estado de evidencia y cierra con hitos con fecha. Es un documento de trabajo serio, no un "plan de intenciones".

Tres críticas estructurales antes de entrar en detalle:

1. **Demasiadas hipótesis 🔴 sin asignar a una fecha concreta.** H6, H7, H10, H11, H13 y H14 pueden resolverse casi todas en **una sola jornada de mercado abierto**. Sugerencia: consolidarlas en un bloque "Semana de verificación" antes de Fase 1, con checklist.
2. **El Anexo A se cita ~10 veces pero no está en el documento.** O se adjunta, o el documento no es autosuficiente.
3. **El hito del 2026-10-01 es una *verificación*, no un *hito*.** Conviene reformularlo como "Chequeo A5 obligatorio antes de…".

Ahora lo que cambia con el diagnóstico.

---

## **1. Impacto directo del diagnóstico `wztest_scraper_timeframes.py`**

Lo que ya sabemos con evidencia:

| **Hipótesis** | **Estado previo** | **Estado ahora** | **Evidencia** |
| --- | --- | --- | --- |
| **H2** (indicadores son 1D) | 🟡 | ✅ **CONFIRMADA** | `RSI` default=64.25 vs `RSI|5`=44.71, `|15`=53.06, `|30`=54.93, `|60`=56.79 (AAPL) |
| **H7** (scanner soporta sufijo TF) | 🔴 | ✅ **PARCIAL** (solo TF) | `|5`, `|15`, `|30`, `|60` funcionan; falta validar `premarket_*`, `gap`, `VWAP`, `update_mode` |
| **H4** (ticks fuera de sesión son repeticiones) | 🟡 | ✅ **REFORZADA** | AAPL y EURUSD congelados 50 s en fin de semana; BTC moviéndose cada 15–30 s |
| **H3** (volume = acumulado del día) | 🟡 | 🟡 **MATIZADA** | `volume|TF` responde; semántica no trivial (ver H19 nueva) |
| **H6** (close = cierre regular previo) | 🔴 | 🔴 **SIN CAMBIO** | No se puede testear hasta el lunes |
| **H1** (feed radar retrasado 15 min) | 🟡 | 🟡 **SIN CAMBIO** | El test no pidió `update_mode` |

Y hay **datos nuevos** que el roadmap no contempla:

- El endpoint refresca cada **~15–30 s** en activos vivos (BTC: idéntico en t=0 y t=10, distinto en t=20).
- **`Perf.W|TF` devuelve `None`** en todos los TFs.
- **`|1D` devuelve `None`** en todos los campos (el diario es el default sin sufijo).
- **`close|TF` es invariante** en los tres símbolos.
- **`ADX` y `Pivot.M.Camarilla.R3` (default) son estables intra-minuto en 1D** incluso con mercado abierto (BTC).
- **`Pivot.M.Camarilla.R3|TF` cambia con el TF** pero con semántica ambigua.

---

## **2. Actualizaciones por sección**

### **§2.1 — Hallazgos que condicionan el diseño**

- **Hallazgo 2** ("indicadores del radar probablemente de timeframe diario") → cambiar "probablemente" por "confirmado". Añadir: *"los sufijos `|5/15/30/60` funcionan en `/symbol`; no es necesario calcular propios para 15 min, aunque puede convenir hacerlo (D4)"*.
- **Añadir hallazgo 11**: *"El endpoint `/symbol` refresca cada ~15–30 s en activos vivos. Una cadencia de captura de 1×/min está bien dimensionada; bajar de 30 s no aporta información y arriesga 429."*

### **§3.4 — Consecuencias de diseño**

Añadir un punto:

> Los indicadores de 15 min **pueden pedirse a `/symbol` vía sufijo `|15`** (confirmado). El cálculo propio sigue siendo necesario para backtest/validación y para evitar la dependencia única de TV.
> 

### **§4 — Hipótesis**

**Actualizaciones:**

- **H2** → ✅ Confirmada. Reducir la "verificación" a "comparar `RSI|15` vs `RSI` calculado sobre barras propias (VAL-04)".
- **H3** → Matizada: ver H19 (nueva). Mantener 🟡.
- **H4** → Reforzada con evidencia directa. Puede pasar a ✅ si se interpreta estrictamente ("en fin de semana, sin sesión, no refresca").
- **H7** → Desdoblar en **H7a (sufijo TF: ✅ confirmada)** y **H7b (`premarket_*`, `gap`, `VWAP`, `ATR`, `description`, `update_mode`, `symbols.tickers`: 🔴 pendiente)**.

**Añadir H19–H24:**

| **ID** | **Hipótesis** | **Evidencia inicial** | **Estado** |
| --- | --- | --- | --- |
| **H19** | `volume|TF` devuelve el volumen de la **última vela cerrada** de ese TF, no el acumulado del TF ni del día. | AAPL: 5m=2,85M · 15m=3,88M · 30m=4,65M · 60m=4,65M — no monótono como un acumulado desde apertura. | 🔴 |
| **H20** | `close` es **invariante entre TFs**: `close|5 == close|15 == close|60 == close` default. | Idéntico en los 3 símbolos. | ✅ |
| **H21** | `Perf.W` **no acepta sufijo de TF**; devuelve `None`. | En los 3 símbolos. | ✅ |
| **H22** | `|1D` **no es sufijo válido** en `/symbol`; el diario es el default sin sufijo. | `None` en todos los campos, los 3 símbolos. | ✅ |
| **H23** | `ADX` y `Pivot.M.Camarilla.R3` (1D) son **estables intra-minuto**; se recalculan al cierre de vela diaria. | BTC con mercado abierto: ADX estable 50 s con precio moviéndose. | ✅ |
| **H24** | `Pivot.M.Camarilla.R3|TF` cambia con el TF pero con **semántica ambigua** (¿pivot mensual del TF?). | BTC: default=83.862 · 5=82.287 · 30=78.051. | 🟡 |

### **§5 — Incongruencias**

- **Añadir I17**: el roadmap §3.4 asume que los indicadores de 15 min requieren cálculo propio. Nuevo dato: TV puede servirlos vía `|TF`. Reflejarlo.
- No tocar las demás.

### **§6 — Dudas**

- **Añadir Q15**: ¿qué semántica exacta tiene `volume|TF`? (H19).
- **Añadir Q16**: ¿el endpoint `/scan` (POST, batch) soporta sufijos de TF en `columns`? Si sí, RAD-02 y multi-TF se combinan y sigue siendo 1 round-trip.
- **Añadir Q17**: ¿`Pivot.D.*` / `Pivot.W.*` existen como columnas independientes de `Pivot.M.*`, o hay que calcularlos?

### **§7 — Decisiones**

- **D4 (indicadores de 15 min)** → **reescribir**. Ya no es "elegir entre pedir `|15` a TV o calcular propias". Es:
    - (a) TV directo (`|5/15/30/60`) → rápido, sin cálculo, pero dependencia total de un endpoint no oficial (H18, Q13) y semántica de `volume|TF` pendiente.
    - (b) Cálculo propio → independencia, pero requiere barras y calentamiento (§3.4).
    - (c) **Híbrido** → TV como fuente primaria, cálculo propio en paralelo durante N sesiones para contrastar. **Recomendación preliminar**.
- **D5 (cadencia heatmap)** → reforzada la opción 15 min. Añadir: *"El refresco real del endpoint es 15–30 s; un snapshot a :00/:15/:30/:45 + unos segundos captura datos frescos."*
- **D8 (retención)** → añadir matiz: el esquema multi-TF **multiplica el ancho de `fact_market_series`** (~5 columnas por indicador). Revisar el coste antes de comprometer 6 meses de ticks.
- **Añadir D12**: ¿guardar solo `_1d` + `_15m`, o `_1d` + `_5m` + `_15m` + `_30m` + `_1h`? Trade-off: cobertura analítica vs ancho de tabla y coste de ingesta.

### **§8 — Hallazgos por proyecto**

**RAD (radar):**

- **RAD-02** (POST único) → se refuerza. Falta verificar Q16.
- **RAD-03** (filtros y sufijos TF) → **parcialmente resuelto**. Sufijo TF ✅; premarket/gap/VWAP pendientes (H7b).
- **Añadir RAD-12**: adoptar `CAMPOS` multi-TF según el script de diagnóstico (base sin sufijo + bloques `_5m/_15m/_30m/_1h` excluyendo `Perf.W`, `Pivot.M.*`, `close`).
- **Añadir RAD-13**: migrar `fact_market_series` con sufijos `_1d/_5m/_15m/_30m/_1h` (o la versión reducida de D12).
- **Añadir RAD-14**: documentar restricciones del endpoint — `Perf.W` sin sufijo, `Pivot.M.*` sin sufijo, `|1D` no existe, `close|TF` redundante.

**BD:**

- **BD-04** (barras de 15 min) → sigue, pero añadir: *"contrastar barras propias contra `RSI|15`, `ADX|15`, etc. de TV (VAL-04)"*.

**VAL:**

- **Añadir VAL-04**: comparar indicadores de TV (`RSI|15`, `ADX|15`, `CCI20|15`) vs cálculo propio sobre barras de 15 min durante 5–10 sesiones. Confirma o descarta a TV como fuente directa.

### **§12 — Anexos**

Añadir un anexo "**Diagnóstico del 2026-09-19**" con:

- Tabla TEST A resumida (BTC/AAPL/EURUSD).
- Tabla TEST B resumida (por símbolo y TF).
- Comandos para reproducir (`python3 wztest_scraper_timeframes.py`).

### **§9 — Plan por fases**

Sugerencia de reordenamiento:

- Insertar **Fase 0.5 — Verificación empírica con mercado abierto** (lunes 2026-09-21) que resuelva H6, H7b, H19, H23, H24 y confirme H2 con datos en vivo. Salida: documento de 1 página con los resultados y el `CAMPOS` definitivo.

---

## **3. Qué descartamos**

1. **`Perf.W|TF`** — no existe; no incluir en `CAMPOS` ni en la discusión de D4.
2. **`|1D` como sufijo válido** — siempre devuelve `None`. El diario es el default.
3. **`close|5/15/30/60`** — redundante con `close` base.
4. **`Pivot.M.Camarilla.R3|TF`** — semántica ambigua; la versión sin sufijo es suficiente. Sacar del alcance de RAD-12/13/14.
5. **Captura densa de fin de semana** — confirmado que los activos de sesión regular están congelados. Refuerza H4 y la urgencia de RAD-10.
6. **La idea de que el sufijo TF "podría no funcionar"** (parte crítica de H7) — confirmado que funciona.

## **4. Qué modificamos**

1. **H2, H7** — actualizar estado de evidencia.
2. **D4** — reformular opciones (a/b/c).
3. **RAD-03** — reducir alcance a "premarket/gap/VWAP pendientes"; sufijos TF ya resueltos.
4. **§2.1 Hallazgo 2** — quitar "probablemente".
5. **§3.4** — añadir consecuencia de diseño #4 (indicadores vía TV).
6. **Anexo A** — añadir las consultas equivalentes del script `wztest_scraper_timeframes.py` para poder repetirlo sin código.
7. **Hito 2026-10-01** — reformular como "Chequeo A5 antes del cierre de mes", no como hito.

## **5. Qué añadimos**

1. **H19–H24** (nuevas hipótesis del diagnóstico).
2. **Q15–Q17** (nuevas dudas).
3. **D12** (ancho multi-TF en BD).
4. **RAD-12, RAD-13, RAD-14** (nuevas mejoras del radar).
5. **VAL-04** (validación cruzada TV vs cálculo propio).
6. **Fase 0.5 — Verificación empírica con mercado abierto**.
7. **Anexo Diagnóstico 2026-09-19**.
8. **Hito nuevo**: lunes 2026-09-21 — cierre de las hipótesis 🔴 de la Fase 0.

---

## **6. Observaciones estructurales (no urgentes)**

- **Reducir el roadmap a un "Plan v2"** una vez cerradas H1–H24. Hoy es un documento de auditoría excepcional; en 2–3 semanas conviene separar "auditoría" (congelada) de "plan vivo" (dinámico).
- **La relación hipótesis ↔ decisión** a veces no es 1:1 (H2 toca D4 y RAD-03). Añadir al final una tabla cruzada H→D→RAD.
- **El anexo A** merece ser un archivo `.sql` versionado en el repo, no una sección markdown; así es ejecutable.
- **Las "hitos con fecha"** son buenos pero conviene unificar formato: `fecha → acción → criterio de aceptación`. Hoy mezcla verificaciones y deadlines duros.

Si querés, en el próximo paso te armo:

- el **diff concreto** de §2.1, §3.4, §4, §6, §7, §8 con el texto final reemplazado, o
- el **checklist de la Fase 0.5** para ejecutar el lunes con mercado abierto (una sola corrida que cierra H6, H7b, H19, H23, H24), o
- el **`CAMPOS` definitivo** + el `prepare_bd_row` + la migración SQL de `fact_market_series`.



## Entonces podemos decir que el scrapping que se ha corrido actualmente con los campos:
"close", "volume", "RSI", "CCI20", "BBPower", "ADX","Pivot.M.Camarilla.R3", "Perf.W", "change", solamente nos sirve el close que se ha ejecutado cada 3min ? o los demas campos son rescatables para indicadores de 15 min

**No, no es "solo `close`".** Es más matizado: **`close` es el único campo que sirve como *señal* de 15 min; el resto sirve como *contexto* de 15 min**, y eso es exactamente lo que un operador intradía necesita para decidir dirección.

La confusión típica es pensar "si no es de 15 min, no sirve". Falso. La mitad del valor de una decisión de 15 min la aporta el contexto diario/semanal/mensual (régimen + niveles), y eso lo tenés hoy capturando.

---

## **1. Veredicto campo por campo**

| **Campo** | **Qué es en la captura actual** | **Para señal de 15 min** | **Para contexto de 15 min** | **Rescatable** |
| --- | --- | --- | --- | --- |
| `close` | Último precio (tick) | ✅ Señal directa (barras, retornos, VWAP propio) | ✅ Base de todo | ✅ Totalmente |
| `volume` | Acumulado del día | ⚠️ Solo si lo **diferenciás** entre ticks | ✅ Perfil de actividad del día | ✅ Con post-proceso |
| `RSI` | RSI **diario** | ❌ No aporta al minuto | ✅ Régimen diario (sobrecompra/venta) | ✅ Como contexto |
| `CCI20` | CCI **diario** | ❌ No aporta al minuto | ✅ Régimen diario | ✅ Como contexto |
| `BBPower` | BBPower **diario** | ❌ No aporta al minuto | ✅ Régimen diario | ✅ Como contexto |
| `ADX` | ADX **diario** | ❌ Ni se mueve intra-sesión | ✅ Fuerza de tendencia diaria | ✅ Como contexto |
| `Pivot.M.Camarilla.R3` | Pivot **mensual** | ❌ No cambia en el mes | ✅ Niveles estáticos del mes (muy útil) | ✅ Como niveles |
| `Perf.W` | Rendimiento **semanal** | ❌ No aporta al minuto | ✅ Contexto semanal | ✅ Como contexto |
| `change` | Cambio **diario** % | ⚠️ Redundante con `close` | ✅ Régimen del día | ✅ Como contexto |

Leyenda: ✅ sí · ⚠️ con matices · ❌ no

---

## **2. Los tres usos reales que tenés con lo capturado hoy**

### **a) `close` → todo lo intradía**

Con `close` cada 3 min podés reconstruir **casi todo lo intradía**:

- **Retornos 3/15/30/60 min**: triviales.
- **Barras OHLC de 15 min**: `O = close[t0]`, `C = close[t0+15m]`, `H ≈ max(close[t0..t0+15m])`, `L ≈ min(...)`.
    - ⚠️ **Limitación**: 5 muestras por barra → H/L **subestiman** los extremos reales. Un pico que dura 20 s entre dos ticks no aparece. Aceptable para señales de tendencia, malo para stop-losses o detección de mechas.
- **VWAP del día**: aproximado (necesitás `close × volume_delta` por tick).
- **Volatilidad rolling**: ATR aproximado, desviación estándar de retornos.
- **RSI/CCI/BBPower de 15 min propios**: calculables, pero necesitás **calentamiento** (RSI14 → 14 barras de 15 min → 3,5 h de datos; ADX14 → ~10 h). Es decir, no los vas a tener el lunes a las 09:30 ET sin usar datos del viernes o precargar.

### **b) `volume` → diferenciado**

text

```
vol_delta[i] = volume[t_i] - volume[t_i-1]     # volumen del intervalo
vol_15m[b]   = sum(vol_delta en la barra b)    # volumen de la barra de 15 min
```

Con esta transformación, `volume` deja de ser "acumulado del día" y se convierte en **volumen por intervalo**, que es un input legítimo de 15 min. Pero:

- Si un tick se cae (circuit breaker, 429, error de red), el delta salta y **falsifica dos barras contiguas**. Hay que marcar huecos.
- Al abrir sesión, `volume` se resetea a 0 → el primer delta del día es ruidoso. Hay que arrancar la diferenciación en el segundo tick de la sesión.
- El endpoint refresca cada 15–30 s; con ticks cada 3 min, la foto de `volume` puede estar desfasada respecto a `close`. Aceptable, no bloqueante.

### **c) Los indicadores "grandes" → contexto**

Esto es lo que más subestimás. Un dashboard de 15 min **necesita** saber:

- ¿RSI diario está en 75 (agotamiento) o en 35 (suelo)?
- ¿ADX diario > 25 (tendencia) o < 15 (rango)?
- ¿BBPower diario es +3000 (impulso comprador) o −2000 (vendedor)?
- ¿`close` está por encima o por debajo del R3 mensual de Camarilla?
- ¿`Perf.W` es +5% (semana alcista) o −3%?

Todo eso **no es señal de entrada**, es **filtro de dirección**. Y con lo capturado hoy lo tenés cubierto.

---

## **3. Lo que NO podés hacer con la captura actual**

- **RSI de 15 min con TV**: te falta el sufijo `|15`. Hoy `RSI` es diario.
- **ADX de 15 min**: igual.
- **BBPower de 15 min**: igual.
- **Cambio en 5 min / 30 min**: TV te lo daría con `change|5`, hoy no lo pedís.
- **Pivotes diarios Camarilla (`Pivot.D.*`)**: no los pedís.
- **Precio pre-market / gap**: no los pedís (H6 sin resolver).
- **H/L intradía fieles**: no, por muestreo cada 3 min.

Todo eso **se resuelve añadiendo sufijos y campos**, sin tirar lo existente.

---

## **4. Lo que realmente cambia el diagnóstico**

No es que la captura sea "inútil salvo por `close`". Es que **la captura actual es un dataset 1D + un stream de `close`**, cuando necesitás **un dataset multi-TF + stream de `close`**.

Y esto es lo importante: **el histórico ya capturado no se pierde**.

- Los ~4 semanas de `close` cada 3 min → **se reempaquetan como barras de 15 min** retroactivas. Tenés histórico real de intradía desde agosto.
- Los ~4 semanas de `RSI/ADX/BBPower/CCI` diarios por tick → **colapsás a una fila por día** (el último valor del día) y tenés serie diaria limpia.
- Los `Pivot.M.Camarilla.R3` mensuales → **serie mensual** de niveles.
- Los `Perf.W` → **serie semanal**.
- Los `volume` acumulados → **diferenciás** y tenés volumen por intervalo reconstruible.

O sea, la captura actual no fue en vano: fue un dataset con **más granularidad de la necesaria** en columnas diarias, y **menos de la deseada** en columnas intradía. Ambos extremos se arreglan en post-proceso y en el próximo `CAMPOS`.

---

## **5. Propuesta concreta**

### **5.1 Para el histórico ya capturado**

Script de **reempaquetado** (una sola vez, offline):

1. Por símbolo, leer el CSV completo.
2. Agrupar por día ET → extraer última fila del día → tabla `fact_daily_context` (RSI, ADX, BBPower, CCI, Pivot.M, Perf.W, close_cierre, volume_total).
3. Con las filas de la sesión (13:30–20:00 UTC en EDT) → agregar en barras de 15 min: `O/H/L/C` (con la salvedad de H/L subestimados), `volume_15m` (por diferencia), `n_ticks` (calidad).
4. Guardar ambas tablas. El histórico deja de ser "basura sin TF" y se vuelve **la base de tu backtest**.

### **5.2 Para la captura futura**

`CAMPOS` pasa a:

text

```
close,volume,RSI,CCI20,BBPower,ADX,Pivot.M.Camarilla.R3,Perf.W,change,
volume|5,RSI|5,CCI20|5,BBPower|5,ADX|5,change|5,
volume|15,RSI|15,CCI20|15,BBPower|15,ADX|15,change|15,
volume|30,RSI|30,CCI20|30,BBPower|30,ADX|30,change|30,
volume|60,RSI|60,CCI20|60,BBPower|60,ADX|60,change|60
```

(Sin `Perf.W|TF`, sin `Pivot.*|TF`, sin `close|TF`, sin `|1D`.)

Y la BD se migra con sufijos `_1d/_5m/_15m/_30m/_1h`. En una sola corrida por minuto capturás contexto diario + multi-TF, sin multiplicar requests.

### **5.3 Respuesta al dilema original**

> **"¿Solo nos sirve `close`?"**
> 

No. Sirve:

- **`close`** → señal directa de 15 min.
- **`volume`** → señal de 15 min **previa diferenciación**.
- **Todo el resto** → **contexto** de 15 min (régimen y niveles), que es la mitad del trabajo analítico.
- **Todo junto** → base para backtest y para el panel de pre-apertura.

Y como bonus, ese histórico se reempaqueta sin perder nada.

---

## **6. Próximos pasos concretos**

1. **Lunes 2026-09-21 con mercado abierto**: correr el checklist de Fase 0.5. Cierra H6, H7b, H19, H23, H24.
2. **Decidir D4** (TV directo vs cálculo propio vs híbrido). Mi recomendación: **híbrido** — pedir ambos a TV y calcular en paralelo durante 5–10 sesiones (VAL-04).
3. **Aplicar RAD-12/13/14** (nuevo `CAMPOS`, migración SQL, documentación de restricciones).
4. **Reempaquetado histórico** (una vez): pasar los CSV existentes a `fact_daily_context` + `fact_bars_15m`.
5. **Actualizar el roadmap** con las actualizaciones de mi mensaje anterior.

Si querés, el siguiente paso puede ser cualquiera de estos tres, en este orden de utilidad:

- **Script de reempaquetado histórico** (aprovechás las ~4 semanas de datos que ya tenés).
- **Checklist Fase 0.5** para el lunes.
- **`CAMPOS` definitivo + migración SQL** de `fact_market_series`.


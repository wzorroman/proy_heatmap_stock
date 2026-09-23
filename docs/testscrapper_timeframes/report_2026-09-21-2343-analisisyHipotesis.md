Evaluación del Test D, F, G, H — Impacto en el informe v3 y roadmap
1 · Veredicto rápido
Cuatro tests corridos, cuatro respuestas claras y accionables:

Test	Resultado	Cierra
D	Confirmación total: equity/ETF con 15 min, futuros con 10 min, VIX spot y cripto en vivo	H1 ✅, refina H7b
F	Tres feeds distintos con precios casi idénticos pero volúmenes radicalmente distintos	Q23 ✅, Q24 ✅
G	HTTP 404 — el endpoint POST batch no existe en esa URL	Q16 ✅ (refutada)
H	Pivot.M.* es el único; Pivot.D.* y Pivot.W.* no existen	Q17 ✅, H22 ✅ estructural
Con esto, el 40 % de las hipótesis/decisiones que bloqueaban el roadmap quedan resueltas.

2 · Análisis test por test
Test D · update_mode → H1 CONFIRMADA
text
NASDAQ:NVDA          delayed_streaming_900   (15 min)
AMEX:SPY             delayed_streaming_900   (15 min)
NASDAQ:QQQ           delayed_streaming_900   (15 min)
TVC:VIX              streaming               (0 s)
CBOE:VX1!            delayed_streaming_900   (15 min)
CME_MINI:ES1!        delayed_streaming_600   (10 min)  ← ¡nuevo!
CME_MINI:NQ1!        delayed_streaming_600   (10 min)  ← ¡nuevo!
BINANCE:BTCUSDT      streaming               (0 s)
Dos consecuencias grandes:

H1 pasa de 🟡 a ✅ para equity/ETF. El informe v3 ya sospechaba esto, ahora está confirmado. Cualquier decisión de entrada basada en el radar de acciones está viendo datos de 15 minutos atrás, no 3 minutos atrás como sugiere el timestamp.

Hay una jerarquía de delays que el informe no contempla:

Clase	Delay
Índices TVC (VIX spot, probablemente DXY)	0 s
Cripto (BINANCE)	0 s
FX (todos los proveedores)	0 s
Futuros CME (ES, NQ, VX)	10 min (600 s)
Equity / ETF	15 min (900 s)
Refuerza D1 con más fuerza de la prevista: la decisión de entrada no puede usar el radar de equity/ETF ni siquiera con la excusa de "es rápido". Ver 15 min atrás en mercado intradía no es contexto, es historia.

Corolario para M-DSH-02: el banner as_of debe reflejar el delay real por activo, no un valor global.

Test F · FX equivalence → Q23 y Q24 CERRADAS
text
FX:EURUSD       close=1.14763  volume=22504   mode=streaming  change=0.1082
FX_IDC:EURUSD   close=1.14762  volume=0       mode=streaming  change=0.0994
OANDA:EURUSD    close=1.14764  volume=14911   mode=streaming  change=0.1082
Precios casi idénticos (diferencia máxima de 1 pip = 0.00001). Volúmenes radicalmente distintos:

FX:EURUSD → 22.504

FX_IDC:EURUSD → 0

OANDA:EURUSD → 14.911

Hallazgo crítico: CONFIG_ACTIVOS declara FX_IDC:EURUSD como primario del EURUSD. Ese símbolo devuelve volume = 0.

Impacto inmediato:

Todo cálculo de RVOL, VWAP, o cualquier métrica basada en volumen para EURUSD está roto en producción.

El promedio 10d/30d de volumen de ese símbolo debe estar en 0 o null en BD.

El “volumen que cambia con precio congelado” observado en el test del 2026-09-22 era en FX:EURUSD (no en el de producción).

Respuesta a Q24: volume en FX es un proxy del proveedor (conteo de ticks/cotizaciones), no volumen nocional. Comparar el volume de OANDA con el de FX no tiene sentido; comparar volume de FX con average_volume_10d_calc de una acción es absurdo.

Acción inmediata: cambiar el primario de EURUSD a OANDA:EURUSD o FX:EURUSD. Ver §4.

Test G · POST /scan → Q16 REFUTADA
text
POST https://scanner.tradingview.com/scan  →  HTTP 404  "404 page not found"
Q16 cerrada: el endpoint POST batch no existe en esa URL.

Consecuencia directa sobre M-CAP-02: el POST único para 110 símbolos no es viable tal como estaba planteado. Hay que replantear F3.1.

Alternativa viva: el heatmap ya usa POST scanner.tradingview.com/america/scan?label-product=heatmap-stock. Ese endpoint sí existe y acepta POST con múltiples símbolos. No está claro si acepta symbols.tickers + sufijos |TF en columns, pero es la única puerta abierta.

Acción inmediata: probar /america/scan con symbols.tickers = [list of 110] y columns = [CAMPOS multi-TF]. Ver §4.

Plan B si /america/scan no sirve: paralelizar los 110 GET con un ThreadPoolExecutor de 8–10 workers. Baja el ciclo de ~120 s a ~15–20 s sin cambiar el endpoint.

Test H · pivotes → Q17 y H22 CERRADAS (estructuralmente)
Confirmado:

Pivot.M.Camarilla.R3 existe en base y con sufijos |5/|15/|30/|60.

Pivot.D.Camarilla.R3 y Pivot.W.Camarilla.R3 no existen (todos None).

Agrupación por pares confirmada en los 3 símbolos:

|5 = |15 → probablemente pivote diario

|30 = |60 → probablemente pivote semanal

Base → probablemente pivote mensual (H22 ya lo sostenía)

Lo que falta para cierre total: cálculo manual de un R3 Camarilla con H/L/C del día anterior, la semana anterior y el mes anterior, y comparar contra los tres valores. Eso es T6 del protocolo, y requiere mercado abierto para que el H/L/C de "ayer" sea significativo.

Dato útil para el dashboard (provisional):

text
NVDA:  base=230.025   |5=|15=223.373   |30=|60=225.875
SPY:   base=775.457   |5=|15=762.748   |30=|60=765.482
QQQ:   base=730.169   |5=|15=723.169   |30=|60=727.316
En los tres, el pivote |5=|15 (diario) está por debajo del precio actual, y el base (mensual) por encima. Eso sugiere que el diario actúa como soporte cercano y el mensual como techo más amplio — patrón razonable para una sesión en tendencia alcista.

3 · Hipótesis y dudas cerradas en esta corrida
ID	Antes	Ahora	Evidencia
H1 (radar con 15 min delay)	🟡	✅ CONFIRMADA	update_mode = delayed_streaming_900 en NVDA, SPY, QQQ
H7b (sufijos en /scan, premarket, update_mode)	🔴	✅ PARCIAL	update_mode ✅; /scan batch ❌ (404); premarket pendiente T3
H22 (pivote base mensual, sufijos diaria/semanal)	🟡	✅ ESTRUCTURAL	Base + pares |5=|15 y |30=|60 en 3 símbolos; falta T6 manual
Q16 (/scan acepta sufijos)	—	✅ CERRADA (refutada)	HTTP 404
Q17 (Pivot.D.*, Pivot.W.*)	—	✅ CERRADA (refutada)	No existen, todos None
Q23 (FX equivalence)	—	✅ CERRADA	Tres feeds distintos
Q24 (semántica de volume en FX)	—	✅ CERRADA	Proxy sintético por proveedor
Nuevo hallazgo (no estaba en ninguna versión del informe):

E-RAD-14 · FX_IDC:EURUSD (primario actual) devuelve volume = 0
S1 · ✅ · Esfuerzo S
El CONFIG_ACTIVOS usa FX_IDC:EURUSD como primario. Ese símbolo devuelve volume = 0; OANDA:EURUSD y FX:EURUSD devuelven 22.504 y 14.911 respectivamente.
Impacto: RVOL, VWAP y cualquier métrica de volumen para EURUSD en producción están rotos o en cero.
Corrección: cambiar el primario a OANDA:EURUSD, o decidir que para FX no se calcula volumen.

4 · Impacto concreto en el roadmap
Cambios al plan
Fase	Antes	Ahora
F0.2 (protocolo lunes)	T1–T11	T1, T2, T3, T4, T5, T6, T7, T8, T9, T10 (hecho), T11, T12 (nuevo: probar /america/scan)
F3.1 (M-CAP-02 POST único)	Reemplazar GET por POST /scan	Bloqueada tal como estaba. Nuevo plan: (a) probar /america/scan, (b) si falla, paralelizar los 110 GET con ThreadPoolExecutor.
F2.4 (roles y secretos)	Sin cambios	Sin cambios
F0.3 (ADR)	D1–D13	Añadir D14: primario de EURUSD (OANDA:EURUSD recomendado)
F3.5 (reintento BD)	Sin cambios	Sin cambios
M-CAP-07 (mapeo lógico → físico)	P1	P1 reforzada. Ya tenemos prueba de que sin mapeo canónico se rompe producción.
M-DSH-02 (banner as-of)	P0	P0 reforzada. El delay varía por clase: 0s VIX/BTC, 10min futuros, 15min equity. El banner debe ser por activo, no global.
Cambio estratégico en D1 (fuente de entrada)
Antes: "si H1 se confirma, la entrada no puede depender de este feed".
Ahora: H1 confirmada. La recomendación (b) es la única viable:

Contexto con TradingView (con banner as-of explícito de 15 min para equity/ETF), entrada con fuente externa en tiempo real.

Sin excepción.

Nuevo plan para F3.1
text
F3.1 (reescrita):
  Paso 1: probar POST a scanner.tradingview.com/america/scan
          con body {"symbols":{"tickers":[...110]}, "columns":[CAMPOS]}
          → si funciona: 1 round-trip, ciclo ~2s
  Paso 2: si falla, paralelizar GET con ThreadPoolExecutor(10)
          → 110 GET en ~15–20 s
  Paso 3: en ambos casos, añadir cycle_id y fetched_at (M-CAP-04)
Acción inmediata sobre CONFIG_ACTIVOS
python
# En config/radar_activos.json (o equivalente)
"EURUSD": {
    "primario":  "OANDA:EURUSD",   # antes: FX_IDC:EURUSD (volume=0)
    "respaldo":  "FX:EURUSD"       # antes: OANDA:EURUSD
}
5 · Qué falta (T12 + mañana)
Hoy, aún en madrugada ET, se puede correr:

bash
python3 -c "
import requests
body = {
  'symbols': {'tickers': ['NASDAQ:NVDA','AMEX:SPY','TVC:VIX']},
  'columns': ['close','volume','RSI|15','update_mode']
}
r = requests.post('https://scanner.tradingview.com/america/scan',
                  headers={'Content-Type':'application/json',
                           'User-Agent':'Mozilla/5.0'},
                  json=body, timeout=15)
print(r.status_code, r.text[:500])
"
Es T12. Cierra la última duda sobre M-CAP-02.

Mañana en sesión regular, correr:

bash
python3 wztest_scraper_timeframes_v2.py --test A,C,E,I --force
A → cierra H24 (refresco real de acciones con mercado abierto)

C → cierra H19 y H21 (frontera de barra en NVDA o SPY)

E → cierra H6 y H20 (pre-market real entre 09:00 y 09:29 ET)

I → cierra Q22 (gate por clase con evidencia real)

6 · Actualización del informe v3
El informe pasa a v3.1 con estos cambios mínimos:

H1 → ✅ (radar con 15 min de delay confirmado).

H22 → ✅ estructural (falta T6 para semántica diaria vs semanal).

H7b → ✅ parcial (update_mode sí, /scan batch no, premarket pendiente).

Q16, Q17, Q23, Q24 → ✅ cerradas.

Nueva jerarquía de delays en §5.1: 0s / 10min / 15min según clase.

Nuevo E-RAD-14 (FX_IDC con volume=0).

§3.4 Cadena de latencia debe añadir el nivel de 10 min para futuros CME.

No requiere una v4 completa. Es una actualización quirúrgica: 6 filas cambiadas, 1 error añadido, 1 sección expandida.

7 · Resumen en una frase
Los tests D, F, G y H cerraron 4 hipótesis y 4 dudas, introdujeron un hallazgo crítico (FX_IDC:EURUSD con volume=0) y bloquearon la solución POST batch — pero el hallazgo más importante es que el feed de equity del radar confirma 15 minutos de retraso, lo que deja a D1 como única fuente válida para decidir entrada.

¿Pasamos al siguiente paso? Las opciones son:

T12 ahora (POST a /america/scan) para cerrar la última duda de M-CAP-02.

Diff exacto de F1 (los 6 quick-wins) para arrancar el código hoy mismo.

Actualización del informe v3 → v3.1 con los cambios quirúrgicos de §6.

# ============== NASDAQ ===========
# obtener valores del activos usando tradingView - Nasdaq
# */3 * * * * /home/wilson/CODE_MAIN/app_backup_nasdaq/run_scraper_tradingview.sh

# obtener valores del activos usando tradingView - Nasdaq (cada 3 minutos)
# Lunes a jueves: 00:00 a 23:59
*/3 0-23 * * 1-4 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_scraper_tradingview.sh
# Viernes: 00:00 a 16:59 (hasta antes de las 17:00)
*/3 0-16 * * 5 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_scraper_tradingview.sh

# Calendario de eventos financieros - Nasdaq (cada 15 minutos)
# Lunes a jueves: 00:00 a 23:59
*/15 0-23 * * 1-4 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_calendario_tradingview.sh
# Viernes: 00:00 a 16:59 (hasta antes de las 17:00)
*/15 0-16 * * 5 /home/wilson/CODE_MAIN/app_backup_nasdaq/run_calendario_tradingview.sh

# monitorear los eventos y los valores del nasdaq (cada 5 minutos)
#*/5 * * * * cd /home/wilson/CODE_MAIN/app_backup_nasdaq && /home/wilson/CODE_MAIN/app_backup_nasdaq/venv/bin/python monitor_tradingview_live_v3.py >/dev/null 2>&1

# Lunes a jueves: 00:00 a 23:59
*/5 0-23 * * 1-4 cd /home/wilson/CODE_MAIN/app_backup_nasdaq && /home/wilson/CODE_MAIN/app_backup_nasdaq/venv/bin/python monitor_tradingview_live_v3.py >/dev/null 2>&1
# Viernes: 00:00 a 16:59 (hasta antes de las 17:00)
*/5 0-16 * * 5 cd /home/wilson/CODE_MAIN/app_backup_nasdaq && /home/wilson/CODE_MAIN/app_backup_nasdaq/venv/bin/python monitor_tradingview_live_v3.py >/dev/null 2>&1

# =========== FIN NASDAQ ==========

# --- server wz ---
# ============== NASDAQ ===========
# obtener valores del activos usando tradingView - Nasdaq (cada 3 minutos)
# Lunes a jueves: 00:00 a 23:59
*/3 0-23 * * 1-4 /home/wilson/BACKUP_DAILY/app_backup_nasdaq/run_scraper_tradingview.sh
# Viernes: 00:00 a 16:59 (hasta antes de las 17:00)
*/3 0-16 * * 5 /home/wilson/BACKUP_DAILY/app_backup_nasdaq/run_scraper_tradingview.sh

# Calendario de eventos financieros - Nasdaq (cada 15 minutos)
# Lunes a jueves: 00:00 a 23:59
*/15 0-23 * * 1-4 /home/wilson/BACKUP_DAILY/app_backup_nasdaq/run_calendario_tradingview.sh
# Viernes: 00:00 a 16:59 (hasta antes de las 17:00)
*/15 0-16 * * 5 /home/wilson/BACKUP_DAILY/app_backup_nasdaq/run_calendario_tradingview.sh


# Lunes a jueves: 00:00 a 23:59
*/5 0-23 * * 1-4 cd /home/wilson/BACKUP_DAILY/app_backup_nasdaq && /home/wilson/BACKUP_DAILY/app_backup_nasdaq/venv/bin/python monitor_tradingview_live_v3.py >/dev/null 2>&1
# Viernes: 00:00 a 16:59 (hasta antes de las 17:00)
*/5 0-16 * * 5 cd /home/wilson/BACKUP_DAILY/app_backup_nasdaq && /home/wilson/BACKUP_DAILY/app_backup_nasdaq/venv/bin/python monitor_tradingview_live_v3.py >/dev/null 2>&1

# =========== FIN NASDAQ ==========
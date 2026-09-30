## 1. Error: Permission denied: '/tmp/scraper_live_tradingview_v5.lock
    ```txt
    Traceback (most recent call last):
    File "/opt/proy_heatmap_stock/proy_scrapping_detail/scraper_live_tradingview_v5.py", line 629, in <module>
        main()
        ~~~~^^
    File "/opt/proy_heatmap_stock/proy_scrapping_detail/scraper_live_tradingview_v5.py", line 485, in main
        lock_fh = open(lock_path, "w")
    PermissionError: [Errno 13] Permission denied: '/tmp/scraper_live_tradingview_v5.lock'
    [2026-09-29 19:40:02]    Fin: 19:40:02 - Código: 1
    ```
   ### Solucion:
     $ sudo rm -R /tmp/scraper_live_tradingview_v5.lock

## 2. Error:
    # sudo chown -R appuser:appuser "/opt/DATOS_LIVE"
    # sudo chown -R appuser:appuser "/opt/DATOS_LIVE_CALENDAR"

# 🚀 Próximos pasos sugeridos
1. Probar el modo API cuando abra el mercado
En tu .env:

env
HEATMAP_USE_FALLBACK_ONLY=false
Ejecuta el scraper y verifica que:

El log diga 🌐 Consultando API de TradingView...

Se obtengan 502 símbolos reales (el d[] completo)

Si la API falla, caiga al fallback automáticamente

2. Configurar el cronjob
bash
# Editar crontab
crontab -e

# Ejecutar cada 15 minutos en horario de mercado (14:30 - 21:00 UTC, L-V)
*/15 14-21 * * 1-5 cd /home/wilson/CODE_MAIN/OPENCODE_WZ/proy_heatmap_stock/proy_heatmap && \
    ./venv/bin/python scrapper_heatmap.py >> /var/log/scrapper_heatmap.log 2>&1

# Crear particiones futuras el primer día de cada mes
5 0 1 * * cd /home/wilson/CODE_MAIN/OPENCODE_WZ/proy_heatmap_stock/proy_heatmap && \
    ./venv/bin/python create_partitions.py --all --months 3 >> /var/log/create_partitions.log 2>&1

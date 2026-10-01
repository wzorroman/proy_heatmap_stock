# -- Crear entorno virtual
 $ python3.13 -m venv venv

# -- Clear cache python
 $ find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

# -- Clear python - Uvicorn port 8006
 $ kill $(ps aux | grep 'uvicorn.*8006' | grep -v grep | awk '{print $2}') 2>/dev/null; echo "Cleaned up port 8006"
 
#!/bin/bash
set -e

echo "=================================================="
echo "🚀 INICIANDO STAGE 8: API SERVING (WAF) EN PRODUCCIÓN"
echo "=================================================="

# 1. Matar cualquier instancia previa
lsof -ti:5083 | xargs kill -9 2>/dev/null || true
docker rm -f nginx_waf 2>/dev/null || true

# 2. Levantar la FastAPI apuntando a Producción (Puerto 5083)
echo "[1/3] Levantando modelo de Producción (Alias: production)..."
export MLFLOW_MODEL_ALIAS=production
export UVICORN_PORT=5083
uvicorn src.mlsec.api.model_serving:app --host 0.0.0.0 --port 5083 &
API_PID=$!

# Esperar a que levante
sleep 5

# 3. Levantar NGINX en Docker apuntando al config y al dummy site
echo "[2/3] Levantando NGINX (Reverse Proxy + AI WAF)..."
# Get absolute path for mounts
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker run -d --name nginx_waf \
    -p 8080:8080 \
    -v "$DIR/nginx_waf/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
    -v "$DIR/nginx_waf/dummy_site:/usr/share/nginx/html:ro" \
    nginx:alpine

echo "[3/3] ¡Todo listo! 🛡️"
echo ""
echo "=================================================="
echo "🎯 CÓMO DEMOSTRAR EL FUNCIONAMIENTO"
echo "=================================================="
echo ""
echo "1. Prueba tráfico normal (Debería dar HTTP 200 OK):"
echo "   curl -i http://localhost:8080/"
echo "   curl -i http://localhost:8080/assets/css/style.css"
echo ""
echo "2. Prueba tráfico malicioso (Debería dar HTTP 403 BLOCKED):"
echo "   curl -i http://localhost:8080/login?username=admin%27+OR+1%3D1"
echo "   curl -i http://localhost:8080/execute.sh"
echo ""
echo "Para apagar el entorno, corre: docker rm -f nginx_waf && kill -9 $API_PID"
echo "=================================================="

# Mantener el script corriendo para no perder los logs de Uvicorn
wait $API_PID

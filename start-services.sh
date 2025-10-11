#!/bin/bash

echo "🐍 Configurando servicios Python con venv..."
echo ""

SERVICES=("gateway" "citizen" "ingestion" "transfer" "mintic_client")
BASE_PORT=8000

for i in "${!SERVICES[@]}"; do
    SERVICE="${SERVICES[$i]}"
    PORT=$((BASE_PORT + i))
    
    echo "📦 Configurando $SERVICE (puerto $PORT)..."
    
    cd services/$SERVICE
    
    # Crear venv si no existe
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    # Activar venv e instalar
    source venv/bin/activate
    pip install --quiet poetry
    poetry install --no-root --quiet
    
    # Iniciar servicio en background
    echo "🚀 Iniciando $SERVICE en puerto $PORT..."
    PORT=$PORT venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT > /tmp/$SERVICE.log 2>&1 &
    echo $! > /tmp/$SERVICE.pid
    
    deactivate
    cd ../..
    
    echo "✅ $SERVICE iniciado (PID: $(cat /tmp/$SERVICE.pid))"
    echo ""
done

echo "════════════════════════════════════════════════════════════════"
echo "✅ Todos los servicios iniciados!"
echo ""
echo "Servicios corriendo:"
echo "  Frontend:    http://localhost:3000"
echo "  Gateway:     http://localhost:8000"
echo "  Citizen:     http://localhost:8001"
echo "  Ingestion:   http://localhost:8002"
echo "  Transfer:    http://localhost:8003"
echo "  MinTIC:      http://localhost:8004"
echo ""
echo "Infraestructura:"
echo "  PostgreSQL:  localhost:5432"
echo "  OpenSearch:  http://localhost:9200"
echo "  Redis:       localhost:6379"
echo "  LocalStack:  http://localhost:4566"
echo "  Jaeger:      http://localhost:16686"
echo ""
echo "Logs en: /tmp/{service}.log"
echo "PIDs en: /tmp/{service}.pid"
echo ""
echo "🛑 Para detener todo:"
echo "  ./stop-services.sh"
echo "════════════════════════════════════════════════════════════════"

#!/bin/bash

echo "🚀 Iniciando Carpeta Ciudadana - Stack Completo"
echo ""

# 1. Iniciar frontend (Next.js)
echo "📦 Configurando Frontend (Next.js)..."
cd apps/frontend

# Cargar nvm y usar Node.js v22
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use v22

if [ ! -d "node_modules" ]; then
    echo "  → Instalando dependencias de Node.js..."
    npm install
fi

echo "🚀 Iniciando Frontend en puerto 3000..."
npm run dev > /tmp/frontend.log 2>&1 &
echo $! > /tmp/frontend.pid
echo "✅ Frontend iniciado (PID: $(cat /tmp/frontend.pid))"
echo ""

cd ../..

# 2. Iniciar servicios Python
echo "🐍 Configurando servicios Python con venv..."
echo ""

SERVICES=("gateway" "citizen" "ingestion" "metadata" "transfer" "mintic_client")
BASE_PORT=8000

for i in "${!SERVICES[@]}"; do
    SERVICE="${SERVICES[$i]}"
    PORT=$((BASE_PORT + i))
    
    echo "📦 Configurando $SERVICE (puerto $PORT)..."
    
    cd services/$SERVICE
    
    # Crear y configurar venv si no existe
    if [ ! -d "venv" ]; then
        echo "  → Creando venv..."
        python3 -m venv venv
        source venv/bin/activate
        pip install --quiet --upgrade pip
        pip install --quiet poetry
        echo "  → Instalando dependencias..."
        poetry install --no-root --quiet
        deactivate
    fi
    
    # Activar venv (ya configurado)
    source venv/bin/activate
    
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
echo "  Metadata:    http://localhost:8003"
echo "  Transfer:    http://localhost:8004"
echo "  MinTIC:      http://localhost:8005"
echo ""
echo "Infraestructura (Docker):"
echo "  PostgreSQL:  localhost:5432"
echo "  OpenSearch:  http://localhost:9200"
echo "  Redis:       localhost:6379"
echo "  Jaeger:      http://localhost:16686"
echo ""
echo "Azure (real):"
echo "  Blob Storage, Service Bus, PostgreSQL Flexible"
echo ""
echo "Logs en: /tmp/{service}.log"
echo "PIDs en: /tmp/{service}.pid"
echo ""
echo "🛑 Para detener todo:"
echo "  ./stop-services.sh"
echo "════════════════════════════════════════════════════════════════"

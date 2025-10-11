#!/bin/bash

echo "🛑 Deteniendo Carpeta Ciudadana - Stack Completo"
echo ""

# Detener servicios por PID
SERVICES=("frontend" "gateway" "citizen" "ingestion" "metadata" "transfer" "mintic_client")

for SERVICE in "${SERVICES[@]}"; do
    PID_FILE="/tmp/$SERVICE.pid"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "🛑 Deteniendo $SERVICE (PID: $PID)..."
            kill "$PID" 2>/dev/null
            rm "$PID_FILE"
        else
            echo "⚠️  $SERVICE no estaba corriendo (PID file: $PID)"
            rm "$PID_FILE"
        fi
    else
        echo "ℹ️  $SERVICE: no se encontró PID file"
    fi
done

# Detener procesos por nombre (fallback)
echo ""
echo "🧹 Limpiando procesos residuales..."
pkill -f "next dev" 2>/dev/null && echo "  ✅ Next.js detenido" || echo "  ℹ️  Next.js no estaba corriendo"
pkill -f "uvicorn" 2>/dev/null && echo "  ✅ Uvicorn detenido" || echo "  ℹ️  Uvicorn no estaba corriendo"

# Limpiar logs opcionales (comentado por defecto)
# echo ""
# echo "🧹 ¿Limpiar logs? (y/N)"
# read -r CLEAN_LOGS
# if [ "$CLEAN_LOGS" = "y" ] || [ "$CLEAN_LOGS" = "Y" ]; then
#     rm /tmp/*.log 2>/dev/null
#     echo "  ✅ Logs limpiados"
# fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Todos los servicios detenidos!"
echo ""
echo "Logs conservados en: /tmp/*.log"
echo ""
echo "Para reiniciar:"
echo "  ./start-services.sh"
echo "════════════════════════════════════════════════════════════════"


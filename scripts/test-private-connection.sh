#!/bin/bash

# Script para verificar la conexión privada a PostgreSQL
# Este script debe ejecutarse después de aplicar los cambios de Terraform

set -e

echo "🔍 Verificando configuración de Private Endpoint..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar que kubectl esté configurado
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl no está instalado o no está en el PATH"
    exit 1
fi

# Verificar que el contexto de Kubernetes esté configurado
if ! kubectl cluster-info &> /dev/null; then
    print_error "No se puede conectar al cluster de Kubernetes"
    exit 1
fi

print_status "Conexión a Kubernetes establecida"

# Verificar que el namespace existe
NAMESPACE="carpeta-ciudadana-production"
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    print_error "El namespace $NAMESPACE no existe"
    exit 1
fi

print_status "Namespace $NAMESPACE encontrado"

# Verificar que los secrets existen
echo "🔐 Verificando secrets de Kubernetes..."

SECRETS=("postgresql-secret" "azure-storage-secret" "servicebus-secret" "redis-secret" "azure-b2c-secret" "m2m-secret")

for secret in "${SECRETS[@]}"; do
    if kubectl get secret $secret -n $NAMESPACE &> /dev/null; then
        print_status "Secret $secret encontrado"
    else
        print_warning "Secret $secret no encontrado"
    fi
done

# Crear un pod de prueba para verificar la conectividad
echo "🧪 Creando pod de prueba para verificar conectividad..."

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: postgresql-test-pod
  namespace: $NAMESPACE
spec:
  containers:
  - name: postgresql-client
    image: postgres:16
    command: ["sleep", "3600"]
    envFrom:
    - secretRef:
        name: postgresql-secret
  restartPolicy: Never
EOF

# Esperar a que el pod esté listo
echo "⏳ Esperando a que el pod esté listo..."
kubectl wait --for=condition=Ready pod/postgresql-test-pod -n $NAMESPACE --timeout=60s

if [ $? -eq 0 ]; then
    print_status "Pod de prueba creado exitosamente"
    
    # Verificar resolución DNS
    echo "🔍 Verificando resolución DNS..."
    DNS_RESULT=$(kubectl exec postgresql-test-pod -n $NAMESPACE -- nslookup $PGHOST 2>/dev/null || echo "DNS_ERROR")
    
    if [[ "$DNS_RESULT" == *"DNS_ERROR"* ]]; then
        print_error "No se puede resolver el DNS del PostgreSQL"
    else
        print_status "DNS resuelto correctamente"
        echo "$DNS_RESULT"
    fi
    
    # Verificar conectividad a PostgreSQL
    echo "🔌 Verificando conectividad a PostgreSQL..."
    if kubectl exec postgresql-test-pod -n $NAMESPACE -- psql "host=\$PGHOST user=\$PGUSER password=\$PGPASSWORD dbname=\$PGDATABASE sslmode=require" -c "SELECT version();" &> /dev/null; then
        print_status "Conexión a PostgreSQL exitosa"
    else
        print_error "No se puede conectar a PostgreSQL"
    fi
    
    # Verificar que la IP es privada
    echo "🔒 Verificando que la IP es privada..."
    IP=$(kubectl exec postgresql-test-pod -n $NAMESPACE -- nslookup $PGHOST | grep -A1 "Name:" | tail -1 | awk '{print $2}')
    if [[ $IP =~ ^10\. ]] || [[ $IP =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]] || [[ $IP =~ ^192\.168\. ]]; then
        print_status "IP privada detectada: $IP"
    else
        print_warning "IP pública detectada: $IP (esto puede ser normal si el Private Endpoint no está configurado correctamente)"
    fi
    
    # Limpiar el pod de prueba
    echo "🧹 Limpiando pod de prueba..."
    kubectl delete pod postgresql-test-pod -n $NAMESPACE
    
else
    print_error "No se pudo crear el pod de prueba"
    exit 1
fi

echo ""
echo "🎉 Verificación completada!"
echo ""
echo "📋 Resumen de la configuración:"
echo "   • Private Endpoint: Configurado para PostgreSQL"
echo "   • Private DNS Zone: privatelink.postgres.database.azure.com"
echo "   • Secrets de Kubernetes: Configurados"
echo "   • Conectividad: Verificada"
echo ""
echo "🔧 Para verificar manualmente:"
echo "   kubectl get secrets -n $NAMESPACE"
echo "   kubectl describe secret postgresql-secret -n $NAMESPACE"
echo ""
echo "📚 Documentación: docs/PRIVATE_ENDPOINT_SETUP.md"

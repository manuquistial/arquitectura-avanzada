#!/bin/bash

# =============================================================================
# Script para ACTIVAR servicios de Azure
# =============================================================================
# Este script reactiva los servicios de Azure que fueron detenidos
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLATFORM_DIR="$PROJECT_ROOT/infra/terraform/layers/platform"
BASE_DIR="$PROJECT_ROOT/infra/terraform/layers/base"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Activando Servicios de Azure${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verificar que Azure CLI está instalado
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI no está instalado${NC}"
    exit 1
fi

# Verificar que estamos logueados en Azure
if ! az account show &> /dev/null; then
    echo -e "${RED}❌ No estás logueado en Azure. Ejecuta: az login${NC}"
    exit 1
fi

# Obtener nombres de recursos desde Terraform outputs
echo -e "${CYAN}📋 Obteniendo nombres de recursos desde Terraform...${NC}"

if [ ! -f "$BASE_DIR/terraform.tfstate" ]; then
    echo -e "${RED}❌ No se encontró terraform.tfstate en $BASE_DIR${NC}"
    exit 1
fi

if [ ! -f "$PLATFORM_DIR/terraform.tfstate" ]; then
    echo -e "${RED}❌ No se encontró terraform.tfstate en $PLATFORM_DIR${NC}"
    exit 1
fi

# Obtener Resource Group
RESOURCE_GROUP=$(cd "$BASE_DIR" && terraform output -raw resource_group_name 2>/dev/null || echo "")
if [ -z "$RESOURCE_GROUP" ]; then
    echo -e "${RED}❌ No se pudo obtener el nombre del Resource Group${NC}"
    exit 1
fi

# Obtener AKS Cluster Name
AKS_CLUSTER=$(cd "$PLATFORM_DIR" && terraform output -raw aks_cluster_name 2>/dev/null || echo "")
if [ -z "$AKS_CLUSTER" ]; then
    echo -e "${YELLOW}⚠️  No se pudo obtener el nombre del cluster AKS${NC}"
fi

# Obtener PostgreSQL Server Name
PG_SERVER=$(cd "$PLATFORM_DIR" && terraform output -raw database_fqdn 2>/dev/null | cut -d'.' -f1 || echo "")
if [ -z "$PG_SERVER" ]; then
    echo -e "${YELLOW}⚠️  No se pudo obtener el nombre del servidor PostgreSQL${NC}"
fi

# Obtener Redis Cache Name
REDIS_NAME=$(cd "$PLATFORM_DIR" && terraform output -raw redis_hostname 2>/dev/null | cut -d'.' -f1 || echo "")
if [ -z "$REDIS_NAME" ]; then
    echo -e "${YELLOW}⚠️  Redis no está desplegado${NC}"
fi

# Obtener Service Bus Namespace
SERVICEBUS_NAMESPACE=$(cd "$PLATFORM_DIR" && terraform output -raw servicebus_namespace_name 2>/dev/null || echo "")
if [ -z "$SERVICEBUS_NAMESPACE" ]; then
    echo -e "${YELLOW}⚠️  Service Bus no está desplegado${NC}"
fi

echo -e "${GREEN}✅ Resource Group: ${RESOURCE_GROUP}${NC}"
[ -n "$AKS_CLUSTER" ] && echo -e "${GREEN}✅ AKS Cluster: ${AKS_CLUSTER}${NC}"
[ -n "$PG_SERVER" ] && echo -e "${GREEN}✅ PostgreSQL: ${PG_SERVER}${NC}"
[ -n "$REDIS_NAME" ] && echo -e "${GREEN}✅ Redis: ${REDIS_NAME}${NC}"
[ -n "$SERVICEBUS_NAMESPACE" ] && echo -e "${GREEN}✅ Service Bus: ${SERVICEBUS_NAMESPACE}${NC}"
echo ""

# Función para escalar AKS node pools de vuelta
start_aks() {
    if [ -z "$AKS_CLUSTER" ]; then
        echo -e "${YELLOW}⏭️  Saltando AKS (no disponible)${NC}"
        return 0
    fi

    echo -e "${CYAN}☸️  Escalando AKS node pools de vuelta...${NC}"
    
    # Obtener lista de node pools y sus configuraciones originales
    NODE_POOLS_JSON=$(az aks nodepool list \
        --resource-group "$RESOURCE_GROUP" \
        --cluster-name "$AKS_CLUSTER" \
        --query "[].{name:name, min:minCount, max:maxCount}" -o json 2>/dev/null || echo "[]")
    
    if [ "$NODE_POOLS_JSON" = "[]" ] || [ -z "$NODE_POOLS_JSON" ]; then
        echo -e "${YELLOW}⚠️  No se pudieron obtener los node pools de AKS${NC}"
        echo -e "${YELLOW}   Escalando a valores por defecto...${NC}"
        
        # Escalar a valores por defecto
        for POOL in system user; do
            echo -e "  ${YELLOW}→ Escalando node pool '${POOL}' a 1...${NC}"
            if az aks nodepool scale \
                --resource-group "$RESOURCE_GROUP" \
                --cluster-name "$AKS_CLUSTER" \
                --name "$POOL" \
                --node-count 1 \
                --no-wait 2>/dev/null; then
                echo -e "  ${GREEN}✓ Node pool '${POOL}' escalado a 1${NC}"
            else
                echo -e "  ${YELLOW}⚠️  Node pool '${POOL}' no existe o ya está escalado${NC}"
            fi
        done
    else
        # Usar valores mínimos de cada node pool
        # Si jq está disponible, usarlo; si no, usar valores por defecto
        if command -v jq &> /dev/null; then
            echo "$NODE_POOLS_JSON" | jq -r '.[] | "\(.name)|\(.min)"' | while IFS='|' read -r POOL MIN_COUNT; do
                if [ -z "$MIN_COUNT" ] || [ "$MIN_COUNT" = "null" ] || [ "$MIN_COUNT" = "0" ]; then
                    MIN_COUNT=1
                fi
                echo -e "  ${YELLOW}→ Escalando node pool '${POOL}' a ${MIN_COUNT}...${NC}"
                if az aks nodepool scale \
                    --resource-group "$RESOURCE_GROUP" \
                    --cluster-name "$AKS_CLUSTER" \
                    --name "$POOL" \
                    --node-count "$MIN_COUNT" \
                    --no-wait 2>/dev/null; then
                    echo -e "  ${GREEN}✓ Node pool '${POOL}' escalado a ${MIN_COUNT}${NC}"
                else
                    echo -e "  ${YELLOW}⚠️  Error escalando node pool '${POOL}'${NC}"
                fi
            done
        else
            # Sin jq, usar valores por defecto
            echo -e "${YELLOW}⚠️  jq no está instalado, usando valores por defecto${NC}"
            for POOL in system user; do
                echo -e "  ${YELLOW}→ Escalando node pool '${POOL}' a 1...${NC}"
                if az aks nodepool scale \
                    --resource-group "$RESOURCE_GROUP" \
                    --cluster-name "$AKS_CLUSTER" \
                    --name "$POOL" \
                    --node-count 1 \
                    --no-wait 2>/dev/null; then
                    echo -e "  ${GREEN}✓ Node pool '${POOL}' escalado a 1${NC}"
                else
                    echo -e "  ${YELLOW}⚠️  Node pool '${POOL}' no existe o ya está escalado${NC}"
                fi
            done
        fi
    fi
}

# Función para iniciar PostgreSQL
start_postgresql() {
    if [ -z "$PG_SERVER" ]; then
        echo -e "${YELLOW}⏭️  Saltando PostgreSQL (no disponible)${NC}"
        return 0
    fi

    echo -e "${CYAN}📊 Iniciando PostgreSQL Flexible Server...${NC}"
    
    # Verificar estado actual
    STATUS=$(az postgres flexible-server show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$PG_SERVER" \
        --query "state" -o tsv 2>/dev/null || echo "Unknown")
    
    if [ "$STATUS" = "Unknown" ]; then
        echo -e "${YELLOW}⚠️  No se pudo obtener el estado de PostgreSQL${NC}"
        return 0
    fi
    
    if [ "$STATUS" = "Ready" ]; then
        echo -e "${GREEN}✓ PostgreSQL ya está activo${NC}"
        return 0
    fi
    
    if az postgres flexible-server start \
        --resource-group "$RESOURCE_GROUP" \
        --name "$PG_SERVER" \
        --no-wait 2>/dev/null; then
        echo -e "${GREEN}✓ PostgreSQL iniciando (puede tardar 2-3 minutos)${NC}"
        echo -e "${YELLOW}  ⏳ Esperando a que PostgreSQL esté listo...${NC}"
        
        # Esperar hasta que esté listo (máximo 5 minutos)
        TIMEOUT=300
        ELAPSED=0
        while [ $ELAPSED -lt $TIMEOUT ]; do
            STATUS=$(az postgres flexible-server show \
                --resource-group "$RESOURCE_GROUP" \
                --name "$PG_SERVER" \
                --query "state" -o tsv 2>/dev/null || echo "Unknown")
            
            if [ "$STATUS" = "Ready" ]; then
                echo -e "${GREEN}✓ PostgreSQL está listo${NC}"
                return 0
            fi
            
            sleep 10
            ELAPSED=$((ELAPSED + 10))
            echo -e "  ${YELLOW}... Esperando (${ELAPSED}s / ${TIMEOUT}s)${NC}"
        done
        
        echo -e "${YELLOW}⚠️  Timeout esperando PostgreSQL. Continúa iniciando en segundo plano.${NC}"
    else
        echo -e "${RED}✗ Error iniciando PostgreSQL${NC}"
    fi
}

# Función para escalar Redis de vuelta a Standard tier
start_redis() {
    if [ -z "$REDIS_NAME" ]; then
        echo -e "${YELLOW}⏭️  Saltando Redis (no disponible)${NC}"
        return 0
    fi

    echo -e "${CYAN}🔴 Escalando Redis de vuelta a Standard tier...${NC}"
    
    # Verificar SKU actual
    CURRENT_SKU=$(az redis show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$REDIS_NAME" \
        --query "sku.name" -o tsv 2>/dev/null || echo "")
    
    if [ "$CURRENT_SKU" = "Standard" ]; then
        echo -e "${GREEN}✓ Redis ya está en Standard tier${NC}"
    else
        if az redis update \
            --resource-group "$RESOURCE_GROUP" \
            --name "$REDIS_NAME" \
            --set sku.name=Standard sku.family=C sku.capacity=1 \
            --no-wait 2>/dev/null; then
            echo -e "${GREEN}✓ Redis escalado a Standard tier${NC}"
        else
            echo -e "${YELLOW}⚠️  No se pudo escalar Redis (puede requerir configuración manual)${NC}"
        fi
    fi
}

# Función para escalar Service Bus de vuelta a Standard tier
start_servicebus() {
    if [ -z "$SERVICEBUS_NAMESPACE" ]; then
        echo -e "${YELLOW}⏭️  Saltando Service Bus (no disponible)${NC}"
        return 0
    fi

    echo -e "${CYAN}📨 Escalando Service Bus a Standard tier...${NC}"
    
    # Verificar SKU actual
    CURRENT_SKU=$(az servicebus namespace show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$SERVICEBUS_NAMESPACE" \
        --query "sku.name" -o tsv 2>/dev/null || echo "")
    
    if [ "$CURRENT_SKU" = "Standard" ]; then
        echo -e "${GREEN}✓ Service Bus ya está en Standard tier${NC}"
    else
        if az servicebus namespace update \
            --resource-group "$RESOURCE_GROUP" \
            --name "$SERVICEBUS_NAMESPACE" \
            --sku Standard \
            2>/dev/null; then
            echo -e "${GREEN}✓ Service Bus escalado a Standard tier${NC}"
        else
            echo -e "${YELLOW}⚠️  No se pudo escalar Service Bus${NC}"
        fi
    fi
}

# Ejecutar activaciones
echo -e "${BLUE}🚀 Iniciando activación de servicios...${NC}"
echo ""

start_postgresql
echo ""

start_aks
echo ""

start_redis
echo ""

start_servicebus
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Servicios activados${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}📝 Notas:${NC}"
echo -e "  • PostgreSQL puede tardar 2-3 minutos en estar completamente listo"
echo -e "  • Los pods de AKS pueden tardar unos minutos en iniciar"
echo -e "  • Verifica el estado con: ${CYAN}kubectl get pods -n carpeta-ciudadana${NC}"
echo ""






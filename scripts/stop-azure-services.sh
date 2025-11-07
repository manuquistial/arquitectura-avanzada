#!/bin/bash

# =============================================================================
# Script para DETENER servicios de Azure sin hacer destroy
# =============================================================================
# Este script detiene los servicios costosos de Azure para ahorrar recursos
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
echo -e "${BLUE}  Deteniendo Servicios de Azure${NC}"
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
    echo -e "${YELLOW}   Asegúrate de haber desplegado la infraestructura primero${NC}"
    exit 1
fi

if [ ! -f "$PLATFORM_DIR/terraform.tfstate" ]; then
    echo -e "${RED}❌ No se encontró terraform.tfstate en $PLATFORM_DIR${NC}"
    echo -e "${YELLOW}   Asegúrate de haber desplegado la infraestructura primero${NC}"
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
    echo -e "${YELLOW}⚠️  No se pudo obtener el nombre del cluster AKS (puede que no esté desplegado)${NC}"
fi

# Obtener PostgreSQL Server Name (desde outputs del módulo)
PG_SERVER=$(cd "$PLATFORM_DIR" && terraform output -raw database_fqdn 2>/dev/null | cut -d'.' -f1 || echo "")
if [ -z "$PG_SERVER" ]; then
    echo -e "${YELLOW}⚠️  No se pudo obtener el nombre del servidor PostgreSQL${NC}"
fi

# Obtener Redis Cache Name
REDIS_NAME=$(cd "$PLATFORM_DIR" && terraform output -raw redis_hostname 2>/dev/null | cut -d'.' -f1 || echo "")
if [ -z "$REDIS_NAME" ]; then
    echo -e "${YELLOW}⚠️  Redis no está desplegado o no se pudo obtener su nombre${NC}"
fi

# Obtener Service Bus Namespace
SERVICEBUS_NAMESPACE=$(cd "$PLATFORM_DIR" && terraform output -raw servicebus_namespace_name 2>/dev/null || echo "")
if [ -z "$SERVICEBUS_NAMESPACE" ]; then
    echo -e "${YELLOW}⚠️  Service Bus no está desplegado o no se pudo obtener su nombre${NC}"
fi

echo -e "${GREEN}✅ Resource Group: ${RESOURCE_GROUP}${NC}"
[ -n "$AKS_CLUSTER" ] && echo -e "${GREEN}✅ AKS Cluster: ${AKS_CLUSTER}${NC}"
[ -n "$PG_SERVER" ] && echo -e "${GREEN}✅ PostgreSQL: ${PG_SERVER}${NC}"
[ -n "$REDIS_NAME" ] && echo -e "${GREEN}✅ Redis: ${REDIS_NAME}${NC}"
[ -n "$SERVICEBUS_NAMESPACE" ] && echo -e "${GREEN}✅ Service Bus: ${SERVICEBUS_NAMESPACE}${NC}"
echo ""

# Función para escalar AKS node pools a 0
stop_aks() {
    if [ -z "$AKS_CLUSTER" ]; then
        echo -e "${YELLOW}⏭️  Saltando AKS (no disponible)${NC}"
        return 0
    fi

    echo -e "${CYAN}☸️  Escalando AKS node pools a 0...${NC}"
    
    # Obtener lista de node pools
    NODE_POOLS=$(az aks nodepool list \
        --resource-group "$RESOURCE_GROUP" \
        --cluster-name "$AKS_CLUSTER" \
        --query "[].name" -o tsv 2>/dev/null || echo "")
    
    if [ -z "$NODE_POOLS" ]; then
        echo -e "${YELLOW}⚠️  No se pudieron obtener los node pools de AKS${NC}"
        return 0
    fi
    
    for POOL in $NODE_POOLS; do
        echo -e "  ${YELLOW}→ Escalando node pool '${POOL}' a 0...${NC}"
        if az aks nodepool scale \
            --resource-group "$RESOURCE_GROUP" \
            --cluster-name "$AKS_CLUSTER" \
            --name "$POOL" \
            --node-count 0 \
            --no-wait 2>/dev/null; then
            echo -e "  ${GREEN}✓ Node pool '${POOL}' escalado a 0${NC}"
        else
            echo -e "  ${RED}✗ Error escalando node pool '${POOL}'${NC}"
        fi
    done
}

# Función para detener PostgreSQL
stop_postgresql() {
    if [ -z "$PG_SERVER" ]; then
        echo -e "${YELLOW}⏭️  Saltando PostgreSQL (no disponible)${NC}"
        return 0
    fi

    echo -e "${CYAN}📊 Deteniendo PostgreSQL Flexible Server...${NC}"
    
    # Verificar estado actual
    STATUS=$(az postgres flexible-server show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$PG_SERVER" \
        --query "state" -o tsv 2>/dev/null || echo "Unknown")
    
    if [ "$STATUS" = "Unknown" ]; then
        echo -e "${YELLOW}⚠️  No se pudo obtener el estado de PostgreSQL${NC}"
        return 0
    fi
    
    if [ "$STATUS" = "Stopped" ]; then
        echo -e "${GREEN}✓ PostgreSQL ya está detenido${NC}"
        return 0
    fi
    
    if az postgres flexible-server stop \
        --resource-group "$RESOURCE_GROUP" \
        --name "$PG_SERVER" \
        --no-wait 2>/dev/null; then
        echo -e "${GREEN}✓ PostgreSQL detenido (puede tardar unos minutos)${NC}"
    else
        echo -e "${RED}✗ Error deteniendo PostgreSQL${NC}"
    fi
}

# Función para escalar Redis a Basic tier (más barato)
stop_redis() {
    if [ -z "$REDIS_NAME" ]; then
        echo -e "${YELLOW}⏭️  Saltando Redis (no disponible)${NC}"
        return 0
    fi

    echo -e "${CYAN}🔴 Escalando Redis a Basic tier (más económico)...${NC}"
    
    # Verificar si ya está en Basic tier
    CURRENT_SKU=$(az redis show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$REDIS_NAME" \
        --query "sku.name" -o tsv 2>/dev/null || echo "")
    
    if [ "$CURRENT_SKU" = "Basic" ]; then
        echo -e "${GREEN}✓ Redis ya está en Basic tier${NC}"
    else
        if az redis update \
            --resource-group "$RESOURCE_GROUP" \
            --name "$REDIS_NAME" \
            --set sku.name=Basic sku.family=C sku.capacity=0 \
            --no-wait 2>/dev/null; then
            echo -e "${GREEN}✓ Redis escalado a Basic tier${NC}"
        else
            echo -e "${YELLOW}⚠️  No se pudo escalar Redis (puede requerir eliminación manual)${NC}"
        fi
    fi
}

# Función para escalar Service Bus a Basic tier
stop_servicebus() {
    if [ -z "$SERVICEBUS_NAMESPACE" ]; then
        echo -e "${YELLOW}⏭️  Saltando Service Bus (no disponible)${NC}"
        return 0
    fi

    echo -e "${CYAN}📨 Escalando Service Bus a Basic tier...${NC}"
    
    # Verificar SKU actual
    CURRENT_SKU=$(az servicebus namespace show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$SERVICEBUS_NAMESPACE" \
        --query "sku.name" -o tsv 2>/dev/null || echo "")
    
    if [ "$CURRENT_SKU" = "Basic" ]; then
        echo -e "${GREEN}✓ Service Bus ya está en Basic tier${NC}"
    else
        if az servicebus namespace update \
            --resource-group "$RESOURCE_GROUP" \
            --name "$SERVICEBUS_NAMESPACE" \
            --sku Basic \
            2>/dev/null; then
            echo -e "${GREEN}✓ Service Bus escalado a Basic tier${NC}"
        else
            echo -e "${YELLOW}⚠️  No se pudo escalar Service Bus${NC}"
        fi
    fi
}

# Ejecutar detenciones
echo -e "${BLUE}🛑 Iniciando detención de servicios...${NC}"
echo ""

stop_postgresql
echo ""

stop_aks
echo ""

stop_redis
echo ""

stop_servicebus
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Servicios detenidos${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}📝 Notas:${NC}"
echo -e "  • Storage Account y Key Vault se mantienen activos (costo mínimo)"
echo -e "  • Para reactivar los servicios, ejecuta: ${CYAN}./scripts/start-azure-services.sh${NC}"
echo -e "  • PostgreSQL puede tardar 2-3 minutos en iniciar"
echo ""







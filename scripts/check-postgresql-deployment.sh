#!/bin/bash

# Script para verificar el estado del despliegue de PostgreSQL Flexible Server
# y solucionar problemas comunes

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar estado de Terraform
check_terraform_state() {
    log "Verificando estado de Terraform..."
    
    cd infra/terraform
    
    if [ ! -f "terraform.tfstate" ]; then
        error "No existe terraform.tfstate. Debes ejecutar 'terraform apply' primero."
        return 1
    fi
    
    # Verificar recursos desplegados
    log "Recursos desplegados:"
    terraform show -json | jq -r '.values.root_module.resources[]? | select(.type | contains("azurerm_postgresql_flexible_server")) | .values.name' 2>/dev/null || echo "No se encontraron servidores PostgreSQL"
    
    success "Estado de Terraform verificado"
}

# Verificar conectividad a PostgreSQL
check_postgresql_connectivity() {
    log "Verificando conectividad a PostgreSQL..."
    
    cd infra/terraform
    
    # Obtener información de conexión
    PG_HOST=$(terraform output -raw postgresql_fqdn 2>/dev/null || echo "")
    PG_USER=$(grep 'db_admin_username' terraform.tfvars | cut -d'"' -f2)
    
    if [ -z "$PG_HOST" ]; then
        error "No se pudo obtener el host de PostgreSQL desde Terraform outputs"
        return 1
    fi
    
    log "Intentando conectar a: $PG_HOST"
    
    # Verificar si psql está disponible
    if ! command -v psql &> /dev/null; then
        warning "psql no está instalado. Instalando postgresql-client..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y postgresql-client
        elif command -v brew &> /dev/null; then
            brew install postgresql
        else
            error "No se puede instalar psql automáticamente. Instálalo manualmente."
            return 1
        fi
    fi
    
    # Intentar conexión
    if timeout 10 psql -h "$PG_HOST" -U "$PG_USER" -d "carpeta_ciudadana" -c "SELECT version();" &>/dev/null; then
        success "Conexión a PostgreSQL exitosa"
        return 0
    else
        error "No se pudo conectar a PostgreSQL"
        log "Posibles causas:"
        echo "  1. El servidor aún se está inicializando (puede tomar 5-10 minutos)"
        echo "  2. Problemas de red/VNet"
        echo "  3. Credenciales incorrectas"
        echo "  4. Firewall bloqueando la conexión"
        return 1
    fi
}

# Verificar configuración de red
check_network_config() {
    log "Verificando configuración de red..."
    
    cd infra/terraform
    
    # Verificar VNet
    VNET_NAME=$(terraform output -raw vnet_name 2>/dev/null || echo "")
    if [ -n "$VNET_NAME" ]; then
        log "VNet encontrada: $VNET_NAME"
    else
        warning "No se encontró VNet en los outputs"
    fi
    
    # Verificar subnets
    log "Subnets configuradas:"
    az network vnet subnet list --resource-group "$(terraform output -raw resource_group_name)" --vnet-name "$VNET_NAME" --query "[].{Name:name,AddressPrefix:addressPrefix}" -o table 2>/dev/null || echo "No se pudieron obtener las subnets"
    
    success "Configuración de red verificada"
}

# Solucionar problemas comunes
troubleshoot_common_issues() {
    log "Verificando problemas comunes..."
    
    cd infra/terraform
    
    # Verificar si el servidor está en estado "Ready"
    PG_SERVER_NAME=$(terraform output -raw postgresql_server_name 2>/dev/null || echo "")
    if [ -n "$PG_SERVER_NAME" ]; then
        log "Verificando estado del servidor PostgreSQL: $PG_SERVER_NAME"
        SERVER_STATE=$(az postgres flexible-server show --name "$PG_SERVER_NAME" --resource-group "$(terraform output -raw resource_group_name)" --query "state" -o tsv 2>/dev/null || echo "Unknown")
        log "Estado del servidor: $SERVER_STATE"
        
        if [ "$SERVER_STATE" != "Ready" ]; then
            warning "El servidor no está en estado 'Ready'. Estado actual: $SERVER_STATE"
            echo "Esto es normal si acabas de crear el servidor. Espera 5-10 minutos."
        fi
    fi
    
    # Verificar logs de Terraform
    if [ -f "terraform.tfstate" ]; then
        log "Última modificación del estado: $(stat -c %y terraform.tfstate 2>/dev/null || stat -f %Sm terraform.tfstate)"
    fi
    
    success "Verificación de problemas completada"
}

# Mostrar información útil
show_connection_info() {
    log "Información de conexión:"
    
    cd infra/terraform
    
    echo ""
    success "=== INFORMACIÓN DE CONEXIÓN ==="
    echo ""
    
    # PostgreSQL connection info
    if terraform output postgresql_connection_string &>/dev/null; then
        echo "PostgreSQL Connection String:"
        terraform output -raw postgresql_connection_string
        echo ""
    fi
    
    if terraform output postgresql_fqdn &>/dev/null; then
        echo "PostgreSQL Host:"
        terraform output -raw postgresql_fqdn
        echo ""
    fi
    
    # AKS info
    if terraform output aks_cluster_name &>/dev/null; then
        echo "AKS Cluster:"
        terraform output -raw aks_cluster_name
        echo ""
        echo "Para conectar kubectl:"
        echo "az aks get-credentials --resource-group $(terraform output -raw resource_group_name) --name $(terraform output -raw aks_cluster_name)"
        echo ""
    fi
    
    success "Información mostrada"
}

# Función principal
main() {
    log "Verificando despliegue de PostgreSQL Flexible Server..."
    
    if ! check_terraform_state; then
        error "No se puede verificar el estado. Asegúrate de haber ejecutado 'terraform apply'."
        exit 1
    fi
    
    check_network_config
    troubleshoot_common_issues
    
    if check_postgresql_connectivity; then
        success "¡PostgreSQL está funcionando correctamente!"
    else
        warning "PostgreSQL no está respondiendo. Revisa los logs arriba."
    fi
    
    show_connection_info
    
    echo ""
    log "Comandos útiles:"
    echo "  - Ver estado: terraform show"
    echo "  - Ver outputs: terraform output"
    echo "  - Reconectar: terraform refresh"
    echo "  - Destruir: terraform destroy"
}

# Ejecutar función principal
main "$@"

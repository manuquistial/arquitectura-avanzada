#!/bin/bash

# Script para desplegar Azure PostgreSQL Flexible Server
# Este script maneja el despliegue paso a paso para evitar errores

set -e  # Exit on any error

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

# Verificar prerequisitos
check_prerequisites() {
    log "Verificando prerequisitos..."
    
    # Verificar Azure CLI
    if ! command -v az &> /dev/null; then
        error "Azure CLI no está instalado. Instálalo desde: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    
    # Verificar Terraform
    if ! command -v terraform &> /dev/null; then
        error "Terraform no está instalado. Instálalo desde: https://www.terraform.io/downloads.html"
        exit 1
    fi
    
    # Verificar autenticación de Azure
    if ! az account show &> /dev/null; then
        error "No estás autenticado en Azure CLI. Ejecuta: az login"
        exit 1
    fi
    
    success "Prerequisitos verificados correctamente"
}

# Verificar archivo de variables
check_tfvars() {
    log "Verificando archivo terraform.tfvars..."
    
    if [ ! -f "infra/terraform/terraform.tfvars" ]; then
        error "No existe terraform.tfvars. Debes crear este archivo con tu configuración."
        echo ""
        echo "Puedes usar como base:"
        echo "  cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars"
        echo ""
        echo "Luego edita las siguientes variables importantes:"
        echo "  1. db_admin_password - Usa una contraseña segura"
        echo "  2. opensearch_password - Usa una contraseña segura"
        echo "  3. letsencrypt_email - Tu email para certificados SSL"
        echo "  4. environment - Cambia de 'production' a 'dev' si es desarrollo"
        echo ""
        exit 1
    fi
    
    success "Archivo terraform.tfvars encontrado"
    
    # Mostrar configuración actual
    log "Configuración actual:"
    echo "  Environment: $(grep 'environment' infra/terraform/terraform.tfvars | head -1)"
    echo "  Azure Region: $(grep 'azure_region' infra/terraform/terraform.tfvars | head -1)"
    echo "  PostgreSQL SKU: $(grep 'db_sku_name' infra/terraform/terraform.tfvars | head -1)"
}

# Inicializar Terraform
init_terraform() {
    log "Inicializando Terraform..."
    
    cd infra/terraform
    terraform init
    success "Terraform inicializado correctamente"
}

# Validar configuración
validate_terraform() {
    log "Validando configuración de Terraform..."
    
    terraform validate
    success "Configuración válida"
}

# Plan de despliegue
plan_terraform() {
    log "Generando plan de despliegue..."
    
    terraform plan -out=tfplan
    success "Plan generado correctamente"
}

# Desplegar infraestructura
deploy_infrastructure() {
    log "Desplegando infraestructura..."
    
    echo ""
    warning "IMPORTANTE: Este despliegue puede tomar 10-15 minutos."
    warning "Costos estimados mensuales (basado en tu terraform.tfvars):"
    
    # Leer configuración del archivo tfvars
    PG_SKU=$(grep 'db_sku_name' infra/terraform/terraform.tfvars | cut -d'"' -f2)
    AKS_VM=$(grep 'aks_vm_size' infra/terraform/terraform.tfvars | cut -d'"' -f2)
    
    echo "  - PostgreSQL Flexible Server ($PG_SKU): ~$15-40/mes"
    echo "  - AKS ($AKS_VM): ~$3-15/mes"
    echo "  - Storage (32GB): ~$1-2/mes"
    echo "  - Service Bus: ~$0.05/mes"
    echo "  - OpenSearch: ~$0 (self-hosted en AKS)"
    echo ""
    
    read -p "¿Continuar con el despliegue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Despliegue cancelado por el usuario"
        exit 0
    fi
    
    terraform apply tfplan
    success "Infraestructura desplegada correctamente"
}

# Obtener información de conexión
get_connection_info() {
    log "Obteniendo información de conexión..."
    
    echo ""
    success "=== INFORMACIÓN DE CONEXIÓN ==="
    echo ""
    
    # PostgreSQL connection info
    echo "PostgreSQL Connection:"
    terraform output -raw postgresql_connection_string || echo "No disponible"
    echo ""
    
    # AKS connection info
    echo "AKS Cluster:"
    terraform output -raw aks_cluster_name || echo "No disponible"
    echo ""
    
    # Storage info
    echo "Storage Account:"
    terraform output -raw storage_account_name || echo "No disponible"
    echo ""
    
    success "Despliegue completado exitosamente!"
}

# Función principal
main() {
    log "Iniciando despliegue de Azure PostgreSQL Flexible Server..."
    
    check_prerequisites
    check_tfvars
    init_terraform
    validate_terraform
    plan_terraform
    deploy_infrastructure
    get_connection_info
    
    success "¡Despliegue completado exitosamente!"
    echo ""
    log "Próximos pasos:"
    echo "1. Configura kubectl: az aks get-credentials --resource-group <rg-name> --name <cluster-name>"
    echo "2. Despliega la aplicación: kubectl apply -f deploy/helm/carpeta-ciudadana/"
    echo "3. Verifica el estado: kubectl get pods -n carpeta-ciudadana-dev"
}

# Ejecutar función principal
main "$@"

#!/bin/bash

# =============================================================================
# SCRIPT DE VERIFICACIÓN PARA TERRAFORM - CARPETA CIUDADANA
# =============================================================================
# Este script verifica que todas las configuraciones estén correctas antes de
# ejecutar terraform apply
# Uso: ./scripts/verify-terraform-setup.sh

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Contadores
PASSED=0
FAILED=0
WARNINGS=0

# Función para imprimir mensajes con color
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✅ PASS]${NC} $1"
    ((PASSED++))
}

print_error() {
    echo -e "${RED}[❌ FAIL]${NC} $1"
    ((FAILED++))
}

print_warning() {
    echo -e "${YELLOW}[⚠️  WARN]${NC} $1"
    ((WARNINGS++))
}

print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}\n"
}

# Función para verificar comando
check_command() {
    local cmd=$1
    local name=$2
    
    if command -v $cmd &> /dev/null; then
        print_success "$name está instalado"
        return 0
    else
        print_error "$name NO está instalado"
        return 1
    fi
}

# Función para verificar variable de entorno
check_env_var() {
    local var=$1
    local name=$2
    
    if [ -n "${!var}" ]; then
        print_success "$name está configurado: ${!var}"
        return 0
    else
        print_error "$name NO está configurado"
        return 1
    fi
}

# Función para verificar comando de Azure
check_azure_command() {
    local cmd=$1
    local name=$2
    
    if $cmd &> /dev/null; then
        print_success "$name funciona correctamente"
        return 0
    else
        print_error "$name falló"
        return 1
    fi
}

echo -e "${BLUE}"
echo "🚀 VERIFICACIÓN DE CONFIGURACIÓN PARA TERRAFORM"
echo "📋 Carpeta Ciudadana - Configuración de Producción"
echo -e "${NC}"

# =============================================================================
# 1. VERIFICAR HERRAMIENTAS INSTALADAS
# =============================================================================
print_header "1. VERIFICANDO HERRAMIENTAS INSTALADAS"

check_command "az" "Azure CLI"
check_command "kubectl" "kubectl"
check_command "terraform" "Terraform"
check_command "helm" "Helm (opcional)"

# =============================================================================
# 2. VERIFICAR AUTENTICACIÓN DE AZURE
# =============================================================================
print_header "2. VERIFICANDO AUTENTICACIÓN DE AZURE"

if az account show &> /dev/null; then
    print_success "Azure CLI autenticado"
    
    # Verificar suscripción
    SUBSCRIPTION=$(az account show --query id -o tsv)
    if [ "$SUBSCRIPTION" = "635ab07e-b29c-417e-b2b2-008bc4fc57d6" ]; then
        print_success "Suscripción correcta: $SUBSCRIPTION"
    else
        print_warning "Suscripción actual: $SUBSCRIPTION (esperada: 635ab07e-b29c-417e-b2b2-008bc4fc57d6)"
    fi
    
    # Verificar tenant
    TENANT=$(az account show --query tenantId -o tsv)
    if [ "$TENANT" = "48d06645-ab3b-4ac4-b121-c63bb238ef6e" ]; then
        print_success "Tenant correcto: $TENANT"
    else
        print_warning "Tenant actual: $TENANT (esperado: 48d06645-ab3b-4ac4-b121-c63bb238ef6e)"
    fi
else
    print_error "Azure CLI NO está autenticado"
    echo "Ejecuta: az login"
fi

# =============================================================================
# 3. VERIFICAR VARIABLES DE ENTORNO
# =============================================================================
print_header "3. VERIFICANDO VARIABLES DE ENTORNO"

check_env_var "AZURE_SUBSCRIPTION_ID" "AZURE_SUBSCRIPTION_ID"
check_env_var "AZURE_TENANT_ID" "AZURE_TENANT_ID"
check_env_var "TF_VAR_environment" "TF_VAR_environment"
check_env_var "TF_VAR_azure_region" "TF_VAR_azure_region"
check_env_var "TF_VAR_project_name" "TF_VAR_project_name"

# Verificar variables críticas
if [ -n "$TF_VAR_db_admin_password" ]; then
    if [ "$TF_VAR_db_admin_password" = "CHANGE_ME_STRONG_PASSWORD_123!" ]; then
        print_warning "Contraseña de BD es la de ejemplo - cambiar en producción"
    else
        print_success "Contraseña de BD configurada"
    fi
else
    print_error "TF_VAR_db_admin_password NO está configurado"
fi

# =============================================================================
# 4. VERIFICAR ACCESO A KUBERNETES
# =============================================================================
print_header "4. VERIFICANDO ACCESO A KUBERNETES"

if kubectl get nodes &> /dev/null; then
    NODE_COUNT=$(kubectl get nodes --no-headers | wc -l)
    print_success "Acceso a Kubernetes funcionando ($NODE_COUNT nodos)"
    
    # Verificar que hay nodos
    if [ $NODE_COUNT -gt 0 ]; then
        print_success "Cluster AKS tiene nodos disponibles"
    else
        print_error "Cluster AKS no tiene nodos"
    fi
else
    print_error "NO se puede acceder a Kubernetes"
    echo "Ejecuta: az aks get-credentials --resource-group carpeta-ciudadana-production-rg --name carpeta-ciudadana-production --admin --overwrite-existing"
fi

# =============================================================================
# 5. VERIFICAR RECURSOS DE AZURE
# =============================================================================
print_header "5. VERIFICANDO RECURSOS DE AZURE"

# Verificar Resource Group
if az group show --name carpeta-ciudadana-production-rg &> /dev/null; then
    print_success "Resource Group existe: carpeta-ciudadana-production-rg"
else
    print_error "Resource Group NO existe: carpeta-ciudadana-production-rg"
fi

# Verificar cluster AKS
if az aks show --resource-group carpeta-ciudadana-production-rg --name carpeta-ciudadana-production &> /dev/null; then
    print_success "Cluster AKS existe: carpeta-ciudadana-production"
    
    # Verificar estado del cluster
    AKS_STATE=$(az aks show --resource-group carpeta-ciudadana-production-rg --name carpeta-ciudadana-production --query provisioningState -o tsv)
    if [ "$AKS_STATE" = "Succeeded" ]; then
        print_success "Cluster AKS está en estado: $AKS_STATE"
    else
        print_warning "Cluster AKS está en estado: $AKS_STATE"
    fi
else
    print_error "Cluster AKS NO existe: carpeta-ciudadana-production"
fi

# =============================================================================
# 6. VERIFICAR CONFIGURACIÓN DE TERRAFORM
# =============================================================================
print_header "6. VERIFICANDO CONFIGURACIÓN DE TERRAFORM"

# Verificar que estamos en el directorio correcto
if [ -f "main.tf" ] && [ -f "terraform.tfvars" ]; then
    print_success "Directorio de Terraform correcto"
else
    print_error "NO estás en el directorio correcto de Terraform"
    echo "Ejecuta: cd infra/terraform"
fi

# Verificar inicialización de Terraform
if [ -d ".terraform" ]; then
    print_success "Terraform inicializado"
else
    print_warning "Terraform NO está inicializado"
    echo "Ejecuta: terraform init"
fi

# Verificar configuración válida
if terraform validate &> /dev/null; then
    print_success "Configuración de Terraform válida"
else
    print_error "Configuración de Terraform NO es válida"
    echo "Ejecuta: terraform validate"
fi

# =============================================================================
# 7. VERIFICAR PERMISOS
# =============================================================================
print_header "7. VERIFICANDO PERMISOS"

# Verificar permisos de Azure
USER_ID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || echo "")
if [ -n "$USER_ID" ]; then
    print_success "Usuario autenticado: $USER_ID"
    
    # Verificar roles
    ROLES=$(az role assignment list --assignee $USER_ID --query "[].roleDefinitionName" -o tsv 2>/dev/null || echo "")
    if echo "$ROLES" | grep -q "Owner\|Contributor"; then
        print_success "Tienes permisos suficientes en Azure"
    else
        print_warning "Verificar permisos en Azure - se requiere Owner o Contributor"
    fi
else
    print_error "No se puede obtener información del usuario"
fi

# =============================================================================
# 8. RESUMEN FINAL
# =============================================================================
print_header "8. RESUMEN DE VERIFICACIÓN"

echo -e "${GREEN}✅ PASARON: $PASSED${NC}"
echo -e "${YELLOW}⚠️  ADVERTENCIAS: $WARNINGS${NC}"
echo -e "${RED}❌ FALLARON: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 ¡CONFIGURACIÓN COMPLETA!${NC}"
    echo -e "${GREEN}✅ Puedes ejecutar: terraform apply${NC}"
    
    if [ $WARNINGS -gt 0 ]; then
        echo -e "\n${YELLOW}⚠️  Revisa las advertencias antes de continuar${NC}"
    fi
else
    echo -e "\n${RED}❌ CONFIGURACIÓN INCOMPLETA${NC}"
    echo -e "${RED}🔧 Corrige los errores antes de ejecutar terraform apply${NC}"
    exit 1
fi

echo -e "\n${BLUE}📋 Próximos pasos:${NC}"
echo "1. cd infra/terraform"
echo "2. terraform plan"
echo "3. terraform apply"

echo -e "\n${BLUE}📚 Documentación:${NC}"
echo "- Ver TERRAFORM_SETUP.md para detalles completos"
echo "- Ver .envrc.example para configuración de variables"

echo -e "\n${BLUE}🆘 Si necesitas ayuda:${NC}"
echo "- Verificar logs: terraform plan -detailed-exitcode"
echo "- Verificar Azure: az activity log list --resource-group carpeta-ciudadana-production-rg"
echo "- Verificar Kubernetes: kubectl get events --all-namespaces"

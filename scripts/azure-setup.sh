#!/bin/bash

# Azure Setup Script
# Configura los permisos y autenticación de Azure para evitar problemas de login

set -e

echo "🚀 Configurando Azure CLI y permisos..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con color
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar si Azure CLI está instalado
if ! command -v az &> /dev/null; then
    print_error "Azure CLI no está instalado. Por favor instálalo primero:"
    echo "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

print_success "Azure CLI está instalado"

# Configurar variables de entorno
export AZURE_SUBSCRIPTION_ID="<SUBSCRIPTION_ID>"
export AZURE_TENANT_ID="<TENANT_ID>"

print_status "Variables de entorno configuradas:"
echo "  AZURE_SUBSCRIPTION_ID: $AZURE_SUBSCRIPTION_ID"
echo "  AZURE_TENANT_ID: $AZURE_TENANT_ID"

# Verificar si ya está autenticado
if az account show &> /dev/null; then
    print_success "Ya estás autenticado en Azure CLI"
    CURRENT_SUB=$(az account show --query id -o tsv)
    if [ "$CURRENT_SUB" = "$AZURE_SUBSCRIPTION_ID" ]; then
        print_success "Suscripción correcta configurada"
    else
        print_warning "Cambiando a la suscripción correcta..."
        az account set --subscription "$AZURE_SUBSCRIPTION_ID"
        print_success "Suscripción cambiada correctamente"
    fi
else
    print_status "Iniciando sesión en Azure..."
    az login --tenant "$AZURE_TENANT_ID"
    az account set --subscription "$AZURE_SUBSCRIPTION_ID"
    print_success "Autenticación completada"
fi

# Verificar permisos
print_status "Verificando permisos..."

USER_ID=$(az ad signed-in-user show --query id -o tsv)
ROLE_ASSIGNMENTS=$(az role assignment list --assignee "$USER_ID" --query "[].roleDefinitionName" -o tsv)

if echo "$ROLE_ASSIGNMENTS" | grep -q "Owner"; then
    print_success "Tienes permisos de Owner - ¡Perfecto!"
elif echo "$ROLE_ASSIGNMENTS" | grep -q "Contributor"; then
    print_warning "Tienes permisos de Contributor - Puede que necesites permisos adicionales"
else
    print_error "No tienes permisos suficientes. Contacta al administrador de Azure."
    exit 1
fi

# Configurar Terraform
print_status "Configurando Terraform..."

# Crear archivo de configuración de Azure para Terraform
cat > ~/.azure/credentials << EOF
[default]
subscription_id = $AZURE_SUBSCRIPTION_ID
tenant_id = $AZURE_TENANT_ID
EOF

print_success "Archivo de credenciales de Azure creado en ~/.azure/credentials"

# Verificar que Terraform puede autenticarse
if [ -d "infra/terraform" ]; then
    cd infra/terraform
    print_status "Verificando configuración de Terraform..."
    if terraform init &> /dev/null; then
        print_success "Terraform configurado correctamente"
    else
        print_warning "Terraform necesita ser inicializado manualmente"
    fi
    cd - > /dev/null
fi

# Crear archivo .bashrc/.zshrc con las variables de entorno
SHELL_CONFIG=""
if [ -f ~/.zshrc ]; then
    SHELL_CONFIG=~/.zshrc
elif [ -f ~/.bashrc ]; then
    SHELL_CONFIG=~/.bashrc
elif [ -f ~/.bash_profile ]; then
    SHELL_CONFIG=~/.bash_profile
fi

if [ -n "$SHELL_CONFIG" ]; then
    print_status "Agregando variables de entorno a $SHELL_CONFIG"
    
    # Verificar si ya existen las variables
    if ! grep -q "AZURE_SUBSCRIPTION_ID" "$SHELL_CONFIG"; then
        cat >> "$SHELL_CONFIG" << EOF

# Azure Configuration
export AZURE_SUBSCRIPTION_ID="$AZURE_SUBSCRIPTION_ID"
export AZURE_TENANT_ID="$AZURE_TENANT_ID"
EOF
        print_success "Variables de entorno agregadas a $SHELL_CONFIG"
        print_warning "Ejecuta 'source $SHELL_CONFIG' o reinicia tu terminal para aplicar los cambios"
    else
        print_success "Las variables de entorno ya están configuradas en $SHELL_CONFIG"
    fi
fi

# Crear script de login rápido
cat > azure-login.sh << 'EOF'
#!/bin/bash
# Script para login rápido en Azure
echo "🔐 Iniciando sesión en Azure..."
az login --tenant "$AZURE_TENANT_ID"
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
echo "✅ Sesión iniciada correctamente"
EOF

chmod +x azure-login.sh
print_success "Script de login rápido creado: ./azure-login.sh"

print_success "🎉 Configuración de Azure completada!"
print_status "Para usar en el futuro:"
echo "  1. Ejecuta: ./azure-login.sh (si necesitas reautenticarte)"
echo "  2. Las variables de entorno están configuradas automáticamente"
echo "  3. Terraform debería funcionar sin problemas"

print_status "Información de tu cuenta:"
az account show --query "{subscription:name, tenant:tenantId, user:user.name}" -o table

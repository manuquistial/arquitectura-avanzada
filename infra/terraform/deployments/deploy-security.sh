#!/bin/bash
# =============================================================================
# DEPLOY SECURITY LAYER
# =============================================================================
# Script para desplegar la capa de seguridad (Key Vault y MI)
# =============================================================================

set -e

echo "🚀 Deploying SECURITY LAYER..."

# Cambiar al directorio de la capa de seguridad
cd "$(dirname "$0")/../layers/security"

# Inicializar Terraform
echo "📦 Initializing Terraform..."
terraform init -upgrade

# Validar configuración
echo "✅ Validating configuration..."
terraform validate

# Plan de despliegue
echo "📋 Planning deployment..."
terraform plan -out=security.tfplan

# Aplicar cambios
echo "🏗️ Applying changes..."
terraform apply security.tfplan

echo "✅ SECURITY LAYER deployed successfully!"
echo "📊 Outputs:"
terraform output

echo ""
echo "🎯 Next steps:"
echo "1. Run: ./deploy-platform.sh"

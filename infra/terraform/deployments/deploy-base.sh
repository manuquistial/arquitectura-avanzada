#!/bin/bash
# =============================================================================
# DEPLOY BASE LAYER
# =============================================================================
# Script para desplegar la capa base (infraestructura base)
# =============================================================================

set -e

echo "🚀 Deploying BASE LAYER..."

# Cambiar al directorio de la capa base
cd layers/base

# Inicializar Terraform
echo "📦 Initializing Terraform..."
terraform init

# Validar configuración
echo "✅ Validating configuration..."
terraform validate

# Plan de despliegue
echo "📋 Planning deployment..."
terraform plan -out=base.tfplan

# Aplicar cambios
echo "🏗️ Applying changes..."
terraform apply base.tfplan

echo "✅ BASE LAYER deployed successfully!"
echo "📊 Outputs:"
terraform output

echo ""
echo "🎯 Next steps:"
echo "1. Run: ./deploy-security.sh"
echo "2. Run: ./deploy-platform.sh"
echo "3. Run: ./deploy-external-secrets.sh"
echo "4. Run: ./deploy-application.sh"

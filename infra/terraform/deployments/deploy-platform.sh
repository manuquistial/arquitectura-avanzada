#!/bin/bash
# =============================================================================
# DEPLOY PLATFORM LAYER
# =============================================================================
# Script para desplegar la capa de plataforma (servicios)
# =============================================================================

set -e

echo "🚀 Deploying PLATFORM LAYER..."

# Cambiar al directorio de la capa de plataforma
cd layers/platform

# Inicializar Terraform
echo "📦 Initializing Terraform..."
terraform init

# Validar configuración
echo "✅ Validating configuration..."
terraform validate

# Plan de despliegue
echo "📋 Planning deployment..."
terraform plan -out=platform.tfplan

# Aplicar cambios
echo "🏗️ Applying changes..."
terraform apply platform.tfplan

echo "✅ PLATFORM LAYER deployed successfully!"
echo "📊 Outputs:"
terraform output

echo ""
echo "🎯 Next steps:"
echo "1. Run: ./deploy-application.sh"


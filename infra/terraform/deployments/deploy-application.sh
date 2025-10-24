#!/bin/bash
# =============================================================================
# DEPLOY APPLICATION LAYER
# =============================================================================
# Script para desplegar la capa de aplicación (apps y servicios)
# =============================================================================

set -e

echo "🚀 Deploying APPLICATION LAYER..."

# Cambiar al directorio de la capa de aplicación
cd layers/application

# Inicializar Terraform
echo "📦 Initializing Terraform..."
terraform init

# Validar configuración
echo "✅ Validating configuration..."
terraform validate

# Plan de despliegue
echo "📋 Planning deployment..."
terraform plan -out=application.tfplan

# Aplicar cambios
echo "🏗️ Applying changes..."
terraform apply application.tfplan

echo "✅ APPLICATION LAYER deployed successfully!"
echo "📊 Outputs:"
terraform output

echo ""
echo "🎉 All layers deployed successfully!"
echo "🌐 Your application should be available at the configured endpoints."



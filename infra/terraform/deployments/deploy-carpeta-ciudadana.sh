#!/bin/bash
# =============================================================================
# DEPLOY CARPETA CIUDADANA LAYER
# =============================================================================
# Script para desplegar la capa de la aplicación Carpeta Ciudadana (helm chart)
# =============================================================================

set -e

echo "🚀 Deploying CARPETA CIUDADANA LAYER..."

# Cambiar al directorio de la capa carpeta-ciudadana
cd "$(dirname "$0")/../layers/carpeta-ciudadana"

# Inicializar Terraform
echo "📦 Initializing Terraform..."
terraform init -upgrade

# Validar configuración
echo "✅ Validating configuration..."
terraform validate

# Plan de despliegue
echo "📋 Planning deployment..."
terraform plan -out=carpeta.tfplan

# Aplicar cambios
echo "🏗️ Applying changes..."
terraform apply carpeta.tfplan

echo "✅ CARPETA CIUDADANA LAYER deployed successfully!"

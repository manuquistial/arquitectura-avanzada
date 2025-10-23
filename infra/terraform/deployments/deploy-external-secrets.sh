#!/bin/bash

# =============================================================================
# DEPLOY EXTERNAL SECRETS LAYER
# =============================================================================
# Script para desplegar la capa de External Secrets
# =============================================================================

set -e

echo "🚀 Deploying External Secrets Layer..."

# Cambiar al directorio de External Secrets
cd layers/external-secrets

# Inicializar Terraform
echo "📦 Initializing Terraform..."
terraform init

# Validar configuración
echo "✅ Validating configuration..."
terraform validate

# Plan de despliegue
echo "📋 Planning deployment..."
terraform plan

# Aplicar cambios
echo "🚀 Applying changes..."
terraform apply -auto-approve

echo "✅ External Secrets Layer deployed successfully!"
echo "📊 Next step: Deploy Application Layer"

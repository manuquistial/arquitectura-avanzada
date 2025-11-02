#!/bin/bash

# =============================================================================
# DEPLOY EXTERNAL SECRETS LAYER
# =============================================================================
# Script para desplegar la capa de External Secrets
# =============================================================================

set -e

echo "🚀 Deploying External Secrets Layer..."

# -----------------------------------------------------------------------------
# Refrescar credenciales de AKS para evitar errores de DNS del API Server
# -----------------------------------------------------------------------------
if command -v az >/dev/null 2>&1; then
  echo "🔐 Refreshing AKS kubeconfig from Platform outputs..."
  # Descubrir RG y nombre del cluster desde la capa PLATFORM (ya aplicada)
  PLATFORM_DIR="$(cd "$(dirname "$0")/../layers/platform" && pwd)"
  if [ -d "$PLATFORM_DIR" ]; then
    if terraform -chdir="$PLATFORM_DIR" output >/dev/null 2>&1; then
      AKS_RG="$(terraform -chdir="$PLATFORM_DIR" output -raw resource_group_name)"
      AKS_NAME="$(terraform -chdir="$PLATFORM_DIR" output -raw aks_cluster_name)"
      if [ -n "$AKS_RG" ] && [ -n "$AKS_NAME" ]; then
        # Respetar AZURE_SUBSCRIPTION_ID si está definido
        if [ -n "${AZURE_SUBSCRIPTION_ID:-}" ]; then
          echo "🪪 Setting Azure subscription: $AZURE_SUBSCRIPTION_ID"
          az account set --subscription "$AZURE_SUBSCRIPTION_ID" || true
        fi
        echo "🔧 az aks get-credentials -g $AKS_RG -n $AKS_NAME --admin --overwrite-existing"
        az aks get-credentials -g "$AKS_RG" -n "$AKS_NAME" --admin --overwrite-existing
      else
        echo "⚠️  Could not resolve AKS RG/NAME from Platform outputs. Skipping kubeconfig refresh."
      fi
    else
      echo "⚠️  Platform layer outputs not available yet. Skipping kubeconfig refresh."
    fi
  else
    echo "⚠️  Platform directory not found at $PLATFORM_DIR. Skipping kubeconfig refresh."
  fi
else
  echo "ℹ️  Azure CLI not found. Assuming kubeconfig is already configured."
fi

# Mostrar contexto actual (si kubectl está disponible)
if command -v kubectl >/dev/null 2>&1; then
  echo "🧭 Current kube context: $(kubectl config current-context 2>/dev/null || echo 'unknown')"
fi

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







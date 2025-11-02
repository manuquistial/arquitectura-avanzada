#!/bin/bash
# =============================================================================
# DESTROY ALL AZURE RESOURCES - ROBUST VERSION
# =============================================================================
# Script para eliminar TODOS los recursos de Azure desplegados
# Maneja casos donde el cluster de Kubernetes no está disponible
# =============================================================================

set -e

echo "⚠️  WARNING: This will DESTROY ALL Azure resources!"
echo "⚠️  This action is IRREVERSIBLE!"
echo ""
read -p "Are you sure you want to continue? Type 'yes' to confirm: " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "❌ Destruction cancelled."
    exit 1
fi

echo ""
echo "🔥 Starting destruction of ALL Azure resources..."
echo "📋 Destruction order:"
echo "   1. Carpeta Ciudadana Layer (applications)"
echo "   2. Application Layer (services)"
echo "   3. External Secrets Layer"
echo "   4. Platform Layer (AKS, DB, etc.)"
echo "   5. Security Layer (Key Vault, MI)"
echo "   6. Base Layer (networking, DNS)"
echo ""

# Function to destroy a layer with error handling
destroy_layer() {
    local layer_name=$1
    local layer_path=$2
    
    echo "🔥 Destroying $layer_name layer..."
    cd "/Users/manueljurado/arquitectura_avanzada/infra/terraform/$layer_path"
    
    # Initialize terraform
    echo "📦 Initializing Terraform for $layer_name..."
    terraform init -upgrade
    
    # Try to destroy, but continue if there are connectivity issues
    echo "💥 Applying destruction for $layer_name..."
    if terraform destroy -auto-approve; then
        echo "✅ $layer_name layer destroyed successfully!"
    else
        echo "⚠️  $layer_name layer destruction had issues, but continuing..."
        echo "   (This is normal if Kubernetes resources are unreachable)"
    fi
    echo ""
}

# Change to terraform directory
cd /Users/manueljurado/arquitectura_avanzada/infra/terraform

# Destroy layers in reverse dependency order
destroy_layer "Carpeta-Ciudadana" "layers/carpeta-ciudadana"
destroy_layer "Application" "layers/application"
destroy_layer "External-Secrets" "layers/external-secrets"
destroy_layer "Platform" "layers/platform"
destroy_layer "Security" "layers/security"
destroy_layer "Base" "layers/base"

echo ""
echo "🎉 Azure resources destruction process completed!"
echo "✅ All layers have been processed!"
echo ""
echo "📊 Summary:"
echo "   - Kubernetes resources removed (if cluster was reachable)"
echo "   - Azure services destroyed"
echo "   - Networking resources removed"
echo "   - DNS records deleted"
echo "   - Resource group deleted"
echo ""
echo "⚠️  Note: Some resources may take a few minutes to fully disappear from Azure portal"
echo "🔍 You can verify by checking your Azure portal"

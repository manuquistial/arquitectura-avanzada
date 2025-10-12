#!/bin/bash

#############################################
# cert-manager Deployment Script for AKS
# Despliega cert-manager y ClusterIssuers
#############################################

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones helper
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Verificar que terraform.tfvars existe
if [ ! -f "infra/terraform/terraform.tfvars" ]; then
    log_error "terraform.tfvars no encontrado"
    log_info "Copiando terraform.tfvars.example a terraform.tfvars"
    cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
    log_warn "Por favor, edita infra/terraform/terraform.tfvars con tus credenciales antes de continuar"
    exit 1
fi

# Verificar que letsencrypt_email está configurado
if grep -q "your-email@example.com" infra/terraform/terraform.tfvars; then
    log_error "Por favor, cambia letsencrypt_email en terraform.tfvars antes de continuar"
    log_info "El email es necesario para notificaciones de Let's Encrypt"
    exit 1
fi

log_step "Desplegando cert-manager en AKS..."

# Cambiar al directorio de Terraform
cd infra/terraform

# Inicializar Terraform
log_info "Inicializando Terraform..."
terraform init

# Planificar el despliegue
log_info "Planificando despliegue..."
terraform plan -out=tfplan

# Preguntar confirmación
echo ""
read -p "¿Deseas aplicar los cambios? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "Despliegue cancelado"
    exit 0
fi

# Aplicar cambios
log_info "Aplicando cambios..."
terraform apply tfplan

# Obtener outputs
log_info "Obteniendo información de cert-manager..."
CERT_MANAGER_NS=$(terraform output -raw cert_manager_namespace)
STAGING_ISSUER=$(terraform output -raw letsencrypt_staging_issuer)
PROD_ISSUER=$(terraform output -raw letsencrypt_prod_issuer)

if [ -n "$CERT_MANAGER_NS" ]; then
    log_info "cert-manager desplegado exitosamente!"
    echo ""
    echo "Namespace: $CERT_MANAGER_NS"
    echo "Staging ClusterIssuer: $STAGING_ISSUER"
    echo "Production ClusterIssuer: $PROD_ISSUER"
    echo ""
    
    # Volver al directorio raíz
    cd ../..
    
    # Verificar el despliegue
    log_step "Verificando el despliegue..."
    
    # Obtener kubeconfig
    RESOURCE_GROUP=$(terraform -chdir=infra/terraform output -raw resource_group_name)
    CLUSTER_NAME=$(terraform -chdir=infra/terraform output -raw aks_cluster_name)
    
    log_info "Obteniendo kubeconfig..."
    az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --overwrite-existing
    
    # Verificar pods
    log_info "Verificando pods de cert-manager..."
    kubectl get pods -n "$CERT_MANAGER_NS"
    
    # Esperar a que los pods estén ready
    log_info "Esperando a que cert-manager esté listo..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n "$CERT_MANAGER_NS" --timeout=120s
    
    # Verificar ClusterIssuers
    log_info "Verificando ClusterIssuers..."
    kubectl get clusterissuers
    
    # Describir ClusterIssuers
    echo ""
    log_info "Estado del ClusterIssuer staging:"
    kubectl describe clusterissuer "$STAGING_ISSUER" | grep -A 5 "Status:"
    
    echo ""
    log_info "Estado del ClusterIssuer production:"
    kubectl describe clusterissuer "$PROD_ISSUER" | grep -A 5 "Status:"
    
    echo ""
    log_info "Para ver los logs de cert-manager:"
    echo "  kubectl logs -n $CERT_MANAGER_NS deployment/cert-manager -f"
    echo ""
    
    log_step "Próximos pasos:"
    echo ""
    echo "1. Si tienes un dominio:"
    echo "   - Configura un registro DNS A apuntando al LoadBalancer del Ingress"
    echo "   - Habilita TLS en values.yaml o values-dev.yaml"
    echo "   - Usa letsencrypt-staging para testing"
    echo "   - Cambia a letsencrypt-prod cuando todo funcione"
    echo ""
    echo "2. Si NO tienes un dominio:"
    echo "   - Deja TLS deshabilitado (tls.enabled: false)"
    echo "   - Accede a la aplicación vía IP del LoadBalancer"
    echo "   - Considera usar nip.io para DNS gratuito"
    echo ""
    echo "3. Para instalar Nginx Ingress Controller:"
    echo "   helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx"
    echo "   helm repo update"
    echo "   helm install nginx-ingress ingress-nginx/ingress-nginx \\"
    echo "     --namespace ingress-nginx --create-namespace \\"
    echo "     --set controller.service.type=LoadBalancer"
    echo ""
    
    log_info "Documentación completa: docs/CERT_MANAGER_TLS.md"
    
else
    log_error "Error al desplegar cert-manager"
    exit 1
fi

log_info "¡Despliegue completado!"


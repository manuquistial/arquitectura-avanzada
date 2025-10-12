#!/bin/bash

#############################################
# OpenSearch Deployment Script for AKS
# Despliega OpenSearch usando Terraform
#############################################

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Verificar que terraform.tfvars existe
if [ ! -f "infra/terraform/terraform.tfvars" ]; then
    log_error "terraform.tfvars no encontrado"
    log_info "Copiando terraform.tfvars.example a terraform.tfvars"
    cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
    log_warn "Por favor, edita infra/terraform/terraform.tfvars con tus credenciales antes de continuar"
    exit 1
fi

# Verificar que opensearch_password está configurado
if grep -q "CHANGE_ME_STRONG_OPENSEARCH_PASSWORD" infra/terraform/terraform.tfvars; then
    log_error "Por favor, cambia opensearch_password en terraform.tfvars antes de continuar"
    exit 1
fi

log_info "Desplegando OpenSearch en AKS..."

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
log_info "Obteniendo endpoints..."
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)
OPENSEARCH_SECRET=$(terraform output -raw opensearch_secret_name)

if [ -n "$OPENSEARCH_ENDPOINT" ]; then
    log_info "OpenSearch desplegado exitosamente!"
    echo ""
    echo "Endpoints:"
    echo "  - OpenSearch: http://$OPENSEARCH_ENDPOINT"
    
    DASHBOARDS_ENDPOINT=$(terraform output -raw opensearch_dashboards_endpoint)
    if [ -n "$DASHBOARDS_ENDPOINT" ] && [ "$DASHBOARDS_ENDPOINT" != "null" ]; then
        echo "  - Dashboards: http://$DASHBOARDS_ENDPOINT"
    fi
    
    echo ""
    echo "Credenciales almacenadas en Secret: $OPENSEARCH_SECRET"
    echo ""
    
    # Volver al directorio raíz
    cd ../..
    
    # Verificar el despliegue
    log_info "Verificando el despliegue..."
    
    # Obtener kubeconfig
    RESOURCE_GROUP=$(terraform -chdir=infra/terraform output -raw resource_group_name)
    CLUSTER_NAME=$(terraform -chdir=infra/terraform output -raw aks_cluster_name)
    
    log_info "Obteniendo kubeconfig..."
    az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --overwrite-existing
    
    # Verificar pods
    log_info "Verificando pods de OpenSearch..."
    kubectl get pods -l app.kubernetes.io/name=opensearch
    
    # Verificar servicios
    log_info "Verificando servicios de OpenSearch..."
    kubectl get svc -l app.kubernetes.io/name=opensearch
    
    # Verificar secret
    log_info "Verificando secret opensearch-auth..."
    kubectl get secret opensearch-auth
    
    echo ""
    log_info "Para ver los logs de OpenSearch:"
    echo "  kubectl logs -f -l app.kubernetes.io/name=opensearch"
    echo ""
    log_info "Para acceder a OpenSearch Dashboards localmente:"
    echo "  kubectl port-forward svc/opensearch-dashboards 5601:5601"
    echo "  Luego abre http://localhost:5601 en tu navegador"
    echo ""
    log_info "Para probar la conexión a OpenSearch:"
    echo "  kubectl port-forward svc/opensearch-cluster-master 9200:9200"
    echo "  curl http://localhost:9200/_cluster/health"
    echo ""
    
else
    log_error "Error al desplegar OpenSearch"
    exit 1
fi

log_info "¡Despliegue completado!"


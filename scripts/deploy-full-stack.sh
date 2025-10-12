#!/bin/bash

##############################################################
# Full Stack Deployment Script
# Despliega infraestructura + aplicación automáticamente
##############################################################

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Variables
ENVIRONMENT="${ENVIRONMENT:-dev}"
NAMESPACE="${NAMESPACE:-default}"
TERRAFORM_DIR="infra/terraform"
HELM_DIR="deploy/helm"

log_step "Deploying Carpeta Ciudadana - Environment: $ENVIRONMENT"

##############################################################
# PASO 1: Terraform - Infraestructura
##############################################################

log_step "1/6 - Deploying infrastructure with Terraform..."

cd "$TERRAFORM_DIR"

# Verificar terraform.tfvars
if [ ! -f "terraform.tfvars" ]; then
    log_error "terraform.tfvars not found"
    log_info "Copying from example..."
    cp terraform.tfvars.example terraform.tfvars
    log_error "Please configure terraform.tfvars before continuing"
    exit 1
fi

# Verificar credenciales críticas
if grep -q "CHANGE_ME" terraform.tfvars; then
    log_error "Please update CHANGE_ME placeholders in terraform.tfvars"
    exit 1
fi

log_info "Initializing Terraform..."
terraform init

log_info "Planning infrastructure..."
terraform plan -out=tfplan

echo ""
read -p "Apply Terraform plan? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "Deployment cancelled"
    exit 0
fi

log_info "Applying Terraform..."
terraform apply tfplan

log_info "✅ Infrastructure deployed"

cd ../..

##############################################################
# PASO 2: Obtener Kubeconfig
##############################################################

log_step "2/6 - Getting AKS credentials..."

RESOURCE_GROUP=$(terraform -chdir="$TERRAFORM_DIR" output -raw resource_group_name)
CLUSTER_NAME=$(terraform -chdir="$TERRAFORM_DIR" output -raw aks_cluster_name)

log_info "Resource Group: $RESOURCE_GROUP"
log_info "Cluster: $CLUSTER_NAME"

az aks get-credentials \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --overwrite-existing

log_info "✅ Kubeconfig configured"

##############################################################
# PASO 3: Nginx Ingress Controller
##############################################################

log_step "3/6 - Installing Nginx Ingress Controller..."

if helm list -n ingress-nginx | grep -q nginx-ingress; then
    log_info "Nginx Ingress already installed, skipping..."
else
    log_info "Installing Nginx Ingress Controller..."
    
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    
    helm install nginx-ingress ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.type=LoadBalancer \
        --set controller.metrics.enabled=true \
        --set controller.podAnnotations."prometheus\.io/scrape"=true \
        --set controller.podAnnotations."prometheus\.io/port"=10254 \
        --wait \
        --timeout 5m
    
    log_info "✅ Nginx Ingress installed"
fi

##############################################################
# PASO 4: Crear Secrets desde Terraform Outputs
##############################################################

log_step "4/6 - Creating Kubernetes Secrets..."

export NAMESPACE="$NAMESPACE"
export TERRAFORM_DIR="$TERRAFORM_DIR"

./scripts/create-k8s-secrets.sh

log_info "✅ Secrets created"

##############################################################
# PASO 5: Desplegar Aplicación con Helm
##############################################################

log_step "5/6 - Deploying application with Helm..."

cd "$HELM_DIR"

# Obtener valores de Terraform
STORAGE_ACCOUNT=$(terraform -chdir="../../$TERRAFORM_DIR" output -raw storage_account_name)
DB_HOST=$(terraform -chdir="../../$TERRAFORM_DIR" output -raw postgresql_fqdn)
SERVICEBUS_CONN=$(terraform -chdir="../../$TERRAFORM_DIR" output -raw servicebus_connection_string)

# Determinar values file según ambiente
if [ "$ENVIRONMENT" = "prod" ]; then
    VALUES_FILE="values-prod.yaml"
    log_info "Using production values"
else
    VALUES_FILE="values-dev.yaml"
    log_info "Using development values"
fi

# Helm upgrade --install
log_info "Deploying with Helm..."

helm upgrade --install carpeta-ciudadana ./carpeta-ciudadana \
    -f carpeta-ciudadana/values.yaml \
    -f "$VALUES_FILE" \
    --set postgresql.host="$DB_HOST" \
    --set azure.storage.accountName="$STORAGE_ACCOUNT" \
    --set serviceBus.connectionString="$SERVICEBUS_CONN" \
    --set serviceBus.enabled=true \
    --namespace "$NAMESPACE" \
    --create-namespace \
    --wait \
    --timeout 15m

log_info "✅ Application deployed"

cd ../..

##############################################################
# PASO 6: Verificación
##############################################################

log_step "6/6 - Verifying deployment..."

echo ""
log_info "Checking migration jobs..."
kubectl get jobs -n "$NAMESPACE" | grep migrate || true

echo ""
log_info "Checking pods..."
kubectl get pods -n "$NAMESPACE"

echo ""
log_info "Checking services..."
kubectl get svc -n "$NAMESPACE"

echo ""
log_info "Checking ingress..."
kubectl get ingress -n "$NAMESPACE"

echo ""
log_info "Checking secrets..."
kubectl get secrets -n "$NAMESPACE" | grep -E "(database|sb-conn|opensearch|azure-storage)" || true

echo ""
log_info "Checking configmaps..."
kubectl get configmap -n "$NAMESPACE" | grep -E "(app-flags|cors-origins)" || true

##############################################################
# Información de Acceso
##############################################################

echo ""
log_step "Deployment Complete!"
echo ""

# Obtener IP del Ingress
INGRESS_IP=$(kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending...")

if [ "$INGRESS_IP" != "pending..." ]; then
    log_info "Access URLs:"
    echo "  Frontend: http://$INGRESS_IP"
    echo "  API:      http://$INGRESS_IP/api"
else
    log_warn "LoadBalancer IP pending, check with: kubectl get svc -n ingress-nginx"
fi

echo ""
log_info "Useful commands:"
echo "  View pods:         kubectl get pods -n $NAMESPACE"
echo "  View logs:         kubectl logs -f deployment/carpeta-ciudadana-gateway -n $NAMESPACE"
echo "  Port forward:      kubectl port-forward svc/carpeta-ciudadana-gateway 8000:8000 -n $NAMESPACE"
echo "  Migration logs:    kubectl logs job/carpeta-ciudadana-migrate-citizen-<revision> -n $NAMESPACE"
echo ""

log_info "🎉 Full stack deployment completed!"


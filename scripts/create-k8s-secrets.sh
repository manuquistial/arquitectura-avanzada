#!/bin/bash

##############################################################
# Create Kubernetes Secrets from Terraform Outputs
# Automáticamente crea todos los secrets necesarios
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
NAMESPACE="${NAMESPACE:-default}"
TERRAFORM_DIR="${TERRAFORM_DIR:-infra/terraform}"

log_step "Creating Kubernetes Secrets from Terraform outputs..."

# Verificar que estamos en el directorio correcto
if [ ! -d "$TERRAFORM_DIR" ]; then
    log_error "Terraform directory not found: $TERRAFORM_DIR"
    exit 1
fi

# Obtener outputs de Terraform
cd "$TERRAFORM_DIR"

log_info "Extracting Terraform outputs..."

# PostgreSQL
POSTGRES_HOST=$(terraform output -raw postgresql_fqdn 2>/dev/null || echo "")
POSTGRES_USER=$(terraform output -raw postgresql_admin_username 2>/dev/null || echo "")
POSTGRES_PASS=$(terraform output -raw db_admin_password 2>/dev/null || echo "")
POSTGRES_DB="carpeta_ciudadana"

# Service Bus
SERVICEBUS_CONN=$(terraform output -raw servicebus_connection_string 2>/dev/null || echo "")

# Storage
STORAGE_ACCOUNT=$(terraform output -raw storage_account_name 2>/dev/null || echo "")
STORAGE_KEY=$(terraform output -raw storage_account_key 2>/dev/null || echo "")

# OpenSearch
OS_USERNAME=$(terraform output -raw opensearch_username 2>/dev/null || echo "admin")
OS_PASSWORD=$(terraform output -raw opensearch_password 2>/dev/null || echo "")

# Volver al root
cd ../..

log_info "Switching to namespace: $NAMESPACE"
kubectl config set-context --current --namespace="$NAMESPACE"

# 1. Database Secret
log_step "Creating Secret: carpeta-ciudadana-database"

if [ -n "$POSTGRES_HOST" ] && [ -n "$POSTGRES_USER" ] && [ -n "$POSTGRES_PASS" ]; then
    DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASS}@${POSTGRES_HOST}:5432/${POSTGRES_DB}"
    POSTGRES_URI="postgresql://${POSTGRES_USER}:${POSTGRES_PASS}@${POSTGRES_HOST}:5432/${POSTGRES_DB}"
    
    kubectl create secret generic carpeta-ciudadana-database \
        --from-literal=DATABASE_URL="$DATABASE_URL" \
        --from-literal=POSTGRES_URI="$POSTGRES_URI" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "✅ Database secret created/updated"
else
    log_warn "⚠️  PostgreSQL credentials not found in Terraform outputs"
fi

# 2. Service Bus Secret
log_step "Creating Secret: sb-conn"

if [ -n "$SERVICEBUS_CONN" ]; then
    kubectl create secret generic sb-conn \
        --from-literal=SERVICEBUS_CONNECTION_STRING="$SERVICEBUS_CONN" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "✅ Service Bus secret created/updated"
else
    log_warn "⚠️  Service Bus connection string not found"
fi

# 3. Azure Storage Secret
log_step "Creating Secret: azure-storage"

if [ -n "$STORAGE_ACCOUNT" ] && [ -n "$STORAGE_KEY" ]; then
    STORAGE_CONN="DefaultEndpointsProtocol=https;AccountName=${STORAGE_ACCOUNT};AccountKey=${STORAGE_KEY};EndpointSuffix=core.windows.net"
    
    kubectl create secret generic azure-storage \
        --from-literal=AZURE_STORAGE_ACCOUNT_NAME="$STORAGE_ACCOUNT" \
        --from-literal=AZURE_STORAGE_ACCOUNT_KEY="$STORAGE_KEY" \
        --from-literal=AZURE_STORAGE_CONNECTION_STRING="$STORAGE_CONN" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "✅ Azure Storage secret created/updated"
else
    log_warn "⚠️  Azure Storage credentials not found"
fi

# 4. OpenSearch Auth (si no existe desde Terraform)
log_step "Checking Secret: opensearch-auth"

if kubectl get secret opensearch-auth >/dev/null 2>&1; then
    log_info "✅ opensearch-auth already exists (created by Terraform)"
else
    log_warn "⚠️  opensearch-auth not found, creating manually..."
    
    if [ -n "$OS_PASSWORD" ]; then
        kubectl create secret generic opensearch-auth \
            --from-literal=OS_USERNAME="$OS_USERNAME" \
            --from-literal=OS_PASSWORD="$OS_PASSWORD" \
            --from-literal=OPENSEARCH_URL="http://opensearch-cluster-master:9200" \
            --dry-run=client -o yaml | kubectl apply -f -
        
        log_info "✅ OpenSearch secret created/updated"
    fi
fi

# 5. Redis Password (opcional)
log_step "Creating Secret: redis-password"

REDIS_PASSWORD="${REDIS_PASSWORD:-}"

kubectl create secret generic redis-password \
    --from-literal=password="$REDIS_PASSWORD" \
    --dry-run=client -o yaml | kubectl apply -f -

log_info "✅ Redis secret created/updated"

# 6. SMTP/Email credentials (opcional, para notifications)
log_step "Creating Secret: smtp-credentials"

SMTP_HOST="${SMTP_HOST:-}"
SMTP_PORT="${SMTP_PORT:-587}"
SMTP_USER="${SMTP_USER:-}"
SMTP_PASS="${SMTP_PASS:-}"
SMTP_FROM="${SMTP_FROM:-noreply@carpeta-ciudadana.example.com}"

kubectl create secret generic smtp-credentials \
    --from-literal=SMTP_HOST="$SMTP_HOST" \
    --from-literal=SMTP_PORT="$SMTP_PORT" \
    --from-literal=SMTP_USER="$SMTP_USER" \
    --from-literal=SMTP_PASSWORD="$SMTP_PASS" \
    --from-literal=SMTP_FROM="$SMTP_FROM" \
    --dry-run=client -o yaml | kubectl apply -f -

log_info "✅ SMTP secret created/updated"

# 7. Azure Communication Services (opcional)
log_step "Creating Secret: acs-credentials"

ACS_ENDPOINT="${ACS_ENDPOINT:-}"
ACS_KEY="${ACS_KEY:-}"

kubectl create secret generic acs-credentials \
    --from-literal=ACS_ENDPOINT="$ACS_ENDPOINT" \
    --from-literal=ACS_KEY="$ACS_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -

log_info "✅ ACS secret created/updated"

# Resumen
log_step "Summary of Secrets Created"
echo ""
kubectl get secrets | grep -E "(carpeta-ciudadana-database|sb-conn|azure-storage|opensearch-auth|redis-password|smtp-credentials|acs-credentials)"
echo ""

log_info "✅ All secrets created/updated successfully!"
log_info "Secrets are ready for Helm deployment"


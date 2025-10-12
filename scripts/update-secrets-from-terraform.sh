#!/bin/bash

##############################################################
# Update Kubernetes Secrets from Terraform State
# Para CI/CD o actualizaciones manuales
##############################################################

set -e

# Variables
NAMESPACE="${1:-default}"
TERRAFORM_DIR="${TERRAFORM_DIR:-infra/terraform}"

echo "Updating Kubernetes secrets in namespace: $NAMESPACE"

cd "$TERRAFORM_DIR"

# Extract outputs
echo "Extracting Terraform outputs..."

POSTGRES_HOST=$(terraform output -raw postgresql_fqdn)
POSTGRES_USER=$(terraform output -raw postgresql_admin_username)
POSTGRES_PASS=$(terraform output -raw db_admin_password)
POSTGRES_DB="carpeta_ciudadana"

SERVICEBUS_CONN=$(terraform output -raw servicebus_connection_string)

STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)
STORAGE_KEY=$(terraform output -raw storage_account_key)

OS_USERNAME=$(terraform output -raw opensearch_username)
OS_PASSWORD=$(terraform output -raw opensearch_password)

cd ../..

# Switch to namespace
kubectl config set-context --current --namespace="$NAMESPACE"

echo ""
echo "Creating/Updating secrets..."
echo ""

# Database
echo "1. carpeta-ciudadana-database"
DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASS}@${POSTGRES_HOST}:5432/${POSTGRES_DB}"
POSTGRES_URI="postgresql://${POSTGRES_USER}:${POSTGRES_PASS}@${POSTGRES_HOST}:5432/${POSTGRES_DB}"

kubectl create secret generic carpeta-ciudadana-database \
    --from-literal=DATABASE_URL="$DATABASE_URL" \
    --from-literal=POSTGRES_URI="$POSTGRES_URI" \
    --dry-run=client -o yaml | kubectl apply -f -

# Service Bus
echo "2. sb-conn"
kubectl create secret generic sb-conn \
    --from-literal=SERVICEBUS_CONNECTION_STRING="$SERVICEBUS_CONN" \
    --dry-run=client -o yaml | kubectl apply -f -

# Azure Storage (fallback, Managed Identity preferred)
echo "3. azure-storage"
STORAGE_CONN="DefaultEndpointsProtocol=https;AccountName=${STORAGE_ACCOUNT};AccountKey=${STORAGE_KEY};EndpointSuffix=core.windows.net"

kubectl create secret generic azure-storage \
    --from-literal=AZURE_STORAGE_ACCOUNT_NAME="$STORAGE_ACCOUNT" \
    --from-literal=AZURE_STORAGE_ACCOUNT_KEY="$STORAGE_KEY" \
    --from-literal=AZURE_STORAGE_CONNECTION_STRING="$STORAGE_CONN" \
    --dry-run=client -o yaml | kubectl apply -f -

# OpenSearch (check if Terraform created it)
echo "4. opensearch-auth"
if ! kubectl get secret opensearch-auth >/dev/null 2>&1; then
    kubectl create secret generic opensearch-auth \
        --from-literal=OS_USERNAME="$OS_USERNAME" \
        --from-literal=OS_PASSWORD="$OS_PASSWORD" \
        --from-literal=OPENSEARCH_URL="http://opensearch-cluster-master:9200" \
        --dry-run=client -o yaml | kubectl apply -f -
fi

echo ""
echo "✅ All secrets updated successfully!"
echo ""

# Show secrets (without values)
kubectl get secrets | grep -E "(database|sb-conn|azure-storage|opensearch-auth)"


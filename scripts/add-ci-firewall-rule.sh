#!/bin/bash

##############################################################
# Add Temporary Firewall Rule for CI/CD Runner
# Permite acceso temporal desde GitHub Actions runner
##############################################################

set -e

# Variables
RESOURCE_GROUP="${RESOURCE_GROUP:-}"
SERVER_NAME="${SERVER_NAME:-}"
RULE_NAME="${RULE_NAME:-AllowCIRunner}"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Obtener IP pública del runner
log_info "Detecting CI runner public IP..."
RUNNER_IP=$(curl -s https://api.ipify.org)

if [ -z "$RUNNER_IP" ]; then
    log_error "Could not detect runner IP"
    exit 1
fi

log_info "Runner IP detected: $RUNNER_IP"

# Obtener server name desde Terraform si no se proporciona
if [ -z "$SERVER_NAME" ]; then
    if [ -f "infra/terraform/terraform.tfstate" ]; then
        log_info "Getting server name from Terraform..."
        cd infra/terraform
        SERVER_NAME=$(terraform output -raw postgresql_fqdn | cut -d'.' -f1)
        RESOURCE_GROUP=$(terraform output -raw resource_group_name)
        cd ../..
    fi
fi

if [ -z "$SERVER_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
    log_error "SERVER_NAME and RESOURCE_GROUP must be provided"
    log_error "Usage: RESOURCE_GROUP=rg-name SERVER_NAME=server-name ./add-ci-firewall-rule.sh"
    exit 1
fi

log_info "Adding firewall rule to PostgreSQL server..."
log_info "  Resource Group: $RESOURCE_GROUP"
log_info "  Server Name: $SERVER_NAME"
log_info "  IP Address: $RUNNER_IP"

# Añadir regla de firewall
az postgres flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$SERVER_NAME" \
    --rule-name "$RULE_NAME" \
    --start-ip-address "$RUNNER_IP" \
    --end-ip-address "$RUNNER_IP"

if [ $? -eq 0 ]; then
    log_info "✅ Firewall rule added successfully"
    echo ""
    echo "To remove this rule later, run:"
    echo "  az postgres flexible-server firewall-rule delete \\"
    echo "    --resource-group $RESOURCE_GROUP \\"
    echo "    --name $SERVER_NAME \\"
    echo "    --rule-name $RULE_NAME \\"
    echo "    --yes"
    echo ""
    echo "Or use: ./scripts/remove-ci-firewall-rule.sh"
else
    log_error "Failed to add firewall rule"
    exit 1
fi


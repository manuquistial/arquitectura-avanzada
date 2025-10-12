#!/bin/bash

##############################################################
# Remove Temporary Firewall Rule for CI/CD Runner
# Limpia la regla temporal después de migraciones
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
    log_error "Usage: RESOURCE_GROUP=rg-name SERVER_NAME=server-name ./remove-ci-firewall-rule.sh"
    exit 1
fi

log_info "Removing firewall rule from PostgreSQL server..."
log_info "  Resource Group: $RESOURCE_GROUP"
log_info "  Server Name: $SERVER_NAME"
log_info "  Rule Name: $RULE_NAME"

# Verificar si la regla existe
if az postgres flexible-server firewall-rule show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$SERVER_NAME" \
    --rule-name "$RULE_NAME" >/dev/null 2>&1; then
    
    # Eliminar regla de firewall
    az postgres flexible-server firewall-rule delete \
        --resource-group "$RESOURCE_GROUP" \
        --name "$SERVER_NAME" \
        --rule-name "$RULE_NAME" \
        --yes
    
    log_info "✅ Firewall rule removed successfully"
else
    log_warn "⚠️  Firewall rule '$RULE_NAME' not found, nothing to remove"
fi


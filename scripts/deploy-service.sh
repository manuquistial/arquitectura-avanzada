#!/bin/bash

# =============================================================================
# Deploy Single Service via Terraform
# =============================================================================
# Script para desplegar un servicio específico usando Terraform
# Uso: ./scripts/deploy-service.sh SERVICE_NAME [IMAGE_TAG]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Defaults
SERVICE_NAME=""
IMAGE_TAG="latest"
TERRAFORM_DIR="infra/terraform/layers/carpeta-ciudadana"

# Parse arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}❌ Service name is required${NC}"
    echo "Usage: $0 SERVICE_NAME"
    echo ""
    echo "Services: transfer, citizen, metadata, notification"
    echo ""
    echo "Note: Image tag is configured in Helm values.yaml (default: latest)"
    exit 1
fi

SERVICE_NAME=$1

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deploy Service: ${SERVICE_NAME}${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Service: ${SERVICE_NAME}${NC}"
echo -e "${YELLOW}Image Tag: latest (configured in Helm values.yaml)${NC}"
echo ""

# Validate service name
VALID_SERVICES=("transfer" "citizen" "metadata" "notification")
if [[ ! " ${VALID_SERVICES[@]} " =~ " ${SERVICE_NAME} " ]]; then
    echo -e "${RED}❌ Invalid service name: ${SERVICE_NAME}${NC}"
    echo -e "${YELLOW}Valid services: ${VALID_SERVICES[*]}${NC}"
    exit 1
fi

# Check if terraform directory exists
if [ ! -d "$TERRAFORM_DIR" ]; then
    echo -e "${RED}❌ Terraform directory not found: ${TERRAFORM_DIR}${NC}"
    exit 1
fi

cd "$TERRAFORM_DIR"

# Initialize terraform if needed
if [ ! -d ".terraform" ]; then
    echo -e "${CYAN}🔧 Initializing Terraform...${NC}"
    terraform init
fi

# Plan (no need for -var, everything is configured to use latest by default)
echo -e "${CYAN}📋 Running Terraform plan...${NC}"
if ! terraform plan -out="plan-${SERVICE_NAME}.out"; then
    echo -e "${RED}❌ Terraform plan failed${NC}"
    exit 1
fi

# Show plan summary
echo ""
echo -e "${YELLOW}Terraform plan completed. Review the plan above.${NC}"
read -p "Apply changes? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${YELLOW}Cancelled. Plan saved to plan-${SERVICE_NAME}.out${NC}"
    exit 0
fi

# Apply
echo -e "${CYAN}🚀 Applying Terraform changes...${NC}"
if terraform apply "plan-${SERVICE_NAME}.out"; then
    echo -e "${GREEN}✅ Deployment successful for ${SERVICE_NAME}${NC}"
else
    echo -e "${RED}❌ Deployment failed for ${SERVICE_NAME}${NC}"
    exit 1
fi

# Cleanup
rm -f "plan-${SERVICE_NAME}.out"

cd - > /dev/null

echo ""
echo -e "${GREEN}✅ Service ${SERVICE_NAME} deployed successfully${NC}"
echo -e "${YELLOW}Image tag: latest (configured in Helm values.yaml)${NC}"
echo -e "${YELLOW}Next: Verify the service is running${NC}"


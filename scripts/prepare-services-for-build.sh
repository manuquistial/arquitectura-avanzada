#!/bin/bash

# =============================================================================
# Prepare Services for Build - Generate poetry.lock
# =============================================================================
# Script para generar poetry.lock para servicios nuevos o modificados
# Uso: ./scripts/prepare-services-for-build.sh [service1] [service2] ...

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default: prepare all modified services
SERVICES_TO_PREPARE=("transfer" "citizen" "metadata" "notification")

# If services specified, use those
if [ $# -gt 0 ]; then
    SERVICES_TO_PREPARE=("$@")
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Prepare Services for Build${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Services to prepare: ${SERVICES_TO_PREPARE[*]}${NC}"
echo ""

# Function to prepare a service
prepare_service() {
    local service_name=$1
    local service_path="services/${service_name}"
    
    if [ ! -d "$service_path" ]; then
        echo -e "${RED}❌ Service directory not found: ${service_path}${NC}"
        return 1
    fi
    
    echo -e "${BLUE}📦 Preparing ${service_name}...${NC}"
    
    cd "$service_path"
    
    # Check if pyproject.toml exists
    if [ ! -f "pyproject.toml" ]; then
        echo -e "${RED}❌ pyproject.toml not found in ${service_path}${NC}"
        cd - > /dev/null
        return 1
    fi
    
    # Activate venv if exists
    if [ -d "venv" ]; then
        echo -e "${YELLOW}   Activating venv...${NC}"
        source venv/bin/activate
    else
        echo -e "${YELLOW}   Creating venv...${NC}"
        python3 -m venv venv
        source venv/bin/activate
    fi
    
    # Install Poetry if not installed
    if ! command -v poetry &> /dev/null; then
        echo -e "${YELLOW}   Installing Poetry...${NC}"
        pip install poetry==2.2.1
    fi
    
    # Install dependencies (this will generate/update poetry.lock)
    echo -e "${YELLOW}   Installing dependencies and generating poetry.lock...${NC}"
    poetry install --no-root
    
    # Verify poetry.lock was created
    if [ -f "poetry.lock" ]; then
        echo -e "${GREEN}✅ poetry.lock generated for ${service_name}${NC}"
    else
        echo -e "${RED}❌ poetry.lock was not generated for ${service_name}${NC}"
        cd - > /dev/null
        return 1
    fi
    
    cd - > /dev/null
    echo ""
}

# Prepare each service
for service in "${SERVICES_TO_PREPARE[@]}"; do
    if ! prepare_service "$service"; then
        echo -e "${RED}❌ Failed to prepare ${service}${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ All services prepared successfully${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "${YELLOW}  1. Verify poetry.lock files were generated${NC}"
echo -e "${YELLOW}  2. Run build-and-push.sh to build and push images${NC}"


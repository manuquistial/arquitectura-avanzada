#!/bin/bash
# Run all tests for Carpeta Ciudadana
# Usage: ./scripts/run-tests.sh [service_name]

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Running Carpeta Ciudadana Tests${NC}"
echo "======================================"

# If service specified, run only that service
if [ -n "$1" ]; then
    SERVICE=$1
    echo -e "${YELLOW}Testing service: ${SERVICE}${NC}"
    
    cd "services/${SERVICE}"
    
    if [ ! -d "tests" ]; then
        echo -e "${RED}❌ No tests directory found for ${SERVICE}${NC}"
        exit 1
    fi
    
    poetry run pytest tests/ \
        --cov=app \
        --cov-report=term-missing \
        --cov-report=html:coverage_html \
        --cov-fail-under=70 \
        -v
    
    echo -e "${GREEN}✅ Tests completed for ${SERVICE}${NC}"
    exit 0
fi

# Run all service tests
SERVICES=(
    "citizen"
    "ingestion"
    "metadata"
    "transfer"
    "signature"
    "sharing"
    "auth"
    "gateway"
    "mintic_client"
    "notification"
    "read_models"
    "transfer_worker"
)

FAILED_SERVICES=()
PASSED_SERVICES=()

for SERVICE in "${SERVICES[@]}"; do
    echo ""
    echo -e "${YELLOW}Testing: ${SERVICE}${NC}"
    echo "--------------------------------------"
    
    cd "/Users/manueljurado/arquitectura_avanzada/services/${SERVICE}"
    
    # Check if tests directory exists
    if [ ! -d "tests" ]; then
        echo -e "${YELLOW}⚠️  No tests directory for ${SERVICE}, skipping${NC}"
        continue
    fi
    
    # Run tests
    if poetry run pytest tests/ \
        --cov=app \
        --cov-report=term \
        --cov-fail-under=50 \
        -v --tb=short 2>&1 | tee "/tmp/test_${SERVICE}.log"; then
        echo -e "${GREEN}✅ ${SERVICE} tests passed${NC}"
        PASSED_SERVICES+=("$SERVICE")
    else
        echo -e "${RED}❌ ${SERVICE} tests failed${NC}"
        FAILED_SERVICES+=("$SERVICE")
    fi
    
    cd - > /dev/null
done

# Test common package
echo ""
echo -e "${YELLOW}Testing: common (carpeta_common)${NC}"
echo "--------------------------------------"

cd "services/common"

if poetry run pytest carpeta_common/tests/ \
    --cov=carpeta_common \
    --cov-report=term \
    --cov-fail-under=80 \
    -v --tb=short; then
    echo -e "${GREEN}✅ common tests passed${NC}"
    PASSED_SERVICES+=("common")
else
    echo -e "${RED}❌ common tests failed${NC}"
    FAILED_SERVICES+=("common")
fi

cd - > /dev/null

# Summary
echo ""
echo "======================================"
echo -e "${GREEN}📊 Test Summary${NC}"
echo "======================================"
echo -e "${GREEN}✅ Passed: ${#PASSED_SERVICES[@]}${NC}"
echo -e "${RED}❌ Failed: ${#FAILED_SERVICES[@]}${NC}"
echo ""

if [ ${#PASSED_SERVICES[@]} -gt 0 ]; then
    echo -e "${GREEN}Passed services:${NC}"
    for SERVICE in "${PASSED_SERVICES[@]}"; do
        echo "  ✅ $SERVICE"
    done
    echo ""
fi

if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    echo -e "${RED}Failed services:${NC}"
    for SERVICE in "${FAILED_SERVICES[@]}"; do
        echo "  ❌ $SERVICE"
    done
    echo ""
    exit 1
fi

echo -e "${GREEN}🎉 All tests passed!${NC}"
exit 0


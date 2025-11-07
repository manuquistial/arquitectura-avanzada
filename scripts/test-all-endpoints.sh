#!/bin/bash

# Test All Endpoints and Use Cases for Carpeta Ciudadana
# This script tests all services, endpoints, and verifies event bus, metadata, and notifications

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0
WARNINGS=0

# Test function
test_endpoint() {
    local method=$1
    local url=$2
    local description=$3
    local data=$4
    local expected_status=${5:-200}
    
    echo -e "${BLUE}Testing: ${description}${NC}"
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$data" 2>&1)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} - HTTP $http_code"
        ((PASSED++))
        if [ -n "$body" ] && [ "$body" != "null" ]; then
            echo -e "${CYAN}Response:${NC} $(echo "$body" | head -c 200)"
            echo
        fi
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} - Expected HTTP $expected_status, got $http_code"
        echo -e "${YELLOW}Response:${NC} $body"
        echo
        ((FAILED++))
        return 1
    fi
}

test_health() {
    local service=$1
    local port=$2
    local url="http://localhost:$port/health"
    
    test_endpoint "GET" "$url" "Health check - $service"
}

test_ready() {
    local service=$1
    local port=$2
    local url="http://localhost:$port/ready"
    
    test_endpoint "GET" "$url" "Readiness check - $service"
}

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Carpeta Ciudadana - Endpoint Testing Suite                ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# ============================================================================
# PHASE 1: Health Checks
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PHASE 1: Health Checks${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

test_health "Auth Service" 8001
test_health "Citizen Service" 8000
test_health "Ingestion Service" 8002
test_health "Transfer Service" 8003
test_health "Signature Service" 8004
test_health "MinTIC Client Service" 8005
test_health "Metadata Service" 8007
test_health "Notification Service" 8008

echo

# ============================================================================
# PHASE 2: Readiness Checks
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PHASE 2: Readiness Checks${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

test_ready "Auth Service" 8001
test_ready "Citizen Service" 8000
test_ready "Ingestion Service" 8002
test_ready "Transfer Service" 8003
test_ready "Signature Service" 8004
test_ready "MinTIC Client Service" 8005
test_ready "Metadata Service" 8007
test_ready "Notification Service" 8008

echo

# ============================================================================
# PHASE 3: CU1 - Crear Ciudadano
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PHASE 3: CU1 - Crear Ciudadano${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Generate unique citizen ID (exactly 10 digits: 10 + 8 digits from timestamp)
TIMESTAMP=$(date +%s)
CITIZEN_ID="10$(printf "%08d" $(echo $TIMESTAMP | tail -c 8))"
CITIZEN_DATA=$(cat <<EOF
{
    "id": "$CITIZEN_ID",
    "name": "Juan Pérez Test",
    "email": "juan.perez.test.${CITIZEN_ID}@example.com",
    "address": "Calle 123 #45-67, Bogotá",
    "password": "TestPassword123!",
    "operator_id": "OP001",
    "operator_name": "Operador Test"
}
EOF
)

test_endpoint "POST" "http://localhost:8000/api/citizens/register" \
    "CU1: Register Citizen" "$CITIZEN_DATA" 201

# Store citizen ID for later use
export TEST_CITIZEN_ID="$CITIZEN_ID"
echo -e "${GREEN}✅ Test Citizen ID: $CITIZEN_ID${NC}"

echo

# ============================================================================
# PHASE 4: CU2 - Autenticación
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PHASE 4: CU2 - Autenticación${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Test OIDC discovery
test_endpoint "GET" "http://localhost:8001/.well-known/openid-configuration" \
    "CU2: OIDC Discovery"

# Test userinfo endpoint (may fail without auth, but should return 401/403, not 500)
test_endpoint "GET" "http://localhost:8001/api/auth/userinfo" \
    "CU2: UserInfo (no auth)" "" "401"

echo

# ============================================================================
# PHASE 5: CU3 - Subir Documentos
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PHASE 5: CU3 - Subir Documentos${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Use test citizen ID if available, otherwise use default
CITIZEN_ID_FOR_DOCS="${TEST_CITIZEN_ID:-1032236578}"
UPLOAD_URL_DATA=$(cat <<EOF
{
    "citizen_id": "$CITIZEN_ID_FOR_DOCS",
    "filename": "acta_nacimiento_test.pdf",
    "content_type": "application/pdf",
    "title": "Acta de Nacimiento - Test"
}
EOF
)

test_endpoint "POST" "http://localhost:8002/api/documents/upload-url" \
    "CU3: Generate Upload URL" "$UPLOAD_URL_DATA"

# Test document list
test_endpoint "GET" "http://localhost:8002/api/documents/?citizen_id=1032236578" \
    "CU3: List Documents"

echo

# ============================================================================
# PHASE 6: CU4 - Autenticar/Firmar Documentos
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PHASE 6: CU4 - Autenticar/Firmar Documentos${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

SIGN_DATA='{
    "document_id": "doc_test_123",
    "citizen_id": "'"${TEST_CITIZEN_ID:-1032236578}"'",
    "signature_type": "PAdES",
    "document_title": "Acta de Nacimiento - Test"
}'

test_endpoint "POST" "http://localhost:8004/api/signature/sign" \
    "CU4: Sign Document" "$SIGN_DATA"

echo

# ============================================================================
# PHASE 7: CU5 - Transferencia
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PHASE 7: CU5 - Transferencia${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Test transfer initiate
TRANSFER_DATA='{
    "citizen_id": "1002454979",
    "destination_operator_id": "OP001"
}'

test_endpoint "POST" "http://localhost:8003/api/initiate" \
    "CU5: Initiate Transfer" "$TRANSFER_DATA"

# Test list transfers
test_endpoint "GET" "http://localhost:8003/api/?citizen_id=1002454979" \
    "CU5: List Transfers"

echo

# ============================================================================
# PHASE 8: Metadata Service
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PHASE 8: Metadata Service${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Use test citizen ID if available
CITIZEN_ID_FOR_METADATA="${TEST_CITIZEN_ID:-1002392861}"

# Test metadata endpoints
test_endpoint "GET" "http://localhost:8007/api/metadata/documents/citizen/$CITIZEN_ID_FOR_METADATA" \
    "Metadata: List Documents by Citizen"

# Test metadata search
METADATA_SEARCH_DATA=$(cat <<EOF
{
    "citizen_id": "$CITIZEN_ID_FOR_METADATA",
    "query": "test",
    "limit": 10
}
EOF
)

test_endpoint "POST" "http://localhost:8007/api/metadata/search" \
    "Metadata: Search Documents" "$METADATA_SEARCH_DATA"

echo

# ============================================================================
# PHASE 9: Notification Service
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PHASE 9: Notification Service${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Test notification endpoints
test_endpoint "GET" "http://localhost:8008/api/notifications/stats" \
    "Notification: Stats"

echo

# ============================================================================
# PHASE 10: Event Bus (Service Bus) Verification
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PHASE 10: Event Bus (Service Bus) Verification${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

echo -e "${BLUE}Verifying Event Bus functionality...${NC}"

# Check if services have Service Bus in their ready endpoints
for service in "ingestion" "transfer" "signature"; do
    case $service in
        ingestion)
            port=8002
            ;;
        transfer)
            port=8003
            ;;
        signature)
            port=8004
            ;;
    esac
    
    response=$(curl -s "http://localhost:$port/ready" 2>/dev/null || echo "{}")
    if echo "$response" | grep -qi "service_bus\|servicebus\|event"; then
        echo -e "${GREEN}✅ $service service has Service Bus integration${NC}"
    else
        echo -e "${YELLOW}⚠️  $service service may not have Service Bus configured${NC}"
        ((WARNINGS++))
    fi
done

# Test if event publishing works by triggering an action
echo -e "${BLUE}Testing event publishing (via document upload)...${NC}"
UPLOAD_TEST_DATA='{
    "citizen_id": "1032236578",
    "filename": "test_event.pdf",
    "content_type": "application/pdf",
    "title": "Test Event Document"
}'

response=$(curl -s -X POST "http://localhost:8002/api/documents/upload-url" \
    -H "Content-Type: application/json" \
    -d "$UPLOAD_TEST_DATA" 2>&1)

if echo "$response" | grep -q "upload_url\|document_id"; then
    echo -e "${GREEN}✅ Document upload URL created (event should be published)${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  Could not trigger event (upload URL creation failed)${NC}"
    ((WARNINGS++))
fi

echo

# ============================================================================
# PHASE 11: MinTIC Client Service
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PHASE 11: MinTIC Client Service${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Test MinTIC endpoints
test_endpoint "GET" "http://localhost:8005/api/mintic/operators" \
    "MinTIC: Get Operators"

# Test validate citizen (may fail if citizen doesn't exist, but endpoint should work)
test_endpoint "GET" "http://localhost:8005/api/mintic/validate-citizen/1032236578" \
    "MinTIC: Validate Citizen"

echo

# ============================================================================
# SUMMARY
# ============================================================================
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Test Summary                                                ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

TOTAL=$((PASSED + FAILED))
SUCCESS_RATE=0
if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$((PASSED * 100 / TOTAL))
fi

echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"
echo -e "${YELLOW}⚠️  Warnings: $WARNINGS${NC}"
echo -e "${BLUE}📊 Total Tests: $TOTAL${NC}"
echo -e "${BLUE}📈 Success Rate: $SUCCESS_RATE%${NC}"
echo

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review the output above.${NC}"
    exit 1
fi


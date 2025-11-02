#!/bin/bash

# Carpeta Ciudadana - Kubernetes Port Forwarding
# This script creates port forwarding tunnels to connect local frontend to deployed services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="carpeta-ciudadana"  # Adjust if your namespace is different
RELEASE_NAME="carpeta-ciudadana"  # Adjust if your Helm release name is different

echo -e "${BLUE}🔗 Setting up Port Forwarding for Carpeta Ciudadana Services${NC}"
echo

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed or not in PATH${NC}"
    echo -e "${YELLOW}💡 Install kubectl: https://kubernetes.io/docs/tasks/tools/install-kubectl/${NC}"
    exit 1
fi

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster${NC}"
    echo -e "${YELLOW}💡 Make sure your kubeconfig is configured correctly${NC}"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${RED}❌ Namespace '$NAMESPACE' not found${NC}"
    echo -e "${YELLOW}💡 Available namespaces:${NC}"
    kubectl get namespaces
    exit 1
fi

echo -e "${GREEN}✅ Connected to Kubernetes cluster${NC}"
echo -e "${GREEN}✅ Namespace '$NAMESPACE' found${NC}"

# Function to start port forwarding for a service
start_port_forward() {
    local service_name=$1
    local local_port=$2
    local service_port=$3
    local description=$4
    
    echo -e "${BLUE}🔗 Setting up port forwarding for $description...${NC}"
    
    # Check if service exists
    if ! kubectl get service "$service_name" -n "$NAMESPACE" &> /dev/null; then
        echo -e "${YELLOW}⚠️  Service '$service_name' not found in namespace '$NAMESPACE'${NC}"
        return 1
    fi
    
    # Check if port is already in use
    if lsof -Pi :$local_port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $local_port is already in use. Skipping $description${NC}"
        return 1
    fi
    
    # Start port forwarding in background
    kubectl port-forward -n "$NAMESPACE" "service/$service_name" "$local_port:$service_port" > /dev/null 2>&1 &
    local pid=$!
    
    # Wait a moment to check if port forwarding started successfully
    sleep 2
    if kill -0 $pid 2>/dev/null; then
        echo -e "${GREEN}✅ $description: http://localhost:$local_port${NC}"
        echo "$pid" >> /tmp/carpeta-port-forwards.pid
    else
        echo -e "${RED}❌ Failed to start port forwarding for $description${NC}"
        return 1
    fi
}

# Clean up any existing port forwards
echo -e "${BLUE}🧹 Cleaning up existing port forwards...${NC}"
if [ -f /tmp/carpeta-port-forwards.pid ]; then
    while read pid; do
        if kill -0 $pid 2>/dev/null; then
            kill $pid 2>/dev/null || true
        fi
    done < /tmp/carpeta-port-forwards.pid
    rm -f /tmp/carpeta-port-forwards.pid
fi

echo -e "${BLUE}🚀 Starting port forwarding for services...${NC}"

# Port forwarding configuration
# Format: service_name local_port service_port description
# Note: Frontend is excluded as it runs locally
services=(
    "$RELEASE_NAME-auth:8001:8000:Auth Service"
    "$RELEASE_NAME-citizen:8000:8000:Citizen Service"
    "$RELEASE_NAME-ingestion:8002:8000:Ingestion Service"
    "$RELEASE_NAME-transfer:8003:8000:Transfer Service"
    "$RELEASE_NAME-signature:8004:8000:Signature Service"
    "$RELEASE_NAME-mintic-client:8005:8000:MinTIC Client Service"
    "$RELEASE_NAME-transfer-worker:8006:8012:Transfer Worker Service"
)

# Start port forwarding for each service
for service_config in "${services[@]}"; do
    IFS=':' read -r service_name local_port service_port description <<< "$service_config"
    start_port_forward "$service_name" "$local_port" "$service_port" "$description"
done

echo
echo -e "${GREEN}🎉 Port forwarding setup completed!${NC}"
echo
echo -e "${BLUE}📋 Service URLs:${NC}"
echo -e "  🔐 Auth Service:      http://localhost:8001"
echo -e "  👤 Citizen Service:   http://localhost:8000"
echo -e "  📥 Ingestion Service: http://localhost:8002"
echo -e "  🔄 Transfer Service:  http://localhost:8003"
echo -e "  ✍️  Signature Service: http://localhost:8004"
echo -e "  🏛️  MinTIC Client:     http://localhost:8005"
echo -e "  ⚙️  Transfer Worker:   http://localhost:8006"
echo
echo -e "${YELLOW}💡 Now you can run your frontend locally:${NC}"
echo -e "  ./scripts/dev-frontend.sh"
echo
echo -e "${YELLOW}💡 To stop port forwarding, run:${NC}"
echo -e "  ./scripts/stop-port-forward.sh"
echo
echo -e "${BLUE}📝 Port forwarding PIDs saved to: /tmp/carpeta-port-forwards.pid${NC}"

#!/bin/bash

# Carpeta Ciudadana - Kubernetes Port Forwarding
# This script creates port forwarding tunnels to connect local frontend to deployed services

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

# Function to kill process on a port
kill_port_process() {
    local port=$1
    local pid=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        # Check if it's a kubectl port-forward process
        if ps -p "$pid" -o comm= 2>/dev/null | grep -q "kubectl\|port-forward"; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            return 0
        fi
    fi
    return 1
}

# Function to validate port forward is working
validate_port_forward() {
    local local_port=$1
    local description=$2
    local max_attempts=5
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        # Check if port is listening
        if lsof -Pi :$local_port -sTCP:LISTEN -t >/dev/null 2>&1; then
            # Try to connect to the port (health check)
            if curl -s -f -m 2 "http://localhost:$local_port/health" >/dev/null 2>&1 || \
               curl -s -f -m 2 "http://localhost:$local_port/" >/dev/null 2>&1 || \
               nc -z localhost $local_port 2>/dev/null; then
                return 0
            fi
        fi
        ((attempt++))
        sleep 1
    done
    return 1
}

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
    
    # Check if port is already in use and kill it if it's a kubectl port-forward
    if lsof -Pi :$local_port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $local_port is already in use. Attempting to free it...${NC}"
        if kill_port_process "$local_port"; then
            echo -e "${GREEN}✅ Freed port $local_port${NC}"
            sleep 1
        else
            echo -e "${YELLOW}⚠️  Port $local_port is in use by another process. Skipping $description${NC}"
            return 1
        fi
    fi
    
    # Start port forwarding in background
    kubectl port-forward -n "$NAMESPACE" "service/$service_name" "$local_port:$service_port" > /dev/null 2>&1 &
    local pid=$!
    
    # Wait a moment to check if port forwarding started successfully
    sleep 2
    
    # Check if process is still alive
    if ! kill -0 $pid 2>/dev/null; then
        echo -e "${RED}❌ Port forward process died immediately for $description${NC}"
        echo -e "${YELLOW}   This may indicate a connection issue with Kubernetes${NC}"
        return 1
    fi
    
    # Check if port is actually listening
    if ! lsof -Pi :$local_port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port forward process is running but port $local_port is not listening${NC}"
        echo -e "${YELLOW}   Waiting a bit longer...${NC}"
        sleep 3
        if ! lsof -Pi :$local_port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${RED}❌ Port $local_port is still not listening after retry${NC}"
            kill $pid 2>/dev/null || true
            return 1
        fi
    fi
    
    # Validate that the port forward is actually working
    if validate_port_forward "$local_port" "$description"; then
        echo -e "${GREEN}✅ $description: http://localhost:$local_port (validated)${NC}"
        echo "$pid" >> /tmp/carpeta-port-forwards.pid
        return 0
    else
        # Process is alive and port is listening, but validation failed
        # This might be OK if the service is still starting up
        echo -e "${YELLOW}⚠️  Port forward started but validation failed for $description${NC}"
        echo -e "${YELLOW}   Port $local_port is listening but service may not be ready yet${NC}"
        echo "$pid" >> /tmp/carpeta-port-forwards.pid
        return 0  # Still return success, port forward is running
    fi
}

# Clean up any existing port forwards
echo -e "${BLUE}🧹 Cleaning up existing port forwards...${NC}"

# Stop processes from PID file if it exists
if [ -f /tmp/carpeta-port-forwards.pid ]; then
    dead_pids=()
    while read pid; do
        if [ -n "$pid" ]; then
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            else
                # Track dead PIDs to remove from file
                dead_pids+=("$pid")
            fi
        fi
    done < /tmp/carpeta-port-forwards.pid
    
    # Remove dead PIDs from file if any
    if [ ${#dead_pids[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Found ${#dead_pids[@]} dead port forward process(es) in PID file${NC}"
        # Create new PID file with only alive processes (but we're removing it anyway)
    fi
    
    rm -f /tmp/carpeta-port-forwards.pid
fi

# Find and kill any remaining kubectl port-forward processes
pids=$(pgrep -f "kubectl.*port-forward.*carpeta-ciudadana" 2>/dev/null || true)
if [ -n "$pids" ]; then
    for pid in $pids; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
fi

# Also kill processes on the specific ports we'll use
ports=(8000 8001 8002 8003 8004 8005 8006 8007 8008)
for port in "${ports[@]}"; do
    kill_port_process "$port" > /dev/null 2>&1 || true
done

# Wait a moment for processes to terminate
sleep 1

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
    "$RELEASE_NAME-metadata:8007:8000:Metadata Service"
    "$RELEASE_NAME-notification:8008:8000:Notification Service"
    "$RELEASE_NAME-transfer-worker:8006:8012:Transfer Worker Service"
)

# Track successful and failed port forwards
successful_forwards=()
failed_forwards=()

# Start port forwarding for each service
for service_config in "${services[@]}"; do
    IFS=':' read -r service_name local_port service_port description <<< "$service_config"
    if start_port_forward "$service_name" "$local_port" "$service_port" "$description"; then
        successful_forwards+=("$description (port $local_port)")
    else
        failed_forwards+=("$description (port $local_port)")
    fi
done

echo
echo -e "${BLUE}🔍 Validating port forwards...${NC}"

# Validate all port forwards
validated_count=0
total_count=0

for service_config in "${services[@]}"; do
    IFS=':' read -r service_name local_port service_port description <<< "$service_config"
    total_count=$((total_count + 1))
    
    # Check if port is listening
    if lsof -Pi :$local_port -sTCP:LISTEN -t >/dev/null 2>&1; then
        # Try to validate connectivity
        if validate_port_forward "$local_port" "$description"; then
            validated_count=$((validated_count + 1))
        fi
    fi
done

echo
if [ $validated_count -eq $total_count ]; then
    echo -e "${GREEN}✅ All $validated_count port forwards validated successfully!${NC}"
elif [ $validated_count -gt 0 ]; then
    echo -e "${YELLOW}⚠️  $validated_count of $total_count port forwards validated${NC}"
    echo -e "${YELLOW}   Some ports may still be initializing...${NC}"
else
    echo -e "${RED}❌ No port forwards validated${NC}"
    echo -e "${YELLOW}   Port forwards may still be initializing. Wait a few seconds and try again.${NC}"
fi

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
echo -e "  📊 Metadata Service:   http://localhost:8007"
echo -e "  📧 Notification Service: http://localhost:8008"
echo -e "  ⚙️  Transfer Worker:   http://localhost:8006"
echo
if [ ${#failed_forwards[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Failed to start:${NC}"
    for failed in "${failed_forwards[@]}"; do
        echo -e "${YELLOW}   - $failed${NC}"
    done
    echo
fi
echo -e "${YELLOW}💡 Now you can run your frontend locally:${NC}"
echo -e "  ./scripts/dev-frontend.sh"
echo
echo -e "${YELLOW}💡 To stop port forwarding, run:${NC}"
echo -e "  ./scripts/stop-port-forward.sh"
echo
echo -e "${BLUE}📝 Port forwarding PIDs saved to: /tmp/carpeta-port-forwards.pid${NC}"

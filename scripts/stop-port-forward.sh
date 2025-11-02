#!/bin/bash

# Carpeta Ciudadana - Stop Port Forwarding
# This script stops all port forwarding tunnels

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Carpeta Ciudadana Port Forwarding${NC}"
echo

# Check if PID file exists
if [ ! -f /tmp/carpeta-port-forwards.pid ]; then
    echo -e "${YELLOW}⚠️  No port forwarding PIDs found${NC}"
    echo -e "${YELLOW}💡 Port forwarding may not be running${NC}"
    exit 0
fi

echo -e "${BLUE}🧹 Stopping port forwarding processes...${NC}"

# Stop all port forwarding processes
stopped_count=0
while read pid; do
    if kill -0 $pid 2>/dev/null; then
        kill $pid 2>/dev/null || true
        echo -e "${GREEN}✅ Stopped process $pid${NC}"
        ((stopped_count++))
    fi
done < /tmp/carpeta-port-forwards.pid

# Clean up PID file
rm -f /tmp/carpeta-port-forwards.pid

echo -e "${GREEN}✅ Stopped $stopped_count port forwarding processes${NC}"
echo -e "${GREEN}🎉 All port forwarding stopped successfully!${NC}"

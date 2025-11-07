#!/bin/bash

# Carpeta Ciudadana - Stop Port Forwarding
# This script stops all port forwarding tunnels

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Carpeta Ciudadana Port Forwarding${NC}"
echo

stopped_count=0
ports=(8000 8001 8002 8003 8004 8005 8006 8007 8008)

# Function to get process info
get_process_info() {
    local pid=$1
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        local cmd=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        local args=$(ps -p "$pid" -o args= 2>/dev/null | head -c 80 || echo "")
        echo "$cmd ($args)"
    fi
}

# Stop processes from PID file if it exists
if [ -f /tmp/carpeta-port-forwards.pid ]; then
    echo -e "${BLUE}🧹 Stopping port forwarding processes from PID file...${NC}"
    dead_pids=0
    while read pid; do
        if [ -n "$pid" ]; then
            if kill -0 "$pid" 2>/dev/null; then
                local info=$(get_process_info "$pid")
                kill "$pid" 2>/dev/null || true
                sleep 0.5
                # Verify it's actually stopped
                if kill -0 "$pid" 2>/dev/null; then
                    # Force kill if still running
                    kill -9 "$pid" 2>/dev/null || true
                    sleep 0.5
                fi
                if ! kill -0 "$pid" 2>/dev/null; then
                    echo -e "${GREEN}✅ Stopped process $pid${NC}"
                    ((stopped_count++))
                else
                    echo -e "${YELLOW}⚠️  Process $pid still running (may require manual kill)${NC}"
                fi
            else
                # Process is already dead
                ((dead_pids++))
            fi
        fi
    done < /tmp/carpeta-port-forwards.pid
    
    if [ $dead_pids -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Found $dead_pids dead process(es) in PID file (cleaning up)${NC}"
    fi
    
    rm -f /tmp/carpeta-port-forwards.pid
fi

# Find and kill any remaining kubectl port-forward processes
echo -e "${BLUE}🔍 Searching for remaining kubectl port-forward processes...${NC}"

# Find all kubectl port-forward processes related to carpeta-ciudadana
pids=$(pgrep -f "kubectl.*port-forward.*carpeta-ciudadana" 2>/dev/null || true)

if [ -n "$pids" ]; then
    for pid in $pids; do
        if kill -0 "$pid" 2>/dev/null; then
            local info=$(get_process_info "$pid")
            kill "$pid" 2>/dev/null || true
            sleep 0.5
            # Verify it's actually stopped
            if kill -0 "$pid" 2>/dev/null; then
                # Force kill if still running
                kill -9 "$pid" 2>/dev/null || true
                sleep 0.5
            fi
            if ! kill -0 "$pid" 2>/dev/null; then
                echo -e "${GREEN}✅ Stopped kubectl port-forward process $pid${NC}"
                ((stopped_count++))
            fi
        fi
    done
fi

# Also check for processes using the specific ports
echo -e "${BLUE}🔍 Checking for processes using port forwarding ports...${NC}"

for port in "${ports[@]}"; do
    # Find processes listening on these ports
    pids=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            # Check if it's a kubectl port-forward process
            local cmd=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")
            if echo "$cmd" | grep -q "kubectl"; then
                local args=$(ps -p "$pid" -o args= 2>/dev/null || echo "")
                if echo "$args" | grep -q "port-forward"; then
                    kill "$pid" 2>/dev/null || true
                    sleep 0.5
                    # Verify it's actually stopped
                    if kill -0 "$pid" 2>/dev/null; then
                        # Force kill if still running
                        kill -9 "$pid" 2>/dev/null || true
                        sleep 0.5
                    fi
                    if ! kill -0 "$pid" 2>/dev/null; then
                        echo -e "${GREEN}✅ Stopped process $pid using port $port${NC}"
                        ((stopped_count++))
                    fi
                fi
            fi
        done
    fi
done

# Final verification - check if any ports are still in use
echo
echo -e "${BLUE}🔍 Verifying all ports are free...${NC}"
still_in_use=0
for port in "${ports[@]}"; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        local cmd=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        if echo "$cmd" | grep -q "kubectl"; then
            echo -e "${YELLOW}⚠️  Port $port still in use by process $pid ($cmd)${NC}"
            ((still_in_use++))
        fi
    fi
done

echo
if [ $still_in_use -eq 0 ] && [ $stopped_count -gt 0 ]; then
    echo -e "${GREEN}✅ Stopped $stopped_count port forwarding process(es)${NC}"
    echo -e "${GREEN}✅ All ports are now free${NC}"
    echo -e "${GREEN}🎉 All port forwarding stopped successfully!${NC}"
elif [ $stopped_count -eq 0 ] && [ $still_in_use -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No port forwarding processes found${NC}"
    echo -e "${YELLOW}💡 Port forwarding may not be running${NC}"
elif [ $still_in_use -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Stopped $stopped_count process(es), but $still_in_use port(s) still in use${NC}"
    echo -e "${YELLOW}💡 You may need to manually kill the remaining processes${NC}"
else
    echo -e "${GREEN}✅ Stopped $stopped_count port forwarding process(es)${NC}"
fi

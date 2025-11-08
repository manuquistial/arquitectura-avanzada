#!/bin/bash

# =============================================================================
# Build and Push Services - Modified and New Services
# =============================================================================
# Script para construir y subir imágenes de servicios modificados y nuevos
# Uso: ./scripts/build-and-push-services.sh --username USERNAME [--services SERVICE1 SERVICE2]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default configuration
DOCKER_HUB_USERNAME=""
DOCKER_HUB_REPOSITORY="carpeta-ciudadana"
VERSION="latest"
NO_CACHE=false
PULL=true

# Services to build (default: modified and new services)
ALL_SERVICES=(
    "transfer"      # Modified (event consumers)
    "citizen"       # Modified (event publishing)
    "ingestion"     # Modified (consumers.py added, uses carpeta_common)
    "mintic_client" # Modified (uses carpeta_common.message_broker)
    "metadata"      # New
    "notification"  # New
)

SERVICES_TO_BUILD=("${ALL_SERVICES[@]}")

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--username)
            DOCKER_HUB_USERNAME="$2"
            shift 2
            ;;
        -r|--repository)
            DOCKER_HUB_REPOSITORY="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --no-pull)
            PULL=false
            shift
            ;;
        --services)
            shift
            SERVICES_TO_BUILD=()
            while [[ $# -gt 0 ]] && [[ $1 != -* ]]; do
                SERVICES_TO_BUILD+=("$1")
                shift
            done
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -u, --username USERNAME    Docker Hub username (required)"
            echo "  -r, --repository REPO       Docker Hub repository name (default: carpeta-ciudadana)"
            echo "  -v, --version VERSION       Image tag version (default: latest)"
            echo "  --no-cache                 Build without cache"
            echo "  --no-pull                  Don't pull base images"
            echo "  --services SERVICE...      Specific services to build (default: all)"
            echo "  -h, --help                 Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$DOCKER_HUB_USERNAME" ]; then
    echo -e "${RED}❌ Docker Hub username is required${NC}"
    echo -e "${YELLOW}Use -u or --username option${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Build and Push Services${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Docker Hub Username: ${DOCKER_HUB_USERNAME}${NC}"
echo -e "${YELLOW}Repository: ${DOCKER_HUB_REPOSITORY}${NC}"
echo -e "${YELLOW}Version: ${VERSION}${NC}"
echo -e "${YELLOW}No Cache: ${NO_CACHE}${NC}"
echo -e "${YELLOW}Pull Base Images: ${PULL}${NC}"
echo -e "${YELLOW}Services: ${SERVICES_TO_BUILD[*]}${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check if logged in to Docker Hub
if ! docker info 2>/dev/null | grep -qi "Username"; then
    if [ -n "$DOCKER_HUB_TOKEN" ] && [ -n "$DOCKER_HUB_USERNAME" ]; then
        echo -e "${CYAN}🔐 Attempting non-interactive Docker login...${NC}"
        if echo "$DOCKER_HUB_TOKEN" | docker login -u "$DOCKER_HUB_USERNAME" --password-stdin; then
            echo -e "${GREEN}✅ Docker login successful${NC}"
        else
            echo -e "${YELLOW}⚠️  Docker login failed. Continuing; push may fail if not authenticated.${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Docker Hub login not detected. Continuing; push may fail if not authenticated.${NC}"
        echo -e "${YELLOW}   Tip: set DOCKER_HUB_TOKEN env or run 'docker login' first${NC}"
    fi
fi

# Function to build and push image
build_and_push() {
    local service_name=$1
    local service_path="services/${service_name}"
    local image_tag="${DOCKER_HUB_USERNAME}/${DOCKER_HUB_REPOSITORY}-${service_name}:${VERSION}"
    
    if [ ! -d "$service_path" ]; then
        echo -e "${RED}❌ Service directory not found: ${service_path}${NC}"
        return 1
    fi
    
    echo -e "${BLUE}🔨 Building ${service_name}...${NC}"
    echo -e "${YELLOW}   Path: ${service_path}${NC}"
    echo -e "${YELLOW}   Image: ${image_tag}${NC}"
    
    # Build context is project root (for COPY services/common)
    local build_context="."
    local dockerfile_path="${service_path}/Dockerfile"
    
    echo -e "${YELLOW}   Context: ${build_context}${NC}"
    echo -e "${YELLOW}   Dockerfile: ${dockerfile_path}${NC}"
    
    # Build command
    local build_cmd="docker build"
    
    if [ "$NO_CACHE" = true ]; then
        build_cmd="$build_cmd --no-cache"
    fi
    
    if [ "$PULL" = true ]; then
        build_cmd="$build_cmd --pull"
    fi
    
    build_cmd="$build_cmd -f ${dockerfile_path} -t ${image_tag} ${build_context}"
    
    # Build
    if eval "$build_cmd"; then
        echo -e "${GREEN}✅ Build successful for ${service_name}${NC}"
        
        # Push to Docker Hub (using latest tag)
        echo -e "${BLUE}📤 Pushing ${service_name} to Docker Hub...${NC}"
        if docker push "${image_tag}"; then
            echo -e "${GREEN}✅ Push successful for ${service_name}${NC}"
        else
            echo -e "${RED}❌ Push failed for ${service_name}${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Build failed for ${service_name}${NC}"
        return 1
    fi
    
    echo ""
}

# Build each service
for service in "${SERVICES_TO_BUILD[@]}"; do
    if ! build_and_push "$service"; then
        echo -e "${RED}❌ Failed to build ${service}${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ All services built and pushed successfully${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
for service in "${SERVICES_TO_BUILD[@]}"; do
    echo -e "${YELLOW}  - ${DOCKER_HUB_USERNAME}/${DOCKER_HUB_REPOSITORY}-${service}:${VERSION}${NC}"
done


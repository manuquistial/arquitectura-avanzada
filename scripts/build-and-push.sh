#!/bin/bash

# =============================================================================
# Build and Push Docker Images (Configurable)
# =============================================================================
# Script para construir y subir todas las imágenes de Docker
# Soporta configuración desde archivo .env y opciones de línea de comandos

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
ENVIRONMENT="production"
NO_CACHE=false
PULL=true
CLEANUP=false
SERVICES_ONLY=false
FRONTEND_ONLY=false

# Services to build
ALL_SERVICES=(
    "auth"
    "citizen"
    "ingestion"
    "metadata"
    "mintic_client"
    "read_models"
    "signature"
    "transfer"
)

# Function to show usage
show_usage() {
    echo -e "${BLUE}Usage: $0 [OPTIONS]${NC}"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo "  -u, --username USERNAME    Docker Hub username (required)"
    echo "  -r, --repository REPO      Docker Hub repository name (default: carpeta-ciudadana)"
    echo "  -v, --version VERSION      Image version tag (default: latest)"
    echo "  -e, --environment ENV      Environment (default: production)"
    echo "  -n, --no-cache            Build without cache"
    echo "  --no-pull                 Don't pull base images before building"
    echo "  --cleanup                 Remove local images after push"
    echo "  --services-only           Build only services (skip frontend)"
    echo "  --frontend-only           Build only frontend (skip services)"
    echo "  --config FILE             Load configuration from file"
    echo "  -h, --help                Show this help message"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 --username myuser --no-cache"
    echo "  $0 --username myuser --version v1.0.0 --cleanup"
    echo "  $0 --username myuser --services-only"
    echo "  $0 --config docker-config.env"
}

# Function to load config from file
load_config() {
    local config_file=$1
    if [ -f "$config_file" ]; then
        echo -e "${CYAN}📄 Loading configuration from $config_file${NC}"
        source "$config_file"
    else
        echo -e "${RED}❌ Configuration file not found: $config_file${NC}"
        exit 1
    fi
}

# Parse command line arguments
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
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -n|--no-cache)
            NO_CACHE=true
            shift
            ;;
        --no-pull)
            PULL=false
            shift
            ;;
        --cleanup)
            CLEANUP=true
            shift
            ;;
        --services-only)
            SERVICES_ONLY=true
            shift
            ;;
        --frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        --config)
            load_config "$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$DOCKER_HUB_USERNAME" ]; then
    echo -e "${RED}❌ Docker Hub username is required${NC}"
    echo -e "${YELLOW}Use -u or --username option, or set DOCKER_HUB_USERNAME in config file${NC}"
    exit 1
fi

# Check for conflicting options
if [ "$SERVICES_ONLY" = true ] && [ "$FRONTEND_ONLY" = true ]; then
    echo -e "${RED}❌ Cannot specify both --services-only and --frontend-only${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Build and Push Docker Images${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Docker Hub Username: ${DOCKER_HUB_USERNAME}${NC}"
echo -e "${YELLOW}Repository: ${DOCKER_HUB_REPOSITORY}${NC}"
echo -e "${YELLOW}Version: ${VERSION}${NC}"
echo -e "${YELLOW}Environment: ${ENVIRONMENT}${NC}"
echo -e "${YELLOW}No Cache: ${NO_CACHE}${NC}"
echo -e "${YELLOW}Pull Base Images: ${PULL}${NC}"
echo -e "${YELLOW}Cleanup After Push: ${CLEANUP}${NC}"
echo -e "${YELLOW}Services Only: ${SERVICES_ONLY}${NC}"
echo -e "${YELLOW}Frontend Only: ${FRONTEND_ONLY}${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check if logged in to Docker Hub
if ! docker info | grep -q "Username"; then
    echo -e "${YELLOW}⚠️  Not logged in to Docker Hub. Please login first:${NC}"
    echo -e "${YELLOW}   docker login${NC}"
    read -p "Press Enter to continue after logging in, or Ctrl+C to exit..."
fi

# Function to build and push image
build_and_push() {
    local service_name=$1
    local service_path=$2
    local image_tag="${DOCKER_HUB_USERNAME}/${DOCKER_HUB_REPOSITORY}-${service_name}:${VERSION}"
    
    echo -e "${BLUE}🔨 Building ${service_name}...${NC}"
    echo -e "${YELLOW}   Path: ${service_path}${NC}"
    echo -e "${YELLOW}   Image: ${image_tag}${NC}"
    
    # Determine build context and dockerfile path
    local build_context="."
    local dockerfile_path="${service_path}/Dockerfile"
    
    # Special handling for frontend
    if [ "$service_name" = "frontend" ]; then
        build_context="."
        dockerfile_path="apps/frontend/Dockerfile"
        echo -e "${YELLOW}   Context: ${build_context}${NC}"
        echo -e "${YELLOW}   Dockerfile: ${dockerfile_path}${NC}"
    else
        # For services, use project root as context so COPY commands work
        build_context="."
        dockerfile_path="${service_path}/Dockerfile"
        echo -e "${YELLOW}   Context: ${build_context}${NC}"
        echo -e "${YELLOW}   Dockerfile: ${dockerfile_path}${NC}"
    fi
    
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
        
        # Push to Docker Hub
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

# Build Frontend (if not services-only)
if [ "$SERVICES_ONLY" != true ]; then
    echo -e "${CYAN}📱 Building Frontend...${NC}"
    build_and_push "frontend" "apps/frontend"
fi

# Build Services (if not frontend-only)
if [ "$FRONTEND_ONLY" != true ]; then
    echo -e "${CYAN}🔧 Building Services...${NC}"
    for service in "${ALL_SERVICES[@]}"; do
        service_path="services/${service}"
        if [ -d "${service_path}" ]; then
            build_and_push "${service}" "${service_path}"
        else
            echo -e "${RED}❌ Service directory not found: ${service_path}${NC}"
        fi
    done
fi

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Build and Push Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}📋 Summary:${NC}"

if [ "$SERVICES_ONLY" != true ]; then
    echo -e "${YELLOW}   Frontend: ${DOCKER_HUB_USERNAME}/${DOCKER_HUB_REPOSITORY}-frontend:${VERSION}${NC}"
fi

if [ "$FRONTEND_ONLY" != true ]; then
    for service in "${ALL_SERVICES[@]}"; do
        echo -e "${YELLOW}   ${service}: ${DOCKER_HUB_USERNAME}/${DOCKER_HUB_REPOSITORY}-${service}:${VERSION}${NC}"
    done
fi

echo ""
echo -e "${GREEN}🎉 All images have been built and pushed successfully!${NC}"
echo -e "${YELLOW}💡 You can now deploy these images to your Kubernetes cluster.${NC}"
echo ""

# Cleanup if requested
if [ "$CLEANUP" = true ]; then
    echo -e "${BLUE}🧹 Cleaning up local images...${NC}"
    
    # Remove frontend image
    if [ "$SERVICES_ONLY" != true ]; then
        docker rmi "${DOCKER_HUB_USERNAME}/${DOCKER_HUB_REPOSITORY}-frontend:${VERSION}" 2>/dev/null || true
    fi
    
    # Remove service images
    if [ "$FRONTEND_ONLY" != true ]; then
        for service in "${ALL_SERVICES[@]}"; do
            docker rmi "${DOCKER_HUB_USERNAME}/${DOCKER_HUB_REPOSITORY}-${service}:${VERSION}" 2>/dev/null || true
        done
    fi
    
    echo -e "${GREEN}✅ Local images cleaned up!${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🎯 Script completed successfully!${NC}"
echo -e "${BLUE}========================================${NC}"

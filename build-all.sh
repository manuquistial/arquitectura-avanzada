#!/bin/bash

echo "🏗️  Building all Docker images locally..."
echo ""

DOCKER_USERNAME=${DOCKER_USERNAME:-"manuelquistial"}
TAG=${TAG:-"local"}

# Build frontend
echo "📦 Building frontend..."
docker build -t ${DOCKER_USERNAME}/carpeta-frontend:${TAG} \
  -f apps/frontend/Dockerfile apps/frontend || exit 1
echo "✅ Frontend built"
echo ""

# Build backend services
SERVICES=("gateway" "citizen" "ingestion" "metadata" "transfer" "mintic_client")

for SERVICE in "${SERVICES[@]}"; do
    echo "📦 Building ${SERVICE}..."
    docker build -t ${DOCKER_USERNAME}/carpeta-${SERVICE}:${TAG} \
      -f services/${SERVICE}/Dockerfile services/${SERVICE} || exit 1
    echo "✅ ${SERVICE} built"
    echo ""
done

echo "════════════════════════════════════════════════════════════════"
echo "✅ All images built successfully!"
echo ""
echo "Images created:"
docker images | grep "carpeta-"
echo ""
echo "To run with Docker Compose:"
echo "  export TAG=local"
echo "  docker-compose --profile app up -d"
echo ""
echo "Or use Makefile:"
echo "  make dev-docker"
echo "════════════════════════════════════════════════════════════════"


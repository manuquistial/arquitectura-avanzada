#!/bin/bash
# Script para construir, subir y desplegar el servicio ingestion
# Uso: ./scripts/build-and-deploy-ingestion.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DOCKER_USERNAME="manuelquistial"
IMAGE_NAME="carpeta-ingestion"
IMAGE_TAG="latest"
FULL_IMAGE="${DOCKER_USERNAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo -e "${BLUE}=== Construyendo imagen del servicio ingestion ===${NC}"
docker build -f services/ingestion/Dockerfile -t "${FULL_IMAGE}" .

echo ""
echo -e "${BLUE}=== Subiendo imagen a Docker Hub ===${NC}"
docker push "${FULL_IMAGE}"

echo ""
echo -e "${BLUE}=== Actualizando deployment en Kubernetes ===${NC}"
kubectl rollout restart deployment/carpeta-ciudadana-ingestion -n carpeta-ciudadana

echo ""
echo -e "${YELLOW}=== Esperando que el deployment esté listo ===${NC}"
kubectl rollout status deployment/carpeta-ciudadana-ingestion -n carpeta-ciudadana --timeout=300s

echo ""
echo -e "${GREEN}✅ Imagen construida, subida y desplegada exitosamente${NC}"
echo -e "${BLUE}Imagen: ${FULL_IMAGE}${NC}"


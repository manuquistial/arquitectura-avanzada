#!/bin/bash

##############################################################
# Script de Actualización Automática
# Actualiza scripts y configuraciones para incluir todos
# los 12 servicios
##############################################################

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

echo "════════════════════════════════════════════════════════"
echo "  ACTUALIZACIÓN AUTOMÁTICA DE SCRIPTS"
echo "  Carpeta Ciudadana - 12 Servicios"
echo "════════════════════════════════════════════════════════"
echo ""

##############################################################
# PASO 1: Actualizar start-services.sh
##############################################################

log_step "1/5 - Actualizando start-services.sh..."

# Backup
cp start-services.sh start-services.sh.backup
log_info "Backup creado: start-services.sh.backup"

# Actualizar lista de servicios
sed -i.tmp 's/SERVICES=("gateway" "citizen" "ingestion" "metadata" "transfer" "mintic_client")/SERVICES=("gateway" "citizen" "ingestion" "metadata" "transfer" "mintic_client" "signature" "sharing" "notification" "read_models" "auth")/' start-services.sh

rm -f start-services.sh.tmp
log_info "✅ start-services.sh actualizado con 11 servicios"

##############################################################
# PASO 2: Actualizar build-all.sh
##############################################################

log_step "2/5 - Actualizando build-all.sh..."

# Backup
cp build-all.sh build-all.sh.backup
log_info "Backup creado: build-all.sh.backup"

# Actualizar lista de servicios
sed -i.tmp 's/SERVICES=("gateway" "citizen" "ingestion" "metadata" "transfer" "mintic_client")/SERVICES=("gateway" "citizen" "ingestion" "metadata" "transfer" "mintic_client" "signature" "sharing" "notification" "read_models" "auth")/' build-all.sh

rm -f build-all.sh.tmp
log_info "✅ build-all.sh actualizado con 11 servicios"

##############################################################
# PASO 3: Actualizar docker-compose.yml
##############################################################

log_step "3/5 - Actualizando docker-compose.yml..."

# Backup
cp docker-compose.yml docker-compose.yml.backup
log_info "Backup creado: docker-compose.yml.backup"

# Añadir servicios faltantes al final del archivo
cat >> docker-compose.yml << 'EOF'

  auth:
    profiles: ["app"]
    image: ${DOCKER_USERNAME:-manuelquistial}/carpeta-auth:${TAG:-local}
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/carpeta_ciudadana
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - postgres
      - redis

  notification:
    profiles: ["app"]
    image: ${DOCKER_USERNAME:-manuelquistial}/carpeta-notification:${TAG:-local}
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/carpeta_ciudadana
      - SERVICE_BUS_ENABLED=false
    depends_on:
      - postgres

  read-models:
    profiles: ["app"]
    image: ${DOCKER_USERNAME:-manuelquistial}/carpeta-read_models:${TAG:-local}
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/carpeta_ciudadana
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - postgres
      - redis
EOF

log_info "✅ docker-compose.yml actualizado con 3 servicios adicionales"

##############################################################
# PASO 4: Actualizar Chart.yaml
##############################################################

log_step "4/5 - Actualizando Chart.yaml..."

# Backup
cp deploy/helm/carpeta-ciudadana/Chart.yaml deploy/helm/carpeta-ciudadana/Chart.yaml.backup
log_info "Backup creado: Chart.yaml.backup"

# Corregir descripción
sed -i.tmp 's/Carpeta Ciudadana operator on AWS with microservices/Carpeta Ciudadana operator on Azure with microservices/' deploy/helm/carpeta-ciudadana/Chart.yaml

rm -f deploy/helm/carpeta-ciudadana/Chart.yaml.tmp
log_info "✅ Chart.yaml actualizado (AWS → Azure)"

##############################################################
# PASO 5: Actualizar values.yaml (limpiar AWS config)
##############################################################

log_step "5/5 - Limpiando configuraciones obsoletas en values.yaml..."

# Backup
cp deploy/helm/carpeta-ciudadana/values.yaml deploy/helm/carpeta-ciudadana/values.yaml.backup
log_info "Backup creado: values.yaml.backup"

# Comentar secciones de AWS
python3 << 'PYTHON_SCRIPT'
import re

with open('deploy/helm/carpeta-ciudadana/values.yaml', 'r') as f:
    content = f.read()

# Encontrar y comentar sección de AWS config
aws_section = re.search(r'(config:\n  database:.*?topicArn: .*?\n)', content, re.DOTALL)

if aws_section:
    aws_text = aws_section.group(1)
    commented = '\n'.join(['# ' + line for line in aws_text.split('\n')])
    content = content.replace(aws_text, f'# OBSOLETE - AWS Configuration (migrated to Azure)\n{commented}')

# Añadir sección auth si no existe
if 'auth:' not in content:
    auth_config = '''
# Auth Service (OIDC Provider)
auth:
  enabled: true
  replicaCount: 2
  image:
    repository: carpeta-auth
    tag: latest
  service:
    type: ClusterIP
    port: 8000
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"
    limits:
      memory: "256Mi"
      cpu: "500m"
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
'''
    # Insertar antes de la sección postgresql
    content = content.replace('# PostgreSQL Configuration', f'{auth_config}\n# PostgreSQL Configuration')

with open('deploy/helm/carpeta-ciudadana/values.yaml', 'w') as f:
    f.write(content)

print("✅ values.yaml actualizado")
PYTHON_SCRIPT

##############################################################
# RESUMEN
##############################################################

echo ""
log_step "═══════════════════════════════════════════════════════"
log_info "🎉 ACTUALIZACIÓN COMPLETADA"
echo ""
log_info "Archivos actualizados:"
echo "  ✅ start-services.sh (11 servicios)"
echo "  ✅ build-all.sh (11 servicios)"
echo "  ✅ docker-compose.yml (3 servicios añadidos)"
echo "  ✅ Chart.yaml (descripción corregida)"
echo "  ✅ values.yaml (limpieza AWS, auth añadido)"
echo ""
log_info "Backups creados:"
echo "  📦 *.backup"
echo ""
log_warn "PRÓXIMOS PASOS:"
echo "  1. Revisar los cambios: git diff"
echo "  2. Crear archivos main.py para: auth, notification, read_models"
echo "  3. Crear Dockerfiles para: auth, notification, read_models"
echo "  4. Crear Helm templates para: frontend, sharing, notification, auth"
echo "  5. Actualizar .github/workflows/ci.yml (build-and-push matrix)"
echo "  6. Ejecutar tests: ./start-services.sh"
echo ""
log_info "Ver ANALISIS_COMPLETO.md y TEMPLATES_IMPLEMENTACION.md para detalles"
log_step "═══════════════════════════════════════════════════════"
echo ""


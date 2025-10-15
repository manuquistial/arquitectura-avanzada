# Configuración Manual Completa - Carpeta Ciudadana

## 🎯 **Objetivo**

Este documento consolida **todas las configuraciones manuales** necesarias para el despliegue local y producción que **NO están cubiertas** por Terraform o Helm.

---

## 📋 **Índice**

1. [Configuración de Ambientes](#configuración-de-ambientes)
2. [Desarrollo Local](#desarrollo-local)
3. [Despliegue a Producción](#despliegue-a-producción)
4. [Configuraciones Específicas](#configuraciones-específicas)
5. [Scripts de Utilidad](#scripts-de-utilidad)
6. [Troubleshooting](#troubleshooting)

---

## 🔧 **Configuración de Ambientes**

### **Cambio de Ambiente**

```bash
# Para desarrollo local
./scripts/setup-environment.sh dev

# Para producción
./scripts/setup-environment.sh prod
```

### **Variables de Entorno por Ambiente**

#### **Desarrollo Local (.env.development)**
```bash
NODE_ENV=development
NEXTAUTH_SECRET=dev-secret-key-for-local-development-only
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_OPERATOR_ID=dev-operator
NEXT_PUBLIC_OPERATOR_NAME=Development Operator
AZURE_AD_B2C_TENANT_ID=
AZURE_AD_B2C_CLIENT_ID=
AZURE_AD_B2C_CLIENT_SECRET=
AZURE_AD_B2C_PRIMARY_USER_FLOW=B2C_1_signupsignin1
```

#### **Producción (.env.production)**
```bash
NODE_ENV=production
NEXTAUTH_SECRET=carpeta-ciudadana-production-secret-2024-secure-key
NEXTAUTH_URL=https://carpetaciudadana.gov.co
NEXT_PUBLIC_API_URL=https://api.carpetaciudadana.gov.co
NEXT_PUBLIC_OPERATOR_ID=carpeta-ciudadana-operator
NEXT_PUBLIC_OPERATOR_NAME=Carpeta Ciudadana Operator
AZURE_AD_B2C_TENANT_ID=
AZURE_AD_B2C_CLIENT_ID=
AZURE_AD_B2C_CLIENT_SECRET=
AZURE_AD_B2C_PRIMARY_USER_FLOW=B2C_1_signupsignin1
```

---

## 🚀 **Desarrollo Local**

### **1. Prerequisitos**

```bash
# Instalar dependencias del sistema
# macOS
brew install node@22 python@3.11 docker

# Ubuntu/Debian
sudo apt update
sudo apt install nodejs python3.11 python3.11-venv docker.io
```

### **2. Configuración Inicial (Una sola vez)**

```bash
# 1. Configurar ambiente de desarrollo
./scripts/setup-environment.sh dev

# 2. Instalar dependencias del frontend
cd apps/frontend
npm install
cd ../..

# 3. Configurar Python para servicios
# Los scripts automáticamente crean venv en cada servicio
```

### **3. Iniciar Servicios Locales**

```bash
# Opción 1: Script automatizado (recomendado)
./start-services.sh

# Opción 2: Manual paso a paso
# 1. Iniciar infraestructura
docker-compose up -d

# 2. Iniciar frontend
cd apps/frontend
npm run dev &

# 3. Iniciar servicios Python (cada uno en terminal separada)
cd services/gateway && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### **4. Verificar Servicios**

```bash
# Verificar que todos los servicios estén corriendo
curl http://localhost:3000  # Frontend
curl http://localhost:8000  # Gateway
curl http://localhost:8001  # Citizen
curl http://localhost:8002  # Ingestion
# ... etc para todos los servicios

# Ver logs
tail -f /tmp/frontend.log
tail -f /tmp/gateway.log
# ... etc para cada servicio
```

### **5. Detener Servicios**

```bash
# Detener todos los servicios
./stop-services.sh

# O detener infraestructura
docker-compose down
```

---

## 🌐 **Despliegue a Producción**

### **1. Configuración Inicial (Una sola vez)**

#### **A. Configurar Azure CLI**
```bash
# Instalar Azure CLI
# macOS
brew install azure-cli

# Ubuntu/Debian
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login
az account set --subscription "tu-subscription-id"
```

#### **B. Configurar Backend de Terraform**
```bash
# Ejecutar script de configuración del backend
./scripts/setup-terraform-backend.sh
```

#### **C. Configurar Terraform**
```bash
cd infra/terraform

# Copiar archivo de configuración
cp terraform.tfvars.example terraform.tfvars

# Editar terraform.tfvars con tus valores
nano terraform.tfvars
```

**Valores requeridos en terraform.tfvars:**
```hcl
# Configuración básica
location = "northcentralus"
environment = "production"

# Nombres únicos (cambiar por tus valores)
resource_group_name = "carpeta-ciudadana-prod-rg"
aks_cluster_name = "carpeta-ciudadana-prod"
storage_account_name = "carpetaciudadanaprod"
postgresql_server_name = "carpeta-ciudadana-prod-psql"

# Credenciales de base de datos
db_admin_username = "psqladmin"
db_admin_password = "tu-password-seguro"

# Configuración de OpenSearch
opensearch_username = "admin"
opensearch_password = "tu-password-opensearch-seguro"

# Configuración de Let's Encrypt
letsencrypt_email = "tu-email@dominio.com"
```

#### **D. Inicializar Terraform**
```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

### **2. Configurar Ambiente de Producción**

```bash
# Configurar ambiente de producción
./scripts/setup-environment.sh prod
```

### **3. Desplegar Infraestructura y Secrets**

```bash
# Terraform crea automáticamente todos los secrets de Kubernetes
# No es necesario ejecutar scripts manuales
```

### **4. Construir y Desplegar Imágenes**

```bash
# Construir todas las imágenes
./build-all.sh

# O usar Terraform para desplegar (recomendado)
cd infra/terraform
terraform apply
```

### **5. Verificar Despliegue**

```bash
# Obtener credenciales de AKS
az aks get-credentials --resource-group carpeta-ciudadana-prod-rg --name carpeta-ciudadana-prod

# Verificar pods
kubectl get pods -n carpeta-ciudadana-prod

# Verificar servicios
kubectl get services -n carpeta-ciudadana-prod

# Verificar ingress
kubectl get ingress -n carpeta-ciudadana-prod
```

---

## ⚙️ **Configuraciones Específicas**

### **1. Configuración de DNS (Producción)**

```bash
# Obtener IP del LoadBalancer
kubectl get service nginx-ingress-ingress-nginx-controller -n ingress-nginx

# Configurar registros DNS
# A record: carpetaciudadana.gov.co -> IP_DEL_LOADBALANCER
# A record: api.carpetaciudadana.gov.co -> IP_DEL_LOADBALANCER
```

### **2. Configuración de Certificados SSL**

```bash
# Los certificados se manejan automáticamente con cert-manager
# Verificar ClusterIssuers
kubectl get clusterissuers

# Verificar certificados
kubectl get certificates -n carpeta-ciudadana-prod
```

### **3. Configuración de Azure AD B2C (Opcional)**

```bash
# 1. Crear tenant de Azure AD B2C
# 2. Configurar User Flow
# 3. Registrar aplicación
# 4. Actualizar variables de entorno en .env.production
```

### **4. Configuración de Monitoring**

```bash
# Los dashboards de Grafana se crean automáticamente
# Acceder a Grafana
kubectl port-forward svc/grafana 3000:80 -n monitoring

# Acceder a Prometheus
kubectl port-forward svc/prometheus-server 9090:80 -n monitoring
```

---

## 🛠️ **Scripts de Utilidad**

### **Scripts de Desarrollo**
```bash
# Iniciar servicios locales
./start-services.sh

# Detener servicios locales
./stop-services.sh

# Construir imágenes Docker
./build-all.sh

# Configurar ambiente
./scripts/setup-environment.sh [dev|prod]
```

### **Scripts de Infraestructura**
```bash
# Configurar backend de Terraform
./scripts/setup-terraform-backend.sh

# Nota: Los secrets de Kubernetes se crean automáticamente con Terraform
# No es necesario ejecutar scripts manuales para crear secrets
```

### **Scripts de Testing**
```bash
# Ejecutar todos los tests
./scripts/run-tests.sh

# Ejecutar tests de un servicio específico
./scripts/run-tests.sh gateway

# Escaneo de seguridad (requiere Docker)
./tests/security/run-zap-scan.sh [target_url]
```

### **Scripts de Backup**
```bash
# Backup de base de datos
./scripts/backup/backup-postgres.sh

# Restaurar desde backup
./scripts/backup/restore-postgres.sh backup_file.sql.gz
```

---

## 🔍 **Troubleshooting**

### **Problemas Comunes**

#### **1. Servicios no inician localmente**
```bash
# Verificar puertos disponibles
lsof -i :3000
lsof -i :8000

# Verificar logs
tail -f /tmp/frontend.log
tail -f /tmp/gateway.log

# Reiniciar servicios
./stop-services.sh
./start-services.sh
```

#### **2. Errores de conexión a base de datos**
```bash
# Verificar que PostgreSQL esté corriendo
docker ps | grep postgres

# Verificar conexión
docker exec -it postgres psql -U postgres -d carpeta_ciudadana

# Reiniciar base de datos
docker-compose restart postgres
```

#### **3. Problemas de despliegue en AKS**
```bash
# Verificar estado del cluster
az aks show --resource-group carpeta-ciudadana-prod-rg --name carpeta-ciudadana-prod

# Verificar pods
kubectl get pods -n carpeta-ciudadana-prod

# Ver logs de pods fallidos
kubectl logs -f deployment/carpeta-ciudadana-gateway -n carpeta-ciudadana-prod

# Verificar eventos
kubectl get events -n carpeta-ciudadana-prod --sort-by='.lastTimestamp'
```

#### **4. Problemas de secrets**
```bash
# Verificar secrets existentes
kubectl get secrets -n carpeta-ciudadana-prod

# Recrear secrets
./scripts/create-k8s-secrets.sh carpeta-ciudadana-prod

# Verificar contenido de secret
kubectl get secret carpeta-ciudadana-database -n carpeta-ciudadana-prod -o yaml
```

#### **5. Problemas de DNS/Ingress**
```bash
# Verificar ingress
kubectl get ingress -n carpeta-ciudadana-prod

# Verificar servicios de ingress
kubectl get svc -n ingress-nginx

# Probar conectividad
curl -H "Host: carpetaciudadana.gov.co" http://IP_DEL_LOADBALANCER
```

### **Comandos de Diagnóstico**

```bash
# Estado general del sistema
kubectl get all -n carpeta-ciudadana-prod

# Verificar recursos
kubectl top nodes
kubectl top pods -n carpeta-ciudadana-prod

# Verificar logs de sistema
kubectl logs -f deployment/carpeta-ciudadana-gateway -n carpeta-ciudadana-prod

# Describir recursos problemáticos
kubectl describe pod NOMBRE_DEL_POD -n carpeta-ciudadana-prod
```

---

## 📋 **Checklist de Despliegue**

### **Desarrollo Local**
- [ ] Configurar ambiente: `./scripts/setup-environment.sh dev`
- [ ] Instalar dependencias: `cd apps/frontend && npm install`
- [ ] Iniciar infraestructura: `docker-compose up -d`
- [ ] Iniciar servicios: `./start-services.sh`
- [ ] Verificar servicios: `curl http://localhost:3000`

### **Producción**
- [ ] Configurar Azure CLI: `az login`
- [ ] Configurar backend Terraform: `./scripts/setup-terraform-backend.sh`
- [ ] Configurar terraform.tfvars
- [ ] Desplegar infraestructura: `terraform apply`
- [ ] Configurar ambiente: `./scripts/setup-environment.sh prod`
- [ ] Secrets creados automáticamente por Terraform
- [ ] Construir imágenes: `./build-all.sh`
- [ ] Desplegar aplicación: `terraform apply`
- [ ] Configurar DNS
- [ ] Verificar despliegue: `kubectl get pods`

---

## ✅ **Configuración Manual Completa**

**¡Todas las configuraciones manuales documentadas! 🎉**

Este documento consolida todas las configuraciones que deben hacerse manualmente y no están cubiertas por Terraform o Helm, proporcionando una guía completa para desarrollo local y despliegue a producción.

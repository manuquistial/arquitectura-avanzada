# 🚀 Deployment Guide - Carpeta Ciudadana

**Guía Completa de Despliegue Automatizado**

**Versión**: 1.0.0  
**Fecha**: 2025-10-13  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Resumen](#resumen)
2. [Prerequisitos](#prerequisitos)
3. [Configuración GitHub Secrets](#configuración-github-secrets)
4. [Deployment Automático](#deployment-automático)
5. [Deployment Manual](#deployment-manual)
6. [Verificación](#verificación)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Resumen

### Pregunta Clave: ¿Con solo hacer push se despliega todo automáticamente?

**Respuesta**: **CASI, pero necesitas configurar GitHub Secrets primero (una sola vez)**

### Proceso Completo

```
┌─────────────────────────────────────────────────────────┐
│  PASO 1: Configuración Inicial (UNA SOLA VEZ)           │
│  - Crear Service Principal en Azure                     │
│  - Configurar GitHub Secrets (15 secrets)               │
│  - Configurar Azure AD B2C                              │
│  ⏱️ Tiempo: 30-60 minutos                               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  PASO 2: Push a master (AUTOMÁTICO)                     │
│  - git push origin master                               │
│  - GitHub Actions SE DISPARA AUTOMÁTICAMENTE            │
│  ⏱️ Tiempo: 0 segundos (tu parte)                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  PASO 3: Pipeline Automático (SIN INTERVENCIÓN)        │
│  ✅ 1. Tests (Unit, E2E)                                │
│  ✅ 2. Security Scan (Trivy, Gitleaks, etc.)           │
│  ✅ 3. Build Images (13 servicios)                      │
│  ✅ 4. Push to Docker Hub                               │
│  ✅ 5. Terraform Apply (Infraestructura)                │
│  ✅ 6. Helm Deploy (Aplicación)                         │
│  ✅ 7. Database Migrations (8 jobs)                     │
│  ✅ 8. Verification (Health checks)                     │
│  ⏱️ Tiempo: 25-35 minutos (automático)                  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  RESULTADO: Sistema Desplegado en Azure ✅              │
│  - 13 servicios corriendo en AKS                        │
│  - Base de datos migrada                                │
│  - URLs públicas disponibles                            │
│  - Listo para usar                                      │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Prerequisitos

### 1. Cuenta Azure

```bash
# Verificar que tienes acceso
az login
az account show
```

**Opciones**:
- ✅ Azure for Students ($100 créditos gratis)
- ✅ Suscripción personal
- ✅ Cuenta corporativa

**Costo Estimado**:
- Desarrollo: ~$35/mes
- Producción: ~$100/mes

---

### 2. Herramientas Locales (Opcional)

Solo necesarias si quieres deployment manual:

```bash
# Azure CLI
az --version  # >= 2.50

# Terraform
terraform --version  # >= 1.6

# kubectl
kubectl version --client  # >= 1.27

# Helm
helm version  # >= 3.13

# Docker
docker --version  # >= 24.0
```

---

### 3. Repositorio GitHub

```bash
# Fork el repo o usar tu copia
git clone https://github.com/manuquistial/arquitectura-avanzada.git
cd arquitectura-avanzada
```

---

## 🔑 Configuración GitHub Secrets

**⚠️ PASO CRÍTICO: Debes configurar estos secrets UNA SOLA VEZ**

### Secrets Requeridos (15)

GitHub → Repo → Settings → Secrets and variables → Actions → New repository secret

| Secret | Descripción | Cómo Obtener | Crítico |
|--------|-------------|--------------|---------|
| **AZURE_CREDENTIALS** | Service Principal JSON | Ver [Azure Setup](#azure-setup) | ✅ SÍ |
| **AZURE_CLIENT_ID** | Azure SP Client ID | Del Service Principal | ✅ SÍ |
| **AZURE_TENANT_ID** | Azure Tenant ID | Del Service Principal | ✅ SÍ |
| **AZURE_SUBSCRIPTION_ID** | Subscription ID | `az account show` | ✅ SÍ |
| **DOCKERHUB_USERNAME** | Docker Hub username | Tu username | ✅ SÍ |
| **DOCKERHUB_TOKEN** | Docker Hub access token | Docker Hub → Settings | ✅ SÍ |
| **DB_ADMIN_USERNAME** | PostgreSQL admin user | Tu elección (ej: `pgadmin`) | ✅ SÍ |
| **DB_ADMIN_PASSWORD** | PostgreSQL password | Generado seguro | ✅ SÍ |
| **REDIS_PASSWORD** | Redis password | Generado seguro | ✅ SÍ |
| **OPENSEARCH_PASSWORD** | OpenSearch password | Generado seguro | ✅ SÍ |
| **LETSENCRYPT_EMAIL** | Email para certs | Tu email | ✅ SÍ |
| **SMTP_HOST** | SMTP server | ej: `smtp.gmail.com` | ⚠️ Opcional |
| **SMTP_USER** | SMTP username | Tu email | ⚠️ Opcional |
| **SMTP_PASSWORD** | SMTP password | App password | ⚠️ Opcional |
| **DOMAIN_NAME** | Dominio (opcional) | ej: `myapp.com` | ⚠️ Opcional |

---

### Azure Setup (Service Principal)

**Paso 1: Crear Service Principal**

```bash
# Login a Azure
az login

# Ver tu subscription ID
az account show --query id -o tsv
# Output: aaaabbbb-cccc-dddd-eeee-ffff00001111

# Crear Service Principal con permisos de Contributor
az ad sp create-for-rbac \
  --name "carpeta-ciudadana-sp" \
  --role contributor \
  --scopes /subscriptions/SUBSCRIPTION_ID \
  --sdk-auth

# Output (GUARDAR TODO ESTO):
{
  "clientId": "12345678-1234-1234-1234-123456789012",
  "clientSecret": "abcdefghijklmnopqrstuvwxyz123456",
  "subscriptionId": "aaaabbbb-cccc-dddd-eeee-ffff00001111",
  "tenantId": "11111111-2222-3333-4444-555555555555",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

**Paso 2: Configurar GitHub Secrets**

```bash
# En GitHub UI → Settings → Secrets → New repository secret

# 1. AZURE_CREDENTIALS (pegar TODO el JSON output anterior)
# 2. AZURE_CLIENT_ID (usar el clientId del JSON)
# 3. AZURE_TENANT_ID (usar el tenantId del JSON)
# 4. AZURE_SUBSCRIPTION_ID (usar el subscriptionId del JSON)
```

---

### Docker Hub Setup

**Paso 1: Crear Access Token**

```bash
# 1. Ir a https://hub.docker.com/
# 2. Login
# 3. Account Settings → Security → New Access Token
# 4. Name: "GitHub Actions"
# 5. Permissions: Read & Write
# 6. Generate token → COPIAR (solo se muestra una vez)
```

**Paso 2: Configurar en GitHub**

```bash
# GitHub Secrets:
# DOCKERHUB_USERNAME: tu_username
# DOCKERHUB_TOKEN: el token generado
```

---

### Database & Services Passwords

**Generar passwords seguros**:

```bash
# Linux/Mac
openssl rand -base64 32

# O usar generador online:
# https://passwordsgenerator.net/
```

**Configurar en GitHub**:
- `DB_ADMIN_PASSWORD`: Password PostgreSQL (min 8 chars, alfanumérico)
- `REDIS_PASSWORD`: Password Redis
- `OPENSEARCH_PASSWORD`: Password OpenSearch

---

### SMTP Setup (Opcional - Para Notificaciones)

**Opción 1: Gmail**

```bash
# 1. Gmail → Settings → Security → 2-Step Verification
# 2. App Passwords → Generate password
# 3. Copiar password de 16 caracteres

# GitHub Secrets:
SMTP_HOST: smtp.gmail.com
SMTP_PORT: 587
SMTP_USER: tu_email@gmail.com
SMTP_PASSWORD: el app password
SMTP_FROM: tu_email@gmail.com
```

**Opción 2: SendGrid**

```bash
# 1. Crear cuenta en SendGrid
# 2. Settings → API Keys → Create API Key
# 3. Copiar API key

# GitHub Secrets:
SMTP_HOST: smtp.sendgrid.net
SMTP_PORT: 587
SMTP_USER: apikey
SMTP_PASSWORD: tu_api_key
SMTP_FROM: noreply@tudominio.com
```

**Opción 3: Skip (Sin notificaciones)**

```bash
# Dejar vacíos, el sistema funcionará sin email
SMTP_HOST: (vacío)
SMTP_USER: (vacío)
SMTP_PASSWORD: (vacío)
```

---

## 🚀 Deployment Automático

### Opción 1: Push a Master (Recomendado)

**¡CERO CONFIGURACIÓN ADICIONAL!** Una vez configurados los secrets:

```bash
# 1. Hacer cambios
git add .
git commit -m "feat: Mi nuevo feature"

# 2. Push a master
git push origin master

# 3. ¡YA ESTÁ! GitHub Actions hace TODO automáticamente 🎉
```

**Qué hace GitHub Actions automáticamente**:

```
✅ 1. Frontend Test (2 min)
   - Lint (ESLint)
   - Type check (TypeScript)
   - Unit tests (Jest)

✅ 2. Backend Test (5 min) - Matrix 12 servicios
   - Lint (Flake8)
   - Type check (mypy)
   - Unit tests (Pytest)

✅ 3. Build Images (8 min) - 13 imágenes
   - Docker build (multi-stage)
   - Tag: latest + SHA
   - Push to Docker Hub

✅ 4. Security Scan (3 min)
   - Trivy (container vulnerabilities)
   - Gitleaks (secrets)
   - CodeQL (code analysis)

✅ 5. Terraform Apply (5 min)
   - Crear/actualizar infraestructura Azure:
     - AKS cluster (multi-AZ, 3 nodepools)
     - PostgreSQL Flexible Server
     - Redis Cache
     - Service Bus
     - Blob Storage
     - Key Vault
     - KEDA
     - NetworkPolicies
     - etc.

✅ 6. Platform Install (3 min)
   - cert-manager (Let's Encrypt)
   - Nginx Ingress
   - Prometheus/Grafana
   - Loki/Promtail

✅ 7. Create Secrets (1 min)
   - Kubernetes secrets from GitHub Secrets
   - Database URLs
   - Service Bus connections
   - SMTP credentials
   - etc.

✅ 8. Helm Deploy (5 min)
   - Deploy 13 servicios
   - ConfigMaps
   - Services
   - Ingress
   - HPA
   - PDB
   - NetworkPolicies

✅ 9. Database Migrations (3 min) - 8 jobs paralelos
   - citizen-migrate
   - ingestion-migrate
   - metadata-migrate
   - transfer-migrate
   - signature-migrate
   - sharing-migrate
   - notification-migrate
   - read-models-migrate

✅ 10. Verification (1 min)
    - Health checks
    - Pod status
    - Service availability

⏱️ TIEMPO TOTAL: 25-35 minutos (TODO AUTOMÁTICO)
```

**Resultado**:
```bash
# GitHub Actions te dará:
Frontend URL: http://XX.XX.XX.XX
API URL: http://XX.XX.XX.XX/api

# Pods corriendo en AKS:
gateway-xxx         1/1     Running
citizen-xxx         1/1     Running
ingestion-xxx       1/1     Running
... (13 servicios)
```

---

### Opción 2: Manual Trigger (Workflow Dispatch)

Si quieres disparar el deployment manualmente:

```bash
# GitHub UI:
# Actions → CI/CD Pipeline → Run workflow → Select branch → Run

# O por CLI:
gh workflow run ci.yml --ref master
```

---

### Workflows Disponibles

El proyecto tiene **5 workflows automatizados**:

| Workflow | Trigger | Propósito | Duración |
|----------|---------|-----------|----------|
| **ci.yml** | Push/PR a master | Build, Test, Deploy | 25-35 min |
| **test.yml** | Push/PR | Solo unit tests | 5 min |
| **e2e-tests.yml** | Push/PR, Manual | E2E con Playwright | 15-20 min |
| **load-tests.yml** | Schedule (nightly), Manual | Load testing k6/Locust | 30-60 min |
| **security-scan.yml** | Weekly, Push, Manual | Security scanning | 15-20 min |

**Workflows que despliegan**: Solo `ci.yml`

---

## 🔐 Configuración GitHub Secrets

### Lista Completa de Secrets Necesarios

#### ✅ Críticos (Necesarios para deployment)

**Azure (4 secrets)**:

1. **`AZURE_CREDENTIALS`** - Service Principal JSON completo
   ```json
   {
     "clientId": "...",
     "clientSecret": "...",
     "subscriptionId": "...",
     "tenantId": "...",
     ...
   }
   ```
   **Cómo obtener**: Ver [Azure Setup](#azure-setup) arriba

2. **`AZURE_CLIENT_ID`** - Del Service Principal
   ```
   12345678-1234-1234-1234-123456789012
   ```

3. **`AZURE_TENANT_ID`** - Del Service Principal
   ```
   11111111-2222-3333-4444-555555555555
   ```

4. **`AZURE_SUBSCRIPTION_ID`** - Tu subscription
   ```bash
   az account show --query id -o tsv
   ```

**Docker Hub (2 secrets)**:

5. **`DOCKERHUB_USERNAME`** - Tu username
   ```
   manuquistial
   ```

6. **`DOCKERHUB_TOKEN`** - Access token
   ```
   dckr_pat_abcdefghijklmnopqrstuvwxyz
   ```

**Databases (3 secrets)**:

7. **`DB_ADMIN_USERNAME`** - PostgreSQL admin
   ```
   pgadmin
   ```

8. **`DB_ADMIN_PASSWORD`** - PostgreSQL password
   ```bash
   # Generar:
   openssl rand -base64 32
   ```

9. **`REDIS_PASSWORD`** - Redis password
   ```bash
   openssl rand -base64 32
   ```

**Services (2 secrets)**:

10. **`OPENSEARCH_PASSWORD`** - OpenSearch password
    ```bash
    openssl rand -base64 32
    ```

11. **`LETSENCRYPT_EMAIL`** - Email para certificados SSL
    ```
    tu_email@ejemplo.com
    ```

---

#### ⚠️ Opcionales (Sistema funciona sin ellos)

**Email/SMS (4 secrets)** - Para notificaciones:

12. **`SMTP_HOST`** - Servidor SMTP
    ```
    smtp.gmail.com
    ```

13. **`SMTP_USER`** - Usuario SMTP
    ```
    tu_email@gmail.com
    ```

14. **`SMTP_PASSWORD`** - Password SMTP
    ```
    abcdefghijklmnop
    ```

15. **`SMTP_FROM`** - Email remitente
    ```
    noreply@carpeta-ciudadana.com
    ```

**DNS (1 secret)** - Para dominio custom:

16. **`DOMAIN_NAME`** - Tu dominio
    ```
    carpeta-ciudadana.com
    ```

---

### Comando Rápido para Configurar Secrets

```bash
# Usando GitHub CLI (gh)
gh auth login

# Configurar secrets uno por uno
gh secret set AZURE_CREDENTIALS < azure-credentials.json
gh secret set AZURE_CLIENT_ID --body "12345678-1234-..."
gh secret set AZURE_TENANT_ID --body "11111111-2222-..."
gh secret set AZURE_SUBSCRIPTION_ID --body "aaaabbbb-cccc-..."
gh secret set DOCKERHUB_USERNAME --body "manuquistial"
gh secret set DOCKERHUB_TOKEN --body "dckr_pat_..."
gh secret set DB_ADMIN_USERNAME --body "pgadmin"
gh secret set DB_ADMIN_PASSWORD --body "$(openssl rand -base64 32)"
gh secret set REDIS_PASSWORD --body "$(openssl rand -base64 32)"
gh secret set OPENSEARCH_PASSWORD --body "$(openssl rand -base64 32)"
gh secret set LETSENCRYPT_EMAIL --body "tu_email@ejemplo.com"

# Opcionales
gh secret set SMTP_HOST --body "smtp.gmail.com"
gh secret set SMTP_USER --body "tu_email@gmail.com"
gh secret set SMTP_PASSWORD --body "tu_app_password"
gh secret set SMTP_FROM --body "noreply@ejemplo.com"

echo "✅ Secrets configurados!"
```

---

## 🎬 Deployment Automático (Después de Secrets)

### Flujo Automático

**Una vez configurados los secrets, el deployment es 100% automático**:

```bash
# 1. Haces cualquier cambio
echo "// nuevo feature" >> apps/frontend/src/app/page.tsx

# 2. Commit
git add .
git commit -m "feat: nuevo feature"

# 3. Push a master
git push origin master

# ¡FIN! No haces nada más 🎉
```

**GitHub Actions automáticamente**:
1. ✅ Corre tests
2. ✅ Escanea seguridad
3. ✅ Build imágenes Docker
4. ✅ Push a Docker Hub
5. ✅ **Crea infraestructura con Terraform** (si no existe)
6. ✅ **Despliega aplicación con Helm**
7. ✅ **Corre migraciones de BD**
8. ✅ Verifica que todo funcione

**Tiempo Total**: 25-35 minutos (cero intervención tuya)

---

### Monitorear el Deployment

**Opción 1: GitHub UI**

```bash
# 1. Ir a GitHub → Actions tab
# 2. Ver el workflow "CI/CD Pipeline" corriendo en tiempo real
# 3. Ver logs de cada step
# 4. Al finalizar, ver summary con URLs
```

**Opción 2: GitHub CLI**

```bash
# Ver workflows corriendo
gh run list

# Ver detalles de un run
gh run view

# Ver logs en tiempo real
gh run watch
```

---

### Qué Pasa en Cada Push

**Push a `master`**:
```
✅ CI/CD Pipeline (ci.yml) SE EJECUTA AUTOMÁTICAMENTE
   - Build + Test + Deploy
   - 25-35 minutos
   - Despliega a Azure

✅ Security Scan (security-scan.yml) SE EJECUTA
   - Trivy, Gitleaks, CodeQL
   - 15-20 minutos
   - No despliega, solo escanea
```

**Push a `develop` o feature branch**:
```
✅ Tests (ci.yml) SE EJECUTAN
   - Build + Test
   - 10-15 minutos
   - NO despliega (solo en master)

✅ Security Scan SE EJECUTA
   - Escaneo completo
   - NO despliega
```

**Pull Request**:
```
✅ Tests SE EJECUTAN
✅ Security Scan SE EJECUTA
✅ Comment con resultados en PR
❌ NO despliega (solo cuando se merge a master)
```

---

## 🛠️ Deployment Manual (Alternativa)

Si prefieres **NO usar GitHub Actions** o quieres deployment local:

### Prerequisito: Tener herramientas instaladas

```bash
# Verificar
az --version
terraform --version
kubectl version
helm version
docker --version
```

### Paso a Paso Manual

```bash
# 1. Login a Azure
az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# 2. Configurar Terraform
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars

# Editar terraform.tfvars:
# - azure_region
# - db_admin_username
# - db_admin_password
# - opensearch_password
# - letsencrypt_email
# etc.

# 3. Deploy infraestructura
terraform init
terraform plan
terraform apply  # Confirmar con 'yes'
# ⏱️ 10-15 minutos

# 4. Configurar kubectl
az aks get-credentials \
  --resource-group carpeta-rg \
  --name carpeta-aks

# 5. Build imágenes Docker
cd ../..
docker-compose build

# O usar script:
./scripts/build-all.sh

# 6. Push imágenes a Docker Hub
docker login
./scripts/push-all.sh
# ⏱️ 5-10 minutos

# 7. Crear Kubernetes secrets
cd deploy/helm

# Opción A: Script automatizado
./scripts/create-k8s-secrets.sh

# Opción B: Manual
kubectl create namespace carpeta-ciudadana

kubectl create secret generic db-secrets \
  --from-literal=DATABASE_URL="postgresql://..." \
  --namespace carpeta-ciudadana

kubectl create secret generic sb-conn \
  --from-literal=SERVICEBUS_CONNECTION_STRING="..." \
  --namespace carpeta-ciudadana

# ... (más secrets)

# 8. Deploy con Helm
helm upgrade --install carpeta-ciudadana ./carpeta-ciudadana \
  --namespace carpeta-ciudadana \
  --set global.environment=production \
  --set frontend.image.tag=latest \
  --set gateway.image.tag=latest \
  --set citizen.image.tag=latest \
  # ... (todos los servicios)
  --wait \
  --timeout 15m
# ⏱️ 5-10 minutos

# 9. Verificar deployment
kubectl get pods -n carpeta-ciudadana
kubectl get svc -n carpeta-ciudadana
kubectl get ingress -n carpeta-ciudadana
```

**Tiempo Total Manual**: 45-60 minutos

---

### Comando Automatizado (Make)

**Alternativa más rápida**:

```bash
# Deploy full stack (automatizado)
make deploy-full-stack

# O paso a paso:
make deploy-infra        # Terraform
make build-images        # Docker build
make push-images         # Docker push
make create-secrets      # K8s secrets
make deploy-helm-prod    # Helm deploy
```

---

## ✅ Verificación Post-Deployment

### 1. Verificar Pods

```bash
kubectl get pods -n carpeta-ciudadana

# Todos deberían estar Running:
NAME                          READY   STATUS    RESTARTS   AGE
gateway-xxx                   1/1     Running   0          5m
citizen-xxx                   1/1     Running   0          5m
ingestion-xxx                 1/1     Running   0          5m
frontend-xxx                  1/1     Running   0          5m
...
```

### 2. Verificar Services

```bash
kubectl get svc -n carpeta-ciudadana

# Deberían tener ClusterIP o LoadBalancer
```

### 3. Verificar Ingress

```bash
kubectl get ingress -n carpeta-ciudadana

# Ver la IP pública
INGRESS_IP=$(kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Frontend: http://$INGRESS_IP"
echo "API: http://$INGRESS_IP/api"
```

### 4. Test Health Endpoints

```bash
# Frontend
curl http://$INGRESS_IP/

# Gateway
curl http://$INGRESS_IP/api/health

# Todos los servicios
for port in 8000 8001 8002 8003 8004 8005 8006 8007 8008 8010 8011; do
  kubectl port-forward svc/$(kubectl get svc -n carpeta-ciudadana -o name | grep -E "gateway|citizen|ingestion" | head -1 | cut -d'/' -f2) $port:$port -n carpeta-ciudadana &
  sleep 2
  curl http://localhost:$port/health || echo "Service on $port not responding"
  pkill -f "port-forward.*$port"
done
```

### 5. Verificar Migrations

```bash
# Ver jobs de migración
kubectl get jobs -n carpeta-ciudadana | grep migrate

# Deberían estar Completed (1/1)
NAME                        COMPLETIONS   DURATION   AGE
citizen-migrate-xxx         1/1           45s        5m
ingestion-migrate-xxx       1/1           52s        5m
...
```

---

## 🔧 Troubleshooting

### Issue: GitHub Actions Falla "Azure Login Failed"

**Causa**: `AZURE_CREDENTIALS` mal configurado

**Solución**:
```bash
# 1. Re-crear Service Principal
az ad sp create-for-rbac \
  --name "carpeta-ciudadana-sp" \
  --role contributor \
  --scopes /subscriptions/SUBSCRIPTION_ID \
  --sdk-auth

# 2. Copiar TODO el output JSON
# 3. Actualizar AZURE_CREDENTIALS en GitHub Secrets
```

---

### Issue: "Docker Push Failed - Unauthorized"

**Causa**: `DOCKERHUB_TOKEN` mal configurado

**Solución**:
```bash
# 1. Docker Hub → Account Settings → Security
# 2. Delete old token
# 3. Create new token (Read & Write)
# 4. Update DOCKERHUB_TOKEN en GitHub
```

---

### Issue: "Terraform State Locked"

**Causa**: Terraform run anterior no terminó

**Solución**:
```bash
# Opción 1: Esperar 15 minutos (timeout automático)

# Opción 2: Force unlock (si estás seguro)
cd infra/terraform
terraform force-unlock LOCK_ID
```

---

### Issue: "Pods in CrashLoopBackOff"

**Causa**: Secrets no configurados correctamente

**Solución**:
```bash
# Ver logs
kubectl logs gateway-xxx -n carpeta-ciudadana

# Verificar secrets existen
kubectl get secrets -n carpeta-ciudadana

# Verificar secret tiene los keys correctos
kubectl describe secret db-secrets -n carpeta-ciudadana
```

---

## 📊 Qué se Despliega Automáticamente

### Infraestructura (Terraform)
- ✅ Azure Resource Group
- ✅ Virtual Network + Subnets
- ✅ AKS Cluster (multi-AZ, 3 nodepools)
- ✅ PostgreSQL Flexible Server
- ✅ Azure Cache for Redis
- ✅ Azure Service Bus
- ✅ Azure Blob Storage
- ✅ Azure Key Vault
- ✅ KEDA (autoscaling)
- ✅ Network Security Groups
- ✅ Managed Identities

### Plataforma (Helm via GitHub Actions)
- ✅ cert-manager (Let's Encrypt)
- ✅ Nginx Ingress Controller
- ✅ Prometheus + Grafana
- ✅ Loki + Promtail
- ✅ OpenSearch (via Helm template)

### Aplicación (Helm Chart)
- ✅ **13 Deployments** (12 backend + 1 frontend)
- ✅ **13 Services** (networking)
- ✅ **1 Ingress** (routing)
- ✅ **8 Migration Jobs** (database)
- ✅ **1 CronJob** (purge unsigned docs)
- ✅ **13 HPA** (autoscaling)
- ✅ **12 PDB** (high availability)
- ✅ **6 NetworkPolicies** (security)
- ✅ **1 ScaledObject** (KEDA - transfer_worker)
- ✅ **Multiple ConfigMaps** (configuration)
- ✅ **Multiple Secrets** (sensitive data)

**Total Recursos Kubernetes**: 80+

---

## ⏱️ Timeline de Deployment Automático

```
00:00 - Push a master
00:01 - GitHub Actions detecta push
00:02 - Comienzan tests (frontend + backend matrix)
00:07 - Tests completan ✅
00:08 - Security scan inicia
00:11 - Security completa ✅
00:12 - Build images inicia (matrix 13 servicios)
00:20 - Build completa ✅
00:21 - Push to Docker Hub
00:23 - Push completa ✅
00:24 - Terraform Apply inicia
00:29 - Infraestructura creada ✅
00:30 - Platform components install
00:33 - Platform ready ✅
00:34 - Create K8s secrets
00:35 - Secrets created ✅
00:36 - Helm deploy inicia
00:41 - Helm deployment completo ✅
00:42 - Database migrations (8 jobs parallel)
00:45 - Migrations completas ✅
00:46 - Verification
00:47 - ✅ DEPLOYMENT COMPLETO

⏱️ TOTAL: ~35 minutos (TODO AUTOMÁTICO)
```

---

## 🎯 Resumen: ¿Qué Necesitas Hacer?

### Primera Vez (Setup - 30-60 min)

```bash
# 1. Configurar Azure Service Principal (5 min)
az ad sp create-for-rbac --name "carpeta-sp" --role contributor --sdk-auth

# 2. Configurar Docker Hub token (2 min)
# Docker Hub UI → Security → New Access Token

# 3. Generar passwords (1 min)
openssl rand -base64 32  # x3 (DB, Redis, OpenSearch)

# 4. Configurar 15 GitHub Secrets (10 min)
# GitHub UI → Settings → Secrets → New

# 5. (Opcional) Configurar SMTP para notificaciones (10 min)
# Gmail/SendGrid → App Password

# 6. (Opcional) Configurar dominio custom (20 min)
# DNS provider → Add A record
```

**Tiempo Total Setup**: 30-60 minutos (UNA SOLA VEZ)

---

### Cada Deployment (Automático - 0 min tu parte)

```bash
# Solo esto:
git push origin master

# GitHub Actions hace todo:
# ✅ Tests (5 min)
# ✅ Security (3 min)
# ✅ Build (8 min)
# ✅ Terraform (5 min)
# ✅ Helm (10 min)
# ✅ Migrations (3 min)
# ✅ Verify (1 min)

# ⏱️ Total: 35 min (automático)
# 👤 Tu tiempo: 0 min (solo push)
```

---

## 🎉 Conclusión

### ✅ SÍ, es casi 100% automático

**Después de configurar secrets (primera vez)**:
1. Haces `git push origin master`
2. GitHub Actions hace **TODO** automáticamente
3. En 35 minutos tienes el sistema desplegado en Azure
4. **Cero intervención manual necesaria**

### Lo Único que Necesitas

**Una sola vez**:
- ✅ Configurar 11 GitHub Secrets críticos
- ✅ (Opcional) Configurar 4 secrets SMTP
- ⏱️ Tiempo: 30-60 minutos

**Cada deployment**:
- ✅ `git push origin master`
- ⏱️ Tu tiempo: 10 segundos
- ⏱️ Tiempo automático: 35 minutos

---

## 🚀 Quick Start Checklist

```bash
# ✅ SETUP (UNA VEZ):
□ Cuenta Azure activa
□ Repositorio GitHub forked/clonado
□ Service Principal creado
□ Docker Hub account + token
□ 15 GitHub Secrets configurados
□ (Opcional) SMTP configurado

# ✅ DEPLOYMENT (CADA VEZ):
□ git push origin master
□ Esperar 35 minutos
□ Verificar en GitHub Actions
□ Probar URLs resultantes

# ✅ VERIFICACIÓN:
□ kubectl get pods -n carpeta-ciudadana
□ curl http://INGRESS_IP
□ curl http://INGRESS_IP/api/health
```

---

**¿Listo para empezar?** → Configure secrets y haz push! 🚀

---

**Última actualización**: 2025-10-13  
**Versión**: 1.0.0  
**Autor**: Manuel Jurado


# 🏗️ Infraestructura y Deployment - Carpeta Ciudadana

Guía completa de la infraestructura Azure con Terraform y deployment con Helm.

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Infraestructura Terraform](#infraestructura-terraform)
3. [Deployment con Helm](#deployment-con-helm)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Gestión de Ambientes](#gestión-de-ambientes)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 Visión General

### Arquitectura de Deployment

```
┌─────────────────────────────────────────────────────┐
│                   Azure Cloud                       │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │           Resource Group                     │  │
│  │     carpeta-ciudadana-dev-rg                │  │
│  │                                              │  │
│  │  ┌────────────────────────────────────────┐ │  │
│  │  │  AKS Cluster (Kubernetes)              │ │  │
│  │  │  • 2 nodes (Standard_B2s)              │ │  │
│  │  │  • 12 microservicios (pods)            │ │  │
│  │  │  • HPA (autoscaling)                   │ │  │
│  │  │  • Ingress Controller                  │ │  │
│  │  └────────────────────────────────────────┘ │  │
│  │                                              │  │
│  │  ┌────────────────────────────────────────┐ │  │
│  │  │  PostgreSQL Flexible Server           │ │  │
│  │  │  • Tier: Burstable                     │ │  │
│  │  │  • Size: B1ms                          │ │  │
│  │  │  • Storage: 32 GB                      │ │  │
│  │  └────────────────────────────────────────┘ │  │
│  │                                              │  │
│  │  ┌────────────────────────────────────────┐ │  │
│  │  │  Azure Blob Storage                    │ │  │
│  │  │  • Container: documents                │ │  │
│  │  │  • Tier: Standard LRS                  │ │  │
│  │  └────────────────────────────────────────┘ │  │
│  │                                              │  │
│  │  ┌────────────────────────────────────────┐ │  │
│  │  │  Service Bus Namespace                 │ │  │
│  │  │  • Tier: Basic                         │ │  │
│  │  │  • 5 queues (events)                   │ │  │
│  │  └────────────────────────────────────────┘ │  │
│  │                                              │  │
│  │  ┌────────────────────────────────────────┐ │  │
│  │  │  Virtual Network                       │ │  │
│  │  │  • CIDR: 10.0.0.0/16                   │ │  │
│  │  │  • Subnet AKS: 10.0.1.0/24            │ │  │
│  │  └────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Stack de Tecnologías

| Componente | Tecnología | Propósito |
|------------|-----------|-----------|
| **IaC** | Terraform 1.6+ | Provisionar infraestructura Azure |
| **Orquestación** | Kubernetes (AKS) | Gestión de contenedores |
| **Package Manager** | Helm 3.13+ | Despliegue de aplicaciones |
| **CI/CD** | GitHub Actions | Pipeline automatizado |
| **Container Registry** | Docker Hub | Almacenamiento de imágenes |

---

## 🏗️ Infraestructura Terraform

### Estructura del Proyecto

```
infra/terraform/
├── main.tf                 # Configuración principal
├── variables.tf            # Variables de entrada
├── outputs.tf             # Outputs de recursos
├── versions.tf            # Versiones de providers
├── terraform.tfvars       # Valores de variables (gitignored)
└── .terraform.lock.hcl    # Lock file de providers
```

### Componentes Principales

#### 1. Provider Configuration

**Archivo:** `versions.tf`

```hcl
terraform {
  required_version = ">= 1.6.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
  
  # Usar Federated Credentials (GitHub Actions)
  use_oidc = true
}
```

#### 2. Resource Group

```hcl
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location
  
  tags = merge(var.common_tags, {
    Environment = var.environment
    ManagedBy   = "Terraform"
  })
}
```

**Variables:**
- `project_name`: "carpeta-ciudadana"
- `environment`: "dev" | "staging" | "prod"
- `location`: "eastus" (región Azure)

#### 3. Virtual Network

```hcl
resource "azurerm_virtual_network" "main" {
  name                = "${var.project_name}-vnet"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.0.0.0/16"]
  
  tags = var.common_tags
}

resource "azurerm_subnet" "aks" {
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}
```

**Configuración:**
- VNet CIDR: `10.0.0.0/16`
- Subnet AKS: `10.0.1.0/24`
- Network Security Groups configurados automáticamente

#### 4. AKS Cluster

```hcl
resource "azurerm_kubernetes_cluster" "main" {
  name                = "${var.project_name}-aks"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "${var.project_name}-aks"
  
  kubernetes_version = "1.28"
  
  default_node_pool {
    name                = "default"
    node_count          = 2
    vm_size             = "Standard_B2s"  # 2 vCPU, 4 GB RAM
    vnet_subnet_id      = azurerm_subnet.aks.id
    enable_auto_scaling = true
    min_count           = 2
    max_count           = 5
    
    os_disk_size_gb = 30
  }
  
  identity {
    type = "SystemAssigned"
  }
  
  network_profile {
    network_plugin = "azure"
    dns_service_ip = "10.0.2.10"
    service_cidr   = "10.0.2.0/24"
  }
  
  tags = var.common_tags
}
```

**Características:**
- **Nodes:** 2 (min) - 5 (max) con autoscaling
- **VM Size:** Standard_B2s (optimizado para free tier)
- **Network Plugin:** Azure CNI
- **Identity:** System-assigned Managed Identity

#### 5. PostgreSQL Flexible Server

```hcl
resource "azurerm_postgresql_flexible_server" "main" {
  name                = "${var.project_name}-postgres"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  
  sku_name   = "B_Standard_B1ms"  # Burstable tier
  storage_mb = 32768               # 32 GB
  version    = "14"
  
  administrator_login    = var.db_admin_username
  administrator_password = var.db_admin_password
  
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false
  
  high_availability {
    mode = "Disabled"  # Para free tier
  }
  
  tags = var.common_tags
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "carpeta_ciudadana"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "aks" {
  name             = "allow-aks"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"  # Permitir desde AKS (VNet integration)
  end_ip_address   = "255.255.255.255"
}
```

**Configuración:**
- **Tier:** Burstable (B_Standard_B1ms)
- **Storage:** 32 GB
- **Version:** PostgreSQL 14
- **Backup:** 7 días de retención
- **High Availability:** Disabled (costo)

#### 6. Azure Blob Storage

```hcl
resource "azurerm_storage_account" "main" {
  name                     = "${var.project_name}storage"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"  # Locally Redundant Storage
  
  blob_properties {
    versioning_enabled = true
    
    delete_retention_policy {
      days = 7
    }
  }
  
  tags = var.common_tags
}

resource "azurerm_storage_container" "documents" {
  name                  = "documents"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}
```

**Características:**
- **Tier:** Standard
- **Replication:** LRS (más económico)
- **Versioning:** Habilitado
- **Soft Delete:** 7 días
- **Container:** `documents` (privado)

#### 7. Service Bus

```hcl
resource "azurerm_servicebus_namespace" "main" {
  name                = "${var.project_name}-servicebus"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Basic"  # Más económico
  
  tags = var.common_tags
}

# Queues para eventos
locals {
  queue_names = [
    "citizen-registered",
    "document-uploaded",
    "document-authenticated",
    "transfer-requested",
    "transfer-confirmed"
  ]
}

resource "azurerm_servicebus_queue" "queues" {
  for_each = toset(local.queue_names)
  
  name         = each.value
  namespace_id = azurerm_servicebus_namespace.main.id
  
  enable_partitioning            = false
  max_delivery_count             = 3
  dead_lettering_on_message_expiration = true
  
  default_message_ttl = "P1D"  # 1 día
  lock_duration       = "PT1M"  # 1 minuto
}
```

**Queues Creadas:**
1. `citizen-registered`: Eventos de registro
2. `document-uploaded`: Documentos subidos
3. `document-authenticated`: Autenticación en hub
4. `transfer-requested`: Solicitudes de transferencia
5. `transfer-confirmed`: Confirmaciones de transferencia

**Configuración:**
- **Tier:** Basic (sin topics)
- **Dead Letter Queue:** Habilitado (3 intentos)
- **TTL:** 1 día
- **Lock Duration:** 1 minuto

### Variables de Terraform

**Archivo:** `variables.tf`

```hcl
variable "subscription_id" {
  description = "Azure Subscription ID"
  type        = string
}

variable "tenant_id" {
  description = "Azure Tenant ID"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "carpeta-ciudadana"
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "db_admin_username" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "psqladmin"
  sensitive   = true
}

variable "db_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project   = "Carpeta Ciudadana"
    ManagedBy = "Terraform"
    Owner     = "Universidad"
  }
}
```

### Outputs de Terraform

**Archivo:** `outputs.tf`

```hcl
output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "aks_fqdn" {
  value = azurerm_kubernetes_cluster.main.fqdn
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "storage_account_name" {
  value = azurerm_storage_account.main.name
}

output "storage_primary_key" {
  value     = azurerm_storage_account.main.primary_access_key
  sensitive = true
}

output "servicebus_connection_string" {
  value     = azurerm_servicebus_namespace.main.default_primary_connection_string
  sensitive = true
}
```

### Comandos Terraform

#### Inicialización

```bash
cd infra/terraform

# Inicializar providers
terraform init

# Validar configuración
terraform validate

# Ver plan de ejecución
terraform plan
```

#### Aplicar Infraestructura

```bash
# Crear archivo de variables
cat > terraform.tfvars <<EOF
subscription_id = "your-subscription-id"
tenant_id = "your-tenant-id"
db_admin_password = "StrongPassword123!"
environment = "dev"
location = "eastus"
EOF

# Aplicar cambios
terraform apply

# Ver outputs
terraform output

# Ver output sensible
terraform output -raw storage_primary_key
```

#### Destruir Infraestructura

```bash
# Destruir todos los recursos
terraform destroy

# Destruir recurso específico
terraform destroy -target=azurerm_kubernetes_cluster.main
```

---

## 📦 Deployment con Helm

### Estructura del Chart

```
deploy/helm/carpeta-ciudadana/
├── Chart.yaml              # Metadata del chart
├── values.yaml             # Valores por defecto
├── templates/              # Templates de Kubernetes
│   ├── _helpers.tpl       # Helpers de templates
│   ├── serviceaccount.yaml
│   ├── secret-*.yaml      # Secrets
│   ├── configmap-*.yaml   # ConfigMaps
│   ├── deployment-*.yaml  # Deployments (12 servicios)
│   ├── service-*.yaml     # Services
│   ├── ingress.yaml       # Ingress
│   └── hpa-*.yaml         # HorizontalPodAutoscalers
└── values-*.yaml          # Values por ambiente
```

### Chart.yaml

```yaml
apiVersion: v2
name: carpeta-ciudadana
description: Carpeta Ciudadana - Sistema de gestión documental
type: application
version: 1.0.0
appVersion: "1.0.0"
keywords:
  - carpeta-ciudadana
  - fastapi
  - nextjs
  - microservices
maintainers:
  - name: Universidad
    email: contact@universidad.edu.co
```

### Values.yaml

**Configuración Global:**

```yaml
# Global configuration
global:
  namespace: carpeta-ciudadana
  domain: carpeta-ciudadana.example.com
  
  # Docker images
  image:
    registry: docker.io
    repository: manuelquistial
    pullPolicy: IfNotPresent
    tag: latest
  
  # PostgreSQL
  postgresql:
    host: carpeta-ciudadana-postgres.postgres.database.azure.com
    port: 5432
    database: carpeta_ciudadana
    auth:
      username: psqladmin
      passwordSecretName: postgresql-auth
      passwordSecretKey: POSTGRESQL_PASSWORD
  
  # Redis (opcional)
  redis:
    host: carpeta-ciudadana-redis.redis.cache.windows.net
    port: 6380
    ssl: true
    passwordSecretName: redis-auth
    passwordSecretKey: REDIS_PASSWORD
  
  # Azure Storage
  storage:
    accountName: carpetaciudadanastorage
    containerName: documents
    secretName: azure-storage-secret
    secretKey: AZURE_STORAGE_ACCOUNT_KEY
  
  # Service Bus
  servicebus:
    namespace: carpeta-ciudadana-servicebus
    secretName: servicebus-connection
    secretKey: SERVICEBUS_CONNECTION_STRING

# Resource limits por servicio
resources:
  frontend:
    requests:
      memory: "128Mi"
      cpu: "100m"
    limits:
      memory: "256Mi"
      cpu: "200m"
  
  gateway:
    requests:
      memory: "128Mi"
      cpu: "100m"
    limits:
      memory: "256Mi"
      cpu: "200m"
  
  backend:  # Para todos los servicios backend
    requests:
      memory: "128Mi"
      cpu: "100m"
    limits:
      memory: "256Mi"
      cpu: "200m"

# Autoscaling
autoscaling:
  enabled: true
  minReplicas: 1
  maxReplicas: 5
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80

# Ingress
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  tls:
    enabled: true
    secretName: carpeta-ciudadana-tls
```

### Templates Principales

#### 1. ServiceAccount

**Archivo:** `templates/serviceaccount.yaml`

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "carpeta-ciudadana.serviceAccountName" . }}
  namespace: {{ .Values.global.namespace }}
  labels:
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
  {{- with .Values.serviceAccount.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
```

#### 2. Secrets

**Archivo:** `templates/secret-postgresql.yaml`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgresql-auth
  namespace: {{ .Values.global.namespace }}
type: Opaque
data:
  POSTGRESQL_PASSWORD: {{ .Values.global.postgresql.auth.password | b64enc }}
  DATABASE_URL: {{ printf "postgresql+asyncpg://%s:%s@%s:%d/%s" 
    .Values.global.postgresql.auth.username 
    .Values.global.postgresql.auth.password 
    .Values.global.postgresql.host 
    .Values.global.postgresql.port 
    .Values.global.postgresql.database | b64enc }}
```

#### 3. Deployment (Ejemplo: Gateway)

**Archivo:** `templates/deployment-gateway.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-gateway
  namespace: {{ .Values.global.namespace }}
  labels:
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
    app.kubernetes.io/component: gateway
spec:
  replicas: {{ .Values.autoscaling.minReplicas }}
  selector:
    matchLabels:
      {{- include "carpeta-ciudadana.selectorLabels" . | nindent 6 }}
      app.kubernetes.io/component: gateway
  template:
    metadata:
      labels:
        {{- include "carpeta-ciudadana.selectorLabels" . | nindent 8 }}
        app.kubernetes.io/component: gateway
    spec:
      serviceAccountName: {{ include "carpeta-ciudadana.serviceAccountName" . }}
      containers:
      - name: gateway
        image: "{{ .Values.global.image.registry }}/{{ .Values.global.image.repository }}/carpeta-gateway:{{ .Values.global.image.tag }}"
        imagePullPolicy: {{ .Values.global.image.pullPolicy }}
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgresql-auth
              key: DATABASE_URL
        - name: REDIS_HOST
          value: {{ .Values.global.redis.host }}
        - name: REDIS_PORT
          value: "{{ .Values.global.redis.port }}"
        - name: REDIS_SSL
          value: "{{ .Values.global.redis.ssl }}"
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: {{ .Values.global.redis.passwordSecretName }}
              key: {{ .Values.global.redis.passwordSecretKey }}
        - name: RATE_LIMIT_PER_MINUTE
          value: "60"
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          {{- toYaml .Values.resources.gateway | nindent 12 }}
```

#### 4. Service

**Archivo:** `templates/service-gateway.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-gateway
  namespace: {{ .Values.global.namespace }}
  labels:
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
    app.kubernetes.io/component: gateway
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: http
    protocol: TCP
    name: http
  selector:
    {{- include "carpeta-ciudadana.selectorLabels" . | nindent 4 }}
    app.kubernetes.io/component: gateway
```

#### 5. HorizontalPodAutoscaler

**Archivo:** `templates/hpa-gateway.yaml`

```yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-gateway
  namespace: {{ .Values.global.namespace }}
  labels:
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "carpeta-ciudadana.fullname" . }}-gateway
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: {{ .Values.autoscaling.targetMemoryUtilizationPercentage }}
{{- end }}
```

#### 6. Ingress

**Archivo:** `templates/ingress.yaml`

```yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}
  namespace: {{ .Values.global.namespace }}
  labels:
    {{- include "carpeta-ciudadana.labels" . | nindent 4 }}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  ingressClassName: {{ .Values.ingress.className }}
  {{- if .Values.ingress.tls.enabled }}
  tls:
  - hosts:
    - {{ .Values.global.domain }}
    secretName: {{ .Values.ingress.tls.secretName }}
  {{- end }}
  rules:
  - host: {{ .Values.global.domain }}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {{ include "carpeta-ciudadana.fullname" . }}-frontend
            port:
              number: 3000
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: {{ include "carpeta-ciudadana.fullname" . }}-gateway
            port:
              number: 8000
{{- end }}
```

### Comandos Helm

#### Instalación

```bash
# Crear namespace
kubectl create namespace carpeta-ciudadana

# Crear secrets manualmente (primera vez)
kubectl create secret generic postgresql-auth \
  --from-literal=POSTGRESQL_PASSWORD='StrongPassword123!' \
  --namespace carpeta-ciudadana

kubectl create secret generic azure-storage-secret \
  --from-literal=AZURE_STORAGE_ACCOUNT_KEY='storage-key' \
  --namespace carpeta-ciudadana

kubectl create secret generic servicebus-connection \
  --from-literal=SERVICEBUS_CONNECTION_STRING='connection-string' \
  --namespace carpeta-ciudadana

# Instalar chart
helm upgrade --install carpeta-ciudadana \
  deploy/helm/carpeta-ciudadana \
  --namespace carpeta-ciudadana \
  --create-namespace \
  --set global.image.tag=latest \
  --values deploy/helm/carpeta-ciudadana/values.yaml
```

#### Actualización

```bash
# Actualizar con nueva versión
helm upgrade carpeta-ciudadana \
  deploy/helm/carpeta-ciudadana \
  --namespace carpeta-ciudadana \
  --set global.image.tag=v1.2.3

# Rollback a versión anterior
helm rollback carpeta-ciudadana \
  --namespace carpeta-ciudadana
```

#### Verificación

```bash
# Ver releases
helm list -n carpeta-ciudadana

# Ver status
helm status carpeta-ciudadana -n carpeta-ciudadana

# Ver valores aplicados
helm get values carpeta-ciudadana -n carpeta-ciudadana

# Ver manifiesto completo
helm get manifest carpeta-ciudadana -n carpeta-ciudadana
```

#### Desinstalación

```bash
# Desinstalar release
helm uninstall carpeta-ciudadana -n carpeta-ciudadana

# Eliminar namespace
kubectl delete namespace carpeta-ciudadana
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

**Archivo:** `.github/workflows/ci-azure-federated.yml`

```yaml
name: CI/CD - Azure (Federated)

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

env:
  AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
  AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
  AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}

jobs:
  # 1. Tests
  backend-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [gateway, citizen, ingestion, metadata, transfer, mintic_client]
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Install dependencies
        working-directory: services/${{ matrix.service }}
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          poetry install --no-root
      - name: Run tests
        working-directory: services/${{ matrix.service }}
        run: poetry run pytest tests/ -v

  # 2. Build & Push Docker Images
  build-push:
    needs: [backend-test]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [frontend, gateway, citizen, ingestion, metadata, transfer, mintic_client, signature, sharing]
    steps:
      - uses: actions/checkout@v4
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          token: ${{ secrets.DOCKERHUB_TOKEN }}
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/${{ matrix.service }}/Dockerfile
          push: true
          tags: |
            ${{ secrets.DOCKERHUB_USERNAME }}/carpeta-${{ matrix.service }}:latest
            ${{ secrets.DOCKERHUB_USERNAME }}/carpeta-${{ matrix.service }}:${{ github.sha }}

  # 3. Deploy to AKS
  deploy-aks:
    needs: [build-push]
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Azure Login (Federated)
        uses: azure/login@v1
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      
      - name: Set AKS context
        uses: azure/aks-set-context@v3
        with:
          resource-group: carpeta-ciudadana-dev-rg
          cluster-name: carpeta-ciudadana-aks
      
      - name: Deploy with Helm
        run: |
          helm upgrade --install carpeta-ciudadana \
            deploy/helm/carpeta-ciudadana \
            --namespace carpeta-ciudadana \
            --create-namespace \
            --set global.image.tag=${{ github.sha }} \
            --wait \
            --timeout 10m
```

### Secrets de GitHub

**Requeridos en Settings → Secrets:**

```
AZURE_CLIENT_ID                  # Managed Identity Client ID
AZURE_TENANT_ID                  # Azure Tenant ID
AZURE_SUBSCRIPTION_ID            # Azure Subscription ID
DOCKERHUB_USERNAME              # Docker Hub username
DOCKERHUB_TOKEN                 # Docker Hub access token
```

---

## 🌍 Gestión de Ambientes

### Ambientes Configurados

| Ambiente | Namespace | Domain | Resources |
|----------|-----------|--------|-----------|
| **Development** | `carpeta-ciudadana-dev` | `dev.carpeta.example.com` | Min resources |
| **Staging** | `carpeta-ciudadana-staging` | `staging.carpeta.example.com` | Med resources |
| **Production** | `carpeta-ciudadana-prod` | `carpeta.example.com` | High resources |

### Values por Ambiente

#### development (values-dev.yaml)

```yaml
global:
  namespace: carpeta-ciudadana-dev
  domain: dev.carpeta.example.com
  image:
    tag: latest

autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 2

resources:
  frontend:
    requests:
      memory: "64Mi"
      cpu: "50m"
    limits:
      memory: "128Mi"
      cpu: "100m"
```

#### production (values-prod.yaml)

```yaml
global:
  namespace: carpeta-ciudadana-prod
  domain: carpeta.example.com
  image:
    tag: v1.0.0  # Tag específico

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10

resources:
  frontend:
    requests:
      memory: "256Mi"
      cpu: "200m"
    limits:
      memory: "512Mi"
      cpu: "500m"
```

### Deploy por Ambiente

```bash
# Development
helm upgrade --install carpeta-ciudadana \
  deploy/helm/carpeta-ciudadana \
  --namespace carpeta-ciudadana-dev \
  --values deploy/helm/carpeta-ciudadana/values-dev.yaml

# Production
helm upgrade --install carpeta-ciudadana \
  deploy/helm/carpeta-ciudadana \
  --namespace carpeta-ciudadana-prod \
  --values deploy/helm/carpeta-ciudadana/values-prod.yaml
```

---

## 🔧 Troubleshooting

### Terraform Issues

#### Error: Subscription Not Found

```bash
# Verificar autenticación
az account show

# Cambiar subscription
az account set --subscription "subscription-name"

# Re-ejecutar
terraform init
```

#### Error: Resource Already Exists

```bash
# Importar recurso existente
terraform import azurerm_resource_group.main /subscriptions/{sub-id}/resourceGroups/{rg-name}

# O destruir y recrear
terraform destroy -target=azurerm_resource_group.main
terraform apply
```

#### State Lock

```bash
# Si el state está bloqueado
terraform force-unlock LOCK_ID

# O eliminar lock manualmente en Azure Portal → Storage Account → Blobs
```

### Helm Issues

#### ImagePullBackOff

```bash
# Verificar imagen existe
docker pull manuelquistial/carpeta-gateway:latest

# Verificar image pull policy
kubectl describe pod gateway-xxx -n carpeta-ciudadana

# Forzar re-pull
kubectl rollout restart deployment carpeta-ciudadana-gateway -n carpeta-ciudadana
```

#### CrashLoopBackOff

```bash
# Ver logs
kubectl logs -f deployment/carpeta-ciudadana-gateway -n carpeta-ciudadana

# Ver eventos
kubectl get events -n carpeta-ciudadana --sort-by='.lastTimestamp'

# Verificar variables de entorno
kubectl exec -it deployment/carpeta-ciudadana-gateway -n carpeta-ciudadana -- env
```

#### Secrets Not Found

```bash
# Listar secrets
kubectl get secrets -n carpeta-ciudadana

# Crear secret faltante
kubectl create secret generic postgresql-auth \
  --from-literal=POSTGRESQL_PASSWORD='password' \
  -n carpeta-ciudadana

# Verificar secret
kubectl describe secret postgresql-auth -n carpeta-ciudadana
```

### Networking Issues

#### Service Not Accessible

```bash
# Verificar service
kubectl get svc -n carpeta-ciudadana

# Verificar endpoints
kubectl get endpoints -n carpeta-ciudadana

# Port forward para debugging
kubectl port-forward svc/carpeta-ciudadana-gateway 8000:8000 -n carpeta-ciudadana
```

#### Ingress Not Working

```bash
# Verificar ingress
kubectl get ingress -n carpeta-ciudadana

# Describir ingress
kubectl describe ingress carpeta-ciudadana -n carpeta-ciudadana

# Verificar ingress controller
kubectl get pods -n ingress-nginx
```

---

## 📚 Recursos Adicionales

### Documentación Relacionada

- **[GUIA_COMPLETA.md](../GUIA_COMPLETA.md)**: Guía completa del proyecto
- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Arquitectura técnica
- **[README.md](../README.md)**: Quick start guide

### Enlaces Externos

- **Terraform Azure Provider**: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs
- **Helm Documentation**: https://helm.sh/docs/
- **Azure AKS Best Practices**: https://learn.microsoft.com/en-us/azure/aks/best-practices
- **Kubernetes Documentation**: https://kubernetes.io/docs/

---

## 📊 Estimación de Costos

### Azure Resources (USD/mes)

| Recurso | Tier | Costo Estimado |
|---------|------|----------------|
| AKS (2 nodes B2s) | Standard | $~40 |
| PostgreSQL (B1ms) | Burstable | $~12 |
| Storage (32 GB) | Standard LRS | $~1 |
| Service Bus | Basic | $~0.05 |
| Networking | Outbound | $~5 |
| **TOTAL** | | **~$58/mes** |

**Con $100 créditos:** ~2 meses de uso continuo

---

**Última actualización:** Octubre 2025  
**Mantenido por:** Universidad - Proyecto Carpeta Ciudadana


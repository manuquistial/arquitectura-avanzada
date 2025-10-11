# 🚀 Azure Quick Start Guide

Guía rápida para desplegar el proyecto en Azure con tus $100 de créditos.

---

## ⏱️ Tiempo Estimado: 30-45 minutos

---

## 📋 Pre-requisitos

1. ✅ Cuenta Azure con $100 créditos
2. ✅ Azure CLI instalado
3. ✅ Terraform instalado
4. ✅ kubectl instalado
5. ✅ Docker instalado (opcional, para build local)

---

## 🎯 Paso 1: Login Azure (2 min)

```bash
# Login
az login

# Verificar créditos
az account show

# Set subscription (si tienes varios)
az account set --subscription "Azure for Students"

# Verificar región disponible
az account list-locations -o table | grep -i east
```

---

## 🏗️ Paso 2: Deploy Infraestructura (10-15 min)

```bash
cd infra/terraform-azure

# Crear terraform.tfvars
cat > terraform.tfvars <<EOF
azure_region  = "eastus"
environment   = "dev"

# Configuración optimizada para $100 créditos
aks_node_count = 1
aks_vm_size    = "Standard_B1s"  # $3.80/mes

db_admin_username = "psqladmin"
db_admin_password = "CarpetaCiudadana2024!"
db_sku_name       = "B_Standard_B1ms"  # $13.87/mes
db_storage_mb     = 32768

search_sku     = "basic"  # Comentar si quieres ahorrar ($75/mes)
servicebus_sku = "Basic"   # $0.05/mes
acr_sku        = "Basic"   # $5/mes
EOF

# Inicializar (primera vez)
terraform init

# Ver plan
terraform plan

# Aplicar (confirma con 'yes')
terraform apply

# Esto tomará ~10-15 minutos
# Mientras tanto, prepara el código...
```

**Costo esperado**: ~$23/mes (sin Cognitive Search) o ~$98/mes (con Cognitive Search)

---

## 💾 Paso 3: Guardar Outputs (1 min)

```bash
# Guardar todos los outputs
terraform output -json > ../../azure-config.json

# Variables importantes
export ACR_NAME=$(terraform output -raw acr_login_server | cut -d. -f1)
export STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)
export PSQL_HOST=$(terraform output -raw postgresql_fqdn)
export RESOURCE_GROUP=$(terraform output -raw resource_group_name)

echo "ACR: $ACR_NAME"
echo "Storage: $STORAGE_ACCOUNT"
echo "PostgreSQL: $PSQL_HOST"
```

---

## 🐳 Paso 4: Build y Push Imágenes (10-15 min)

### Opción A: Push a ACR (recomendado para producción)

```bash
# Login a ACR
az acr login --name $ACR_NAME

# Build y push frontend
cd ../../apps/frontend
docker build -t $ACR_NAME.azurecr.io/carpeta-ciudadana/frontend:latest .
docker push $ACR_NAME.azurecr.io/carpeta-ciudadana/frontend:latest

# Build y push servicios backend
cd ../../services

for service in gateway citizen ingestion transfer mintic_client; do
  echo "Building $service..."
  docker build -t $ACR_NAME.azurecr.io/carpeta-ciudadana/$service:latest $service
  docker push $ACR_NAME.azurecr.io/carpeta-ciudadana/$service:latest
done
```

### Opción B: Usar Docker Hub (gratis, más lento)

```bash
# Login a Docker Hub
docker login

# Build y push
docker build -t tuusuario/carpeta-frontend:latest apps/frontend
docker push tuusuario/carpeta-frontend:latest

# Cambiar IMAGE_REGISTRY en Helm values
export IMAGE_REGISTRY="tuusuario"
```

---

## ☸️ Paso 5: Configure kubectl (1 min)

```bash
# Get AKS credentials
az aks get-credentials \
  --resource-group $RESOURCE_GROUP \
  --name carpeta-ciudadana-dev

# Verificar
kubectl get nodes

# Deberías ver algo como:
# NAME                              STATUS   ROLES   AGE   VERSION
# aks-default-xxxxx-vmss000000      Ready    agent   5m    v1.27.7
```

---

## 📦 Paso 6: Deploy con Helm (5 min)

```bash
cd ../../deploy/helm/carpeta-ciudadana

# Crear values-azure.yaml
cat > values-azure.yaml <<EOF
global:
  environment: dev
  imageRegistry: ${ACR_NAME}.azurecr.io/carpeta-ciudadana

# Configuración optimizada para 1 node B1s (1GB RAM)
gateway:
  replicaCount: 1
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"
    limits:
      memory: "256Mi"
      cpu: "200m"

citizen:
  replicaCount: 1
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"

ingestion:
  replicaCount: 1
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"

transfer:
  replicaCount: 1
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"

minticClient:
  replicaCount: 1
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"

config:
  database:
    host: ${PSQL_HOST}
    port: 5432
    name: carpeta_ciudadana
    username: psqladmin
    password: CarpetaCiudadana2024!
  
  storage:
    accountName: ${STORAGE_ACCOUNT}
    container: documents
    connectionString: "$(az storage account show-connection-string --name ${STORAGE_ACCOUNT} --resource-group ${RESOURCE_GROUP} -o tsv)"
  
  cloudProvider: azure
EOF

# Deploy
helm upgrade --install carpeta-ciudadana . \
  -f values-azure.yaml \
  --namespace carpeta-ciudadana \
  --create-namespace \
  --wait \
  --timeout 10m

# Ver status
kubectl get pods -n carpeta-ciudadana
kubectl get svc -n carpeta-ciudadana
```

---

## 🌐 Paso 7: Acceder a la Aplicación (2 min)

```bash
# Obtener IP pública del Load Balancer
kubectl get svc -n carpeta-ciudadana

# Buscar EXTERNAL-IP del servicio frontend
# Puede tomar 2-3 minutos en aparecer

# O usar port-forward para testing inmediato
kubectl port-forward -n carpeta-ciudadana svc/carpeta-ciudadana-frontend 3000:3000

# Abrir en browser
# http://localhost:3000
```

---

## ✅ Paso 8: Verificar Todo Funciona (5 min)

### Test 1: Health Checks

```bash
# Gateway
kubectl exec -it -n carpeta-ciudadana deployment/carpeta-ciudadana-gateway -- curl http://localhost:8000/health

# Citizen service
kubectl exec -it -n carpeta-ciudadana deployment/carpeta-ciudadana-citizen -- curl http://localhost:8000/health
```

### Test 2: Upload de Documento

```bash
# Get gateway service IP
GATEWAY_IP=$(kubectl get svc -n carpeta-ciudadana carpeta-ciudadana-gateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Request upload URL
curl -X POST http://$GATEWAY_IP:8000/api/ingestion/upload-url \
  -H "Content-Type: application/json" \
  -d '{
    "citizen_id": 123,
    "filename": "test.pdf",
    "content_type": "application/pdf",
    "title": "Test Document"
  }'

# Deberías recibir un upload_url con SAS token de Azure
```

### Test 3: Verificar PostgreSQL

```bash
# Connect to PostgreSQL
kubectl run -it --rm psql \
  --image=postgres:15-alpine \
  --restart=Never \
  -n carpeta-ciudadana -- \
  psql -h $PSQL_HOST \
       -U psqladmin \
       -d carpeta_ciudadana

# Dentro de psql:
\dt  # Ver tablas
\q   # Salir
```

---

## 📊 Paso 9: Monitorear Costos (Importante!)

```bash
# Ver costos actuales
az consumption usage list \
  --start-date $(date -d "yesterday" +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  -o table

# Configurar alerta de presupuesto
az consumption budget create \
  --budget-name carpeta-ciudadana-budget \
  --amount 100 \
  --time-grain Monthly \
  --start-date $(date +%Y-%m-01) \
  --notification-enabled true \
  --notification-threshold 80 \
  --contact-emails tu@email.com

# Ver en portal
# https://portal.azure.com/#view/Microsoft_Azure_CostManagement
```

---

## 🛑 Paso 10: Stopear para Ahorrar Créditos (Opcional)

Cuando no estés usando el proyecto:

```bash
# Stopear AKS (ahorra ~$4/día)
az aks stop \
  --resource-group $RESOURCE_GROUP \
  --name carpeta-ciudadana-dev

# Stopear PostgreSQL (ahorra ~$14/mes)
az postgres flexible-server stop \
  --resource-group $RESOURCE_GROUP \
  --name dev-psql-server

# Para reiniciar cuando necesites
az aks start --resource-group $RESOURCE_GROUP --name carpeta-ciudadana-dev
az postgres flexible-server start --resource-group $RESOURCE_GROUP --name dev-psql-server
```

---

## 🔧 Troubleshooting

### Problema: "Cannot pull image from ACR"

```bash
# Attach ACR to AKS
az aks update \
  --name carpeta-ciudadana-dev \
  --resource-group $RESOURCE_GROUP \
  --attach-acr $ACR_NAME
```

### Problema: "Pods en estado Pending"

```bash
# Ver eventos
kubectl describe pod -n carpeta-ciudadana <pod-name>

# Causa común: Not enough resources
# Solución: Reducir replicas o resources en values.yaml
```

### Problema: "Cannot connect to PostgreSQL"

```bash
# Agregar firewall rule
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name dev-psql-server \
  --rule-name allow-all \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 255.255.255.255
```

---

## 📝 Next Steps

1. ✅ **Configurar GitHub Actions**: Ver `.github/workflows/ci-azure.yml`
2. ✅ **Agregar certificados mTLS**: Para integración MinTIC
3. ✅ **Configurar Azure AD B2C**: Para login de usuarios
4. ✅ **Agregar monitoring**: Azure Monitor + Application Insights
5. ✅ **Configurar alertas**: Para errores y métricas

---

## 💰 Resumen de Costos

Con configuración optimizada:

```
✅ AKS Control Plane:    $0/mes (GRATIS)
✅ 1x VM B1s:            $3.80/mes
✅ PostgreSQL B1ms:      $13.87/mes
✅ Blob Storage 10GB:    $0.50/mes
✅ Service Bus Basic:    $0.05/mes
✅ ACR Basic:            $5/mes (o gratis con Docker Hub)
─────────────────────────────────────
TOTAL:                   ~$23/mes

Con $100: ~4.3 meses online 24/7 ✅
```

---

## 🎓 Para tu Proyecto Universitario

**Recomendación**:
1. Usar durante 2-3 meses en modo "Always On"
2. Los últimos 2 meses, stopear cuando no uses
3. Te durará ~5-6 meses total

**En tu CV**:
```
- Deployed microservices architecture on Azure AKS
- Implemented Infrastructure as Code with Terraform
- Configured CI/CD pipelines with GitHub Actions
- Used Azure Blob Storage, PostgreSQL, Service Bus
- Managed Kubernetes deployments with Helm
```

¡Éxito! 🚀


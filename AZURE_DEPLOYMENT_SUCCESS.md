# 🎉 Despliegue Azure Exitoso!

## ✅ Infraestructura Creada

Fecha: 11 de octubre de 2025
Región: **northcentralus** (Iowa)
Subscription: Azure for Students

---

## 📋 Recursos Desplegados

### 1. AKS (Azure Kubernetes Service)
```
✅ Cluster: carpeta-ciudadana-dev
✅ Nodos: 1x Standard_B2s (2 vCPU, 4GB RAM)
✅ Auto-scaling: 1-3 nodos
✅ Kubernetes: v1.32.7
✅ Control Plane: GRATIS
✅ Endpoint: carpeta-ciudadana-dev-dns-bi7ubgw8.hcp.northcentralus.azmk8s.io
```

**Verificar:**
```bash
kubectl get nodes
kubectl cluster-info
```

### 2. PostgreSQL Flexible Server
```
✅ Server: dev-psql-server
✅ FQDN: dev-psql-server.postgres.database.azure.com
✅ SKU: B_Standard_B1ms (1 vCPU, 2GB RAM)
✅ Storage: 32GB
✅ Database: carpeta_ciudadana
✅ Version: PostgreSQL 14
✅ Admin: psqladmin
```

**Conectar:**
```bash
psql -h dev-psql-server.postgres.database.azure.com \
     -U psqladmin \
     -d carpeta_ciudadana
# Password: CarpetaCiudadana2024!Secure
```

### 3. Blob Storage
```
✅ Account: devcarpetastorage
✅ Container: documents
✅ Endpoint: https://devcarpetastorage.blob.core.windows.net
✅ Versioning: Enabled
✅ CORS: Configurado para uploads
```

**Test:**
```bash
az storage blob list \
  --account-name devcarpetastorage \
  --container-name documents
```

### 4. Service Bus
```
✅ Namespace: dev-carpeta-bus
✅ Queue 1: events-queue
✅ Queue 2: notifications-queue
✅ Tier: Basic ($0.05/mes)
```

**Test:**
```bash
az servicebus queue show \
  --resource-group carpeta-ciudadana-dev-rg \
  --namespace-name dev-carpeta-bus \
  --name events-queue
```

### 5. Networking
```
✅ VNet: dev-vnet (10.0.0.0/16)
✅ Subnet AKS: 10.0.1.0/24
✅ Subnet DB: 10.0.2.0/24
```

### 6. Identity & Access
```
✅ Managed Identity: carpeta-ciudadana-dev-aks-identity
✅ Client ID: d8b7b6fd-84da-43a8-8d0e-9ba81e59befc
✅ Role: Storage Blob Data Contributor
```

---

## 💰 Costos

### Desglose Mensual:
```
AKS Control Plane:        $0/mes      (GRATIS!)
1x Standard_B2s node:     $30.37/mes
PostgreSQL B1ms:          $13.87/mes
Blob Storage (10GB):      $0.50/mes
Service Bus Basic:        $0.05/mes
Bandwidth (100GB):        $0/mes      (GRATIS!)
────────────────────────────────────
TOTAL:                    $44.79/mes
```

### Con $100 créditos:
- **24/7**: 2.2 meses
- **Stop cuando no uses**: 4-5 meses
- **Solo fines de semana**: 6-8 meses

---

## 🚀 Próximos Pasos

### Paso 1: Verificar cluster (HECHO ✅)
```bash
kubectl get nodes
# NAME                              STATUS   ROLES    AGE     VERSION
# aks-default-20262258-vmss000000   Ready    <none>   4m54s   v1.32.7
```

### Paso 2: Deploy aplicación

#### Opción A: Docker Hub (Gratis - Recomendado)

```bash
# 1. Crear cuenta en Docker Hub
# https://hub.docker.com/signup

# 2. Login
docker login
# Username: tu_usuario
# Password: tu_password

# 3. Build y push frontend
cd apps/frontend
docker build -t tuusuario/carpeta-frontend:latest .
docker push tuusuario/carpeta-frontend:latest

# 4. Build y push servicios
cd ../../services/gateway
docker build -t tuusuario/carpeta-gateway:latest .
docker push tuusuario/carpeta-gateway:latest

# (Repetir para: citizen, ingestion, transfer, mintic_client)
```

#### Opción B: Usar imágenes pre-built (más rápido)

```bash
# Por ahora, deploy Elasticsearch en AKS
kubectl create namespace carpeta-ciudadana

kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elasticsearch
  namespace: carpeta-ciudadana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
        env:
        - name: discovery.type
          value: single-node
        - name: ES_JAVA_OPTS
          value: "-Xms512m -Xmx512m"
        - name: xpack.security.enabled
          value: "false"
        ports:
        - containerPort: 9200
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: elasticsearch
  namespace: carpeta-ciudadana
spec:
  selector:
    app: elasticsearch
  ports:
  - port: 9200
    targetPort: 9200
EOF
```

### Paso 3: Verificar pods

```bash
kubectl get pods -n carpeta-ciudadana
kubectl logs -f deployment/elasticsearch -n carpeta-ciudadana
```

---

## 📝 Información de Conexión

### Variables de Entorno para Servicios

```bash
# Crear .env para servicios
cat > ../../services/.env.azure <<EOF
# Cloud Provider
CLOUD_PROVIDER=azure

# Azure Storage
AZURE_STORAGE_ACCOUNT_NAME=devcarpetastorage
AZURE_STORAGE_CONTAINER_NAME=documents
AZURE_STORAGE_CONNECTION_STRING="$(cd ../../infra/terraform-azure && terraform output -raw storage_primary_connection_string)"

# Azure Service Bus
AZURE_SERVICEBUS_CONNECTION_STRING="$(cd ../../infra/terraform-azure && terraform output -raw servicebus_connection_string)"
AZURE_SERVICEBUS_QUEUE_NAME=events-queue

# PostgreSQL
DB_HOST=dev-psql-server.postgres.database.azure.com
DB_PORT=5432
DB_NAME=carpeta_ciudadana
DB_USER=psqladmin
DB_PASSWORD=CarpetaCiudadana2024!Secure

# Search (Elasticsearch en AKS)
SEARCH_HOST=elasticsearch.carpeta-ciudadana.svc.cluster.local
SEARCH_PORT=9200
SEARCH_USE_SSL=false

# OpenTelemetry
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger-collector:4317
EOF

echo "✅ Variables de entorno creadas en services/.env.azure"
```

---

## 💡 Comandos Útiles

### Ver recursos en Azure Portal
```bash
# Abrir Resource Group en browser
az group show --name carpeta-ciudadana-dev-rg --query id -o tsv | \
  xargs -I {} echo "https://portal.azure.com/#@/resource{}/overview"
```

### Stopear servicios (ahorrar créditos)
```bash
# Stopear AKS (ahorra ~$30/mes = $1/día)
az aks stop --resource-group carpeta-ciudadana-dev-rg --name carpeta-ciudadana-dev

# Stopear PostgreSQL (ahorra ~$14/mes = $0.46/día)
az postgres flexible-server stop --resource-group carpeta-ciudadana-dev-rg --name dev-psql-server

# Reiniciar cuando necesites
az aks start --resource-group carpeta-ciudadana-dev-rg --name carpeta-ciudadana-dev
az postgres flexible-server start --resource-group carpeta-ciudadana-dev-rg --name dev-psql-server
```

### Ver costos acumulados
```bash
# Costos del mes
az consumption usage list --output table

# O en portal
open "https://portal.azure.com/#view/Microsoft_Azure_CostManagement"
```

### Logs de AKS
```bash
# Ver logs de un servicio
kubectl logs -f deployment/NOMBRE_DEPLOYMENT -n carpeta-ciudadana

# Ver todos los pods
kubectl get pods -n carpeta-ciudadana -w
```

---

## 🎯 Estado Actual

✅ **Infraestructura**: Desplegada (19 recursos)
✅ **Kubernetes**: Cluster funcionando (1 nodo)
✅ **kubectl**: Configurado
⏳ **Aplicaciones**: Pendiente de deploy
⏳ **GitHub Actions**: Pendiente configurar federated auth

---

## 📅 Próximos Pasos

1. **Deploy Elasticsearch** (búsqueda - $0 extra)
   ```bash
   kubectl apply -f kubernetes/elasticsearch.yaml
   ```

2. **Build y Push imágenes Docker**
   - Crear cuenta Docker Hub (gratis)
   - Build todas las imágenes
   - Push a Docker Hub

3. **Deploy con Helm**
   ```bash
   helm upgrade --install carpeta-ciudadana \
     deploy/helm/carpeta-ciudadana \
     --namespace carpeta-ciudadana
   ```

4. **Configurar GitHub Actions** (opcional)
   ```bash
   ~/setup-github-federated-auth.sh
   ```

5. **Testing**
   - Upload de documentos
   - Búsqueda
   - Transferencias P2P

---

## 📊 Resumen Ejecutivo

| Concepto | Valor |
|----------|-------|
| **Costo mensual** | $44.79 |
| **Créditos disponibles** | $100 |
| **Duración estimada** | 2-5 meses |
| **Recursos desplegados** | 19 |
| **Región** | northcentralus |
| **Status** | ✅ OPERATIVO |

---

## ⚠️ Recordatorios

1. **Stopear cuando no uses** para alargar tus créditos
2. **Monitorear costos** semanalmente
3. **Backups automáticos** habilitados (7 días)
4. **No committear** archivos `.env` con passwords

---

## 🆘 Soporte

Si algo falla:
```bash
# Ver eventos del cluster
kubectl get events -n carpeta-ciudadana --sort-by='.lastTimestamp'

# Diagnosticar pod
kubectl describe pod POD_NAME -n carpeta-ciudadana

# Ver logs
kubectl logs POD_NAME -n carpeta-ciudadana
```

**Documentación completa:**
- `AZURE_QUICKSTART.md`
- `MIGRATION_GUIDE.md`
- `GITHUB_ACTIONS_SETUP.md`

¡Éxito con tu proyecto! 🚀


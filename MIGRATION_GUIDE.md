# Guía de Migración: AWS → Azure

## 📋 Resumen de Cambios

Esta guía documenta todos los cambios necesarios para migrar de AWS a Azure.

---

## 🔄 Tabla de Equivalencias

| AWS Service | Azure Service | Cambios en Código |
|-------------|---------------|-------------------|
| **EKS** | **AKS** | Helm charts (mínimos) |
| **S3** | **Blob Storage** | SDK boto3 → azure-storage-blob |
| **RDS PostgreSQL** | **Azure Database for PostgreSQL** | Connection string |
| **OpenSearch** | **Azure Cognitive Search** | API client |
| **SQS/SNS** | **Service Bus** | SDK boto3 → azure-servicebus |
| **Cognito** | **Azure AD B2C** | OIDC config |
| **ACM PCA** | **Key Vault** | Certificate management |
| **ECR** | **ACR** | Registry URL |
| **CloudWatch** | **Azure Monitor** | Exporter config |
| **IAM Roles** | **Managed Identities** | RBAC |

---

## 1️⃣ Infraestructura (Terraform)

### Nueva estructura:
```
infra/
├── terraform/          # AWS (original)
└── terraform-azure/    # Azure (nuevo)
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    └── modules/
        ├── aks/
        ├── postgresql/
        ├── storage/
        ├── servicebus/
        └── ...
```

### Desplegar infraestructura Azure:

```bash
cd infra/terraform-azure

# Crear terraform.tfvars
cp terraform.tfvars.example terraform.tfvars
# Editar con tus valores

# Deploy
terraform init
terraform plan
terraform apply

# Guardar outputs
terraform output -json > ../outputs.json
```

---

## 2️⃣ Código de Aplicación

### Shared Library

**Nuevo archivo**: `services/shared/carpeta_shared/azure_clients.py`

Clientes Azure equivalentes:
- `AzureBlobClient` ← `S3Client`
- `AzureServiceBusClient` ← `SQSClient`/`SNSClient`
- `AzureKeyVaultClient` ← Certificados mTLS

### Configuración

**Actualizado**: `services/shared/carpeta_shared/config.py`

Nueva clase `AzureConfig` con:
- Storage account
- Service Bus
- Key Vault
- Azure AD B2C

### Variables de Entorno

**AWS (antes)**:
```bash
AWS_REGION=us-east-1
S3_BUCKET=carpeta-ciudadana-documents
SQS_QUEUE_URL=https://...
SNS_TOPIC_ARN=arn:aws:...
COGNITO_USER_POOL_ID=...
```

**Azure (ahora)**:
```bash
CLOUD_PROVIDER=azure
AZURE_STORAGE_ACCOUNT_NAME=carpetastorage
AZURE_STORAGE_ACCOUNT_KEY=...
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_STORAGE_CONTAINER_NAME=documents
AZURE_SERVICEBUS_CONNECTION_STRING=...
AZURE_SERVICEBUS_NAMESPACE=...
AZURE_KEYVAULT_URL=https://...vault.azure.net
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
```

---

## 3️⃣ Servicios Actualizados

### Ingestion Service

**Nuevo archivo**: `services/ingestion/app/azure_storage.py`

```python
from app.azure_storage import AzureBlobDocumentClient

# Auto-detecta cloud provider
CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "azure")

if CLOUD_PROVIDER == "azure":
    storage_client = AzureBlobDocumentClient(...)
else:
    storage_client = S3DocumentClient(...)  # Legacy
```

**Funcionalidad idéntica**:
- `generate_presigned_put()` - URLs de subida
- `generate_presigned_get()` - URLs de descarga
- `calculate_sha256()` - Verificación integridad

---

## 4️⃣ Helm Charts

### Cambios mínimos en `values.yaml`:

```yaml
# Antes (AWS)
global:
  imageRegistry: 123456789.dkr.ecr.us-east-1.amazonaws.com

config:
  s3:
    bucket: carpeta-ciudadana-documents
  sqs:
    queueUrl: https://sqs.us-east-1.amazonaws.com/...

# Ahora (Azure)
global:
  imageRegistry: carpetaciudadanaacr.azurecr.io

config:
  storage:
    accountName: carpetastorage
    container: documents
  servicebus:
    namespace: carpeta-ciudadana-bus.servicebus.windows.net
```

---

## 5️⃣ CI/CD (GitHub Actions)

### Nuevo archivo: `.github/workflows/ci-azure.yml`

**Cambios principales**:

```yaml
# AWS (antes)
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4

- name: Login to Amazon ECR
  uses: aws-actions/amazon-ecr-login@v2

# Azure (ahora)
- name: Azure Login
  uses: azure/login@v1
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}

- name: Login to ACR
  run: az acr login --name ${{ secrets.ACR_NAME }}
```

### GitHub Secrets necesarios:

```
AZURE_CREDENTIALS      # Service Principal JSON
ACR_NAME              # Container Registry name
```

Crear Service Principal:
```bash
az ad sp create-for-rbac \
  --name "carpeta-ciudadana-github" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group} \
  --sdk-auth
```

---

## 6️⃣ Dependencias (pyproject.toml)

```toml
[tool.poetry.dependencies]
# AWS (mantener para retrocompatibilidad)
boto3 = "^1.34.0"

# Azure (nuevo)
azure-identity = "^1.15.0"
azure-storage-blob = "^12.19.0"
azure-servicebus = "^7.11.4"
azure-keyvault-certificates = "^4.7.0"
azure-keyvault-secrets = "^4.7.0"
```

Instalar:
```bash
cd services/shared
poetry install

cd ../ingestion
poetry install
```

---

## 7️⃣ Frontend (Next.js)

### Cambios mínimos en variables:

```javascript
// .env.local
NEXT_PUBLIC_API_URL=http://AZURE_LOAD_BALANCER_IP
NEXT_PUBLIC_COGNITO_REGION=         # ← Quitar
NEXT_PUBLIC_COGNITO_USER_POOL_ID=   # ← Quitar
NEXT_PUBLIC_COGNITO_CLIENT_ID=      # ← Quitar

// Nuevas (Azure AD B2C)
NEXT_PUBLIC_AZURE_AD_TENANT_ID=...
NEXT_PUBLIC_AZURE_AD_CLIENT_ID=...
NEXT_PUBLIC_AZURE_AD_B2C_POLICY=B2C_1_signupsignin
```

**Nota**: El resto del frontend NO cambia (las URLs de API siguen iguales).

---

## 8️⃣ Despliegue Paso a Paso

### Paso 1: Deploy Infraestructura

```bash
cd infra/terraform-azure
terraform init
terraform apply

# Obtener outputs
STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)
ACR_NAME=$(terraform output -raw acr_login_server | cut -d. -f1)
PSQL_HOST=$(terraform output -raw postgresql_fqdn)
```

### Paso 2: Build y Push Imágenes

```bash
# Login a ACR
az acr login --name $ACR_NAME

# Build frontend
docker build -t $ACR_NAME.azurecr.io/carpeta-ciudadana/frontend:latest apps/frontend
docker push $ACR_NAME.azurecr.io/carpeta-ciudadana/frontend:latest

# Build backend services
for service in gateway citizen ingestion transfer mintic_client; do
  docker build -t $ACR_NAME.azurecr.io/carpeta-ciudadana/$service:latest services/$service
  docker push $ACR_NAME.azurecr.io/carpeta-ciudadana/$service:latest
done
```

### Paso 3: Deploy a AKS

```bash
# Get AKS credentials
az aks get-credentials \
  --resource-group carpeta-ciudadana-prod-rg \
  --name carpeta-ciudadana-prod

# Verify
kubectl get nodes

# Deploy with Helm
cd deploy/helm/carpeta-ciudadana

helm upgrade --install carpeta-ciudadana . \
  --namespace carpeta-ciudadana-prod \
  --create-namespace \
  --set global.imageRegistry=$ACR_NAME.azurecr.io \
  --set config.database.host=$PSQL_HOST \
  --set config.storage.accountName=$STORAGE_ACCOUNT \
  --wait
```

### Paso 4: Verificar Deployment

```bash
# Pods
kubectl get pods -n carpeta-ciudadana-prod

# Services
kubectl get svc -n carpeta-ciudadana-prod

# Logs
kubectl logs -f deployment/carpeta-ciudadana-gateway -n carpeta-ciudadana-prod
```

---

## 9️⃣ Testing

### Test local con Azure

```bash
# Crear .env con credenciales Azure
cat > services/ingestion/.env <<EOF
CLOUD_PROVIDER=azure
AZURE_STORAGE_ACCOUNT_NAME=...
AZURE_STORAGE_ACCOUNT_KEY=...
AZURE_STORAGE_CONTAINER_NAME=documents
EOF

# Run service
cd services/ingestion
poetry run uvicorn app.main:app --reload

# Test upload URL
curl -X POST http://localhost:8000/api/documents/upload-url \
  -H "Content-Type: application/json" \
  -d '{
    "citizen_id": 123,
    "filename": "test.pdf",
    "content_type": "application/pdf",
    "title": "Test Document"
  }'
```

---

## 🔟 Rollback Plan

Si necesitas volver a AWS:

```bash
# 1. Set CLOUD_PROVIDER=aws
export CLOUD_PROVIDER=aws

# 2. Use AWS credentials
export AWS_REGION=us-east-1
export S3_BUCKET=carpeta-ciudadana-documents

# 3. Deploy with AWS Helm values
helm upgrade carpeta-ciudadana deploy/helm/carpeta-ciudadana \
  -f values-aws.yaml
```

---

## ✅ Checklist de Migración

### Pre-migración
- [ ] Backup de datos en AWS
- [ ] Documentar endpoints actuales
- [ ] Lista de secretos/certificados

### Infraestructura
- [ ] Deploy Terraform Azure
- [ ] Verificar AKS funcional
- [ ] Verificar PostgreSQL conectividad
- [ ] Verificar Blob Storage
- [ ] Verificar Service Bus

### Código
- [ ] Instalar Azure SDKs
- [ ] Actualizar variables de entorno
- [ ] Tests locales con Azure
- [ ] Build imágenes Docker

### Deployment
- [ ] Push imágenes a ACR
- [ ] Deploy Helm a AKS
- [ ] Verificar pods running
- [ ] Verificar logs sin errores

### Testing
- [ ] Test upload documento
- [ ] Test download documento
- [ ] Test registro ciudadano
- [ ] Test transferencia P2P
- [ ] Test integración MinTIC

### Post-migración
- [ ] Monitoreo Azure Monitor
- [ ] Configurar alertas
- [ ] Documentar nueva arquitectura
- [ ] Eliminar recursos AWS (opcional)

---

## 📊 Comparación de Costos

| Concepto | AWS/mes | Azure/mes | Ahorro |
|----------|---------|-----------|--------|
| Kubernetes | $73 (EKS) | $0 (AKS) | **$73** |
| Nodes (3x t3.medium) | $92 | $23 (3x B1s) | **$69** |
| PostgreSQL | $157 | $14 (B1ms) | **$143** |
| Storage 1TB | $24 | $24 | $0 |
| Messaging | $5 | $0.05 | **$5** |
| **TOTAL** | **$351** | **$61** | **$290** |

**Ahorro con Azure: ~83%** (con $100 créditos = gratis por 20 meses!)

---

## 🆘 Troubleshooting

### Error: "Cannot pull image from ACR"

```bash
# Attach ACR to AKS
az aks update \
  --name carpeta-ciudadana-prod \
  --resource-group carpeta-ciudadana-prod-rg \
  --attach-acr carpetaciudadanaacr
```

### Error: "Cannot connect to PostgreSQL"

```bash
# Add firewall rule
az postgres flexible-server firewall-rule create \
  --resource-group carpeta-ciudadana-prod-rg \
  --name carpeta-ciudadana-psql \
  --rule-name allow-aks \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 255.255.255.255
```

### Error: "Blob upload failed"

```bash
# Verify storage account key
az storage account keys list \
  --resource-group carpeta-ciudadana-prod-rg \
  --account-name carpetastorage
```

---

## 📚 Recursos

- [Azure Kubernetes Service Docs](https://learn.microsoft.com/azure/aks/)
- [Azure Blob Storage SDK](https://learn.microsoft.com/python/api/azure-storage-blob/)
- [Azure Service Bus SDK](https://learn.microsoft.com/python/api/azure-servicebus/)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)

---

## 🎓 Para Proyecto Universitario

Con tus $100 de créditos Azure:
- **Costo estimado**: $18-25/mes
- **Duración**: 4-5 meses
- **Experiencia completa**: AKS, Blob Storage, PostgreSQL, Service Bus
- **CV-friendly**: "Deployed microservices on Azure AKS with Terraform"

¡Éxito con tu proyecto! 🚀


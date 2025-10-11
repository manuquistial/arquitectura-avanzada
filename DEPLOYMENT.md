# Guía de Despliegue - Carpeta Ciudadana

## Prerequisitos

### Herramientas Locales
- Node.js 22+
- Python 3.11+
- Poetry
- Docker & Docker Compose
- Terraform >= 1.6
- kubectl >= 1.28
- Helm >= 3.13
- AWS CLI v2

### Cuentas y Accesos
- Cuenta AWS con permisos de administrador
- Acceso al hub MinTIC (credenciales OAuth + certificados mTLS)
- GitHub (para CI/CD)

## 1. Configuración Inicial

### 1.1 Clonar Repositorio
```bash
git clone https://github.com/tu-org/carpeta-ciudadana.git
cd carpeta-ciudadana
```

### 1.2 Configurar Variables de Entorno

#### Backend Services
Crear `.env` en cada servicio basado en `.env.example`:

```bash
# services/mintic_client/.env
MINTIC_BASE_URL=https://hub.mintic.gov.co
MINTIC_OPERATOR_ID=tu-operator-id
MINTIC_OPERATOR_NAME=Tu Operador
MINTIC_CLIENT_ID=tu-client-id
MINTIC_CLIENT_SECRET=tu-client-secret
MTLS_CERT_PATH=/etc/ssl/certs/client.crt
MTLS_KEY_PATH=/etc/ssl/private/client.key
CA_BUNDLE_PATH=/etc/ssl/certs/ca-bundle.crt
```

#### Frontend
```bash
# apps/frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_COGNITO_REGION=us-east-1
NEXT_PUBLIC_COGNITO_USER_POOL_ID=tu-user-pool-id
NEXT_PUBLIC_COGNITO_CLIENT_ID=tu-client-id
NEXT_PUBLIC_OPERATOR_ID=tu-operator-id
NEXT_PUBLIC_OPERATOR_NAME=Tu Operador
```

## 2. Desarrollo Local

### 2.1 Iniciar Infraestructura Local
```bash
# Inicia PostgreSQL, OpenSearch, LocalStack, Redis, Jaeger
make dev-up
```

### 2.2 Instalar Dependencias

#### Frontend
```bash
cd apps/frontend
npm install
```

#### Backend (cada servicio)
```bash
cd services/gateway
poetry install
```

### 2.3 Ejecutar Servicios

#### Frontend
```bash
cd apps/frontend
npm run dev
# http://localhost:3000
```

#### Backend (ejemplo: gateway)
```bash
cd services/gateway
poetry run uvicorn app.main:app --reload --port 8000
```

### 2.4 Tests
```bash
make test          # Todos los tests
make test-unit     # Tests unitarios
make test-e2e      # Tests E2E
make lint          # Linters
```

## 3. Infraestructura AWS (Terraform)

### 3.1 Backend S3 para Terraform State
```bash
# Crear bucket para terraform state
aws s3 mb s3://carpeta-ciudadana-terraform-state --region us-east-1

# Crear tabla DynamoDB para lock
aws dynamodb create-table \
  --table-name terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 3.2 Configurar Terraform
```bash
cd infra/terraform

# Copiar y editar variables
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tus valores

# Inicializar
terraform init

# Planificar
terraform plan -out=tfplan

# Aplicar
terraform apply tfplan
```

### 3.3 Outputs
```bash
# Guardar outputs importantes
terraform output eks_cluster_name
terraform output rds_endpoint
terraform output s3_bucket_name
terraform output cognito_user_pool_id
terraform output cognito_client_id
terraform output ecr_repositories
```

## 4. Configurar kubectl para EKS

```bash
# Actualizar kubeconfig
aws eks update-kubeconfig \
  --name carpeta-ciudadana-prod \
  --region us-east-1

# Verificar conexión
kubectl get nodes
```

## 5. Certificados mTLS (ACM PCA)

### 5.1 Solicitar Certificados
```bash
# Obtener ARN de la CA privada
CA_ARN=$(terraform output -raw acm_pca_arn)

# Solicitar certificado de cliente
aws acm-pca issue-certificate \
  --certificate-authority-arn $CA_ARN \
  --csr file://client.csr \
  --signing-algorithm SHA256WITHRSA \
  --validity Value=365,Type=DAYS

# Descargar certificado
aws acm-pca get-certificate \
  --certificate-authority-arn $CA_ARN \
  --certificate-arn CERT_ARN \
  --output text > client.crt

# Descargar CA bundle
aws acm-pca get-certificate-authority-certificate \
  --certificate-authority-arn $CA_ARN \
  --output text > ca-bundle.crt
```

### 5.2 Crear Secrets en Kubernetes
```bash
kubectl create secret generic mintic-mtls-certs \
  --from-file=client.crt \
  --from-file=client.key \
  --from-file=ca-bundle.crt \
  --namespace carpeta-ciudadana-prod
```

## 6. Build y Push de Imágenes Docker

### 6.1 Login a ECR
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  YOUR_ECR_REGISTRY
```

### 6.2 Build y Push
```bash
# Build todas las imágenes
make docker-build

# Tag y push (ejemplo: frontend)
docker tag carpeta-ciudadana/frontend:latest \
  YOUR_ECR_REGISTRY/carpeta-ciudadana/frontend:v1.0.0

docker push YOUR_ECR_REGISTRY/carpeta-ciudadana/frontend:v1.0.0
```

## 7. Despliegue con Helm

### 7.1 Actualizar values.yaml
```bash
cd deploy/helm/carpeta-ciudadana

# Editar values-prod.yaml con tus valores
vim values-prod.yaml
```

Ejemplo de valores a actualizar:
```yaml
global:
  imageRegistry: YOUR_ECR_REGISTRY

config:
  database:
    host: YOUR_RDS_ENDPOINT
  s3:
    bucket: YOUR_S3_BUCKET
  opensearch:
    host: YOUR_OPENSEARCH_ENDPOINT
  cognito:
    userPoolId: YOUR_USER_POOL_ID
    clientId: YOUR_CLIENT_ID
  mintic:
    operatorId: YOUR_OPERATOR_ID
    operatorName: YOUR_OPERATOR_NAME
```

### 7.2 Deploy
```bash
# Crear namespace
kubectl create namespace carpeta-ciudadana-prod

# Deploy con Helm
helm upgrade --install carpeta-ciudadana . \
  -f values-prod.yaml \
  --namespace carpeta-ciudadana-prod \
  --wait \
  --timeout 10m

# Verificar pods
kubectl get pods -n carpeta-ciudadana-prod

# Ver logs
kubectl logs -f deployment/carpeta-ciudadana-gateway \
  -n carpeta-ciudadana-prod
```

## 8. Configurar Ingress

### 8.1 Instalar AWS Load Balancer Controller
```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=carpeta-ciudadana-prod \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

### 8.2 Obtener URL del ALB
```bash
kubectl get ingress -n carpeta-ciudadana-prod

# Configurar DNS (Route 53)
# Apuntar carpeta-ciudadana.example.com al ALB
```

## 9. Configurar CI/CD (GitHub Actions)

### 9.1 Secrets de GitHub
En GitHub → Settings → Secrets and variables → Actions, agregar:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `ECR_REGISTRY`

### 9.2 Verificar Workflow
```bash
# Push a main dispara el pipeline
git push origin main

# Ver en GitHub Actions
# https://github.com/tu-org/carpeta-ciudadana/actions
```

## 10. Registro en Hub MinTIC

### 10.1 Registrar Operador
```bash
curl -X POST https://hub.mintic.gov.co/apis/registerOperator \
  --cert client.crt \
  --key client.key \
  --cacert ca-bundle.crt \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tu Operador",
    "address": "Cra 34 # 35 -67",
    "contactMail": "info@tuoperador.com",
    "participants": ["Nombre 1", "Nombre 2"]
  }'

# Guardar el operatorId retornado
```

### 10.2 Registrar Endpoint de Transferencia
```bash
curl -X PUT https://hub.mintic.gov.co/apis/registerTransferEndPoint \
  --cert client.crt \
  --key client.key \
  --cacert ca-bundle.crt \
  -H "Content-Type: application/json" \
  -d '{
    "idOperator": "TU_OPERATOR_ID",
    "endPoint": "https://tuoperador.com/api/transferCitizen",
    "endPointConfirm": "https://tuoperador.com/api/transferCitizenConfirm"
  }'
```

## 11. Verificación Post-Despliegue

### 11.1 Health Checks
```bash
# Frontend
curl https://carpeta-ciudadana.example.com

# Gateway
curl https://carpeta-ciudadana.example.com/api/health

# Servicios internos
kubectl exec -it deployment/carpeta-ciudadana-gateway \
  -n carpeta-ciudadana-prod -- \
  curl http://carpeta-ciudadana-citizen:8000/health
```

### 11.2 Logs y Métricas
```bash
# Ver logs
kubectl logs -f deployment/carpeta-ciudadana-gateway \
  -n carpeta-ciudadana-prod

# Metrics (Prometheus)
kubectl port-forward svc/prometheus-server 9090:80 \
  -n monitoring

# Jaeger UI
kubectl port-forward svc/jaeger-query 16686:16686
```

### 11.3 Tests de Integración
```bash
# Test de registro de ciudadano
curl -X POST https://carpeta-ciudadana.example.com/api/citizen/register \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1234567890,
    "name": "Test User",
    "address": "Test Address",
    "email": "test@example.com",
    "operatorId": "TU_OPERATOR_ID",
    "operatorName": "Tu Operador"
  }'
```

## 12. Mantenimiento

### 12.1 Actualizar Servicios
```bash
# Build nueva versión
make docker-build

# Tag
docker tag carpeta-ciudadana/gateway:latest \
  YOUR_ECR_REGISTRY/carpeta-ciudadana/gateway:v1.0.1

# Push
docker push YOUR_ECR_REGISTRY/carpeta-ciudadana/gateway:v1.0.1

# Update Helm
helm upgrade carpeta-ciudadana deploy/helm/carpeta-ciudadana \
  -f deploy/helm/carpeta-ciudadana/values-prod.yaml \
  --set gateway.image.tag=v1.0.1 \
  --namespace carpeta-ciudadana-prod
```

### 12.2 Scaling
```bash
# Manual
kubectl scale deployment carpeta-ciudadana-gateway \
  --replicas=5 \
  -n carpeta-ciudadana-prod

# HPA automático (ya configurado en Helm)
kubectl get hpa -n carpeta-ciudadana-prod
```

### 12.3 Backups

#### Base de Datos
```bash
# Snapshot automático de RDS (configurado en Terraform)
aws rds create-db-snapshot \
  --db-instance-identifier carpeta-ciudadana-prod \
  --db-snapshot-identifier manual-backup-$(date +%Y%m%d)
```

#### S3
```bash
# Versionado habilitado (en Terraform)
# Lifecycle policies para mover a Glacier después de 90 días
```

## 13. Troubleshooting

### 13.1 Pods no inician
```bash
kubectl describe pod POD_NAME -n carpeta-ciudadana-prod
kubectl logs POD_NAME -n carpeta-ciudadana-prod
```

### 13.2 Problemas de conectividad
```bash
# Test desde un pod
kubectl run -it --rm debug \
  --image=nicolaka/netshoot \
  -n carpeta-ciudadana-prod -- bash

# Dentro del pod
curl http://carpeta-ciudadana-gateway:8000/health
nslookup carpeta-ciudadana-gateway
```

### 13.3 Problemas con mTLS
```bash
# Verificar certificados
openssl x509 -in client.crt -text -noout

# Test de conexión
curl -v \
  --cert client.crt \
  --key client.key \
  --cacert ca-bundle.crt \
  https://hub.mintic.gov.co/apis/getOperators
```

## 14. Rollback

### 14.1 Helm
```bash
# Ver historial
helm history carpeta-ciudadana -n carpeta-ciudadana-prod

# Rollback a versión anterior
helm rollback carpeta-ciudadana 1 -n carpeta-ciudadana-prod
```

### 14.2 Terraform
```bash
cd infra/terraform

# Volver a versión anterior del state
terraform state pull > backup.tfstate

# Aplicar configuración anterior
git checkout COMMIT_ANTERIOR
terraform apply
```

## 15. Monitoreo y Alertas

### 15.1 CloudWatch Alarms
- CPU alta (>80%)
- Memoria alta (>80%)
- Errores HTTP 5xx
- Latencia P99 alta

### 15.2 Logs Centralizados
- CloudWatch Logs Insights
- OpenTelemetry traces en Jaeger
- Métricas en Prometheus/Grafana

## 16. Seguridad

### 16.1 Rotación de Secretos
```bash
# Rotar certificados mTLS (cada 90 días)
# Rotar contraseñas de BD (cada 30 días)
# Rotar API keys (cada 60 días)
```

### 16.2 Auditoría
- Todos los eventos firmados con JWS
- Logs en CloudWatch con retención de 90 días
- Traces en X-Ray para análisis forense

## Soporte

Para ayuda adicional:
- Documentación: `/docs`
- Issues: GitHub Issues
- Email: soporte@tuoperador.com


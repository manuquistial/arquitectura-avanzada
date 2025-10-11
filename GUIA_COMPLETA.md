# 📚 Carpeta Ciudadana - Guía Completa del Proyecto

> Sistema de Carpeta Ciudadana con arquitectura de microservicios event-driven  
> **Migrado de AWS a Azure** | **Python 3.13** | **Node.js 22** | **Kubernetes (AKS)**

---

## 📖 Índice

1. [Visión General](#visión-general)
2. [Arquitectura](#arquitectura)
3. [Servicios Implementados](#servicios-implementados)
4. [Infraestructura Azure](#infraestructura-azure)
5. [Desarrollo Local](#desarrollo-local)
6. [CI/CD con GitHub Actions](#cicd-con-github-actions)
7. [Deployment](#deployment)
8. [Testing](#testing)
9. [Configuración](#configuración)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Visión General

### ¿Qué es Carpeta Ciudadana?

Sistema que permite a los ciudadanos:
- ✅ Registrarse en un operador (ej: universidad, gobierno)
- ✅ Subir y almacenar documentos digitales
- ✅ Buscar y recuperar documentos
- ✅ Transferir documentos entre operadores (P2P)
- ✅ Compartir documentos de forma segura

### Arquitectura de Alto Nivel

```
┌─────────────┐
│  Frontend   │  Next.js 14 (App Router)
│ localhost:  │  
│    3000     │
└──────┬──────┘
       │
┌──────▼──────┐
│   Gateway   │  Rate Limiting + Auth
│ localhost:  │
│    8000     │
└──────┬──────┘
       │
       ├─────────────────────────────────┐
       │                                 │
┌──────▼──────┐  ┌──────────┐   ┌──────▼──────┐
│   Citizen   │  │Ingestion │   │  Metadata   │
│     8001    │  │   8002   │   │    8003     │
└─────────────┘  └──────────┘   └─────────────┘
       │                                 │
       │         ┌──────────┐           │
       ├─────────►MinTIC Hub│           │
       │         │ GovCarpe │           │
       │         │   ta     │           │
       │         └──────────┘           │
       │                                 │
┌──────▼──────────────────────────────▼──┐
│       Azure Infrastructure              │
│  • PostgreSQL  • Blob Storage           │
│  • Service Bus • OpenSearch             │
└─────────────────────────────────────────┘
```

---

## 🏗️ Arquitectura

### Stack Tecnológico

#### Frontend
- **Framework**: Next.js 14 (App Router)
- **Runtime**: Node.js 22 (con nvm)
- **Lenguaje**: TypeScript
- **Estilos**: Tailwind CSS
- **Fuente**: Montserrat (global)
- **Puerto**: 3000

#### Backend
- **Framework**: FastAPI
- **Runtime**: Python 3.13.7
- **Package Manager**: Poetry 2.2.1
- **Base de Datos**: PostgreSQL (asyncpg)
- **Cache**: Redis
- **Búsqueda**: OpenSearch
- **HTTP Client**: httpx 0.26.x

#### Infraestructura
- **Cloud**: Microsoft Azure
- **Orquestación**: Kubernetes (AKS)
- **IaC**: Terraform 1.6+
- **Deploy**: Helm 3.13+
- **CI/CD**: GitHub Actions (Federated Credentials)
- **Registry**: Docker Hub

### Microservicios

| Servicio | Puerto | Descripción | Base de Datos |
|----------|--------|-------------|---------------|
| **frontend** | 3000 | Next.js UI | - |
| **gateway** | 8000 | API Gateway, rate limiting, auth | Redis |
| **citizen** | 8001 | Gestión de ciudadanos | PostgreSQL |
| **ingestion** | 8002 | Upload/download documentos | PostgreSQL |
| **metadata** | 8003 | Metadata y búsqueda | PostgreSQL + OpenSearch |
| **transfer** | 8004 | Transferencias P2P | PostgreSQL |
| **mintic_client** | 8005 | Cliente hub MinTIC (GovCarpeta) | - |

### Patrones de Arquitectura

- ✅ **Microservicios**: Cada servicio es independiente
- ✅ **Event-Driven**: (Preparado para Service Bus/SQS)
- ✅ **CQRS**: (Preparado, reads vs writes separados)
- ✅ **API Gateway**: Gateway centralizado con rate limiting
- ✅ **Service Discovery**: URLs auto-detectan ambiente (local vs K8s)
- ✅ **Presigned URLs**: Upload/download directo a storage sin pasar por backend

---

## 🔧 Servicios Implementados

### 1. Gateway Service

**Responsabilidades:**
- Routing a microservicios backend
- Rate limiting (60 req/min)
- Validación JWT (OIDC)
- CORS habilitado

**Configuración:**
```bash
# Variables de entorno
ENVIRONMENT=development
RATE_LIMIT_PER_MINUTE=60
REDIS_HOST=localhost
REDIS_PORT=6379
CITIZEN_SERVICE_URL=http://localhost:8001
INGESTION_SERVICE_URL=http://localhost:8002
METADATA_SERVICE_URL=http://localhost:8003
...
```

**Rutas Públicas (sin auth):**
- `/health`
- `/docs`
- `/api/citizens/register`
- `/api/auth/login`

### 2. Citizen Service

**Responsabilidades:**
- Registrar ciudadanos en DB local
- Sincronizar con hub MinTIC (GovCarpeta)
- Gestionar afiliaciones

**Flujo de Registro:**
```
1. Frontend → POST /api/citizens/register
2. Citizen service guarda en PostgreSQL
3. Llama a mintic_client → POST /apis/registerCitizen
4. mintic_client → Hub GovCarpeta
5. Retorna success al frontend
```

**Integración MinTIC:**
- URL configurable vía `MINTIC_CLIENT_URL`
- Auto-detección: localhost (dev) vs K8s service (prod)
- Timeout: 5 segundos
- No bloquea si MinTIC falla

### 3. Ingestion Service

**Responsabilidades:**
- Generar presigned URLs para upload (PUT)
- Generar presigned URLs para download (GET)
- Guardar metadata de documentos
- Confirmar uploads y verificar integridad

**Flujo de Upload:**
```
1. Frontend solicita → POST /api/documents/upload-url
2. Ingestion genera presigned URL (Azure Blob o S3)
3. Ingestion guarda metadata en PostgreSQL (status=pending)
4. Frontend sube archivo directo a storage con PUT
5. Frontend confirma → POST /api/documents/confirm-upload
6. Ingestion actualiza status=uploaded y hash SHA-256
```

**Cloud Provider:**
- Detecta via `CLOUD_PROVIDER` env var
- Soporta Azure Blob Storage y AWS S3
- Presigned URLs con expiración de 1 hora

### 4. Metadata Service (✨ NUEVO)

**Responsabilidades:**
- Listar documentos por ciudadano
- Búsqueda full-text (PostgreSQL ILIKE + OpenSearch preparado)
- Eliminar documentos (soft delete)
- Obtener metadata de documento

**Endpoints:**
- `GET /api/metadata/documents?citizen_id={id}` - Listar documentos
- `GET /api/metadata/search?q={query}` - Buscar documentos
- `DELETE /api/metadata/documents/{id}` - Eliminar documento
- `GET /api/metadata/documents/{id}` - Obtener metadata

**Base de Datos:**
- Tabla compartida con ingestion: `document_metadata`
- Campos: id, citizen_id, filename, content_type, size_bytes, sha256_hash, blob_name, storage_provider, status, description, tags, created_at, is_deleted

### 5. Transfer Service

**Responsabilidades:**
- Transferencias P2P entre operadores
- Gestión de idempotencia
- Confirmación de transferencias

**Flujo P2P:**
```
1. Operador A inicia transferencia
2. POST /api/transferCitizen a operador B
3. Operador B descarga docs con presigned URLs
4. Operador B confirma: POST /api/transferCitizenConfirm
5. Operador A elimina datos tras confirmación
```

### 6. MinTIC Client Service

**Responsabilidades:**
- Integración con hub MinTIC (GovCarpeta APIs)
- Registro de ciudadanos y operadores
- Autenticación de documentos

**Hub MinTIC (GovCarpeta):**
- URL: `https://govcarpeta-apis-4905ff3c005b.herokuapp.com`
- Autenticación: API pública (sin OAuth ni mTLS)
- Operator ID: `operator-demo` (configurable)

**Endpoints Implementados:**
- `POST /apis/registerCitizen` - Registrar ciudadano
- `DELETE /apis/unregisterCitizen` - Desafiliar ciudadano
- `PUT /apis/authenticateDocument` - Autenticar documento
- `GET /apis/validateCitizen/{id}` - Validar ciudadano
- `POST /apis/registerOperator` - Registrar operador
- `PUT /apis/registerTransferEndPoint` - Registrar endpoint P2P
- `GET /apis/getOperators` - Listar operadores

---

## ☁️ Infraestructura Azure

### Recursos Desplegados

**Región:** northcentralus (Iowa, USA)  
**Resource Group:** carpeta-ciudadana-dev-rg

| Recurso | Nombre | Detalles | Costo/mes |
|---------|--------|----------|-----------|
| **AKS Cluster** | carpeta-ciudadana-dev | 1 nodo B2s (2 vCPU, 4GB) | ~$36 |
| **PostgreSQL** | dev-psql-server | Flexible Server (Burstable B1ms) | ~$13 |
| **Storage Account** | devcarpetastorage | Blob Storage (LRS) | ~$0.50 |
| **Service Bus** | dev-carpeta-bus | Basic tier (2 queues) | ~$0.05 |
| **VNet** | dev-vnet | 10.0.0.0/16 | Gratis |
| **NSG** | dev-nsg | Security rules | Gratis |

**Total estimado:** ~$44.79/mes  
**Con $100 USD:** 2-5 meses de uso

### Servicios Comentados (para free tier)

Los siguientes servicios estaban en el plan original pero fueron comentados para ahorrar costos:

- ❌ **Azure Cognitive Search** (~$250/mes)
- ❌ **Azure Container Registry** (~$5-20/mes)
- ❌ **Azure Key Vault** (~$0.03/mes pero requiere permisos)
- ❌ **Azure AD B2C** (Gratis con límites, requiere permisos)

**Alternativas usadas:**
- OpenSearch en Docker local/K8s pods
- Docker Hub (gratis para repos públicos)
- Secrets en Kubernetes Secrets
- Cognito OIDC (preparado, usando mock por ahora)

### Conexión a Azure

**Herramientas:**
```bash
# Azure CLI
az login
az account set --subscription <subscription-id>

# kubectl (AKS)
az aks get-credentials \
  --resource-group carpeta-ciudadana-dev-rg \
  --name carpeta-ciudadana-dev
  
kubectl get nodes
kubectl get pods -n carpeta-ciudadana
```

---

## 💻 Desarrollo Local

### Requisitos

- **Node.js**: 22.16.0 (instalar con nvm)
- **Python**: 3.13.7
- **Poetry**: 2.2.1
- **Docker**: Desktop o Engine
- **Git**: Con SSH configurado

### Opción 1: Desarrollo con venv (Recomendado)

Más rápido, código se actualiza al instante.

```bash
# 1. Levantar infraestructura
docker-compose up -d

# 2. Iniciar servicios
./start-services.sh

# Servicios disponibles:
# - Frontend: http://localhost:3000
# - Gateway: http://localhost:8000
# - Citizen: http://localhost:8001
# - Ingestion: http://localhost:8002
# - Metadata: http://localhost:8003
# - Transfer: http://localhost:8004
# - MinTIC: http://localhost:8005

# 3. Detener servicios
./stop-services.sh
docker-compose down
```

### Opción 2: Stack completo en Docker

Simula ambiente de producción.

```bash
# 1. Build imágenes
./build-all.sh

# 2. Levantar stack completo
export TAG=local
docker-compose --profile app up -d

# 3. Ver logs
docker-compose logs -f gateway

# 4. Detener
docker-compose --profile app down
```

### Opción 3: Usando Makefile

```bash
# Desarrollo con venv
make dev-up       # Levanta infra + servicios
make dev-down     # Para todo

# Desarrollo con Docker
make dev-docker   # Build + stack completo

# Testing
make test-unit    # Unit tests
make lint         # Linters
make format       # Format code

# Build
make docker-build # Build imágenes

# Cleanup
make clean        # Limpia artifacts
```

### Variables de Entorno

Crear archivo `.env` en cada servicio (ver `.env.example`):

```bash
# services/citizen/.env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/carpeta_ciudadana
MINTIC_CLIENT_URL=http://localhost:8005
ENVIRONMENT=development

# apps/frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_OPERATOR_ID=operator-demo
NEXT_PUBLIC_OPERATOR_NAME=Carpeta Ciudadana Demo
```

---

## 🚀 CI/CD con GitHub Actions

### Configuración

**Autenticación:** Federated Credentials (sin Service Principal)

**Managed Identity:**
- Name: `github-actions-identity`
- Client ID: `7c7ccca1-aee5-457a-a0c1-aba3c3d21aa7`
- Permissions: Contributor en `carpeta-ciudadana-dev-rg`

**GitHub Secrets Requeridos:**
```bash
AZURE_CLIENT_ID=7c7ccca1-aee5-457a-a0c1-aba3c3d21aa7
AZURE_TENANT_ID=<tu-tenant-id>
AZURE_SUBSCRIPTION_ID=<tu-subscription-id>
DOCKERHUB_USERNAME=manuelquistial
DOCKERHUB_TOKEN=dckr_pat_xxxxx
```

### Workflow Pipeline

Archivo: `.github/workflows/ci-azure-federated.yml`

**Fases:**

1. **Lint & Security Scan** (~2 min)
   - Ruff para Python
   - ESLint para TypeScript
   - Trivy security scan

2. **Backend Tests** (~3 min)
   - Unit tests con pytest
   - Servicios en paralelo: gateway, citizen, ingestion, metadata, transfer, mintic_client

3. **Frontend Tests** (~2 min)
   - Type checking
   - Build verification

4. **Build & Push Images** (~5 min)
   - Docker build en paralelo
   - Push a Docker Hub
   - Tags: `latest` y `{git-sha}`

5. **Deploy to AKS** (~3 min)
   - Azure login con federated credentials
   - Set AKS context
   - Helm upgrade --install

**Tiempo total:** ~15 minutos

### Trigger del Pipeline

```bash
# Cualquier push a master
git push origin master

# Ver estado
gh run list
gh run watch

# Ver logs
gh run view --log
```

---

## 📦 Deployment

### Helm Charts

Estructura:
```
deploy/helm/carpeta-ciudadana/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── serviceaccount.yaml
│   ├── deployment-gateway.yaml
│   ├── deployment-citizen.yaml
│   ├── deployment-ingestion.yaml
│   ├── deployment-metadata.yaml
│   ├── deployment-transfer.yaml
│   └── deployment-mintic-client.yaml
```

### Deploy Manual a AKS

```bash
# 1. Conectar a AKS
az aks get-credentials \
  --resource-group carpeta-ciudadana-dev-rg \
  --name carpeta-ciudadana-dev

# 2. Verificar conexión
kubectl get nodes

# 3. Deploy con Helm
helm upgrade --install carpeta-ciudadana \
  deploy/helm/carpeta-ciudadana \
  --namespace carpeta-ciudadana \
  --create-namespace \
  --set global.imageRegistry=manuelquistial \
  --set frontend.image.tag=latest \
  --set gateway.image.tag=latest \
  --set citizen.image.tag=latest \
  --set ingestion.image.tag=latest \
  --set metadata.image.tag=latest \
  --set transfer.image.tag=latest \
  --set minticClient.image.tag=latest \
  --wait \
  --timeout 10m

# 4. Verificar deployment
kubectl get pods -n carpeta-ciudadana
kubectl get svc -n carpeta-ciudadana

# 5. Ver logs
kubectl logs -f deployment/carpeta-ciudadana-gateway -n carpeta-ciudadana
```

### Acceder a la Aplicación

```bash
# Obtener IP del frontend
kubectl get svc carpeta-ciudadana-frontend -n carpeta-ciudadana

# Port-forward para testing local
kubectl port-forward svc/carpeta-ciudadana-gateway 8000:8000 -n carpeta-ciudadana
kubectl port-forward svc/carpeta-ciudadana-frontend 3000:80 -n carpeta-ciudadana
```

---

## 🧪 Testing

### Unit Tests

```bash
# Todos los servicios
make test-unit

# Servicio individual
cd services/gateway
poetry run pytest tests/unit -v

# Con coverage
poetry run pytest --cov=app tests/unit
```

### Integration Tests

```bash
# Levantar stack completo
docker-compose --profile app up -d

# Testing manual
curl http://localhost:8000/health

# Register citizen
curl -X POST http://localhost:8000/api/citizens/register \
  -H "Content-Type: application/json" \
  -d '{
    "id": 123456,
    "name": "Test User",
    "address": "Test Address",
    "email": "test@example.com",
    "operator_id": "operator-demo",
    "operator_name": "Carpeta Demo"
  }'
```

### E2E Tests (Frontend)

```bash
cd apps/frontend
npm run test:e2e
```

---

## ⚙️ Configuración

### Service Discovery

Los servicios se descubren automáticamente según el ambiente:

```python
# services/citizen/app/config.py
def get_service_url(service_name: str, default_port: int) -> str:
    env = os.getenv("ENVIRONMENT", "development")
    if env == "development":
        return f"http://localhost:{default_port}"
    else:
        # Kubernetes service discovery
        release_name = os.getenv("HELM_RELEASE_NAME", "carpeta-ciudadana")
        return f"http://{release_name}-{service_name}:8000"
```

**Resultado:**
- Local: `http://localhost:8005` (mintic_client)
- K8s: `http://carpeta-ciudadana-mintic-client:8000`

### Variables de Entorno por Servicio

#### Gateway
```bash
ENVIRONMENT=development
RATE_LIMIT_PER_MINUTE=60
REDIS_HOST=redis
CITIZEN_SERVICE_URL=http://carpeta-ciudadana-citizen:8000
INGESTION_SERVICE_URL=http://carpeta-ciudadana-ingestion:8000
METADATA_SERVICE_URL=http://carpeta-ciudadana-metadata:8000
TRANSFER_SERVICE_URL=http://carpeta-ciudadana-transfer:8000
MINTIC_CLIENT_URL=http://carpeta-ciudadana-mintic-client:8000
```

#### Citizen
```bash
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/carpeta_ciudadana
MINTIC_CLIENT_URL=http://carpeta-ciudadana-mintic-client:8000
```

#### Ingestion
```bash
ENVIRONMENT=development
CLOUD_PROVIDER=azure
DATABASE_URL=postgresql+asyncpg://...
AZURE_STORAGE_ACCOUNT_NAME=devcarpetastorage
AZURE_STORAGE_ACCOUNT_KEY=...
AZURE_STORAGE_CONTAINER_NAME=documents
```

#### Metadata
```bash
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://...
OPENSEARCH_HOST=opensearch
OPENSEARCH_PORT=9200
```

#### MinTIC Client
```bash
ENVIRONMENT=development
MINTIC_BASE_URL=https://govcarpeta-apis-4905ff3c005b.herokuapp.com
MINTIC_OPERATOR_ID=operator-demo
MINTIC_OPERATOR_NAME=Carpeta Ciudadana Demo
```

---

## 🛠️ Troubleshooting

### Error: asyncpg incompatible con Python 3.13

**Solución:** Actualizar a asyncpg 0.30.0+
```toml
asyncpg = "^0.30.0"
```

### Error: email-validator not installed

**Solución:** Usar pydantic con extras email
```toml
pydantic = {extras = ["email"], version = "^2.5.0"}
```

### Error: CORS bloqueado

**Solución:** Asegurar que OPTIONS requests no requieran auth
```python
# gateway/app/middleware.py
if request.method == "OPTIONS":
    return await call_next(request)
```

### Error: ImagePullBackOff en AKS

**Causas:**
1. Imagen no existe en Docker Hub
2. Secrets no configurados

**Solución:**
```bash
# Verificar secrets
gh secret list

# Configurar Docker Hub
gh secret set DOCKERHUB_USERNAME --body "manuelquistial"
gh secret set DOCKERHUB_TOKEN --body "dckr_pat_xxxxx"

# Trigger redeploy
git commit --allow-empty -m "Trigger redeploy"
git push
```

### Error: ServiceAccount ownership en Helm

**Solución:** Eliminar SA manual y dejar que Helm lo cree
```bash
kubectl delete serviceaccount carpeta-ciudadana-sa -n carpeta-ciudadana
```

### LocalStack: Device or resource busy

**Solución:** LocalStack deshabilitado (usando Azure real)
```yaml
# docker-compose.yml
# localstack: comentado
```

---

## 📊 Comandos Útiles

### Docker

```bash
# Ver contenedores corriendo
docker-compose ps

# Ver logs
docker-compose logs -f gateway

# Rebuild un servicio
docker-compose up -d --build citizen

# Limpiar todo
docker-compose down -v
docker system prune -a
```

### Kubernetes

```bash
# Pods
kubectl get pods -n carpeta-ciudadana
kubectl describe pod <pod-name> -n carpeta-ciudadana
kubectl logs -f <pod-name> -n carpeta-ciudadana

# Services
kubectl get svc -n carpeta-ciudadana

# Helm
helm list -n carpeta-ciudadana
helm status carpeta-ciudadana -n carpeta-ciudadana

# Debugging
kubectl exec -it <pod-name> -n carpeta-ciudadana -- /bin/sh
```

### Git

```bash
# Ver status
git status

# Commit y push
git add .
git commit -m "mensaje"
git push origin master

# Ver pipeline
gh run list
gh run watch
```

---

## 📈 Próximos Pasos

### Implementaciones Pendientes

1. **Event Publishing** (Service Bus/SQS)
   - Publicar eventos en register/unregister
   - Consumers para procesamiento async

2. **OpenSearch Integration**
   - Indexar documentos automáticamente
   - Full-text search optimizado

3. **Signature Service**
   - Firma digital XAdES/CAdES/PAdES
   - Integración con TSA

4. **Sharing & Notification Services**
   - Compartir paquetes de documentos
   - Notificaciones por email/webhook

5. **Auth Real con Cognito/Azure AD B2C**
   - OIDC completo
   - Login social
   - MFA

### Optimizaciones

- [ ] Cache de metadata con Redis
- [ ] CDN para assets estáticos
- [ ] Compression de documentos
- [ ] Batching de eventos
- [ ] Rate limiting adaptativo

---

## 📝 Notas Importantes

### Versiones del Proyecto

- **Python**: 3.13.7
- **Poetry**: 2.2.1
- **Node.js**: 22.16.0 (via nvm)
- **Terraform**: 1.6+
- **Helm**: 3.13+

### Convenciones del Código

- **Backend**: Ruff para linting/formatting
- **Frontend**: ESLint + Prettier
- **Commits**: Conventional Commits
- **Branches**: master (main branch)

### Docker Hub

- **Username**: manuelquistial
- **Registry**: docker.io/manuelquistial/carpeta-ciudadana/*
- **Tags**: 
  - `latest` - última versión estable
  - `{git-sha}` - versión específica por commit

### GovCarpeta Hub

- **URL**: https://govcarpeta-apis-4905ff3c005b.herokuapp.com
- **Tipo**: API pública (sin autenticación)
- **Operator ID**: operator-demo (cambiar para producción)

---

## 🎓 Para Proyecto Universitario

### Free Tier Optimization

El proyecto está optimizado para maximizar el uso del free tier:

**Azure for Students ($100 créditos):**
- ✅ AKS con nodos pequeños (B2s)
- ✅ PostgreSQL Flexible Burstable (B1ms)
- ✅ Blob Storage LRS (económico)
- ✅ Service Bus Basic (sin topics)
- ❌ Cognitive Search deshabilitado
- ❌ ACR deshabilitado (usa Docker Hub)

**Tiempo de uso estimado:** 2-5 meses con $100

**Alternativas gratuitas:**
- OpenSearch en pods (en lugar de Cognitive Search)
- Docker Hub (en lugar de ACR)
- Secrets de K8s (en lugar de Key Vault)

### Presentación del Proyecto

**Puntos clave para demostrar:**

1. ✅ Arquitectura de microservicios moderna
2. ✅ CI/CD automatizado con GitHub Actions
3. ✅ Kubernetes en Azure (AKS)
4. ✅ Infraestructura como Código (Terraform)
5. ✅ Integración con API real (GovCarpeta)
6. ✅ Frontend moderno con Next.js 14
7. ✅ Observabilidad con OpenTelemetry
8. ✅ Multi-cloud ready (AWS + Azure)

---

## 🔗 Enlaces Útiles

- **Repositorio**: https://github.com/manuquistial/arquitectura-avanzada
- **Docker Hub**: https://hub.docker.com/u/manuelquistial
- **GovCarpeta API**: https://govcarpeta-apis-4905ff3c005b.herokuapp.com

---

## 📞 Soporte

Para problemas o preguntas:
1. Ver logs: `docker-compose logs -f {service}`
2. Consultar esta guía
3. Revisar GitHub Actions logs
4. Verificar configuración de Azure

---

**Última actualización:** 11 Octubre 2025  
**Versión:** 1.0.0  
**Autor:** Manuel Jurado (Universidad)


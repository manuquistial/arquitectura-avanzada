# Arquitectura del Sistema - Carpeta Ciudadana

> **Última actualización:** 11 Octubre 2025  
> **Cloud Provider:** Microsoft Azure  
> **Estado:** Migrado de AWS a Azure, completamente funcional

---

## 📋 Visión General

Sistema de Carpeta Ciudadana implementado como operador en **Azure** siguiendo arquitectura de microservicios event-driven con preparación para patrones CQRS.

### Decisiones Arquitectónicas Clave

1. **Microservicios** sobre monolito para escalabilidad independiente
2. **Event-Driven** preparado (Service Bus) para desacoplamiento
3. **Presigned URLs** para upload/download sin pasar por backend (performance)
4. **Service Discovery** automático (local vs Kubernetes)
5. **Multi-cloud** ready (AWS + Azure con abstracción)

---

## 🏗️ Arquitectura de Microservicios

### Frontend

**Tecnología:** Next.js 14 (App Router) con Node.js 22

**Características:**
- ✅ TypeScript estricto
- ✅ Tailwind CSS con fuente Montserrat
- ✅ Inputs con fondo claro (preferencia del usuario)
- ✅ Textos localizados en español (Colombia)
- ✅ Sin labels en inputs
- ✅ API calls directas (sin mocks)

**Rutas Principales:**
- `/` - Landing page
- `/login` - Login (mock, preparado para OIDC)
- `/register` - Registro de ciudadanos
- `/dashboard` - Panel principal
- `/upload` - Subida de documentos
- `/documents` - Lista de documentos
- `/search` - Búsqueda de documentos
- `/transfer` - Transferencias P2P

**Integración Backend:**
- API Gateway: `http://localhost:8000` (dev) / LoadBalancer IP (prod)
- Maneja errores 404 gracefully
- Timeout: 30 segundos

---

### Backend Services

#### 1. Gateway Service (Puerto 8000)

**Responsabilidades:**
- API Gateway centralizado
- Rate limiting (60 req/min con Redis)
- Validación JWT (preparado para Cognito)
- CORS habilitado para todos los orígenes
- Routing a microservicios internos

**Tecnologías:**
- FastAPI
- Redis (rate limiting)
- SlowAPI (rate limiter)
- httpx (proxy HTTP)

**Rutas Públicas (sin autenticación):**
- `/health` - Health check
- `/docs` - Swagger UI
- `/api/citizens/register` - Registro de ciudadanos
- `/api/auth/login` - Login
- `OPTIONS *` - CORS preflight requests

**Service Map:**
```python
{
    "citizen": "http://carpeta-ciudadana-citizen:8000",
    "ingestion": "http://carpeta-ciudadana-ingestion:8000",
    "metadata": "http://carpeta-ciudadana-metadata:8000",
    "transfer": "http://carpeta-ciudadana-transfer:8000",
    "mintic": "http://carpeta-ciudadana-mintic-client:8000",
}
```

**Rate Limiting:**
- Por IP con Redis
- 60 requests/minuto (configurable)
- Respuesta 429 Too Many Requests si excede

---

#### 2. Citizen Service (Puerto 8001)

**Responsabilidades:**
- Registro y gestión de ciudadanos
- Sincronización con hub MinTIC (GovCarpeta)
- Almacenamiento en PostgreSQL
- Validación de ciudadanos

**Base de Datos:**
- Tabla: `citizens`
- Campos: id, name, address, email, operator_id, operator_name, is_active, created_at

**Flujo de Registro:**
```
1. Frontend → POST /api/citizens/register {id, name, address, email, operator_id}
2. Citizen service valida datos
3. Guarda en PostgreSQL
4. Llama async a mintic_client (no bloquea si falla)
5. mintic_client → GovCarpeta hub
6. Retorna success al frontend
```

**Configuración:**
```bash
ENVIRONMENT=development|production
DATABASE_URL=postgresql+asyncpg://...
MINTIC_CLIENT_URL=http://localhost:8005 (dev) | http://carpeta-ciudadana-mintic-client:8000 (K8s)
```

**Dependencias:**
- pydantic[email] para validación de EmailStr
- httpx para calls a mintic_client
- asyncpg para PostgreSQL

---

#### 3. Ingestion Service (Puerto 8002)

**Responsabilidades:**
- Generar presigned URLs para upload (PUT)
- Generar presigned URLs para download (GET)
- Guardar metadata de documentos
- Confirmar uploads y verificar SHA-256

**Cloud Provider Support:**
- Azure Blob Storage (producción)
- AWS S3 (legacy, compatible)
- Auto-detecta via `CLOUD_PROVIDER` env var

**Flujo de Upload:**
```
1. Frontend → POST /api/documents/upload-url
   Request: {citizen_id, filename, content_type}

2. Ingestion genera:
   - document_id (UUID)
   - blob_name: citizens/{citizen_id}/{uuid}-{filename}
   - presigned PUT URL (1 hora expiración)

3. Ingestion guarda metadata en DB:
   - status=pending
   - storage_provider=azure
   
4. Frontend hace PUT directo a Blob Storage

5. Frontend confirma → POST /api/documents/confirm-upload
   - Actualiza status=uploaded
   - Guarda SHA-256 hash
```

**Presigned URL Generation (Azure):**
```python
from azure.storage.blob import generate_blob_sas, BlobSasPermissions

sas_token = generate_blob_sas(
    account_name=account_name,
    container_name=container_name,
    blob_name=blob_name,
    account_key=account_key,
    permission=BlobSasPermissions(write=True),
    expiry=datetime.utcnow() + timedelta(hours=1)
)

url = f"https://{account_name}.blob.core.windows.net/{container}/{blob}?{sas}"
```

**Base de Datos:**
- Tabla: `document_metadata` (compartida con metadata service)
- SQLAlchemy async con asyncpg

---

#### 4. Metadata Service (Puerto 8003) ✨ NUEVO

**Responsabilidades:**
- Listar documentos por ciudadano
- Búsqueda full-text de documentos
- Eliminar documentos (soft delete)
- Obtener metadata de documento

**Endpoints:**

**GET /api/metadata/documents?citizen_id={id}&skip=0&limit=100**
```json
Response:
{
  "documents": [
    {
      "id": "uuid",
      "filename": "documento.pdf",
      "content_type": "application/pdf",
      "size": 1024000,
      "status": "uploaded",
      "description": "...",
      "created_at": "2025-10-11T..."
    }
  ],
  "total": 10
}
```

**GET /api/metadata/search?q={query}&limit=20**
```json
Response:
{
  "results": [
    {
      "id": "uuid",
      "title": "Diploma",
      "description": "...",
      "filename": "diploma.pdf",
      "created_at": "2025-10-11T...",
      "score": 0.95
    }
  ],
  "total": 5,
  "took_ms": 42
}
```

**Implementación de Búsqueda:**
- Actual: PostgreSQL ILIKE (full-text básico)
- Futuro: OpenSearch para búsqueda avanzada
- Pattern matching en: filename, description, tags

**Base de Datos:**
- Tabla compartida: `document_metadata`
- Indices: citizen_id, created_at, is_deleted

---

#### 5. Transfer Service (Puerto 8004)

**Responsabilidades:**
- Transferencias P2P entre operadores
- Gestión de idempotencia con transfer tokens
- Confirmación bidireccional

**Flujo Completo:**

**1. Operador A inicia transferencia:**
```
GET /apis/getOperators (desde MinTIC hub)
→ Lista de operadores disponibles

POST /api/transfer/initiate
Request: {
  destination_operator_id: "operator-b",
  citizen_id: 123456
}
→ Obtiene transfer_endpoint de operador B
```

**2. Operador A → Operador B:**
```
POST {transfer_endpoint}/api/transferCitizen
Request: {
  "id": 123456,
  "name": "Juan Pérez",
  "address": "Calle 123",
  "operatorId": "operator-a",
  "operatorName": "Operador A",
  "urlDocuments": [
    "https://storage.blob.core.windows.net/docs/...",
    "https://storage.blob.core.windows.net/docs/..."
  ],
  "token": "unique-transfer-token"
}

Response: 200 OK "Ciudadano Transferido Exitosamente"
```

**3. Operador B descarga documentos y confirma:**
```
POST {operador_a_endpoint}/api/transferCitizenConfirm
Request: {
  "id": 123456,
  "req_status": 1,  // 1=success, 0=failed
  "operatorId": "operator-b",
  "operatorName": "Operador B",
  "token": "same-transfer-token"
}
```

**4. Operador A elimina datos si req_status=1**

**Idempotencia:**
- Token único por transferencia
- Validación de token en confirm
- Evita transferencias duplicadas

---

#### 6. MinTIC Client Service (Puerto 8005)

**Responsabilidades:**
- Integración con hub MinTIC (GovCarpeta APIs)
- Registro de ciudadanos y operadores
- Autenticación de documentos
- Obtener lista de operadores

**Hub MinTIC (GovCarpeta):**
- URL: `https://govcarpeta-apis-4905ff3c005b.herokuapp.com`
- Autenticación: **API pública** (sin OAuth ni mTLS)
- Retry logic: 3 intentos con exponential backoff

**Cambios respecto a spec original:**
- ❌ No requiere mTLS (GovCarpeta es público)
- ❌ No requiere OAuth 2.1 client_credentials
- ✅ HTTP simple con httpx
- ✅ Timeout: 30 segundos

**Endpoints Implementados:**

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/apis/registerCitizen` | POST | Registrar ciudadano en hub |
| `/apis/unregisterCitizen` | DELETE | Desafiliar ciudadano |
| `/apis/authenticateDocument` | PUT | Autenticar documento |
| `/apis/validateCitizen/{id}` | GET | Validar si existe ciudadano |
| `/apis/registerOperator` | POST | Registrar operador |
| `/apis/registerTransferEndPoint` | PUT | Registrar endpoint P2P |
| `/apis/getOperators` | GET | Listar operadores |

**Configuración:**
```bash
MINTIC_BASE_URL=https://govcarpeta-apis-4905ff3c005b.herokuapp.com
MINTIC_OPERATOR_ID=operator-demo
MINTIC_OPERATOR_NAME=Carpeta Ciudadana Demo
```

---

## ☁️ Infraestructura Azure

### Componentes Desplegados

**Resource Group:** carpeta-ciudadana-dev-rg  
**Región:** northcentralus (Iowa, USA)

| Componente | Servicio Azure | Configuración |
|------------|----------------|---------------|
| **Compute** | AKS (Kubernetes) | 1 nodo Standard_B2s (2 vCPU, 4GB) |
| **Database** | PostgreSQL Flexible Server | Burstable B1ms |
| **Storage** | Blob Storage | LRS, container: documents |
| **Messaging** | Service Bus | Basic tier, 2 queues |
| **Network** | VNet + NSG | 10.0.0.0/16 |
| **Observability** | OpenSearch in K8s | Self-hosted |

### Networking

**VNet:** 10.0.0.0/16
- Subnet AKS: 10.0.1.0/24
- Subnet PostgreSQL: 10.0.2.0/24

**NSG Rules:**
- Inbound: 80, 443, 5432 (PostgreSQL)
- Outbound: All

### Storage

**Blob Storage:**
- Container: `documents`
- Structure: `citizens/{citizen_id}/{uuid}-{filename}`
- Access: Presigned SAS tokens (1 hora)
- CORS: Habilitado para frontend

### Database

**PostgreSQL Flexible Server:**
- Version: 15
- Tier: Burstable B1ms (1 vCPU, 2GB)
- Storage: 32 GB
- Backup: 7 días retención

**Tablas:**
- `citizens` - Información de ciudadanos
- `document_metadata` - Metadata de documentos
- `transfers` - Historial de transferencias

### Messaging

**Service Bus (Basic tier):**
- Queues:
  - `citizen-events` - Eventos de registro/unregister
  - `document-events` - Eventos de upload/confirm
  - `notifications` - Queue para notificaciones (en lugar de topic)

**Nota:** Basic tier no soporta Topics, usando Queues

---

## 🔄 Flujos de Datos

### 1. Registro de Ciudadano

```
┌─────────┐
│Frontend │
└────┬────┘
     │ POST /api/citizens/register
     ▼
┌─────────┐
│ Gateway │ Rate limit + CORS
└────┬────┘
     │ Proxy
     ▼
┌─────────┐
│ Citizen │ 
│ Service │
└────┬────┘
     │ 1. Save to PostgreSQL
     ├────────────────────┐
     │                    │
     ▼                    ▼
┌──────────┐      ┌──────────────┐
│PostgreSQL│      │MinTIC Client │
└──────────┘      └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  GovCarpeta  │
                  │  Hub (API)   │
                  └──────────────┘
```

### 2. Upload de Documento

```
┌─────────┐
│Frontend │
└────┬────┘
     │ 1. POST /api/documents/upload-url
     ▼
┌───────────┐
│Ingestion  │
│ Service   │
└────┬──────┘
     │ 2. Generate presigned URL
     │ 3. Save metadata (status=pending)
     ├────────────────────┐
     │                    │
     ▼                    ▼
┌──────────┐      ┌─────────────┐
│PostgreSQL│      │ Blob Storage│
│(metadata)│      │   (Azure)   │
└──────────┘      └──────┬──────┘
                         ▲
                         │ 4. PUT file
                    ┌────┴────┐
                    │Frontend │
                    └────┬────┘
                         │ 5. POST /confirm-upload
                         ▼
                  ┌───────────┐
                  │Ingestion  │
                  │(update DB)│
                  └───────────┘
```

### 3. Búsqueda de Documentos

```
┌─────────┐
│Frontend │
└────┬────┘
     │ GET /api/metadata/search?q=diploma
     ▼
┌─────────┐
│Metadata │
│ Service │
└────┬────┘
     │ PostgreSQL ILIKE search
     │ (futuro: OpenSearch)
     ▼
┌──────────┐
│PostgreSQL│ SELECT * WHERE filename ILIKE '%diploma%'
└──────────┘
```

### 4. Transferencia P2P

```
┌──────────────┐                    ┌──────────────┐
│ Operador A   │                    │ Operador B   │
│              │                    │              │
│ 1. Initiate  │                    │              │
│ ├─GET ops    │───────┐            │              │
│ │            │       │            │              │
│ │            │       ▼            │              │
│ │            │  ┌─────────┐       │              │
│ │            │  │GovCarpe│        │              │
│ │            │  │ta Hub  │        │              │
│ │            │  └────┬────┘       │              │
│ │            │       │ operators  │              │
│ │            │◄──────┘            │              │
│ │            │                    │              │
│ 2. Transfer  │                    │              │
│ ├─POST       │───────────────────►│3. Receive    │
│ │transfer    │  {citizen, docs,   │  ├─Save DB   │
│ │            │   token}           │  ├─Download  │
│ │            │                    │  │  docs     │
│ │            │                    │  │           │
│ │            │◄───────────────────│4.│Confirm    │
│ 5. Delete    │   POST confirm     │  └─(status=1)│
│    if success│   {id, token,      │              │
│              │    status=1}       │              │
└──────────────┘                    └──────────────┘
```

---

## 🔐 Seguridad

### Autenticación

**B2C (Ciudadanos):**
- Actual: Mock authentication
- Futuro: Azure AD B2C / Cognito OIDC
- Flow: Authorization Code + PKCE

**B2B (Operadores):**
- Actual: No requiere (GovCarpeta público)
- Spec original: OAuth 2.1 client_credentials + mTLS
- Cambio: GovCarpeta simplificado sin auth

### Autorización

**Gateway Middleware:**
- Valida JWT en header `Authorization: Bearer {token}`
- Rutas públicas exentas
- OPTIONS requests exentos (CORS)

### Integridad de Documentos

- SHA-256 hash calculado por frontend
- Guardado en metadata
- TODO: Verificación server-side del hash

### CORS

**Configuración en todos los servicios:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Todos los orígenes (dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Producción:** Restringir `allow_origins` a dominio específico

---

## 📊 Observabilidad

### OpenTelemetry

**Preparado en shared library:**
- Traces: Distributed tracing
- Metrics: Custom metrics
- Logs: Structured logging

**Exporters:**
- Jaeger (traces)
- CloudWatch / Azure Monitor (logs, metrics)

### Logging

**Niveles:**
- INFO: Operaciones normales
- WARNING: Fallos no críticos (ej: MinTIC sync failed)
- ERROR: Errores que requieren atención

**Formato:**
```
2025-10-11T19:00:00.000 INFO [citizen] Registering citizen: 123456
2025-10-11T19:00:01.234 INFO [citizen] Citizen 123456 registered in MinTIC Hub
```

---

## 🚀 Deployment

### Helm Charts

**Release Name:** carpeta-ciudadana  
**Namespace:** carpeta-ciudadana

**Services Deployed:**
- frontend (LoadBalancer)
- gateway (ClusterIP, expuesto via frontend)
- citizen, ingestion, metadata, transfer, mintic-client (ClusterIP internos)

**Autoscaling (HPA):**
- Basado en CPU utilization (70%)
- Min/Max replicas configurables por servicio

**Environment Variables inyectadas por Helm:**
- `ENVIRONMENT=production`
- `DATABASE_URL` (construido desde values.yaml)
- Service URLs (Kubernetes DNS)

### CI/CD Pipeline

**GitHub Actions:** `.github/workflows/ci-azure-federated.yml`

**Jobs:**
1. **lint-and-scan**: Ruff + ESLint + Trivy
2. **backend-test**: Unit tests (matrix: 6 servicios)
3. **frontend-test**: Type check + build
4. **build-and-push**: Docker build → Docker Hub (matrix: 7 images)
5. **deploy**: Helm upgrade en AKS

**Autenticación Azure:**
- Federated Credentials (Workload Identity Federation)
- No Service Principal needed
- GitHub OIDC → Azure Managed Identity

---

## 📈 Escalabilidad

### Horizontal Scaling

**HPA configurado:**
- Gateway: 3-20 replicas
- Citizen: 2-10 replicas
- Ingestion: 2-15 replicas
- Metadata: 2-10 replicas
- Transfer: 2-10 replicas
- MinTIC Client: 2-5 replicas

### Performance Optimizations

**Implementadas:**
- ✅ Presigned URLs (no upload via backend)
- ✅ Redis caching (rate limiting)
- ✅ Async HTTP calls (no bloquea)
- ✅ Connection pooling (asyncpg)

**Futuras:**
- [ ] CDN para assets estáticos
- [ ] Cache de metadata con Redis
- [ ] Batch processing de eventos
- [ ] Read replicas para PostgreSQL

---

## 🔧 Service Discovery

### Auto-detección de Ambiente

```python
def get_service_url(service_name: str, default_port: int) -> str:
    """Detecta automáticamente el ambiente."""
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "development":
        # Local con venv o Docker Compose
        return f"http://localhost:{default_port}"
    else:
        # Kubernetes (AKS)
        release_name = os.getenv("HELM_RELEASE_NAME", "carpeta-ciudadana")
        return f"http://{release_name}-{service_name}:8000"
```

**Resultado:**
- **Local:** `http://localhost:8005` (mintic_client)
- **K8s:** `http://carpeta-ciudadana-mintic-client:8000`

**Override manual:**
```bash
export MINTIC_CLIENT_URL=http://custom-url:8000
```

---

## 🧪 Testing Strategy

### Unit Tests
- Cada servicio tiene `/tests/unit/`
- pytest con pytest-asyncio
- Coverage target: 80%+

### Contract Tests
- Gateway ↔ Services
- MinTIC Client ↔ GovCarpeta Hub
- pytest-httpx para mocking

### E2E Tests
- Frontend flows completos
- TODO: Implementar con Playwright

---

## 📦 Tecnologías

### Backend Stack
- **Framework:** FastAPI 0.109+
- **Runtime:** Python 3.13.7
- **Package Manager:** Poetry 2.2.1
- **ORM:** SQLAlchemy 2.0 (async)
- **DB Driver:** asyncpg 0.30.0
- **HTTP Client:** httpx 0.26.x
- **Validation:** Pydantic 2.5+ (con email validator)

### Frontend Stack
- **Framework:** Next.js 14 (App Router)
- **Runtime:** Node.js 22.16.0
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Font:** Montserrat (global)
- **HTTP Client:** Axios

### Infrastructure
- **Cloud:** Microsoft Azure
- **Orchestration:** Kubernetes (AKS)
- **IaC:** Terraform 1.6+
- **Deployment:** Helm 3.13+
- **CI/CD:** GitHub Actions
- **Container Registry:** Docker Hub

---

## 🎯 Patrones de Diseño

### Implementados

1. **API Gateway Pattern** ✅
   - Gateway centraliza requests
   - Rate limiting
   - Authentication/Authorization

2. **Service Discovery** ✅
   - Auto-detección de ambiente
   - Kubernetes DNS en producción
   - localhost en desarrollo

3. **Presigned URLs** ✅
   - Upload/download directo a storage
   - No saturar backend
   - Menor latencia

4. **Async Communication** ✅
   - httpx AsyncClient
   - Non-blocking calls a MinTIC
   - Fail gracefully

5. **Database per Service** ✅
   - Cada servicio su schema
   - Tablas compartidas: document_metadata
   - Loose coupling

### Preparados (no implementados)

6. **Event Sourcing** ⏳
   - Service Bus/SQS ready
   - TODO: Publishers y consumers

7. **CQRS** ⏳
   - Separación reads/writes
   - TODO: Read models optimizados

8. **Saga Pattern** ⏳
   - Transferencias P2P distribuidas
   - TODO: Compensation logic

---

## 🔄 Ciclo de Vida del Documento

```
1. UPLOAD REQUEST
   Frontend → Ingestion
   ↓
2. PRESIGNED URL GENERATION
   Ingestion → Azure Blob
   Metadata: status=pending
   ↓
3. DIRECT UPLOAD
   Frontend → Azure Blob (PUT)
   ↓
4. CONFIRM UPLOAD
   Frontend → Ingestion
   Metadata: status=uploaded, SHA-256 saved
   ↓
5. INDEXING (TODO)
   Event → Metadata Service
   OpenSearch indexing
   ↓
6. SEARCHABLE
   Documento disponible en búsqueda
   ↓
7. TRANSFER (Opcional)
   Transfer Service → Otro operador
   ↓
8. DELETION (Soft)
   Metadata: is_deleted=true
   Blob: mantener para audit
```

---

## 📝 Próximas Implementaciones

### Alta Prioridad

1. **Event Publishing** (Service Bus)
   - Publicar eventos en citizen register/unregister
   - Publicar eventos en document upload/confirm
   - Consumers para procesamiento async

2. **OpenSearch Integration**
   - Indexar documentos automáticamente
   - Full-text search optimizado
   - Fuzzy matching

3. **Real Authentication**
   - Azure AD B2C para usuarios
   - OIDC completo con PKCE
   - Social login (Google, Microsoft)

### Media Prioridad

4. **Signature Service**
   - Firma digital XAdES/CAdES/PAdES
   - Integración con TSA
   - Verificación de firmas

5. **Sharing Service**
   - Compartir paquetes de documentos
   - URLs temporales
   - Control de acceso

6. **Notification Service**
   - Emails transaccionales
   - Webhooks para eventos
   - Templates personalizables

### Baja Prioridad

7. **Metrics & Monitoring**
   - Azure Monitor integration
   - Custom dashboards
   - Alertas automáticas

8. **Backup & Recovery**
   - Automated backups
   - Disaster recovery plan
   - Data retention policies

---

## 🎓 Notas para Proyecto Universitario

### Free Tier Strategy

**Azure for Students ($100 créditos):**
- Optimizado para 2-5 meses de uso
- VM sizes pequeños (B2s)
- PostgreSQL Burstable
- Service Bus Basic
- Servicios costosos deshabilitados

**Alternativas gratuitas usadas:**
- OpenSearch en pods (vs Cognitive Search $250/mes)
- Docker Hub (vs ACR $5-20/mes)
- K8s Secrets (vs Key Vault)
- Federated Credentials (vs Service Principal)

### Demostración del Proyecto

**Puntos clave:**
1. Arquitectura de microservicios moderna
2. Multi-cloud (AWS y Azure)
3. CI/CD automatizado
4. Kubernetes en Azure
5. IaC con Terraform
6. Integración con API real (GovCarpeta)
7. Testing automatizado
8. Observabilidad con OpenTelemetry

---

**Autor:** Manuel Jurado  
**Universidad:** EAFIT  
**Fecha:** Octubre 2025  
**Versión:** 1.0.0

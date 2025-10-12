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
10. [Observabilidad](#observabilidad)
11. [Troubleshooting](#troubleshooting)

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
| **transfer** | 8004 | Transferencias P2P | PostgreSQL + Redis |
| **mintic_client** | 8005 | Cliente hub MinTIC (GovCarpeta) | Redis (cache) |
| **signature** | 8006 | Firma y autenticación documentos | PostgreSQL + Redis |
| **read_models** | 8007 | CQRS read models (proyecciones) | PostgreSQL + Redis |
| **auth** | 8008 | OIDC provider (JWT emisor) | - |
| **iam** | 8009 | ABAC authorization | - |
| **notification** | 8010 | Email + Webhook notifications | PostgreSQL |
| **sharing** | 8011 | Compartición vía shortlinks | PostgreSQL + Redis |

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
- **Advanced Rate Limiting** con límites por rol
- Sistema de penalización y bans automáticos
- Validación JWT (OIDC)
- CORS habilitado
- Propagación de traces (OpenTelemetry)
- Endpoint de monitoreo `/ops/ratelimit/status`

**Rate Limiting Avanzado:**

| Rol | Límite (rpm) | Uso |
|-----|--------------|-----|
| `ciudadano` | 60 | Usuarios finales (default) |
| `operador` | 200 | Operadores registrados |
| `mintic_client` | 400 | Cliente hub MinTIC |
| `transfer` | 400 | Servicio de transferencias |

**Características:**
- ✅ Sliding window con Redis (buckets de 60s)
- ✅ Penalización: 5 violaciones en 10 min → ban IP por 120s
- ✅ Allowlist: IPs del hub MinTIC bypass todos los límites
- ✅ Métricas OpenTelemetry: `rate_limit.requests`, `rate_limit.rejected`, `rate_limit.banned`

**Configuración:**
```bash
# Variables de entorno
ENVIRONMENT=development

# Redis (requerido para rate limiting)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_SSL=false

# Service URLs (auto-discovery)
CITIZEN_SERVICE_URL=http://localhost:8001
INGESTION_SERVICE_URL=http://localhost:8002
METADATA_SERVICE_URL=http://localhost:8003
SIGNATURE_SERVICE_URL=http://localhost:8006
SHARING_SERVICE_URL=http://localhost:8011

# JWT
JWT_SECRET_KEY=dev-secret-key
JWT_ALGORITHM=HS256
```

**Rutas Públicas (sin auth):**
- `/health`
- `/docs`
- `/api/citizens/register`
- `/api/auth/login`
- `/api/auth/token`
- `/ops/ratelimit/status`

**Monitoreo Rate Limiter:**
```bash
# Ver status propio
curl http://localhost:8000/ops/ratelimit/status

# Ver status de IP específica
curl http://localhost:8000/ops/ratelimit/status?ip=192.168.1.100

# Response incluye:
# - Configuración de límites
# - Estado de ban
# - Contadores actuales por rol
# - Número de violaciones
```

**Ejemplo de Penalización:**
```
1. Request 61/60 → Violación 1
2. Request 61/60 → Violación 2
3. Request 61/60 → Violación 3
4. Request 61/60 → Violación 4
5. Request 61/60 → Violación 5 → BAN por 120 segundos
6. Cualquier request → 429 "IP banned"
```

Ver **`RATE_LIMITER_GUIDE.md`** para documentación completa y troubleshooting.

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
- Generar presigned URLs para upload (PUT) - Frontend → Storage
- Generar presigned URLs para download (GET) - Frontend ← Storage
- Guardar metadata de documentos en PostgreSQL
- Confirmar uploads y verificar integridad (SHA-256)
- **NO canaliza binarios** - Todo directo a storage

**Flujo de Upload (sin binarios en backend):**
```
1. Frontend solicita → POST /api/documents/upload-url
   ↓
2. Ingestion genera presigned PUT URL (1 hora)
   │  Guarda metadata en DB (status=pending)
   ↓
3. Frontend → PUT directo a Azure Blob Storage
   │  (NO pasa por backend)
   ↓
4. Frontend confirma → POST /api/documents/confirm-upload
   │  Envía: document_id, sha256_hash, size_bytes
   ↓
5. Ingestion actualiza status=uploaded
   │  Verifica hash y tamaño
```

**⚠️ IMPORTANTE: Upload Directo**
```
❌ INCORRECTO (no escalable):
Frontend → Backend (upload) → Storage
           ↑ Bottleneck

✅ CORRECTO (presigned URL):
Frontend ─────→ Storage (directo con SAS/presigned)
    ↓
Backend (solo metadata)
```

**Cloud Provider:**
- Detecta via `CLOUD_PROVIDER` env var
- Soporta Azure Blob Storage y AWS S3
- Presigned URLs:
  - Upload (PUT): 1 hora
  - Download (GET): 1 hora (usuarios normales)
  - Hub (GET): 15 minutos (solo para authenticateDocument)

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
- Transferencias P2P seguras entre operadores
- Idempotencia con Redis (previene duplicados)
- Locks distribuidos (previene race conditions)
- Desregistro del hub SOLO después de confirmación
- Background retry para PENDING_UNREGISTER

**⚠️ CRÍTICO - Flujo Seguro (No Pérdida de Datos):**
```
❌ INSEGURO:
Origen elimina → Hub unregister → Destino recibe
         ↑ Si destino falla, se pierden todos los datos

✅ SEGURO (implementado):
Origen espera → Destino confirma → Origen elimina → Hub unregister
         ↑ Datos seguros hasta confirmación
```

**Estados:**
- `PENDING`: Iniciado, destino procesando
- `CONFIRMED`: Destino confirmó recepción
- `PENDING_UNREGISTER`: Esperando desregistro del hub
- `SUCCESS`: Completado (desregistrado del hub)
- `FAILED`: Transfer falló

**Flujo Completo:**
```
1. Origen → POST /api/transferCitizen (destino)
   - Idempotency-Key en header
   - Status: PENDING
   
2. Destino descarga documentos
   - Check: xfer:idemp:{key} (Redis SETNX)
   - Download from presigned URLs
   - Save locally
   - Return 201

3. Destino → POST /api/transferCitizenConfirm (origen)
   - Body: {citizenId, token, req_status: 1}
   
4. Origen recibe confirmación (CON LOCK):
   a. Acquire lock: lock:delete:{citizenId}
   b. Update: status = PENDING_UNREGISTER
   c. Delete: Citizen data from DB
   d. Delete: Documents from storage
   e. Call: mintic_client.unregister_citizen()
   f. Si OK: status = SUCCESS
   g. Si falla: retry_count++, keep PENDING_UNREGISTER
   h. Release lock
   
5. Background job: Retry PENDING_UNREGISTER cada 5min
```

**Redis Keys:**
- `xfer:idemp:{key}`: Idempotency (TTL 900s)
- `lock:delete:{citizenId}`: Distributed lock (TTL 120s)

### 6. MinTIC Client Service

**Responsabilidades:**
- **ÚNICA FACADE** al hub MinTIC (GovCarpeta APIs)
- Centraliza TODAS las llamadas al hub (sin duplicación)
- Registro de ciudadanos y operadores
- Autenticación de documentos
- Cache y retry automático

**Arquitectura:**
```
citizen service ─┐
signature service├─→ mintic_client (facade) ─→ Hub MinTIC
transfer service ─┘         ↓                    (público)
                    No auth, passthrough
                    Cache + retry + logs
```

**Hub MinTIC (GovCarpeta):**
- URL: `https://govcarpeta-apis-4905ff3c005b.herokuapp.com`
- **API completamente pública** (sin autenticación)
- No requiere: OAuth, API keys, mTLS, JWKS, certificados
- Solo HTTP/HTTPS simple con SSL
- Timeout: 10s
- Respuestas: Texto plano o JSON (parsing flexible)

**Retry Inteligente:**
- Retry en: 5xx (excepto 501) y timeouts
- NO retry en: 2xx, 3xx, 4xx, 501
- Exponential backoff + jitter (random 0-2s)
- 501 = error de parámetros o estado (no cambiará con retry)

**DTO Unificado:**
```json
{
  "ok": true/false,      // True si 2xx
  "status": 200,         // HTTP status code
  "message": "...",      // Texto del hub
  "data": {...} | null   // JSON si disponible
}
```

**Facade Endpoints (passthrough sin transformación):**

| Endpoint Interno | Hub Endpoint | Usado por |
|-----------------|--------------|-----------|
| `POST /register-citizen` | `/apis/registerCitizen` | citizen |
| `DELETE /unregister-citizen` | `/apis/unregisterCitizen` | citizen |
| `PUT /authenticate-document` | `/apis/authenticateDocument` | signature |
| `GET /validate-citizen/{id}` | `/apis/validateCitizen/{id}` | citizen |
| `POST /register-operator` | `/apis/registerOperator` | startup |
| `PUT /register-transfer-endpoint` | `/apis/registerTransferEndPoint` | startup |
| `GET /operators` | `/apis/getOperators` | transfer |

**Cache Redis:**

**1. Anti-Stampede (getOperators):**
- Cache: `mintic:operators` (TTL: 300s)
- Lock: `lock:mintic:operators` (TTL: 10s)
- Solo un pod fetchea, otros esperan
- Evita thundering herd al hub

**2. Idempotencia (operaciones de escritura):**

Evita duplicados en reintentos:

| Operación | Redis Key | TTL | Cachea si |
|-----------|-----------|-----|-----------|
| registerCitizen | `hub:registerCitizen:{id}` | 900s | 2xx, 204, 501 |
| unregisterCitizen | `hub:unregisterCitizen:{id}` | 300s | 2xx, 204, 501 |
| authenticateDocument | `hub:authdoc:{citizenId}:{urlHash}` | 900s | 2xx, 204, 501 |

**Flow:**
```
1. Check Redis: hub:registerCitizen:123
2. Si existe y status terminal (2xx/204/501) → return cached
3. Si no existe → call hub
4. Si hub response es terminal → save in Redis
5. Si hub response es 5xx → NO cachear (retry)
```

**Beneficios:**
- ✅ Evita duplicados en hub (ciudadano ya registrado)
- ✅ Safe retries (si 1er intento OK, retries usan cache)
- ✅ Reduce carga al hub
- ✅ Consistencia en reintentos

**Circuit Breakers:**

Cada endpoint tiene su propio circuit breaker:

| Endpoint | Failure Threshold | Recovery Time | Behavior when OPEN |
|----------|-------------------|---------------|-------------------|
| registerCitizen | 5 fallos | 60s | Return 202 + queue |
| authenticateDocument | 5 fallos | 60s | Return 202 + queue |
| getOperators | 5 fallos | 60s | Return 202 + queue |
| ... | 5 fallos | 60s | Return 202 + queue |

**Estados:**
- **CLOSED**: Normal (todas las requests pasan)
- **OPEN**: Demasiados fallos (return 202, encola operación)
- **HALF_OPEN**: Testing recovery (máx 3 requests de prueba)

**Flow:**
```
5 fallos consecutivos (5xx o timeout) → Circuit OPEN
  ↓
Siguiente request → Return 202 Accepted
  ↓
Enqueue to hub-retry-queue
  ↓
Después de 60s → Circuit HALF_OPEN
  ↓
3 requests de prueba → Si OK → CLOSED
                    → Si fallan → OPEN again
```

**Métricas OpenTelemetry:**
```
hub.calls{endpoint, status, success}      # Total calls
hub.latency{endpoint}                     # Latency (histogram)
hub.cb_open{endpoint}                     # 0=CLOSED, 1=OPEN, 2=HALF_OPEN
```

**Normalización de Operadores:**
- Tolera missing fields, whitespace extra, casing inconsistente
- Mapea: `operatorId|operator_id|id` → `OperatorId`
- Mapea: `operatorName|name` → `OperatorName`  
- Mapea: `transferAPIURL|transfer_api_url|url` → `transferAPIURL`
- Filtra operadores sin `transferAPIURL`

**Validación de URLs:**
- **Producción**: Solo `https://` (rechaza `http://`)
- **Desarrollo**: Permite `http://` con warning
- Flag: `ALLOW_INSECURE_OPERATOR_URLS=true` en dev

**Configuración:**
```bash
MINTIC_BASE_URL=https://govcarpeta-apis-4905ff3c005b.herokuapp.com
MINTIC_OPERATOR_ID=operator-demo
MINTIC_OPERATOR_NAME=Carpeta Ciudadana Demo
REQUEST_TIMEOUT=10
MAX_RETRIES=3

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Security
ENVIRONMENT=development
ALLOW_INSECURE_OPERATOR_URLS=true  # false en producción
```

**Ejemplo de Response:**
```json
// Raw from hub (puede variar):
[
  {
    "OperatorId": "op1",
    "operatorName": "  Operador 1  ",  // whitespace
    "transferAPIURL": "https://op1.com/transfer"
  },
  {
    "operator_id": "op2",  // different casing
    "name": "Operador 2",
    "url": null  // missing URL - será filtrado
  },
  {
    "OperatorId": "op3",
    "OperatorName": "Operador 3",
    "transferAPIURL": "http://localhost:8000"  // http:// - warning en dev, reject en prod
  }
]

// Normalizado y filtrado:
[
  {
    "OperatorId": "op1",
    "OperatorName": "Operador 1",  // trimmed
    "transferAPIURL": "https://op1.com/transfer"
  },
  {
    "OperatorId": "op3",
    "OperatorName": "Operador 3",
    "transferAPIURL": "http://localhost:8000"  // solo en dev
  }
]
// op2 filtrado (no transferAPIURL)
```

### 7. Signature Service (✍️ NUEVO)

**Responsabilidades:**
- Calcular hashes SHA-256 de documentos
- Firmar hashes (mock RSA o K8s secret)
- Generar SAS URLs temporales para Azure Blob
- Autenticar documentos en hub MinTIC
- Almacenar registros de firma en PostgreSQL
- Cache de idempotencia en Redis

**Endpoints:**
- `POST /sign` - Firmar documento y autenticar con hub
- `POST /verify` - Verificar firma

### 8. Read Models Service (🔄 CQRS - NUEVO)

**Responsabilidades:**
- Consumir eventos de Service Bus
- Proyectar read models denormalizados
- Proveer queries rápidas con cache Redis
- Deduplicación con `event_id`

**Endpoints:**
- `GET /read/documents?citizenId=...` - Listar documentos optimizado
- `GET /read/transfers?citizenId=...` - Listar transferencias

### 9. Auth Service (🔐 OIDC - NUEVO)

**Responsabilidades:**
- Proveedor OIDC mínimo viable
- Emisión de JWT RS256
- Publicación de JWKS

**Endpoints:**
- `/.well-known/openid-configuration` - Configuración OIDC
- `/.well-known/jwks.json` - Claves públicas
- `POST /auth/token` - Obtener JWT
- `GET /auth/userinfo` - Info del usuario

### 10. IAM Service (🛡️ ABAC - NUEVO)

**Responsabilidades:**
- Evaluador de políticas ABAC (YAML)
- Control de acceso granular
- Contexto dinámico

**Endpoints:**
- `POST /authorize` - Evaluar autorización

### 11. Notification Service (📧 NUEVO)

**Responsabilidades:**
- Consumir eventos `document.authenticated` y `transfer.confirmed`
- Enviar emails (SMTP simulado o console)
- Enviar webhooks HTTP
- Registro en `delivery_logs` con reintentos

**Endpoints:**
- `POST /notify/test` - Prueba de notificación
- `GET /metrics` - Métricas OpenTelemetry

### 12. Sharing Service (📤 NUEVO)

**Responsabilidades:**
- Crear paquetes de compartición con múltiples documentos
- Generar shortlinks (tokens aleatorios de 12 chars)
- Validar permisos con ABAC (IAM)
- Generar SAS URLs temporales para acceso
- Cache de shortlinks en Redis (TTL = expiración)
- Logging de accesos con IP y user agent
- Soporte opcional para watermarks en PDFs

**Endpoints:**
- `POST /share/packages` - Crear paquete compartido
- `GET /s/{token}` - Acceder paquete via shortlink

**Flujo de Compartición:**
```
1. Usuario crea paquete (owner_email, document_ids[], expires_at, audience)
2. ABAC verifica permisos para cada documento
3. Genera token único (12 chars alphanumeric)
4. Almacena en PostgreSQL (share_packages)
5. Cache en Redis (share:{token}, TTL = tiempo hasta expiración)
6. Publica evento share.package.created
7. Retorna shortlink: https://carpeta.local/s/{token}
```

**Flujo de Acceso:**
```
1. Usuario accede GET /s/{token}
2. Busca en Redis cache (share:{token})
3. Si no está → consulta PostgreSQL
4. Valida expiración y estado activo
5. ABAC verifica consentimiento (si audience != public)
6. Genera SAS URLs temporales con expiración corta
7. Log en share_access_logs (IP, user_agent, resultado)
8. Retorna documentos con SAS URLs activas
```

**Database Tables:**
```sql
-- share_packages: paquetes de documentos compartidos
-- share_access_logs: registro de accesos y denegaciones
```

**Error Handling:**
- `404` - Token no encontrado
- `410 Gone` - Token expirado
- `403` - Token revocado o no autorizado (ABAC)
- `400` - Fecha expiración en pasado

**Configuración:**
```bash
AZURE_STORAGE_ACCOUNT_NAME=carpetastorage
AZURE_STORAGE_ACCOUNT_KEY=xxx
SHORTLINK_BASE_URL=https://carpeta.ciudadana.gov.co
SHORTLINK_TOKEN_LENGTH=12
SAS_DEFAULT_EXPIRY_HOURS=24
WATERMARK_ENABLED=false
IAM_SERVICE_URL=http://carpeta-ciudadana-iam:8000
```

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

**Backend (Python):**
```bash
# Todos los servicios
make test-unit

# Servicio individual
cd services/gateway
poetry run pytest tests/unit -v

# Con coverage
poetry run pytest --cov=app tests/unit

# Específico
pytest tests/test_rate_limiter.py -v
```

**Cobertura target:** 80%+

### Integration Tests

```bash
# Levantar stack completo
docker-compose --profile app up -d

# Testing manual de endpoints
curl http://localhost:8000/health

# Register citizen
curl -X POST http://localhost:8000/api/citizens/register \
  -H "Content-Type: application/json" \
  -d '{
    "identification": "1234567890",
    "name": "Test User",
    "address": "Test Address",
    "email": "test@example.com",
    "phone": "3001234567"
  }'

# Upload document
curl -X POST http://localhost:8000/api/documents/upload-url \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.pdf", "contentType": "application/pdf", "citizenId": "1234567890"}'
```

### E2E Tests (Playwright)

**Ubicación:** `tests/e2e/`

**Flow completo:**
```
1. Register citizen → 2. Login → 3. Upload document →
4. Sign document → 5. Authenticate hub → 6. Search →
7. Share (shortlink) → 8. Access share → 9. Transfer →
10. Confirm transfer
```

**Instalar:**
```bash
cd tests/e2e
npm install
npx playwright install
```

**Ejecutar:**
```bash
# Todos los tests
npx playwright test

# Ver en browser
npx playwright test --headed

# Solo Chrome
npx playwright test --project=chromium

# Ver reporte HTML
npx playwright show-report

# Debug mode
npx playwright test --debug
```

**Features:**
- ✅ Mock de MinTIC hub
- ✅ Multi-browser (Chrome, Firefox, Safari, Mobile)
- ✅ Screenshots en fallos
- ✅ Video recording
- ✅ Trace on retry
- ✅ Parallel execution

### Load Tests

**k6 (JavaScript):**

Ubicación: `tests/load/k6-load-test.js`

**Ejecutar:**
```bash
cd tests/load

# Install k6
brew install k6  # macOS
# o descargar de https://k6.io/

# Run test
k6 run k6-load-test.js

# Custom load
k6 run --vus 100 --duration 5m k6-load-test.js

# Con output a JSON
k6 run k6-load-test.js --out json=results.json
```

**Scenarios:**
- 50% Document upload
- 30% Search
- 20% P2P transfer

**Thresholds:**
```javascript
'http_req_duration': ['p(95)<2000', 'p(99)<5000']
'http_req_failed': ['rate<0.05']  // Error < 5%
```

**Locust (Python):**

Ubicación: `tests/load/locustfile.py`

**Ejecutar:**
```bash
cd tests/load

# Install locust
pip install locust

# Run with Web UI
locust -f locustfile.py

# Headless mode
locust -f locustfile.py \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless

# Custom host
locust -f locustfile.py --host=https://api.carpeta.ciudadana.gov.co
```

**Web UI:** http://localhost:8089

**Tasks:**
- Upload document (50% weight)
- Search (30% weight)
- Transfer (20% weight)
- List documents (10% weight)

**Performance Targets:**

| Métrica | Target | Threshold |
|---------|--------|-----------|
| API latency (p95) | < 1s | < 2s |
| API latency (p99) | < 2s | < 5s |
| Error rate | < 1% | < 5% |
| Upload (p95) | < 2s | < 3s |
| Search (p95) | < 500ms | < 1s |
| Transfer (p95) | < 3s | < 5s |

### E2E Tests (Frontend)

```bash
cd apps/frontend
npm run test:e2e
```

---

## 💾 Backup & Disaster Recovery

### RPO y RTO

**Recovery Point Objective (RPO):**
- PostgreSQL: **24 horas** (backups diarios)
- OpenSearch: **24 horas** (snapshots diarios)
- Azure Blob Storage: **0** (replicado LRS por Azure)

**Recovery Time Objective (RTO):**
- PostgreSQL: **< 30 minutos**
- OpenSearch: **< 1 hora**
- Aplicación completa: **< 2 horas**

### PostgreSQL Backups

**Backup manual:**
```bash
cd scripts/backup
./backup-postgres.sh

# Custom retention
./backup-postgres.sh --retention-days 14
```

**Restore:**
```bash
./restore-postgres.sh backups/postgres/postgres_backup_20251012_150000.sql.gz

# Sin confirmación (cuidado!)
./restore-postgres.sh backups/postgres/postgres_backup_20251012_150000.sql.gz --yes
```

**Backup automático (CronJob):**
```bash
# Deploy CronJob (diario a las 2:00 AM)
kubectl apply -f deploy/kubernetes/cronjob-backup-postgres.yaml

# Ver estado
kubectl get cronjob backup-postgres -n carpeta-ciudadana

# Ver ejecuciones
kubectl get jobs -n carpeta-ciudadana -l app=backup-postgres

# Forzar backup
kubectl create job backup-postgres-manual \
  --from=cronjob/backup-postgres -n carpeta-ciudadana
```

**Características:**
- Compresión gzip
- Checksum SHA-256
- Retención 7 días
- Log de backups

### OpenSearch Snapshots

**Scripts:** `scripts/backup/backup-opensearch.sh`

**Manual:**
```bash
cd scripts/backup
./backup-opensearch.sh
```

**Restore:**
```bash
./restore-opensearch.sh snapshot_20251012_150000
```

**Solo cuando uso < 80%** (evita impacto en performance)

### Cleanup de Blobs Huérfanos

**Script:** `scripts/backup/cleanup-orphan-blobs.sh`

**Proceso:**
1. Lista todos los blobs en Azure Storage
2. Consulta PostgreSQL por document_metadata
3. Identifica blobs sin metadata (huérfanos)
4. Soft delete de blobs huérfanos
5. Log de cleanup

**Ejecutar:**
```bash
cd scripts/backup

# Preview (dry-run)
./cleanup-orphan-blobs.sh --dry-run

# Execute
./cleanup-orphan-blobs.sh
```

**CronJob (semanal):**
```bash
kubectl apply -f deploy/kubernetes/cronjob-cleanup-orphans.yaml
```

### Retención de Datos

**Políticas:**

| Data Type | Soft Delete | Hard Delete | Backup Retention |
|-----------|-------------|-------------|------------------|
| Citizens | 30 días | 90 días | 7 días |
| Documents | 30 días | 90 días | 7 días |
| Transfers | No | 1 año | 7 días |
| Logs | No | 30 días | No backup |
| Blobs huérfanos | 7 días | 14 días | - |

**Soft Delete:**
- Campo `is_deleted=true` en PostgreSQL
- Fecha `deleted_at`
- No mostrado en UI
- Recuperable por admin

**Hard Delete (GC):**
```bash
# Deploy GC CronJob (mensual)
kubectl apply -f deploy/kubernetes/cronjob-gc-soft-deleted.yaml
```

### Disaster Recovery Plan

**Escenario 1: Corrupción de PostgreSQL**
```bash
# 1. Detener aplicación
kubectl scale deployment --all --replicas=0 -n carpeta-ciudadana

# 2. Restore último backup
cd scripts/backup
./restore-postgres.sh backups/postgres/postgres_backup_latest.sql.gz --yes

# 3. Verificar integridad
psql -c "SELECT COUNT(*) FROM citizens;"
psql -c "SELECT COUNT(*) FROM document_metadata WHERE is_deleted=false;"

# 4. Reiniciar aplicación
kubectl scale deployment --all --replicas=2 -n carpeta-ciudadana

# RTO: ~30 minutos
```

**Escenario 2: Pérdida de región Azure**
```bash
# 1. Provisionar nueva región
cd infra/terraform
terraform apply -var="azure_region=eastus"

# 2. Restore backups
./restore-postgres.sh offsite/postgres_backup_latest.sql.gz
./restore-opensearch.sh offsite/snapshot_latest

# 3. Deploy aplicación
cd ../../
helm upgrade --install carpeta-ciudadana deploy/helm/carpeta-ciudadana

# RTO: 4-6 horas
```

**Checklist de Restore:**
- [ ] PostgreSQL restaurado y verificado
- [ ] Tablas presentes (citizens, document_metadata, etc.)
- [ ] Conteos de registros correctos
- [ ] OpenSearch índices restaurados
- [ ] Documentos buscables
- [ ] Azure Blobs accesibles
- [ ] Login funciona
- [ ] Upload/download funciona
- [ ] Búsqueda funciona
- [ ] Transferencias funcionan
- [ ] Métricas y logs operativos

**Verificación:**
```bash
# Database integrity
psql -c "SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) 
         FROM information_schema.tables WHERE table_schema = 'public';"

# OpenSearch health
curl -X GET "localhost:9200/_cluster/health"

# Application health
curl http://localhost:8000/health
curl http://localhost:3000/
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

### 🔐 Gestión de Secretos

**Sistema de Rotación Automática:**

Implementado con CronJob de Kubernetes que ejecuta cada 30 días.

**Secretos Rotados Automáticamente:**

| Secret | Key | Frecuencia | Servicios Afectados |
|--------|-----|------------|---------------------|
| `jwt-secret` | `JWT_SECRET_KEY` | 30 días | gateway, auth |
| `api-keys` | `OPERATOR_API_KEY` | 30 días | transfer (P2P) |

**Desplegar CronJob:**
```bash
kubectl apply -f deploy/kubernetes/cronjob-rotate-secrets.yaml
```

**Rotación Manual:**
```bash
cd scripts/secrets

# Rotación completa
./rotate-secrets.sh

# Preview (dry run)
./rotate-secrets.sh --dry-run

# Especificar namespace
./rotate-secrets.sh --namespace carpeta-ciudadana-prod
```

**Backup y Restore:**
```bash
# Crear backup encriptado
./backup-secrets.sh

# Restaurar desde backup
./restore-secrets.sh backups/secrets_backup_20251012_150000.yaml.enc

# Preview restore
./restore-secrets.sh backups/secrets_backup_20251012_150000.yaml.enc --dry-run
```

**Backups Encriptados:**
- Encriptación AES-256-CBC con master key local
- Checksum SHA-256 para integridad
- ⚠️ **CRÍTICO**: Guardar `master.key` en lugar seguro
- Backups automáticos antes de cada rotación

**Secretos de Azure (Rotación Manual):**

```bash
# Service Bus SAS
# 1. Azure Portal → Service Bus → Shared access policies
# 2. Regenerate primary key
# 3. Actualizar secret:
kubectl patch secret servicebus-connection -n carpeta-ciudadana \
  -p '{"data":{"SERVICEBUS_CONNECTION_STRING":"'$(echo -n 'NEW_SAS' | base64)'"}}'

# PostgreSQL password
# 1. Azure Portal → PostgreSQL → Reset password
# 2. Actualizar secret:
kubectl patch secret postgresql-auth -n carpeta-ciudadana \
  -p '{"data":{"POSTGRESQL_PASSWORD":"'$(echo -n 'NEW_PASS' | base64)'"}}'

# Redis password
# 1. Azure Portal → Redis → Access keys → Regenerate
# 2. Actualizar secret:
kubectl patch secret redis-auth -n carpeta-ciudadana \
  -p '{"data":{"REDIS_PASSWORD":"'$(echo -n 'NEW_KEY' | base64)'"}}'

# Storage Account key
# 1. Azure Portal → Storage → Access keys → Rotate key
# 2. Actualizar secret:
kubectl patch secret azure-storage-secret -n carpeta-ciudadana \
  -p '{"data":{"AZURE_STORAGE_ACCOUNT_KEY":"'$(echo -n 'NEW_KEY' | base64)'"}}'
```

**Forzar Rotación Inmediata:**
```bash
kubectl create job rotate-secrets-manual \
  --from=cronjob/rotate-secrets \
  -n carpeta-ciudadana
```

**Verificar Estado:**
```bash
# Ver CronJob
kubectl get cronjob rotate-secrets -n carpeta-ciudadana

# Ver últimas ejecuciones
kubectl get jobs -n carpeta-ciudadana -l app.kubernetes.io/name=secret-rotator

# Ver logs
kubectl logs -n carpeta-ciudadana -l job-name=rotate-secrets-<timestamp>
```

**Migración Futura (con presupuesto):**
- Azure Key Vault + CSI Driver
- Rotación integrada con Azure
- Versionado automático
- Auditoría completa

Ver **`scripts/secrets/README.md`** para documentación completa.

---

## 🧪 Testing Completo

### Suite de Tests del MinTIC Client

**Ubicación:** `services/mintic_client/tests/unit/`

#### 1. test_client_responses.py - Manejo de Respuestas

**Propósito:** Verificar que el cliente maneja correctamente todos los tipos de respuestas del hub.

**Tests:**

```python
# (a) Procesa texto plano y 204
test_client_handles_plain_text_response()
  ✅ Respuestas no-JSON (texto plano)
  ✅ status=201, body="Ciudadano registrado exitosamente"

test_client_handles_204_no_content()
  ✅ 204 No Content con body vacío
  ✅ message="Sin contenido"

test_client_handles_mixed_json_and_text()
  ✅ JSON con campo "message"
  ✅ status=501, json={"message": "Error..."}

# (b) No reintenta en 501
test_no_retry_on_501_invalid_parameters()
  ✅ Exactamente 1 llamada
  ✅ No reintentos para 501 (parámetros inválidos)

test_no_retry_on_4xx_client_errors()
  ✅ No reintentos para 400, 404, etc.

# (c) Reintenta en 5xx
test_retry_on_500_server_error()
  ✅ Reintenta en 500 (max 3 intentos)
  ✅ Falla 2 veces, éxito en el 3er intento

test_retry_on_503_service_unavailable()
  ✅ Reintenta en 503
  ✅ Backoff exponencial + jitter

test_max_retries_exhausted_on_5xx()
  ✅ Para después de 3 intentos
  ✅ Lanza excepción

test_retry_on_timeout()
  ✅ Reintenta en timeouts
  ✅ Reintenta en errores de conexión
```

**Ejecutar:**
```bash
cd services/mintic_client
pytest tests/unit/test_client_responses.py -v
```

#### 2. test_get_operators.py - Normalización de Operadores

**Propósito:** Verificar que `getOperators` tolera y normaliza datos malformados.

**Tests:**

```python
# (d) Tolerancia y filtrado
test_get_operators_tolerates_missing_transfer_url()
  ✅ Filtra operadores sin transferAPIURL
  ✅ Filtra URLs vacías
  ✅ Solo retorna operadores válidos

test_get_operators_filters_http_in_production()
  ✅ Rechaza http:// en producción
  ✅ Solo permite https://
  ✅ environment="production"

test_get_operators_allows_http_in_development()
  ✅ Permite http:// en desarrollo
  ✅ Log warning para http://
  ✅ environment="development", allow_insecure_operator_urls=True

test_get_operators_normalizes_whitespace()
  ✅ Trim espacios en blanco
  ✅ operatorName y transferAPIURL limpios

test_get_operators_handles_empty_list()
  ✅ Lista vacía → []
  ✅ No errores

test_get_operators_handles_malformed_entries()
  ✅ Sin operatorName → filtrado
  ✅ operatorName vacío → filtrado
  ✅ Entradas null → filtradas
  ✅ Retorna solo operadores válidos
```

**Ejecutar:**
```bash
pytest tests/unit/test_get_operators.py -v
```

#### 3. test_idempotency.py - Prevención de Duplicados

**Propósito:** Verificar que la idempotencia evita llamadas duplicadas al hub.

**Tests:**

```python
# (e) Idempotencia
test_idempotency_prevents_duplicate_register_citizen()
  ✅ Primera llamada: ejecuta y cachea
  ✅ Segunda llamada: retorna del cache
  ✅ call_count == 1 (no segunda llamada)

test_idempotency_different_citizens_not_cached()
  ✅ ID diferente = clave diferente
  ✅ No colisiones de cache

test_idempotency_works_for_unregister()
  ✅ Funciona para DELETE operations
  ✅ key: hub:unregisterCitizen:{id}

test_idempotency_works_for_authenticate_document()
  ✅ Funciona para PUT operations
  ✅ key: hub:authdoc:{citizenId}:{docHash}

test_idempotency_only_caches_terminal_statuses()
  ✅ Cachea: 2xx, 204, 501
  ✅ NO cachea: 5xx (pueden recuperarse)

test_idempotency_key_generation_is_consistent()
  ✅ Mismo input = misma clave
  ✅ Diferente input = diferente clave
```

**Ejecutar:**
```bash
pytest tests/unit/test_idempotency.py -v
```

### Suite de Tests del Transfer Service

**Ubicación:** `services/transfer/tests/unit/`

#### 4. test_transfer_order.py - Orden Seguro de Transferencia

**Propósito:** Verificar el flujo seguro: confirmar → borrar local → unregisterCitizen.

**Tests:**

```python
# (f) Orden seguro de transferencia
test_transfer_waits_for_confirmation_before_delete()
  ✅ status=PENDING hasta confirmar
  ✅ confirmed_at=None mientras espera
  ✅ NO borra datos hasta CONFIRMED

test_local_deletion_after_confirmation()
  ✅ Borra DB solo después de CONFIRMED
  ✅ Borra blobs solo después de CONFIRMED
  ✅ Atómico con lock distribuido

test_hub_unregister_after_local_deletion()
  ✅ Llama hub SOLO después de borrar local
  ✅ Si éxito → status=SUCCESS
  ✅ unregistered_at actualizado

test_pending_unregister_state_if_hub_fails()
  ✅ Si hub falla → status=PENDING_UNREGISTER
  ✅ retry_count++
  ✅ unregistered_at=None (no completado)

test_background_job_retries_pending_unregister()
  ✅ Job procesa PENDING_UNREGISTER
  ✅ Reintenta hub unregister
  ✅ Si éxito → status=SUCCESS

test_max_retries_for_pending_unregister()
  ✅ Máximo 10 reintentos
  ✅ Después: intervención manual
  ✅ Alerta para ops

test_distributed_lock_prevents_race_condition()
  ✅ Redis lock: lock:delete:{citizen_id}
  ✅ SETNX con TTL 120s
  ✅ Token UUID para verificación
  ✅ Previene borrados duplicados

test_idempotency_for_transfer_confirm()
  ✅ Header: Idempotency-Key
  ✅ Redis: xfer:idemp:{key} EX 900
  ✅ Segunda llamada → 409 Conflict

test_complete_safe_transfer_flow()
  ✅ PENDING → (espera)
  ✅ CONFIRMED → (borra local)
  ✅ SUCCESS → (unregister hub)
  ✅ Timestamps completos
```

**Ejecutar:**
```bash
cd services/transfer
pytest tests/unit/test_transfer_order.py -v
```

### Garantías de Seguridad Verificadas

**1. Seguridad de Datos:**
- ✅ Sin pérdida si destino falla (datos permanecen en origen)
- ✅ Sin pérdida si hub unregister falla (mecanismo de reintentos)
- ✅ Borrado atómico con locks distribuidos

**2. Contrato API:**
- ✅ Maneja todos los formatos de respuesta del hub
- ✅ Reintentos inteligentes solo cuando es seguro
- ✅ Idempotencia previene operaciones duplicadas

**3. Producción:**
- ✅ Seguridad de URLs (enforcement de https://)
- ✅ Validación y normalización de operadores
- ✅ Degradación elegante ante datos malformados

**4. Orden de Operaciones:**
- ✅ Confirmación → Borrado Local → Hub Unregister
- ✅ Estado PENDING_UNREGISTER si hub falla
- ✅ Reintentos automáticos en background
- ✅ Límite de reintentos con alerta manual

### Ejecutar Todos los Tests

**Backend completo:**
```bash
# Todos los servicios
make test

# Solo MinTIC client
cd services/mintic_client
pytest tests/unit/ -v --cov=app --cov-report=html

# Solo Transfer
cd services/transfer
pytest tests/unit/ -v --cov=app --cov-report=html

# Con coverage
pytest tests/unit/ -v --cov=app --cov-report=term-missing
```

**Coverage esperado:**
- MinTIC client: >90% en `client.py`
- Transfer: >85% en `transfer_safe.py`

### CI/CD - Tests Automáticos

Los tests se ejecutan automáticamente en cada push:

**.github/workflows/ci-azure-federated.yml:**
```yaml
backend-test:
  strategy:
    matrix:
      service: [gateway, citizen, ingestion, metadata, transfer, mintic_client]
  steps:
    - name: Run tests
      run: |
        cd services/${{ matrix.service }}
        poetry run pytest tests/ -v --cov=app
```

**Umbral de cobertura:** Mínimo 80% para merge a master

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

## 📊 Observabilidad

Sistema completo de **OpenTelemetry** con trazas, métricas, dashboards y alertas.

### Arquitectura de Observabilidad

```
┌──────────────────┐
│   Frontend       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐  traceparent
│   Gateway        │─────────────────────┐
└────────┬─────────┘                     │
         │ propagates                    │
         ▼                                │
┌────────────────────────────────────────┴─────┐
│  12 Microservicios Instrumentados            │
│  • FastAPI spans                             │
│  • httpx spans (external)                    │
│  • SQLAlchemy spans (DB)                     │
│  • Redis spans (cache)                       │
│  • Service Bus spans                         │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │  OTLP Exporters     │
         ├─────────────────────┤
         │ • Console (stdout)  │
         │ • Azure Monitor     │
         │ • Prometheus        │
         └─────────────────────┘
```

### Métricas Implementadas

**HTTP Metrics:**
- `http.server.request.duration` - Latencia p50/p95/p99 por endpoint
- `http.server.request.count` - Total requests
- `http.server.error.count` - Errores 5xx

**Cache Metrics:**
- `cache.hits` / `cache.misses`
- `redis.command.duration`
- Cache hit rate

**Queue Metrics:**
- `queue.message.published` / `consumed` / `failed`
- `queue.dlq.length` - Dead Letter Queue
- `queue.processing.duration`

**External Calls:**
- `external.call.duration` - MinTIC Hub, otros operadores
- `external.call.errors`

**Rate Limit:**
- `rate_limit.exceeded`

**Circuit Breaker:**
- `circuit_breaker.state` (0=CLOSED, 1=OPEN, 2=HALF_OPEN)
- `saga.compensation.executed`

### Dashboards Grafana

**4 Dashboards JSON** en `observability/grafana-dashboards/`:

1. **api-latency.json** - HTTP latency p95, error rate, request rate
2. **transfers-saga.json** - Transfer latency, success rate, circuit breakers
3. **queue-health.json** - Messages, DLQ, processing failures
4. **cache-efficiency.json** - Hit rate, Redis latency, locks

**Importar a Grafana:**
```bash
# Via UI
Grafana → Dashboards → Import → Upload JSON

# Via API
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @observability/grafana-dashboards/api-latency.json
```

### Alertas

**11 Alertas Configuradas** en `observability/alerts/prometheus-alerts.yaml`:

- ⚠️ API latency p95 > 2s (5min)
- 🔴 API latency p95 > 5s (2min)
- ⚠️ Error rate > 1% (2min)
- 🔴 Error rate > 5% (1min)
- ⚠️ Transfer intra-region p95 > 2s (5min)
- ⚠️ Transfer inter-region p95 > 5s (5min)
- ⚠️ DLQ length > 10 (2min)
- ⚠️ Queue failures > 10% (5min)
- ℹ️ Cache hit rate < 50% (10min)
- ⚠️ Redis pool > 90% (2min)
- ⚠️ Circuit breaker OPEN (1min)

**Deploy Alertas:**
```bash
# Prometheus
kubectl apply -f observability/alerts/prometheus-alerts.yaml

# Azure Monitor
az monitor metrics alert create \
  --name "High API Latency" \
  --condition "avg http.server.request.duration > 2" \
  --window-size 5m
```

### Configuración

**Local Development (stdout):**
```bash
# .env
OTEL_USE_CONSOLE=true
OTEL_EXPORTER_OTLP_ENDPOINT=
ENVIRONMENT=development
```

**Production (Azure Monitor):**
```bash
# .env
OTEL_USE_CONSOLE=false
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxx;...
ENVIRONMENT=production
```

**Kubernetes:**
```yaml
# Deploy OTEL Collector
kubectl apply -f observability/k8s/otel-collector.yaml

# En cada servicio
env:
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://otel-collector:4317"
```

### Queries Útiles

**Prometheus:**
```promql
# Latencia p95 gateway
histogram_quantile(0.95, 
  sum(rate(http_server_request_duration_bucket{service_name="gateway"}[5m])) by (le)
)

# Error rate
sum(rate(http_server_error_count[5m])) / sum(rate(http_server_request_count[5m])) * 100

# Cache hit rate
sum(rate(cache_hits[5m])) / (sum(rate(cache_hits[5m])) + sum(rate(cache_misses[5m]))) * 100

# Rate limit rejections por rol
sum(rate(rate_limit_rejected{reason="rate_limit"}[5m])) by (role)

# IPs baneadas por minuto
sum(rate(rate_limit_banned[1m]))

# Tasa de rechazo global
sum(rate(rate_limit_rejected[5m])) / sum(rate(rate_limit_requests[5m])) * 100
```

**Azure Monitor (KQL):**
```kusto
// Latencia p95
customMetrics
| where name == "http.server.request.duration"
| summarize percentile(value, 95) by tostring(customDimensions.service_name)

// Trace distribuida
traces
| where operation_Id == "00-abc123-def456-01"
| project timestamp, message, customDimensions.service_name
| order by timestamp asc
```

### Documentación Completa

Ver **`OBSERVABILITY_GUIDE.md`** y **`observability/README.md`** para:
- Guía de implementación paso a paso
- Cómo agregar métricas custom
- Deploy completo de OpenTelemetry Collector
- Integración con Azure Monitor
- Ejemplos de código y queries

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


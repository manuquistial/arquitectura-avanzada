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
- Rate limiting avanzado con límites por rol
- Sistema de penalización y bans automáticos
- Validación JWT (preparado para OIDC)
- CORS habilitado para todos los orígenes
- Routing a microservicios internos
- Propagación de traceparent (OpenTelemetry)

**Tecnologías:**
- FastAPI
- Redis (rate limiting con sliding window)
- AdvancedRateLimiter (custom implementation)
- httpx (proxy HTTP)
- OpenTelemetry (tracing y métricas)

**Rutas Públicas (sin autenticación):**
- `/health` - Health check
- `/docs` - Swagger UI
- `/api/citizens/register` - Registro de ciudadanos
- `/api/auth/login` - Login
- `/api/auth/token` - Obtener JWT
- `/ops/ratelimit/status` - Estado del rate limiter
- `OPTIONS *` - CORS preflight requests

**Service Map:**
```python
{
    "citizens": "http://carpeta-ciudadana-citizen:8000",
    "ingestion": "http://carpeta-ciudadana-ingestion:8000",
    "metadata": "http://carpeta-ciudadana-metadata:8000",
    "transfer": "http://carpeta-ciudadana-transfer:8000",
    "mintic": "http://carpeta-ciudadana-mintic-client:8000",
    "signature": "http://carpeta-ciudadana-signature:8000",
    "sharing": "http://carpeta-ciudadana-sharing:8000",
}
```

**Advanced Rate Limiting:**

Sistema de rate limiting con límites diferenciados por rol:

| Rol | Límite (rpm) | Uso |
|-----|--------------|-----|
| `ciudadano` | 60 | Usuarios finales (default) |
| `operador` | 200 | Operadores con cuenta |
| `mintic_client` | 400 | Cliente hub MinTIC |
| `transfer` | 400 | Servicio de transferencias |

**Características:**
- ✅ **Sliding Window**: Redis con buckets de 60s
- ✅ **Penalización**: 5 violaciones en 10 min → ban 120s
- ✅ **Allowlist**: IPs del hub MinTIC bypass limit
- ✅ **Métricas**: OpenTelemetry (requests, allowed, rejected, banned)
- ✅ **Monitoring**: Endpoint `/ops/ratelimit/status`

**Redis Key Schema:**
```
rl:{route}:{role}:{ip}:{bucket}   # Counter (TTL 60s)
violations:{ip}                    # Sorted set (TTL 600s)
ban:{ip}                          # Ban flag (TTL 120s)
```

**Response 429 (Rate Limit Exceeded):**
```json
{
  "error": "Rate limit exceeded",
  "message": "Rate limit exceeded for role 'ciudadano': 61/60 requests per minute",
  "limit": 60,
  "current": 61,
  "retry_after": 60,
  "violations": 3,
  "ban_threshold": 5
}
```

**Response 429 (IP Banned):**
```json
{
  "error": "IP banned",
  "message": "Your IP x.x.x.x is temporarily banned due to excessive rate limit violations",
  "retry_after": 120
}
```

**Endpoint de Monitoreo:**
```bash
GET /ops/ratelimit/status?ip=192.168.1.100
```

Ver `RATE_LIMITER_GUIDE.md` para documentación completa.

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

# For UPLOAD (frontend → storage): 1 hour, WRITE permission
sas_token = generate_blob_sas(
    account_name=account_name,
    container_name=container_name,
    blob_name=blob_name,
    account_key=account_key,
    permission=BlobSasPermissions(write=True),  # WRITE for upload
    expiry=datetime.utcnow() + timedelta(hours=1)
)

url = f"https://{account_name}.blob.core.windows.net/{container}/{blob}?{sas}"
```

**⚠️ Principio: Frontend → Storage Directo**
```
Frontend                 Ingestion Service          Azure Blob
   │                           │                        │
   │ 1. Request upload URL     │                        │
   │──────────────────────────>│                        │
   │                           │                        │
   │ 2. Presigned PUT URL (1h) │                        │
   │<──────────────────────────│                        │
   │                           │                        │
   │ 3. PUT file DIRECTO       │                        │
   │───────────────────────────┼───────────────────────>│
   │                           │                        │
   │ 4. Confirm upload         │                        │
   │──────────────────────────>│ (update metadata)     │
```

**NO se canaliza por backend** → Performance y escalabilidad

**Base de Datos:**
- Tabla: `document_metadata` (compartida con metadata service)
- SQLAlchemy async con asyncpg

---

#### 4. Metadata Service (Puerto 8003) 🔍

**Responsabilidades:**
- Listar documentos por ciudadano
- Búsqueda full-text con OpenSearch
- Indexación automática de documentos
- Cache de búsquedas con Redis (120s TTL)
- Eliminar documentos (soft delete)

**Endpoints:**

**GET /api/metadata/documents?citizen_id={id}&limit=20**
```json
Response:
{
  "documents": [...],
  "total": 10
}
```

**GET /api/metadata/search?q={query}&citizen_id={id}&page=1&page_size=20**
```json
Response:
{
  "total": 5,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "id": "uuid",
      "documentId": "uuid",
      "citizenId": 1234567890,
      "title": "Diploma",
      "filename": "diploma.pdf",
      "hash": "sha256...",
      "tags": ["educacion", "diploma"],
      "hubAuthAt": "2025-10-11T...",
      "score": 0.95,
      "createdAt": "2025-10-11T..."
    }
  ]
}
```

**OpenSearch Integration:**
- Índice: `documents`
- Multi-match search en: title^2, filename, tags
- Fuzzy matching: AUTO
- Filters: citizenId, tags, status
- Cache: Redis (search:{hash} TTL 120s)

**Base de Datos:**
- Tabla compartida: `document_metadata`
- OpenSearch: Indexación async
- Redis: Cache de resultados

**Tecnologías:**
- opensearch-py 2.4.0
- Redis para caching
- SQLAlchemy async

---

#### 5. Transfer Service (Puerto 8004) 🔄

**Responsabilidades:**
- Transferencias P2P entre operadores (seguras, sin pérdida de datos)
- Idempotencia con Redis (xfer:idemp:{key} TTL 15min)
- Locks distribuidos para eliminación atómica (lock:delete:{citizenId})
- Confirmación bidireccional
- Desregistro del hub SOLO después de confirmación

**⚠️ CRITICAL: Flujo Seguro para Evitar Pérdida de Datos**

```
INCORRECTO (pérdida de datos):
Origen: Elimina → Desregistra hub → Destino recibe
        ↑ Si destino falla, ciudadano pierde todos sus datos

CORRECTO (implementado):
Origen: Espera → Destino confirma → Origen elimina → Desregistra hub
        ↑ Origen mantiene datos hasta confirmación del destino
```

**Estados de Transferencia:**

| Estado | Descripción | Timestamp |
|--------|-------------|-----------|
| `PENDING` | Transfer iniciado, destino procesando | initiated_at |
| `CONFIRMED` | Destino confirmó recepción exitosa | confirmed_at |
| `PENDING_UNREGISTER` | Esperando desregistro del hub | - |
| `SUCCESS` | Completado (desregistrado del hub) | unregistered_at, completed_at |
| `FAILED` | Transfer falló en destino | completed_at |

**Base de Datos:**
```sql
CREATE TABLE transfers (
    id SERIAL PRIMARY KEY,
    citizen_id INTEGER NOT NULL,
    direction VARCHAR NOT NULL,  -- 'incoming' | 'outgoing'
    source_operator_id VARCHAR,
    destination_operator_id VARCHAR,
    idempotency_key VARCHAR UNIQUE NOT NULL,
    status VARCHAR NOT NULL,  -- PENDING | CONFIRMED | PENDING_UNREGISTER | SUCCESS | FAILED
    
    -- Timestamps (track progress)
    initiated_at TIMESTAMP NOT NULL,
    confirmed_at TIMESTAMP,      -- When destination confirmed
    unregistered_at TIMESTAMP,   -- When unregistered from hub
    completed_at TIMESTAMP,      -- Final completion
    
    -- Retry tracking
    retry_count INTEGER DEFAULT 0,
    error_message TEXT
);
```

**Flujo Seguro Completo:**

**Paso 1: Origen inicia transferencia**
```
1. GET /operators (mintic_client, cached 5min)
2. Selecciona operador destino
3. Crea Transfer record (direction=outgoing, status=PENDING)
4. POST {destino}/api/transferCitizen
   Headers:
     Idempotency-Key: {uuid}
     Authorization: Bearer {OPERATOR_API_KEY}
   Body: {
     id, name, email,
     urlDocuments: { doc1: [sas_url], ... },
     confirmAPI: https://origen/api/transferCitizenConfirm
   }
```

**Paso 2: Destino recibe (idempotency check)**
```python
# Redis idempotency: xfer:idemp:{idempotency_key}
if not await setnx(f"xfer:idemp:{key}", "processing", ttl=900):
    return 409 Conflict  # Duplicate

# Download documents from presigned URLs
for doc_id, urls in urlDocuments.items():
    data = await download_document(urls[0])
    await save_to_local_storage(citizen_id, doc_id, data)

# Save transfer (direction=incoming, status=PENDING)
# Return 201 Accepted
```

**Paso 3: Destino confirma exitosamente**
```
POST {confirmAPI}/api/transferCitizenConfirm
Body: {
  citizenId: 123456,
  token: {idempotency_key},
  req_status: 1  // SUCCESS
}
```

**Paso 4: Origen recibe confirmación (CRÍTICO - con lock distribuido)**
```python
# 1. Acquire distributed lock
lock_key = f"lock:delete:{citizen_id}"
lock_token = uuid4()
acquired = await acquire_lock(lock_key, ttl=120, token=lock_token)

if not acquired:
    return 503 "Operation in progress"  # Otra operación concurrente

try:
    # 2. Find transfer record
    transfer = await db.get(Transfer, citizen_id=citizen_id, token=token)
    
    if req_status == 1:
        # SUCCESS - Destino tiene los datos
        
        # 3. Update status to PENDING_UNREGISTER
        transfer.status = TransferStatus.PENDING_UNREGISTER
        transfer.confirmed_at = datetime.utcnow()
        await db.commit()
        
        # 4. Delete citizen data from local DB (atomic)
        await db.delete(Citizen, id=citizen_id)
        
        # 5. Delete documents from local storage
        for doc_id in transfer.document_ids:
            await delete_blob(citizen_id, doc_id)
        
        # 6. Unregister from hub (with retries)
        try:
            result = await mintic_client.unregister_citizen({
                "id": citizen_id,
                "operatorId": source_operator_id,
                "operatorName": source_operator_name
            })
            
            if result.ok or result.status in [204, 501]:
                # Success or already unregistered
                transfer.status = TransferStatus.SUCCESS
                transfer.unregistered_at = datetime.utcnow()
                transfer.completed_at = datetime.utcnow()
                logger.info(f"✅ Transfer completed for citizen {citizen_id}")
            else:
                # Hub failed - keep in PENDING_UNREGISTER for retry
                transfer.error_message = f"Hub unregister failed: {result.message}"
                transfer.retry_count += 1
                logger.error(
                    f"❌ Hub unregister failed, will retry. "
                    f"Transfer in PENDING_UNREGISTER state"
                )
        
        except Exception as e:
            # Hub call failed - keep in PENDING_UNREGISTER
            transfer.error_message = str(e)
            transfer.retry_count += 1
            logger.error(f"❌ Hub unregister error: {e}")
        
        await db.commit()
    
    else:
        # FAILED - Destino reportó fallo
        transfer.status = TransferStatus.FAILED
        transfer.error_message = "Destination reported failure"
        transfer.completed_at = datetime.utcnow()
        await db.commit()
        
        # NO eliminar datos - destino no los tiene
        logger.warning(f"⚠️  Transfer FAILED, keeping citizen data")

finally:
    # 7. Release lock (ALWAYS)
    await release_lock(lock_key, lock_token)
```

**Paso 5: Background Job - Retry PENDING_UNREGISTER**
```python
# CronJob cada 5 minutos busca transfers en PENDING_UNREGISTER
transfers = await db.query(Transfer).filter(
    Transfer.status == TransferStatus.PENDING_UNREGISTER,
    Transfer.retry_count < 10  # Max 10 retries
).all()

for transfer in transfers:
    # Intentar desregistrar del hub
    result = await mintic_client.unregister_citizen(...)
    
    if result.ok:
        transfer.status = TransferStatus.SUCCESS
        transfer.unregistered_at = datetime.utcnow()
    else:
        transfer.retry_count += 1
    
    await db.commit()
```

**Redis Keys:**
```
xfer:idemp:{idempotency_key}   # Idempotency (TTL 900s)
lock:delete:{citizen_id}        # Distributed lock (TTL 120s)
```

**Seguridad y Garantías:**
- ✅ Origen mantiene datos hasta confirmación del destino
- ✅ Lock distribuido evita race conditions en deletion
- ✅ Idempotency previene duplicados
- ✅ Desregistro del hub SOLO después de confirmación
- ✅ Retry automático si hub falla
- ✅ Estado PENDING_UNREGISTER permite troubleshooting
- ✅ No pérdida de datos si destino o hub fallan
finally:
    await release_lock(lock_key, token)
```

**Tecnologías:**
- Redis: Idempotency + distributed locks
- PostgreSQL: Transfer records
- httpx + tenacity: Retry logic

---

#### 6. MinTIC Client Service (Puerto 8005) 🌐

**Responsabilidades:**
- **ÚNICA FACADE** al hub MinTIC (GovCarpeta APIs)
- Centraliza todas las llamadas al hub (sin duplicación)
- Registro de ciudadanos y operadores (validación 10 dígitos)
- Autenticación de documentos
- Cache de lista de operadores (Redis 5min con anti-stampede)
- Retry automático en fallos (3 intentos, exponential backoff)

**Principio de Diseño:**
```
Otros Servicios → mintic_client (facade) → Hub MinTIC (público)
                       ↓
              No auth, no transformación
              Solo passthrough + cache + retry
```

**Hub MinTIC (GovCarpeta):**
- URL: `https://govcarpeta-apis-4905ff3c005b.herokuapp.com`
- **API completamente pública** (sin autenticación)
- No requiere: OAuth, API keys, client_credentials, mTLS, JWKS
- Solo HTTP/HTTPS simple con SSL verification
- Timeout: 10 segundos
- Respuestas: Texto plano o JSON (parsing flexible)

**Validaciones del Hub:**
- ✅ Citizen ID: exactamente 10 dígitos numéricos
- ✅ Error si ID ya registrado: "ya se encuentra registrado en la carpeta ciudadana"
- ✅ Todos los campos obligatorios (id, name, address, email, operatorId, operatorName)

**Códigos de Respuesta del Hub:**
- `200/201`: Operación exitosa
- `204`: Sin contenido (ej: ciudadano no encontrado)
- `500`: Error de aplicación (retry)
- `501`: Error de parámetros o estado existente (NO retry)

**Retry Inteligente:**
```python
# Retry SOLO en:
# - 5xx (excepto 501 = error de parámetros)
# - Timeouts / connection errors

# NO retry en:
# - 2xx, 3xx, 4xx (client errors)
# - 501 (parámetros inválidos o estado ya existe)

@retry(
    retry=retry_if_result(should_retry) | retry_if_exception_type((Timeout, ConnectError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=1, max=10) + wait_random(0, 2)  # Jitter
)
```

**DTO Unificado:**
```typescript
interface MinTICResponse {
  ok: boolean;      // True if 2xx
  status: number;   // HTTP status code
  message: string;  // Texto del hub o error
  data: any | null; // JSON parseado (si disponible)
}

// Ejemplos:
// 201 → {ok: true, status: 201, message: "Ciudadano creado", data: {...}}
// 204 → {ok: true, status: 204, message: "Sin contenido", data: null}
// 501 → {ok: false, status: 501, message: "Error: ya existe", data: null}
// 500 → {ok: false, status: 500, message: "Application Error", data: null}
```

**Cache Redis (anti-stampede):**
```python
# GET /operators con single-flight pattern
cache_key = "mintic:operators"
lock_key = "lock:mintic:operators"

# 1. Check cache
cached = await get_json(cache_key)
if cached:
    return cached  # Cache HIT
    
# 2. Try acquire lock (solo un pod fetchea)
lock_token = await acquire_lock(lock_key, ttl=10)

if not lock_token:
    # Otro pod está fetcheando, esperar y revisar cache
    await asyncio.sleep(1)
    cached = await get_json(cache_key)
    if cached:
        return cached  # Otro pod pobló el cache
    # Si aún no hay cache, fetchear de todos modos

# 3. Fetch from hub
operators = await fetch_operators_from_hub()

# 4. Normalize and filter
valid_operators = [
    normalize_operator(op) 
    for op in operators 
    if normalize_operator(op) is not None
]

# 5. Cache result (TTL=300s)
await set_json(cache_key, valid_operators, ttl=300)

# 6. Release lock
await release_lock(lock_key, lock_token)

return valid_operators
```

**Normalización de Operadores:**
```python
def _normalize_operator(raw_data: dict) -> Optional[OperatorInfo]:
    """Normaliza datos de operador del hub.
    
    Tolerancias:
    - Missing fields
    - Extra whitespace
    - Inconsistent casing (operatorId vs OperatorId)
    - Campos con valores null/empty
    """
    # Map field variations
    operator_id = raw_data.get('OperatorId') or raw_data.get('operatorId') or raw_data.get('id')
    operator_name = raw_data.get('OperatorName') or raw_data.get('operatorName') or raw_data.get('name')
    transfer_url = raw_data.get('transferAPIURL') or raw_data.get('transfer_api_url') or raw_data.get('url')
    
    # Trim whitespace
    operator_id = str(operator_id).strip() if operator_id else ""
    operator_name = str(operator_name).strip() if operator_name else ""
    transfer_url = str(transfer_url).strip() if transfer_url else ""
    
    # Validate required fields
    if not operator_id or not operator_name:
        logger.warning(f"Operator missing ID or Name, skipping")
        return None
    
    # Filter out operators without transfer URL
    if not transfer_url:
        logger.info(f"Operator {operator_id} has no transferAPIURL, filtering out")
        return None
    
    # Validate URL security
    if transfer_url.startswith('http://'):
        if environment == "production" and not ALLOW_INSECURE_OPERATOR_URLS:
            logger.error(f"Rejecting insecure URL in production: {transfer_url}")
            return None
        else:
            logger.warning(f"⚠️  Insecure URL allowed in {environment}: {transfer_url}")
    
    return OperatorInfo(
        OperatorId=operator_id,
        OperatorName=operator_name,
        transferAPIURL=transfer_url
    )
```

**Filtrado y Validación:**
- ✅ Elimina operadores sin `transferAPIURL`
- ✅ Rechaza `http://` en producción (solo `https://`)
- ⚠️ Permite `http://` en dev/lab con warning
- ✅ Tolera campos faltantes o con espacios
- ✅ Normaliza nombres de campos (case-insensitive)

**Idempotencia con Redis:**

Todas las operaciones de escritura al hub usan idempotencia para evitar duplicados en reintentos:

```python
# Redis Keys por operación:
hub:registerCitizen:{citizenId}           # TTL: 900s (15 min)
hub:unregisterCitizen:{citizenId}         # TTL: 300s (5 min)
hub:authdoc:{citizenId}:{urlHash}         # TTL: 900s (15 min)

# Flow de Idempotencia:
1. Antes de llamar al hub:
   cached = await get_json(idempotency_key)
   if cached and cached.status in [2xx, 204, 501]:
       return cached  # 🔁 Operación ya ejecutada
   
2. Llamada al hub:
   result = await hub_call()
   
3. Si status es terminal (2xx, 204, 501):
   await set_json(idempotency_key, result, ttl=900)
   
4. Si status es 5xx:
   No cachear (error retryable)
```

**Estados Terminales (cacheables):**
- `2xx`: Éxito - cachear para evitar duplicados
- `204`: Sin contenido - válido, cachear
- `501`: Error de parámetros/estado - no cambiará, cachear

**Estados No Terminales (no cachear):**
- `500`: Error de servidor - podría recuperarse
- `Timeout`: Transitorio - reintentar

**TTL Strategy:**
```
registerCitizen:      900s (15 min) - rara vez cambia
unregisterCitizen:    300s (5 min)  - cambio de estado
authenticateDocument: 900s (15 min) - inmutable una vez hecho
```

**Ejemplo de Uso:**
```python
# Intento 1: POST /register-citizen (ID: 123)
# Redis: hub:registerCitizen:123 → not found
# Hub call → 201 Success
# Redis: SET hub:registerCitizen:123 {ok:true, status:201,...} EX 900

# Retry (por timeout de red): POST /register-citizen (ID: 123)
# Redis: hub:registerCitizen:123 → Cache HIT
# Return cached 201 (sin llamar al hub)
# ✅ Evita duplicación en hub
```

**Circuit Breakers por Endpoint:**

Cada endpoint del hub tiene su propio circuit breaker independiente:

```python
# Circuit Breakers:
hub_registerCitizen        # States: CLOSED/OPEN/HALF_OPEN
hub_unregisterCitizen
hub_authenticateDocument
hub_validateCitizen
hub_registerOperator
hub_registerTransferEndpoint
hub_getOperators

# Configuración:
failure_threshold: 5        # OPEN después de 5 fallos consecutivos
recovery_timeout: 60s       # Intenta HALF_OPEN después de 60s
half_open_max_calls: 3      # Prueba con 3 llamadas antes de CLOSED
```

**Estados del Circuit Breaker:**

| Estado | Descripción | Comportamiento |
|--------|-------------|----------------|
| **CLOSED** | Normal | Todas las requests pasan |
| **OPEN** | Fallando | Return 202 + encola para retry |
| **HALF_OPEN** | Testing | Permite máx 3 requests de prueba |

**Flow con Circuit Breaker:**
```
1. Check circuit breaker state
   ↓
2. Si OPEN:
   - Return 202 Accepted
   - Enqueue to hub-retry-queue
   - Log warning
   - NO llama al hub
   ↓
3. Si CLOSED o HALF_OPEN:
   - Llamada normal al hub
   - Si 5xx o timeout → increment failure_count
   - Si 5 failures consecutivos → state = OPEN
   ↓
4. Después de 60s en OPEN:
   - state = HALF_OPEN
   - Permite 3 requests de prueba
   ↓
5. Si pruebas exitosas → CLOSED
   Si fallan → OPEN nuevamente
```

**Ejemplo - Circuit Opening:**
```
Request 1: 500 → failure_count = 1
Request 2: 500 → failure_count = 2
Request 3: 500 → failure_count = 3
Request 4: 500 → failure_count = 4
Request 5: 500 → failure_count = 5 → Circuit OPEN
Request 6: Circuit OPEN → Return 202 + queue
...
After 60s: Circuit HALF_OPEN
Request 7: 200 → success 1/2
Request 8: 200 → success 2/2 → Circuit CLOSED
```

**OpenTelemetry Metrics:**

```python
# Métricas exportadas:
hub.calls{endpoint, status, success}       # Counter
hub.latency{endpoint, status, success}     # Histogram (seconds)
hub.cb_open{endpoint}                      # Gauge (0=CLOSED, 1=OPEN, 2=HALF_OPEN)
```

**Queries Prometheus:**
```promql
# Total llamadas al hub por endpoint
sum(rate(hub_calls[5m])) by (endpoint)

# Latencia p95 por endpoint
histogram_quantile(0.95, sum(rate(hub_latency_bucket[5m])) by (le, endpoint))

# Circuit breakers abiertos
hub_cb_open{endpoint="registerCitizen"} == 1

# Tasa de error por endpoint
sum(rate(hub_calls{success="false"}[5m])) by (endpoint) / 
sum(rate(hub_calls[5m])) by (endpoint) * 100
```

**Facade Endpoints (simple passthrough):**

| Endpoint Interno | Hub Endpoint | Método | Cache | Descripción |
|-----------------|--------------|--------|-------|-------------|
| `/register-citizen` | `/apis/registerCitizen` | POST | - | Facade sin transformación |
| `/unregister-citizen` | `/apis/unregisterCitizen` | DELETE | - | Facade sin transformación |
| `/authenticate-document` | `/apis/authenticateDocument` | PUT | - | Facade sin transformación |
| `/validate-citizen/{id}` | `/apis/validateCitizen/{id}` | GET | 5min | Facade con cache |
| `/register-operator` | `/apis/registerOperator` | POST | - | Facade sin transformación |
| `/register-transfer-endpoint` | `/apis/registerTransferEndPoint` | PUT | - | Facade sin transformación |
| `/operators` | `/apis/getOperators` | GET | 5min | Facade con cache + anti-stampede |

**Usado por:**
- `citizen` service: Llama `/register-citizen` (no llama al hub directamente)
- `signature` service: Llama `/authenticate-document` (no llama al hub directamente)
- `transfer` service: Llama `/operators` para discovery (con cache)

**Configuración:**
```bash
# Hub MinTIC (público)
MINTIC_BASE_URL=https://govcarpeta-apis-4905ff3c005b.herokuapp.com
MINTIC_OPERATOR_ID=operator-demo
MINTIC_OPERATOR_NAME=Carpeta Ciudadana Demo

# Redis (cache y anti-stampede)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_SSL=false

# Timeouts y retries
REQUEST_TIMEOUT=10
MAX_RETRIES=3

# Security
ENVIRONMENT=development  # development | production
ALLOW_INSECURE_OPERATOR_URLS=true  # Allow http:// in dev, false in prod
```

**Ejemplo de uso desde otros servicios:**
```python
# En citizen service
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{mintic_client_url}/register-citizen",
        json=citizen_data  # Mismo contrato del hub
    )

# En signature service
async with httpx.AsyncClient() as client:
    response = await client.put(
        f"{mintic_client_url}/authenticate-document",
        json={"idCitizen": 123, "UrlDocument": sas_url, "documentTitle": title}
    )
```

---

#### 7. Signature Service (Puerto 8006) ✍️

**Responsabilidades:**
- Calcular SHA-256 de documentos
- Firmar hashes (RSA mock o certificado K8s)
- Generar SAS URLs para hub
- Autenticar documentos con MinTIC Hub
- Almacenar registros de firma

**Flujo de Firma:**
```
1. POST /api/signature/sign
   Request: {
     document_id: "uuid",
     citizen_id: 1234567890,
     document_title: "Diploma"
   }

2. Signature Service:
   ├─ Calcula SHA-256
   ├─ Firma hash (RSA o mock)
   ├─ Genera SAS URL (24h)
   ├─ PUT /apis/authenticateDocument → Hub MinTIC
   │  Body: {
   │    "idCitizen": 1234567890,
   │    "UrlDocument": "https://...?sas=...",
   │    "documentTitle": "Diploma"
   │  }
   ├─ Guarda en signature_records table
   └─ Publica evento: document.authenticated

3. Response: {
     document_id: "uuid",
     signed_document_id: "uuid_signed",
     sha256_hash: "abc123...",
     signature_type: "RS256",
     signed_at: "2025-10-11T...",
     signed_blob_url: "https://...?sas=..."
   }
```

**POST /api/signature/verify**
- Verifica firma contra hash almacenado
- Publica evento: document.verified

**Base de Datos:**
```sql
CREATE TABLE signature_records (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR NOT NULL,
    citizen_id BIGINT NOT NULL,
    document_title VARCHAR NOT NULL,
    sha256_hash VARCHAR(64) NOT NULL,
    signature_algorithm VARCHAR,
    signature_value TEXT,
    sas_url TEXT,
    sas_expires_at TIMESTAMP,
    hub_authenticated BOOLEAN DEFAULT FALSE,
    hub_response TEXT,
    hub_authenticated_at TIMESTAMP,
    signed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Tecnologías:**
- cryptography (RSA signing)
- azure-storage-blob (SAS generation)
- httpx (hub calls)
- Redis (idempotency: authdoc:{citizenId}:{docId} TTL 15min)

---

#### 8. Read Models Service (Puerto 8007) 🔄 NUEVO - CQRS

**Responsabilidades:**
- Calcular SHA-256 de documentos
- Firmar hashes (RSA mock o certificado K8s)
- Generar SAS URLs para hub
- Autenticar documentos con MinTIC Hub
- Almacenar registros de firma

**Flujo de Firma:**
```
1. POST /api/signature/sign
   Request: {
     document_id: "uuid",
     citizen_id: 1234567890,
     document_title: "Diploma"
   }

2. Signature Service:
   ├─ Calcula SHA-256
   ├─ Firma hash (RSA o mock)
   ├─ Genera SAS URL (24h)
   ├─ PUT /apis/authenticateDocument → Hub MinTIC
   │  Body: {
   │    "idCitizen": 1234567890,
   │    "UrlDocument": "https://...?sas=...",
   │    "documentTitle": "Diploma"
   │  }
   ├─ Guarda en signature_records table
   └─ Publica evento: document.authenticated

3. Response: {
     document_id: "uuid",
     signed_document_id: "uuid_signed",
     sha256_hash: "abc123...",
     signature_type: "RS256",
     signed_at: "2025-10-11T...",
     signed_blob_url: "https://...?sas=..."
   }
```

**POST /api/signature/verify**
- Verifica firma contra hash almacenado
- Publica evento: document.verified

**Base de Datos:**
```sql
CREATE TABLE signature_records (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR NOT NULL,
    citizen_id BIGINT NOT NULL,
    document_title VARCHAR NOT NULL,
    sha256_hash VARCHAR(64) NOT NULL,
    signature_algorithm VARCHAR,
    signature_value TEXT,
    sas_url TEXT,
    sas_expires_at TIMESTAMP,
    hub_authenticated BOOLEAN DEFAULT FALSE,
    hub_response TEXT,
    hub_authenticated_at TIMESTAMP,
    signed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Tecnologías:**
- cryptography (RSA signing)
- azure-storage-blob (SAS generation)
- httpx (hub calls)
- Redis (idempotency: authdoc:{citizenId}:{docId} TTL 15min)

---

#### 8. Auth Service (Puerto 8008) 🔐 OIDC Provider

**Responsabilidades:**
- Proveedor OIDC mínimo viable (reemplaza Azure AD B2C)
- Emisión de JWT RS256
- JWKS endpoint para validación
- OpenID Connect Discovery

**Endpoints OIDC:**

**GET /.well-known/openid-configuration**
- OpenID Connect Discovery document
- Metadata del proveedor
- Endpoints, algoritmos, claims soportados

**GET /.well-known/jwks.json**
- JSON Web Key Set (public keys)
- Para validación de JWT por otros servicios
- Cached por Gateway/IAM en Redis (TTL 3600s)

**POST /auth/token**
- OAuth 2.0 token endpoint
- Input: username + password (OAuth2PasswordRequestForm)
- Output: JWT access token

**JWT Claims:**
```json
{
  "sub": "1234567890",           // Citizen ID
  "iss": "https://auth.carpeta-ciudadana.local",
  "aud": "carpeta-ciudadana",
  "exp": 1234567890,
  "iat": 1234567890,
  "name": "Juan Pérez",
  "email": "juan@example.com",
  "roles": ["citizen", "user"],
  "tenant": "carpeta-demo"
}
```

**GET /auth/userinfo**
- OIDC userinfo endpoint
- Requiere Bearer token válido
- Retorna user claims

**Key Management:**
- RSA 2048 generado in-memory (desarrollo)
- O cargado desde K8s Secret (producción)
- KID: `carpeta-key-1`
- Algorithm: RS256

**MVP Simplificaciones:**
- ❌ No database de usuarios (acepta cualquier credencial en dev)
- ❌ No refresh tokens
- ❌ No authorization code flow (solo password grant)
- ✅ Suficiente para testing y demo

**Uso en Gateway:**
```python
# Gateway valida JWT con JWKS cached
jwks = await get_cached_jwks("https://auth.local/.well-known/jwks.json")
payload = jwt.decode(token, jwks, algorithms=["RS256"])

# Propaga claims como headers internos
headers["X-User-Sub"] = payload["sub"]
headers["X-User-Roles"] = ",".join(payload["roles"])
headers["X-User-Tenant"] = payload["tenant"]
```

**Ventajas vs Azure AD B2C:**
- ✅ Gratis (sin costo)
- ✅ Control total
- ✅ Rápido para desarrollo
- ❌ No production-grade (para demo/universidad OK)

---

#### 9. IAM Service (Puerto 8009) 🛡️ ABAC - NUEVO

**Responsabilidades:**
- Attribute-Based Access Control (ABAC)
- Evaluación de políticas YAML
- Authorization endpoint
- FastAPI dependency para enforce policies

**Modelo ABAC:**
```yaml
# policies/citizen_policies.yaml
policies:
  - id: allow_own_documents_view
    description: "Citizens can view their own documents"
    effect: allow
    subject:
      roles: ["citizen"]
    resource:
      type: "document"
    action: "read"
    condition:
      citizen_id_matches: true  # resource.citizen_id == user.sub
  
  - id: allow_own_documents_download
    description: "Citizens can download their own authenticated documents"
    effect: allow
    subject:
      roles: ["citizen"]
    resource:
      type: "document"
    action: "download"
    condition:
      citizen_id_matches: true
      is_authenticated: true
  
  - id: allow_transfer_own_folder
    description: "Citizens can transfer their own folder"
    effect: allow
    subject:
      roles: ["citizen"]
    resource:
      type: "transfer"
    action: "initiate"
    condition:
      citizen_id_matches: true
  
  - id: deny_transfer_without_auth_docs
    description: "Cannot transfer without authenticated documents"
    effect: deny
    subject:
      roles: ["citizen"]
    resource:
      type: "transfer"
    action: "initiate"
    condition:
      has_unauthenticated_docs: true
```

**POST /authorize**
```json
Request: {
  "subject": {
    "sub": "1234567890",
    "roles": ["citizen"],
    "tenant": "carpeta-demo"
  },
  "resource": {
    "type": "document",
    "id": "doc-uuid",
    "citizen_id": 1234567890,
    "is_authenticated": true
  },
  "action": "download",
  "context": {}
}

Response: {
  "decision": "allow",  // or "deny"
  "reasons": ["Policy: allow_own_documents_download"],
  "evaluated_at": "2025-10-11T..."
}
```

**FastAPI Dependency:**
```python
from app.iam import require_authorization

@router.post("/documents/download")
async def download_document(
    document_id: str,
    user: User = Depends(get_current_user),
    _auth: None = Depends(
        require_authorization(
            resource_type="document",
            action="download"
        )
    )
):
    # Authorization already enforced by dependency
    ...
```

**Policy Evaluation:**
1. Load policies from YAML
2. Match subject (user roles/attributes)
3. Match resource (type, ownership)
4. Match action (read/write/delete/share/transfer)
5. Evaluate conditions (citizen_id_matches, etc.)
6. Return allow/deny

**Tecnologías:**
- PyYAML para políticas
- FastAPI dependencies
- Redis cache (policies, TTL 600s)

---

#### 10. Notification Service (Puerto 8010) 📧 NUEVO

**Responsabilidades:**
- Consumir eventos de Service Bus
- Enviar notificaciones por email (SMTP)
- Enviar webhooks HTTP
- Logging de entregas (delivery_logs table)
- Reintentos automáticos con exponential backoff
- Métricas con OpenTelemetry

**Event Consumers:**
1. `document-authenticated` → Email + Webhook
2. `transfer-confirmed` → Email + Webhook

**Email Templates (Jinja2):**
- `document_authenticated.html` - Notificación de autenticación
- `transfer_confirmed.html` - Notificación de transferencia

**Flow de Notificación:**
```
1. Event arrives from Service Bus
   ↓
2. Consumer validates event_id (Redis dedup)
   ↓
3. Fetch citizen email from DB
   ↓
4. Render Jinja2 template
   ↓
5. Send email (SMTP) con retry (3 intentos)
   ↓
6. Send webhook (HTTP POST) con retry (3 intentos)
   ↓
7. Log to delivery_logs table
   ↓
8. Record OpenTelemetry metrics
```

**POST /notify/test**
```json
Request: {
  "email": "test@example.com",
  "notification_type": "test"
}

Response: {
  "message": "Test notification sent",
  "email": {
    "success": true,
    "sent_at": "2025-10-11T...",
    "method": "smtp" // or "console"
  },
  "webhook": {
    "success": true,
    "status_code": 200,
    "sent_at": "2025-10-11T..."
  }
}
```

**GET /metrics**
- OpenTelemetry metrics
- Email/webhook success/failure counts
- Delivery latency histogram

**Database:**
```sql
CREATE TABLE delivery_logs (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    notification_type VARCHAR NOT NULL,  -- email, webhook
    recipient VARCHAR NOT NULL,
    subject VARCHAR,
    status VARCHAR DEFAULT 'pending',
    delivery_attempts INTEGER DEFAULT 0,
    response_status_code INTEGER,
    response_body TEXT,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    failed_at TIMESTAMP
);
```

**Configuración:**
```bash
# SMTP (optional)
SMTP_ENABLED=false
SMTP_HOST=localhost
SMTP_PORT=1025  # Mailhog for dev
SMTP_FROM_EMAIL=noreply@carpeta-ciudadana.local

# Webhook
WEBHOOK_ENABLED=true
NOTIF_WEBHOOK_URL=https://webhook.site/xxx
WEBHOOK_TIMEOUT=10

# OpenTelemetry
OTEL_ENABLED=true
OTEL_ENDPOINT=http://jaeger:4317
```

**Retry Logic:**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=1, max=10),
    retry=retry_if_exception_type(httpx.HTTPError)
)
async def send_webhook(...):
    # Retry automático
    # Intento 1: inmediato
    # Intento 2: +2s
    # Intento 3: +4s
    # Si falla 3 veces → DLQ
```

**Métricas (OpenTelemetry):**
- `notification_sent_total{type, status}`
- `notification_failed_total{type}`
- `notification_latency_seconds{type}` (histogram)

**Webhook Payload:**
```json
{
  "event_type": "document.authenticated",
  "timestamp": "2025-10-11T12:00:00Z",
  "data": {
    "document_id": "uuid",
    "citizen_id": 1234567890,
    "sha256_hash": "abc...",
    "hub_success": true
  }
}
```

**Tecnologías:**
- aiosmtplib (async SMTP)
- httpx (webhooks)
- Jinja2 (templates)
- tenacity (retry logic)
- OpenTelemetry (metrics)
- Service Bus consumer
- PostgreSQL (delivery logs)

---

#### 11. Sharing Service (Puerto 8011) 📤 NUEVO

**Responsabilidades:**
- Crear paquetes de compartición de documentos
- Generar shortlinks (tokens aleatorios)
- Validar permisos con ABAC (IAM)
- Generar SAS URLs temporales para acceso
- Cache de shortlinks en Redis
- Logging de accesos
- Soporte opcional para watermarks

**Flujo de Compartición:**
```
1. Usuario crea paquete (POST /share/packages)
   ↓
2. ABAC verifica permisos (IAM service)
   ↓
3. Genera token único (12 chars)
   ↓
4. Almacena en PostgreSQL (share_packages)
   ↓
5. Cache en Redis (share:{token}, TTL = expires_at)
   ↓
6. Publica evento share.package.created
   ↓
7. Retorna shortlink: https://carpeta.local/s/{token}
```

**Flujo de Acceso:**
```
1. Usuario accede GET /s/{token}
   ↓
2. Busca en Redis cache (share:{token})
   ↓
3. Si no está → consulta PostgreSQL
   ↓
4. Valida expiración y estado activo
   ↓
5. ABAC verifica consentimiento si audience != public
   ↓
6. Genera SAS URLs temporales (expiración corta)
   ↓
7. Log access (share_access_logs)
   ↓
8. Retorna documentos con SAS URLs
```

**POST /share/packages**
```json
Request: {
  "owner_email": "user@example.com",
  "document_ids": ["doc-uuid-1", "doc-uuid-2"],
  "expires_at": "2025-10-18T12:00:00Z",
  "audience": "public",  // or specific email
  "requires_auth": false,
  "watermark_enabled": false,
  "watermark_text": "Carpeta Ciudadana"
}

Response: {
  "package_id": 123,
  "token": "aBc123XyZ456",
  "shortlink": "https://carpeta.local/s/aBc123XyZ456",
  "expires_at": "2025-10-18T12:00:00Z",
  "document_count": 2
}
```

**GET /s/{token}**
```json
Response: {
  "package_id": 123,
  "owner_email": "user@example.com",
  "expires_at": "2025-10-18T12:00:00Z",
  "documents": [
    {
      "document_id": "doc-uuid-1",
      "filename": "certificado.pdf",
      "content_type": "application/pdf",
      "size": 524288,
      "sas_url": "https://storage.blob.core.windows.net/documents/doc-uuid-1?sv=2021-08-06&se=2025-10-12T12%3A00%3A00Z&sr=b&sp=r&sig=...",
      "watermarked": false
    }
  ],
  "watermark_text": null
}
```

**Database:**
```sql
CREATE TABLE share_packages (
    id SERIAL PRIMARY KEY,
    token VARCHAR(32) UNIQUE NOT NULL,
    owner_email VARCHAR NOT NULL,
    owner_citizen_id INTEGER,
    document_ids JSONB NOT NULL,  -- ["doc1", "doc2"]
    audience VARCHAR,  -- email or "public"
    requires_auth BOOLEAN DEFAULT FALSE,
    watermark_enabled BOOLEAN DEFAULT FALSE,
    watermark_text VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    access_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP NOT NULL,
    created_by VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed_at TIMESTAMP,
    revoked_at TIMESTAMP,
    metadata JSONB,
    
    INDEX idx_token (token),
    INDEX idx_owner (owner_email),
    INDEX idx_expires (expires_at)
);

CREATE TABLE share_access_logs (
    id SERIAL PRIMARY KEY,
    share_package_id INTEGER NOT NULL,
    token VARCHAR NOT NULL,
    accessed_by_email VARCHAR,
    accessed_by_ip VARCHAR,
    user_agent VARCHAR,
    access_granted BOOLEAN DEFAULT FALSE,
    denial_reason VARCHAR,
    accessed_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_package (share_package_id),
    INDEX idx_accessed_at (accessed_at)
);
```

**Redis Cache Schema:**
```
share:{token} → {
  "package_id": 123,
  "owner_email": "user@example.com",
  "document_ids": ["doc1", "doc2"],
  "expires_at": "2025-10-18T12:00:00Z",
  "watermark_enabled": false,
  "watermark_text": "Carpeta Ciudadana"
}
TTL = (expires_at - now) seconds
```

**ABAC Authorization:**
```python
# Para crear paquete (por cada documento)
abac_client.authorize(
    subject="user@example.com",
    resource="document:doc-uuid-1",
    action="share",
    context={"audience": "public"}
)

# Para acceder paquete (si audience != public)
abac_client.authorize(
    subject="viewer@example.com",
    resource="share:123",
    action="access",
    context={
        "owner": "user@example.com",
        "audience": "viewer@example.com"
    }
)
```

**SAS URLs:**
- Generadas al momento de acceso (no persistidas)
- Expiración: mínimo entre `SAS_DEFAULT_EXPIRY_HOURS` y tiempo hasta `expires_at`
- Permisos: READ only
- Opcional: parámetro `&watermark=true` en URL

**Watermark (opcional):**
- Flag en paquete: `watermark_enabled`
- Texto customizable: `watermark_text`
- Implementación:
  - Parámetro en SAS URL
  - O server-side rendering para PDFs

**Error Handling:**
```json
// Token no encontrado
404: {"detail": "Share package not found"}

// Token expirado
410: {"detail": "Share link has expired"}

// Revocado
403: {"detail": "Share link has been revoked"}

// No autorizado (ABAC)
403: {"detail": "Not authorized to share document doc-uuid-1: Not owner"}

// Fecha expiración en pasado
400: {"detail": "Expiration date must be in the future"}
```

**Eventos Publicados:**
```json
{
  "event_type": "share.package.created",
  "queue": "share-events",
  "payload": {
    "package_id": 123,
    "token": "aBc123XyZ456",
    "owner_email": "user@example.com",
    "document_count": 2,
    "audience": "public",
    "expires_at": "2025-10-18T12:00:00Z"
  }
}
```

**Configuración:**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://...

# Azure Blob (SAS generation)
AZURE_STORAGE_ACCOUNT_NAME=carpetastorage
AZURE_STORAGE_ACCOUNT_KEY=xxx
AZURE_STORAGE_CONTAINER=documents

# Redis
REDIS_HOST=carpeta-redis.redis.cache.windows.net
REDIS_PORT=6380
REDIS_SSL=true
REDIS_PASSWORD=xxx

# IAM (ABAC)
IAM_SERVICE_URL=http://carpeta-ciudadana-iam:8000

# Service Bus
SERVICEBUS_CONNECTION_STRING=Endpoint=sb://...

# Shortlink
SHORTLINK_BASE_URL=https://carpeta.ciudadana.gov.co
SHORTLINK_TOKEN_LENGTH=12

# SAS
SAS_DEFAULT_EXPIRY_HOURS=24

# Watermark
WATERMARK_ENABLED=false
WATERMARK_TEXT=Carpeta Ciudadana
```

**Tecnologías:**
- FastAPI (endpoints)
- SQLAlchemy (PostgreSQL)
- azure-storage-blob (SAS generation)
- carpeta-common (Redis, Service Bus, DB utils)
- secrets (secure token generation)
- httpx (IAM ABAC calls)

**Tests:**
- ✅ Token expirado → 410 Gone
- ✅ Documento inexistente → 404 Not Found
- ✅ Rol no autorizado (ABAC) → 403 Forbidden
- ✅ Fecha expiración pasada → 400 Bad Request
- ✅ Token revocado → 403 Forbidden
- ✅ Access logging funcional
- ✅ Redis cache hit/miss

---

#### 12. Read Models Service (Puerto 8007) 🔄 CQRS

**Responsabilidades:**
- Consumir eventos de Service Bus
- Proyectar read models optimizados (denormalizados)
- Proveer queries rápidas
- Cache con Redis

**Event Consumers (background tasks):**

1. **document-uploaded** → Actualiza `read_documents`
2. **document-authenticated** → Actualiza autenticación
3. **citizen-registered** → Enriquece citizen_name
4. **transfer-requested** → Crea registro en `read_transfers`
5. **transfer-confirmed** → Actualiza status de transfer

**Read Models (tablas optimizadas):**

```sql
-- Read model denormalizado para consultas rápidas
CREATE TABLE read_documents (
    id VARCHAR PRIMARY KEY,  -- document_id
    citizen_id BIGINT NOT NULL,
    citizen_name VARCHAR,  -- Denormalizado desde citizen.registered
    filename VARCHAR NOT NULL,
    title VARCHAR,
    sha256_hash VARCHAR(64),
    is_authenticated BOOLEAN DEFAULT FALSE,
    authenticated_at TIMESTAMP,
    status VARCHAR DEFAULT 'uploaded',
    uploaded_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    
    -- Indexes para queries rápidas
    INDEX idx_citizen_status (citizen_id, status),
    INDEX idx_uploaded_at (uploaded_at)
);

CREATE TABLE read_transfers (
    id INTEGER PRIMARY KEY,  -- transfer_id
    citizen_id BIGINT NOT NULL,
    citizen_name VARCHAR,
    source_operator_id VARCHAR,
    destination_operator_id VARCHAR,
    status VARCHAR DEFAULT 'requested',
    success BOOLEAN,
    requested_at TIMESTAMP NOT NULL,
    confirmed_at TIMESTAMP,
    
    INDEX idx_citizen_status (citizen_id, status)
);
```

**Endpoints (optimizados para lectura):**

**GET /read/documents?citizenId={id}&limit=50**
```json
Response: {
  "documents": [
    {
      "id": "uuid",
      "citizenId": 1234567890,
      "citizenName": "Juan Pérez",  // Denormalizado
      "filename": "diploma.pdf",
      "title": "Diploma Universitario",
      "isAuthenticated": true,
      "authenticatedAt": "2025-10-11T...",
      "uploadedAt": "2025-10-10T..."
    }
  ],
  "total": 10
}
```

**GET /read/transfers?citizenId={id}**
```json
Response: {
  "transfers": [
    {
      "id": 1,
      "citizenId": 1234567890,
      "sourceOperator": "operator-a",
      "destinationOperator": "operator-b",
      "status": "confirmed",
      "success": true,
      "requestedAt": "2025-10-11T...",
      "confirmedAt": "2025-10-11T..."
    }
  ],
  "total": 3
}
```

**CQRS Flow:**
```
Write Side (Commands):        Read Side (Queries):
┌─────────────┐             ┌─────────────┐
│  Citizen    │             │Read Models  │
│  Service    │             │  Service    │
└──────┬──────┘             └──────▲──────┘
       │                            │
       │ 1. POST register           │
       ▼                            │
┌─────────────┐                    │
│ PostgreSQL  │ citizens table     │
│  (Write)    │                    │
└──────┬──────┘                    │
       │                            │
       │ 2. Publish event           │
       ▼                            │
┌─────────────┐                    │
│Service Bus  │ citizen.registered │
│   Queue     │────────────────────┘
└─────────────┘   3. Consumer updates
                     read_documents
                     (denormalized)
```

**Ventajas CQRS:**
- ✅ Queries ultra-rápidas (datos denormalizados)
- ✅ Escalado independiente de reads/writes
- ✅ Cache agresivo en reads (writes invalidan)
- ✅ Resilencia (si read_models cae, writes siguen)

**Event Deduplication:**
```python
# Doble capa:
# 1. Service Bus native deduplication (10 min window)
# 2. Redis SETNX before processing
event_key = f"processing:{event_id}"
if not await setnx(event_key, "1", ttl=600):
    return  # Skip duplicate
```

**Tecnologías:**
- Azure Service Bus consumer
- PostgreSQL (read models)
- Redis (idempotency + cache)
- Background asyncio tasks

---

## ☁️ Infraestructura Azure

### Componentes Desplegados

**Resource Group:** carpeta-ciudadana-dev-rg  
**Región:** northcentralus (Iowa, USA)

| Componente | Servicio Azure | Configuración | Costo/mes |
|------------|----------------|---------------|-----------|
| **Compute** | AKS (Kubernetes) | 1 nodo Standard_B2s (2 vCPU, 4GB) | ~$30 |
| **Database** | PostgreSQL Flexible Server | Burstable B1ms | ~$15 |
| **Storage** | Blob Storage | LRS, container: documents | ~$1 |
| **Cache** | Redis self-hosted | En docker-compose (dev) / Pod (prod) | $0 |
| **Messaging** | Service Bus | Basic tier, 5 queues + DLQ | ~$0.05 |
| **Search** | OpenSearch | StatefulSet en AKS con PVC 8GB | $0 |
| **Network** | VNet + NSG | 10.0.0.0/16 | ~$5 |
| **Auth** | Self-hosted OIDC | Auth service en AKS | $0 |
| **IAM** | Self-hosted ABAC | IAM service en AKS | $0 |
| **TOTAL** | | **Free tier optimizado** | **~$51/mes** |

**Optimizaciones para presupuesto:**
- ❌ Sin Azure AD B2C (~$1,500/mes) → Auth service propio
- ❌ Sin ACR (~$5/mes) → Docker Hub gratis
- ❌ Sin Key Vault (~$3/mes) → K8s Secrets
- ❌ Sin Cognitive Search (~$250/mes) → OpenSearch self-hosted
- ✅ Redis self-hosted en pod → $0 vs Azure Cache ~$15/mes
- ✅ Service Bus Basic (no Standard) → $0.05 vs $10/mes

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

**Service Bus (Basic tier ~$0.05/mes):**

**5 Queues para CQRS:**

| Queue | Event Type | Producer | Consumers | DLQ |
|-------|------------|----------|-----------|-----|
| `citizen-registered` | citizen.registered | Citizen | Read Models | 3 retries |
| `document-uploaded` | document.uploaded | Ingestion | Metadata (indexer) | 3 retries |
| `document-authenticated` | document.authenticated | Signature | Metadata + **Notification** | 3 retries |
| `transfer-requested` | transfer.requested | Transfer | Read Models | 3 retries |
| `transfer-confirmed` | transfer.confirmed | Transfer | Read Models + **Notification** | 3 retries |

**Configuración:**
- TTL: 14 días
- Max delivery count: 3 (luego va a DLQ)
- Deduplicación nativa: 10 min window
- Authorization: Send + Listen (no manage)
- Batch size: 10 mensajes

**Dead Letter Queue (DLQ):**
- Auto-creado por Azure
- Mensajes que fallan 3 veces
- Monitoreo requerido para alertas
- Reprocesamiento manual

**Redis Deduplication (adicional):**
```python
# Evita eventos duplicados antes de Service Bus
event_key = f"event:{event_id}"
if not await setnx(event_key, "1", ttl=600):  # 10 min
    return  # Skip duplicate
```

**Mock Mode (desarrollo local):**
```bash
ENVIRONMENT=development
SERVICE_BUS_CONNECTION_STRING=  # Vacío = mock

# Output: 📨 [MOCK EVENT] Queue: citizen-registered | Type: citizen.registered
```

### Cache & Coordination

**Redis (Azure Cache for Redis C0 o self-hosted):**

**Key Patterns por Uso:**

| Uso | Pattern | TTL | Descripción |
|-----|---------|-----|-------------|
| **Rate Limiting** | `rl:{route}:{ip}:{bucket}` | 60s | Sliding window counter |
| **Search Cache** | `search:citizen:{id}:{hash}` | 120s | Query results cache |
| **Operators Cache** | `mintic:operators` | 300s | Hub operators list |
| **Distributed Locks** | `lock:{operation}:{resource}` | 10-120s | Atomic operations |
| **Event Dedup** | `event:{eventId}` | 600s | Event deduplication |
| **Processing Dedup** | `processing:{eventId}` | 600s | Consumer deduplication |
| **Transfer Idemp** | `xfer:idemp:{key}` | 900s | Transfer idempotency |
| **JWKS Cache** | `jwks:{url}` | 3600s | OAuth JWKS keys |
| **Document Cache** | `doc:{citizenId}:{docId}` | 300s | Single doc cache |

**Pub/Sub Channels:**
- `invalidate:search:{citizenId}` - Cache invalidation signals
- Subscribers: metadata service, read_models service

**Cache Invalidation Flow:**
```python
# 1. Document indexed/deleted
await opensearch.index_document(...)

# 2. Publish invalidation
redis.publish(f"invalidate:search:{citizen_id}", {...})

# 3. Subscribers delete matching keys
async for key in redis.scan_iter(match=f"search:*{citizen_id}*"):
    await redis.delete(key)
```

**Configuration:**
```bash
# Development (local Redis, no TLS)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_SSL=false

# Production (Azure Cache for Redis, TLS required)
REDIS_HOST=carpeta-cache.redis.cache.windows.net
REDIS_PORT=6380
REDIS_SSL=true
REDIS_PASSWORD=<primary-key>
```

### Search Engine

**OpenSearch 2.11.0 (StatefulSet en AKS):**
- **Storage**: PVC 8GB (Azure Premium SSD, managed-premium)
- **Resources**: 1Gi RAM, 512m heap (xms=xmx)
- **Security**: Disabled para desarrollo (DISABLE_SECURITY_PLUGIN=true)
- **Replication**: Single node (no replicas, discovery.type=single-node)

**Index: `documents`**

```json
{
  "mappings": {
    "properties": {
      "documentId": {"type": "keyword"},
      "citizenId": {"type": "long"},
      "title": {
        "type": "text",
        "fields": {"keyword": {"type": "keyword"}}
      },
      "filename": {"type": "text"},
      "issuer": {"type": "keyword"},
      "hash": {"type": "keyword"},
      "tags": {"type": "keyword"},
      "hubAuthAt": {"type": "date"},
      "signatureStatus": {"type": "keyword"},
      "status": {"type": "keyword"},
      "contentType": {"type": "keyword"},
      "createdAt": {"type": "date"},
      "updatedAt": {"type": "date"}
    }
  },
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "refresh_interval": "5s"
  }
}
```

**Indexación:**
- **Automática** via event consumers (document.uploaded, document.authenticated)
- **Actualización** parcial en autenticación
- **Eliminación** en soft delete o transfer

**Consumers en metadata-service:**
```python
# Background task en lifespan
consumer = MetadataEventConsumer(settings, opensearch)
consumer_task = asyncio.create_task(consumer.start_consumers())

# Escucha:
# - document-uploaded → index_document()
# - document-authenticated → update authentication
# - Invalida cache vía Redis Pub/Sub
```

---

## 🔄 Flujos de Datos

### 1. Registro de Ciudadano (con validación y eventos)

```
┌─────────┐
│Frontend │ Valida: 10 dígitos, campos obligatorios
└────┬────┘
     │ POST /api/citizens/register
     │ {id: 1234567890, name, address, email}
     ▼
┌─────────┐
│ Gateway │ Rate limit (Redis) + CORS
└────┬────┘
     │ Proxy → citizen service
     ▼
┌─────────┐
│ Citizen │ 
│ Service │
└────┬────┘
     │ 1. Valida 10 dígitos (Pydantic)
     │ 2. Check duplicate en PostgreSQL
     │ 3. db.flush() (no commit)
     ├────────────────────┐
     │                    │
     ▼                    ▼
┌──────────┐      ┌──────────────┐
│PostgreSQL│      │MinTIC Client │
│(pending) │      └──────┬───────┘
└──────────┘             │ POST /apis/registerCitizen
                         │ {id: "1234567890", name, ...}
                         ▼
                  ┌──────────────┐
                  │  GovCarpeta  │
                  │  Hub (API)   │
                  └──────┬───────┘
                         │
                         │ 201 Created ✅
                         │ o 400 "ya registrado" ❌
                         ▼
                  ┌──────────────┐
                  │ Citizen Svc  │
                  │ db.commit()  │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │Service Bus   │
                  │citizen-      │
                  │registered    │
                  └──────────────┘
```

**Rollback en error:**
- Si hub retorna 400/500 → `db.rollback()` 
- Ciudadano NO se crea localmente
- Frontend recibe error específico

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

### 3. Búsqueda de Documentos (CQRS + OpenSearch + Redis Cache)

```
                    WRITE SIDE                    READ SIDE
                    
┌─────────┐                                  ┌─────────┐
│Frontend │                                  │Frontend │
│(Upload) │                                  │(Search) │
└────┬────┘                                  └────┬────┘
     │ POST /api/documents/upload-url            │ GET /api/metadata/search?q=diploma
     ▼                                            ▼
┌───────────┐                              ┌─────────┐
│Ingestion  │                              │Metadata │
│  Service  │                              │ Service │
└─────┬─────┘                              └────┬────┘
      │ 1. Save metadata                        │ 1. Check cache
      ▼                                          ▼
┌───────────┐                              ┌─────────┐
│PostgreSQL │                              │  Redis  │ GET search:citizen:123:abc...
│  (Write)  │                              └────┬────┘
└─────┬─────┘                                   │ HIT? → Return
      │ 2. Publish event                        │ MISS? → Query OpenSearch
      ▼                                          ▼
┌───────────┐                              ┌───────────┐
│Service Bus│ document.uploaded            │OpenSearch │
│   Queue   │─────────────────────────┐    │   Index   │
└───────────┘                         │    └─────┬─────┘
                                      │          │ Results
      ┌───────────────────────────────┘          │
      │ 3. Consumer (metadata-service)           ▼
      ▼                                    ┌─────────┐
┌───────────┐                              │  Redis  │ SET cache EX 120
│ Document  │ index_document()             └─────────┘
│ Indexer   │                                    │
└─────┬─────┘                                   │
      │ 4. Index in OpenSearch                  │
      ▼                                          │
┌───────────┐                                   │
│OpenSearch │                                   │
│documents  │                                   │
└─────┬─────┘                                   │
      │ 5. Invalidate cache                     │
      ▼                                          │
┌───────────┐                                   │
│  Redis    │ PUBLISH invalidate:search:123    │
│  Pub/Sub  │──────────────────────────────────┘
└───────────┘   6. Delete search:*123*
```

**Cache Invalidation (Redis Pub/Sub):**
```python
# Cuando se indexa/actualiza documento:
redis.publish(f"invalidate:search:{citizen_id}", {...})

# Subscriber elimina keys relacionados:
async for key in redis.scan_iter(match=f"search:*{citizen_id}*"):
    await redis.delete(key)
```

**Ventajas:**
- 🚀 Cache reduce latencia 80%+
- 🔍 OpenSearch: fuzzy matching, relevance scoring
- 🔄 Invalidación inteligente (solo citizen afectado)
- 📊 Separación CQRS (writes vs reads)
- 🎯 Read models denormalizados (queries rápidas)

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
- Actual: OIDC con Auth service (JWT RS256)
- Futuro: Azure AD B2C integration
- Flow: Authorization Code + PKCE

**Hub MinTIC (GovCarpeta):**
- API pública, sin autenticación requerida
- Solo HTTP/HTTPS simple con timeouts cortos
- Retry automático en fallos

**B2B (P2P entre Operadores):**
- API Key en header `X-API-Key`
- TLS obligatorio
- Usado solo para transferencias P2P

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

### Gestión de Secretos

**Almacenamiento:**
- ✅ Kubernetes Secrets (base64 encoded)
- ✅ Nunca en código fuente
- ✅ Inyectados por variables de entorno
- 🔄 Rotación automática cada 30 días

**Secretos Gestionados:**

| Secret | Key | Rotación | Usado por |
|--------|-----|----------|-----------|
| `jwt-secret` | `JWT_SECRET_KEY` | Automática (30d) | gateway, auth |
| `api-keys` | `OPERATOR_API_KEY` | Automática (30d) | transfer (P2P entre operadores) |
| `redis-auth` | `REDIS_PASSWORD` | Manual (Azure Portal) | Todos los servicios con Redis |
| `postgresql-auth` | `POSTGRESQL_PASSWORD` | Manual (Azure Portal) | Todos los servicios con DB |
| `azure-storage-secret` | `AZURE_STORAGE_ACCOUNT_KEY` | Manual (Azure Portal) | ingestion, signature, sharing |
| `servicebus-connection` | `SERVICEBUS_CONNECTION_STRING` | Manual (Azure Portal) | metadata, notification, read_models |

**Rotación Automática:**

Sistema implementado con CronJob de Kubernetes:
- **Frecuencia**: Cada 30 días (día 1 del mes a las 3:00 AM)
- **Proceso**:
  1. Backup encriptado de secretos actuales (AES-256-CBC)
  2. Generación de nuevos secretos (JWT: 64 hex, API keys: 32 chars)
  3. Actualización en Kubernetes Secrets
  4. Rollout restart automático de deployments afectados
  5. Log de rotación con timestamp

**Scripts Disponibles:**
```bash
# Rotación manual
./scripts/secrets/rotate-secrets.sh

# Backup encriptado
./scripts/secrets/backup-secrets.sh

# Restore desde backup
./scripts/secrets/restore-secrets.sh backups/secrets_backup_TIMESTAMP.yaml.enc

# Dry run (preview)
./scripts/secrets/rotate-secrets.sh --dry-run
```

**CronJob Kubernetes:**
```bash
# Desplegar rotación automática
kubectl apply -f deploy/kubernetes/cronjob-rotate-secrets.yaml

# Ver estado
kubectl get cronjob rotate-secrets -n carpeta-ciudadana

# Forzar ejecución
kubectl create job rotate-secrets-manual \
  --from=cronjob/rotate-secrets -n carpeta-ciudadana
```

**Backups Encriptados:**
- Master key local (`master.key`) para encriptación
- Backups con AES-256-CBC + PBKDF2
- Checksum SHA-256 para verificación de integridad
- ⚠️ **CRÍTICO**: Guardar master key en lugar seguro

**Deployments Afectados por Rotación:**
- Gateway (JWT)
- Auth (JWT)
- Transfer (OPERATOR_API_KEY para P2P)

**Migración Futura (con presupuesto):**
- Azure Key Vault + CSI Driver
- Rotación integrada con Azure
- Auditoría completa de accesos
- Versionado automático de secretos
- Sin necesidad de almacenar en K8s

Ver `scripts/secrets/README.md` para documentación completa.

---

## 📊 Observabilidad

Sistema completo de observabilidad con **OpenTelemetry** instrumentando todos los servicios.

### 🔍 Trazas Distribuidas

**Propagación de `traceparent`:**
- Gateway es el punto de entrada y propaga contexto de tracing
- Todos los servicios participan en trazas distribuidas
- Correlación automática de logs con trace IDs

**Spans Automáticos:**
```
HTTP Request → Gateway [traceparent]
                 ↓
         ┌───────┴────────┐
         ▼                ▼
    Citizen Service   Metadata Service
         ├─ HTTP span       ├─ HTTP span
         ├─ DB span         ├─ DB span
         ├─ Redis span      ├─ Redis span
         └─ httpx span      └─ Service Bus span
```

**Instrumentación Automática:**
- ✅ FastAPI: Todos los endpoints HTTP
- ✅ httpx: Llamadas externas (MinTIC Hub, otros operadores)
- ✅ SQLAlchemy: Queries a PostgreSQL
- ✅ Redis: Operaciones de cache
- ✅ Service Bus: Publicación y consumo de mensajes

**Custom Spans:**
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("authenticate_document") as span:
    span.set_attribute("document.id", doc_id)
    span.set_attribute("citizen.id", citizen_id)
    # Tu lógica aquí
```

### 📈 Métricas

**HTTP Metrics (todos los servicios):**
- `http.server.request.duration` (histogram) - Latencia p50/p95/p99
- `http.server.request.count` (counter) - Total requests
- `http.server.error.count` (counter) - Errores 5xx

**Cache Metrics (gateway, metadata, mintic_client, sharing):**
- `cache.hits` / `cache.misses` (counter)
- `cache.evictions` (counter)
- `redis.command.duration` (histogram)

**Queue Metrics (metadata, notification, read_models, transfer):**
- `queue.message.published` / `consumed` / `failed` (counter)
- `queue.dlq.length` (gauge) - Dead Letter Queue
- `queue.processing.duration` (histogram)

**External Call Metrics:**
- `external.call.duration` (histogram) - Latencia a MinTIC Hub, otros operadores
- `external.call.errors` (counter)

**Rate Limit Metrics (gateway):**
- `rate_limit.exceeded` (counter)

**Circuit Breaker Metrics (transfer, mintic_client):**
- `circuit_breaker.state` (gauge) - 0=CLOSED, 1=OPEN, 2=HALF_OPEN
- `circuit_breaker.failures` (counter)
- `saga.compensation.executed` (counter)

### 📊 Dashboards Predefinidos

**4 Dashboards Grafana (JSON):**

1. **API Latency** (`observability/grafana-dashboards/api-latency.json`)
   - HTTP request duration p95 por servicio y endpoint
   - Error rate (5xx) por servicio
   - Request rate
   - Rate limit exceeded
   - External API call duration
   - **Alertas**: p95 > 2s, error rate > 1%

2. **Transfers Saga** (`observability/grafana-dashboards/transfers-saga.json`)
   - Transfer saga duration p95
   - Intra-region vs inter-region latency
   - Success rate
   - Circuit breaker state
   - Compensation rollbacks
   - **Alertas**: Intra-region p95 > 2s, inter-region p95 > 5s

3. **Queue Health** (`observability/grafana-dashboards/queue-health.json`)
   - Published vs consumed messages
   - Dead Letter Queue length
   - Failed message processing
   - Queue processing latency
   - Queue backlog (age of oldest message)
   - **Alertas**: DLQ length > 10

4. **Cache Efficiency** (`observability/grafana-dashboards/cache-efficiency.json`)
   - Cache hit rate (overall y por servicio)
   - Redis connection pool usage
   - Redis command latency
   - Distributed lock contention
   - Idempotency key usage
   - Cache evictions

### 🚨 Alertas Configuradas

**11 Alertas con umbrales simples** (`observability/alerts/prometheus-alerts.yaml`):

| Alerta | Umbral | Duración | Severidad |
|--------|--------|----------|-----------|
| HighAPILatencyP95 | > 2s | 5min | warning |
| VeryHighAPILatencyP95 | > 5s | 2min | critical |
| HighErrorRate | > 1% | 2min | warning |
| CriticalErrorRate | > 5% | 1min | critical |
| TransferIntraRegionLatency | > 2s | 5min | warning |
| TransferInterRegionLatency | > 5s | 5min | warning |
| MessagesInDLQ | > 10 | 2min | warning |
| HighQueueProcessingFailures | > 10% | 5min | warning |
| LowCacheHitRate | < 50% | 10min | info |
| RedisConnectionPoolExhausted | > 90% | 2min | warning |
| CircuitBreakerOpen | state=1 | 1min | warning |

### 🔧 Exporters

**Modo Development (sin créditos):**
```bash
OTEL_USE_CONSOLE=true  # Exporta a stdout
OTEL_EXPORTER_OTLP_ENDPOINT=  # Vacío
```

**Modo Production (Azure Monitor):**
```bash
OTEL_USE_CONSOLE=false
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxx;IngestionEndpoint=https://...
```

**OTLP Collector (Kubernetes):**
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

### 📖 Queries Útiles

**Prometheus/Grafana:**
```promql
# Latencia p95 API Gateway
histogram_quantile(0.95, 
  sum(rate(http_server_request_duration_bucket{service_name="gateway"}[5m])) by (le, http_route)
)

# Error rate por servicio
sum(rate(http_server_error_count[5m])) by (service_name) / 
sum(rate(http_server_request_count[5m])) by (service_name) * 100

# Cache hit rate
sum(rate(cache_hits[5m])) / 
(sum(rate(cache_hits[5m])) + sum(rate(cache_misses[5m]))) * 100
```

**Azure Monitor (Kusto):**
```kusto
// Latencia p95 por endpoint
customMetrics
| where name == "http.server.request.duration"
| summarize percentile(value, 95) by tostring(customDimensions.http_route)

// Trace completa de un request
traces
| where operation_Id == "00-abc123-def456-01"
| project timestamp, message, severityLevel, customDimensions
| order by timestamp asc
```

### Logging

**Niveles:**
- INFO: Operaciones normales
- WARNING: Fallos no críticos (ej: MinTIC sync failed)
- ERROR: Errores que requieren atención

**Formato:**
```
2025-10-11T19:00:00.000 INFO [citizen] trace_id=abc123 Registering citizen: 123456
2025-10-11T19:00:01.234 INFO [citizen] trace_id=abc123 Citizen 123456 registered in MinTIC Hub
```

**Correlación con Traces:**
- Todos los logs incluyen `trace_id` y `span_id`
- Permite correlacionar logs con trazas distribuidas en Azure Monitor

### 📚 Documentación Completa

Ver `OBSERVABILITY_GUIDE.md` y `observability/README.md` para:
- Guía de implementación completa
- Cómo agregar métricas custom
- Deploy de dashboards y alertas
- Integración con Azure Monitor
- Ejemplos de queries

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

**Backend (Python):**
- Cada servicio tiene `/tests/unit/`
- pytest con pytest-asyncio
- Coverage target: 80%+
- Mock de Redis con fakeredis
- Mock de Service Bus

**Ejecutar:**
```bash
cd services/gateway
pytest tests/ -v --cov=app
```

### Contract Tests

**Integraciones:**
- Gateway ↔ Services
- MinTIC Client ↔ GovCarpeta Hub
- pytest-httpx para mocking HTTP

**Ejemplo:**
```python
@pytest.mark.asyncio
async def test_mintic_register_citizen(httpx_mock):
    httpx_mock.add_response(
        url="https://govcarpeta-apis.../apis/registerCitizen",
        json={"message": "Success"}
    )
    # Test code
```

### E2E Tests (Playwright)

**Ubicación:** `tests/e2e/`

**Flow completo testado:**
```
1. Register citizen
   ↓
2. Login
   ↓
3. Upload document
   ↓
4. Sign document
   ↓
5. Authenticate with hub
   ↓
6. Search documents
   ↓
7. Share document (generate shortlink)
   ↓
8. Access shared link
   ↓
9. Initiate P2P transfer
   ↓
10. Confirm transfer
```

**Configuración:**
```typescript
// tests/e2e/playwright.config.ts
export default defineConfig({
  projects: [
    { name: 'chromium' },
    { name: 'firefox' },
    { name: 'webkit' },
    { name: 'Mobile Chrome' },
    { name: 'Mobile Safari' }
  ],
  use: {
    baseURL: 'http://localhost:3000',
    apiURL: 'http://localhost:8000'
  }
});
```

**Mocking Hub MinTIC:**
```typescript
// Mock responses for testing
await page.route('**/apis/registerCitizen', async (route) => {
  await route.fulfill({
    status: 200,
    body: JSON.stringify({ message: 'Success' })
  });
});
```

**Ejecutar:**
```bash
cd tests/e2e
npm install
npx playwright test
npx playwright test --headed  # Ver browser
npx playwright show-report    # Ver reporte HTML
```

### Load Tests

**k6 (JavaScript):**

Ubicación: `tests/load/k6-load-test.js`

**Scenarios:**
- 50% Document upload
- 30% Search
- 20% P2P transfer

**Stages:**
```javascript
stages: [
  { duration: '30s', target: 10 },   // Ramp up
  { duration: '1m', target: 50 },    // Normal load
  { duration: '2m', target: 50 },    // Stay
  { duration: '30s', target: 100 },  // Spike
  { duration: '1m', target: 100 },   // Peak
  { duration: '30s', target: 0 }     // Ramp down
]
```

**Thresholds:**
```javascript
thresholds: {
  'http_req_duration': ['p(95)<2000', 'p(99)<5000'],
  'http_req_failed': ['rate<0.05'],  // Error < 5%
  'document_upload_duration': ['p(95)<3000'],
  'search_duration': ['p(95)<1000'],
  'transfer_duration': ['p(95)<5000']
}
```

**Ejecutar:**
```bash
cd tests/load
k6 run k6-load-test.js
k6 run --vus 100 --duration 5m k6-load-test.js
```

**Locust (Python):**

Ubicación: `tests/load/locustfile.py`

**Tasks:**
- Upload document (50% weight)
- Search (30% weight)
- Transfer (20% weight)
- List documents (10% weight)
- Get operators (10% weight)

**Ejecutar:**
```bash
cd tests/load
locust -f locustfile.py
locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m --headless
```

**Web UI:** http://localhost:8089

### Performance Targets

| Métrica | Target | Threshold |
|---------|--------|-----------|
| API latency (p95) | < 1s | < 2s |
| API latency (p99) | < 2s | < 5s |
| Error rate | < 1% | < 5% |
| Upload (p95) | < 2s | < 3s |
| Search (p95) | < 500ms | < 1s |
| Transfer (p95) | < 3s | < 5s |

---

## 💾 Backup & Disaster Recovery

### RPO y RTO

**Recovery Point Objective (RPO):**
- PostgreSQL: **24 horas** (backups diarios)
- OpenSearch: **24 horas** (snapshots diarios)
- Azure Blob Storage: **0** (replicado por Azure LRS)

**Recovery Time Objective (RTO):**
- PostgreSQL: **< 30 minutos**
- OpenSearch: **< 1 hora**
- Aplicación completa: **< 2 horas**

### PostgreSQL Backups

**Backup automático (7 días):**

Script: `scripts/backup/backup-postgres.sh`

**Características:**
- Compresión gzip
- Checksum SHA-256
- Retención 7 días
- Log de backups

**Manual:**
```bash
cd scripts/backup
./backup-postgres.sh

# Custom retention
./backup-postgres.sh --retention-days 14
```

**Restore:**
```bash
./restore-postgres.sh backups/postgres/postgres_backup_20251012_150000.sql.gz
```

**CronJob (Kubernetes):**
```yaml
# Deploy automático cada día a las 2:00 AM
kubectl apply -f deploy/kubernetes/cronjob-backup-postgres.yaml
```

### OpenSearch Snapshots

**Ubicación:** `scripts/backup/backup-opensearch.sh`

**Características:**
- Snapshot repository en Azure Blob
- Incremental snapshots
- Retención 7 días
- Solo cuando uso < 80%

**Manual:**
```bash
cd scripts/backup
./backup-opensearch.sh
```

**Restore:**
```bash
./restore-opensearch.sh snapshot_20251012_150000
```

### Azure Blob Storage

**Backup nativo de Azure:**
- Replicación LRS (3 copias en región)
- Soft delete: 7 días
- Point-in-time restore: No (requiere Premium)

**Cleanup de blobs huérfanos:**

Script: `scripts/backup/cleanup-orphan-blobs.sh`

**Proceso:**
1. Lista todos los blobs en Azure Storage
2. Consulta PostgreSQL por document_metadata
3. Identifica blobs sin metadata (huérfanos)
4. Soft delete de blobs huérfanos
5. Log de cleanup

**Ejecutar:**
```bash
cd scripts/backup
./cleanup-orphan-blobs.sh --dry-run  # Preview
./cleanup-orphan-blobs.sh             # Execute
```

**CronJob (semanal):**
```bash
kubectl apply -f deploy/kubernetes/cronjob-cleanup-orphans.yaml
```

### Pruebas de Restore

**Última prueba:** [Documentar fecha]

**Proceso de prueba:**
1. Crear backup de producción
2. Restaurar en ambiente staging
3. Verificar integridad de datos
4. Probar funcionalidad de aplicación
5. Medir tiempo de restore (RTO)
6. Documentar resultados

**Checklist de restore:**
- [ ] PostgreSQL restaurado correctamente
- [ ] Todas las tablas presentes
- [ ] Conteos de registros correctos
- [ ] OpenSearch índices restaurados
- [ ] Documentos buscables
- [ ] Azure Blobs accesibles
- [ ] Aplicación funcional end-to-end
- [ ] Login funciona
- [ ] Upload/download funciona
- [ ] Búsqueda funciona
- [ ] Transferencias funcionan

**Comando de verificación:**
```bash
# Verificar conteo de ciudadanos
psql -c "SELECT COUNT(*) FROM citizens;"

# Verificar documentos
psql -c "SELECT COUNT(*) FROM document_metadata WHERE is_deleted=false;"

# Verificar OpenSearch
curl -X GET "localhost:9200/documents/_count"
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

**Hard Delete:**
- Job mensual elimina registros soft-deleted > retention
- Blobs eliminados de Azure Storage
- Irreversible

**GC Job:**
```bash
kubectl apply -f deploy/kubernetes/cronjob-gc-soft-deleted.yaml
```

### Disaster Recovery Plan

**Escenarios:**

**1. Corrupción de PostgreSQL:**
- Detener aplicación
- Restore último backup (30 min)
- Verificar integridad
- Reiniciar aplicación

**2. Pérdida de región Azure:**
- Provisionar nueva región
- Deploy infraestructura (Terraform)
- Restore backups desde offsite
- Actualizar DNS
- RTO: 4-6 horas

**3. Eliminación accidental de datos:**
- Restore desde backup a ambiente temporal
- Extraer datos específicos
- Importar a producción
- RTO: 1-2 horas

**4. Compromiso de seguridad:**
- Rotar secretos inmediatamente
- Restore desde backup pre-compromiso
- Auditar accesos
- Notificar stakeholders

**Contactos de emergencia:**
- DevOps: [Documentar]
- Azure Support: [Documentar]
- Database Admin: [Documentar]

---

## 📦 Tecnologías

### Backend Stack
- **Framework:** FastAPI 0.109+
- **Runtime:** Python 3.13.7
- **Package Manager:** Poetry 2.2.1 (con venv)
- **ORM:** SQLAlchemy 2.0 (async)
- **DB Driver:** asyncpg 0.30.0
- **HTTP Client:** httpx 0.26.x
- **Validation:** Pydantic 2.5+ (con email validator)
- **Shared Package:** carpeta-common (utilities compartidas)

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
   - Rate limiting con Redis (sliding window)
   - Authentication/Authorization
   - Proxy a microservicios

2. **Service Discovery** ✅
   - Auto-detección de ambiente
   - Kubernetes DNS en producción
   - localhost en desarrollo

3. **Presigned URLs** ✅
   - Upload/download directo a storage
   - No saturar backend
   - Menor latencia
   - SAS tokens (Azure) con expiración

4. **Async Communication** ✅
   - httpx AsyncClient
   - Non-blocking calls a MinTIC
   - Fail gracefully
   - Retry logic con tenacity

5. **Database per Service** ✅
   - Cada servicio su propia base de datos
   - Tablas compartidas cuando necesario
   - Loose coupling
   - Utilities compartidas (carpeta-common)

6. **Event-Driven Architecture** ✅
   - Azure Service Bus (production)
   - Mock mode (development)
   - Deduplicación con Redis
   - Queues: citizen-registered, document-authenticated, transfer-completed

7. **Distributed Caching** ✅
   - Redis para cache (search, operators)
   - Anti-stampede pattern (single-flight)
   - TTL configurables
   - Cache invalidation

8. **Distributed Locks** ✅
   - Redis locks con tokens UUID
   - Atomic operations (delete, transfer)
   - Auto-expiration (TTL)
   - Compare-and-delete con Lua script

9. **Idempotency** ✅
   - Transfer idempotency keys
   - Event deduplication
   - Redis SETNX pattern
   - 10-15 min windows

10. **Shared Library Pattern** ✅
    - carpeta-common package
    - Utilities: database, redis, messaging, middleware
    - Instalado como editable dependency
    - Fallback mode si no disponible

### Preparados (parcialmente implementados)

11. **CQRS** ⏳
    - Separación reads/writes
    - OpenSearch para reads optimizados
    - PostgreSQL para writes
    - TODO: Event sourcing completo

12. **Saga Pattern** ⏳
    - Transferencias P2P distribuidas
    - Confirmation callbacks
    - TODO: Compensation logic completo

13. **Circuit Breaker** ⏳
    - Retry logic implementado
    - TODO: Circuit breaking real

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

## ✅ Implementaciones Recientes

### Completadas

1. **Event Publishing (Service Bus)** ✅
   - Azure Service Bus (Basic tier, ~$0.05/mes)
   - Mock mode para desarrollo local
   - 3 queues: citizen-registered, document-authenticated, transfer-completed
   - Deduplicación con Redis (event:{id} TTL 10min)
   - Publishers en citizen, signature, transfer services

2. **OpenSearch Integration** ✅
   - StatefulSet en AKS con PVC 8GB
   - Índice `documents` con mapping completo
   - Full-text search (multi-match, fuzzy)
   - Cache de búsquedas en Redis (120s TTL)
   - Integrado en metadata service

3. **Signature Service** ✅
   - SHA-256 hashing
   - RSA signing (mock o certificado K8s)
   - SAS URL generation para hub
   - Autenticación con MinTIC Hub
   - PostgreSQL storage (signature_records table)
   - Event publishing

4. **Redis Integration** ✅
   - Local: Redis 7 en docker-compose
   - Production: Azure Cache for Redis (TLS 6380)
   - Rate limiting (sliding window)
   - Distributed locks
   - Cache (search, operators, JWKS)
   - Idempotency keys

5. **Shared Package (carpeta-common)** ✅
   - Package Python instalable
   - Database utilities (db_utils.py)
   - Redis client (redis_client.py)
   - Message broker (message_broker.py)
   - Middleware (CORS, logging)
   - Instalado en todos los servicios

### En Progreso

6. **Rate Limiting Distribuido** 🔄
   - Redis backend configurado
   - Sliding window algorithm
   - TODO: Integrar slowapi con Redis

7. **MinTIC Cache** 🔄
   - Single-flight pattern implementado
   - TODO: Aplicar a getOperators endpoint

8. **Transfer Locks** 🔄
   - Distributed locks implementados
   - TODO: Integrar en transferCitizenConfirm

### Próximas (Baja Prioridad)

9. **Real Authentication**
   - Azure AD B2C para usuarios
   - OIDC completo con PKCE
   - Social login

10. **Sharing Service**
    - Compartir paquetes de documentos
    - URLs temporales

11. **Notification Service**
    - Emails transaccionales
    - Webhooks

12. **Metrics & Monitoring**
    - Prometheus metrics
    - Grafana dashboards
    - Azure Monitor integration

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

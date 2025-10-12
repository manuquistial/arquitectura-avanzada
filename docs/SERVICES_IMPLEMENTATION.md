# 🔧 Implementación de Servicios y Observabilidad

Documentación completa de la implementación de microservicios y sistema de observabilidad.

---

## 📋 Tabla de Contenidos

1. [Estructura de Services](#estructura-de-services)
2. [Paquete Común (carpeta_common)](#paquete-común-carpeta_common)
3. [Microservicios](#microservicios)
4. [Observabilidad](#observabilidad)
5. [Patrones y Estándares](#patrones-y-estándares)
6. [Testing](#testing)

---

## 📁 Estructura de Services

```
services/
├── common/                      # Paquete compartido
│   ├── carpeta_common/
│   │   ├── __init__.py
│   │   ├── circuit_breaker.py  # Circuit breaker pattern
│   │   ├── db_utils.py          # Utilidades de base de datos
│   │   ├── message_broker.py   # Azure Service Bus client
│   │   ├── middleware.py        # Middlewares comunes (CORS, logging)
│   │   ├── observability.py    # OpenTelemetry setup
│   │   ├── redis_client.py      # Cliente Redis compartido
│   │   └── saga.py              # Saga pattern para transacciones distribuidas
│   ├── pyproject.toml
│   └── poetry.lock
│
├── gateway/                     # API Gateway (puerto 8000)
├── citizen/                     # Gestión de ciudadanos (puerto 8001)
├── ingestion/                   # Upload/download documentos (puerto 8002)
├── metadata/                    # Búsqueda y metadata (puerto 8003)
├── transfer/                    # Transferencias P2P (puerto 8004)
├── mintic_client/              # Cliente MinTIC Hub (puerto 8005)
├── signature/                   # Firma y autenticación (puerto 8006)
├── read_models/                # CQRS read models (puerto 8007)
├── auth/                        # OIDC provider (puerto 8008)
├── iam/                         # ABAC authorization (puerto 8009)
├── notification/               # Email y webhooks (puerto 8010)
└── sharing/                    # Compartición documentos (puerto 8011)
```

---

## 📦 Paquete Común (carpeta_common)

### Propósito

Centralizar funcionalidad compartida para evitar duplicación de código entre microservicios.

### Estructura

```python
carpeta_common/
├── __init__.py
├── circuit_breaker.py      # Circuit breaker pattern
├── db_utils.py             # Database utilities
├── message_broker.py       # Service Bus integration
├── middleware.py           # CORS y logging
├── observability.py        # OpenTelemetry
├── redis_client.py         # Redis client
└── saga.py                 # Saga pattern
```

### Módulos Principales

#### 1. circuit_breaker.py

**Propósito:** Implementar patrón Circuit Breaker para llamadas externas.

**Clases:**

```python
class CircuitBreakerState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: tuple = (Exception,),
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
    
    async def call(self, func: Callable) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
            else:
                raise CircuitBreakerOpenException(f"Circuit breaker {self.name} is OPEN")
        
        try:
            result = await func()
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
```

**Uso:**

```python
from carpeta_common.circuit_breaker import CircuitBreaker

# Crear circuit breaker
cb = CircuitBreaker(
    name="hub_api",
    failure_threshold=5,
    recovery_timeout=60
)

# Usar en llamadas externas
async def call_external_api():
    response = await httpx.get("https://external-api.com")
    return response

try:
    result = await cb.call(call_external_api)
except CircuitBreakerOpenException:
    # Handle circuit open (queue for retry, return cached, etc)
    pass
```

#### 2. redis_client.py

**Propósito:** Cliente Redis compartido con utilidades comunes.

**Funciones:**

```python
def get_redis_client() -> redis.asyncio.Redis:
    """Get configured Redis client."""
    settings = Settings()
    
    return redis.asyncio.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        ssl=settings.redis_ssl,
        db=settings.redis_db,
        socket_timeout=settings.redis_socket_timeout,
        decode_responses=True,
        health_check_interval=30
    )

async def get_json(client: Redis, key: str) -> Optional[dict]:
    """Get JSON value from Redis."""
    value = await client.get(key)
    if value:
        return json.loads(value)
    return None

async def set_json(client: Redis, key: str, value: dict, ttl: int = 3600) -> bool:
    """Set JSON value in Redis with TTL."""
    return await client.setex(key, ttl, json.dumps(value))

async def acquire_lock(
    client: Redis, 
    lock_key: str, 
    ttl: int = 120,
    token: str = None
) -> Optional[str]:
    """Acquire distributed lock with token."""
    if not token:
        token = str(uuid.uuid4())
    
    acquired = await client.set(lock_key, token, nx=True, ex=ttl)
    return token if acquired else None

async def release_lock(
    client: Redis, 
    lock_key: str, 
    token: str
) -> bool:
    """Release distributed lock (only if token matches)."""
    # Lua script for atomic check and delete
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    result = await client.eval(script, 1, lock_key, token)
    return bool(result)
```

**Uso:**

```python
from carpeta_common.redis_client import get_redis_client, acquire_lock, release_lock

redis = get_redis_client()

# Distributed lock
lock_key = f"lock:transfer:{citizen_id}"
token = await acquire_lock(redis, lock_key, ttl=120)

if token:
    try:
        # Critical section
        await perform_atomic_operation()
    finally:
        await release_lock(redis, lock_key, token)
```

#### 3. message_broker.py

**Propósito:** Cliente Azure Service Bus con retry y DLQ.

**Funciones:**

```python
async def publish_event(
    event_type: str,
    queue_name: str,
    payload: dict,
    max_retries: int = 3
) -> bool:
    """Publish event to Service Bus queue."""
    connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")
    
    async with ServiceBusClient.from_connection_string(connection_string) as client:
        sender = client.get_queue_sender(queue_name)
        
        message = ServiceBusMessage(
            body=json.dumps(payload),
            content_type="application/json",
            subject=event_type,
            message_id=str(uuid.uuid4())
        )
        
        for attempt in range(max_retries):
            try:
                async with sender:
                    await sender.send_messages(message)
                return True
            except ServiceBusError as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

async def consume_events(
    queue_name: str,
    handler: Callable,
    max_retries: int = 3
):
    """Consume events from Service Bus queue."""
    connection_string = os.getenv("SERVICEBUS_CONNECTION_STRING")
    
    async with ServiceBusClient.from_connection_string(connection_string) as client:
        receiver = client.get_queue_receiver(queue_name)
        
        async with receiver:
            async for message in receiver:
                try:
                    payload = json.loads(str(message))
                    await handler(payload)
                    await receiver.complete_message(message)
                except Exception as e:
                    # After max_retries, message goes to DLQ
                    await receiver.abandon_message(message)
```

**Uso:**

```python
from carpeta_common.message_broker import publish_event, consume_events

# Publish
await publish_event(
    event_type="citizen.registered",
    queue_name="citizen-registered",
    payload={
        "citizen_id": 1234567890,
        "timestamp": datetime.utcnow().isoformat()
    }
)

# Consume
async def handle_citizen_registered(payload: dict):
    citizen_id = payload["citizen_id"]
    # Process event
    await update_read_model(citizen_id)

await consume_events("citizen-registered", handle_citizen_registered)
```

#### 4. observability.py

**Propósito:** Configurar OpenTelemetry para traces, métricas y logs.

**Función Principal:**

```python
def setup_observability(
    app: FastAPI,
    service_name: str,
    service_version: str = "1.0.0"
) -> tuple[Tracer, Meter, ServiceMetrics]:
    """Setup OpenTelemetry instrumentation."""
    
    # Resource
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development")
    })
    
    # Tracer Provider
    tracer_provider = TracerProvider(resource=resource)
    
    # OTLP Exporter or Console
    if os.getenv("OTEL_USE_CONSOLE", "true") == "true":
        span_exporter = ConsoleSpanExporter()
    else:
        span_exporter = OTLPSpanExporter(
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        )
    
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)
    
    # Meter Provider
    meter_provider = MeterProvider(resource=resource)
    
    if os.getenv("OTEL_USE_CONSOLE", "true") == "true":
        metric_exporter = ConsoleMetricExporter()
    else:
        metric_exporter = OTLPMetricExporter(
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        )
    
    meter_provider.add_metric_reader(PeriodicExportingMetricReader(metric_exporter))
    metrics.set_meter_provider(meter_provider)
    
    # Auto-instrumentation
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
    
    # Get tracer and meter
    tracer = trace.get_tracer(service_name, service_version)
    meter = metrics.get_meter(service_name)
    
    # Custom metrics
    service_metrics = ServiceMetrics(meter)
    
    return tracer, meter, service_metrics
```

**Uso:**

```python
from carpeta_common.observability import setup_observability

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup observability
    tracer, meter, metrics = setup_observability(
        app=app,
        service_name="gateway",
        service_version="1.0.0"
    )
    app.state.tracer = tracer
    app.state.meter = meter
    app.state.metrics = metrics
    
    yield

app = FastAPI(lifespan=lifespan)
```

#### 5. middleware.py

**Propósito:** Middlewares comunes (CORS, logging).

**Funciones:**

```python
def setup_cors(app: FastAPI):
    """Setup CORS middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure per environment
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

def setup_logging(service_name: str):
    """Setup structured logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"/var/log/{service_name}.log")
        ]
    )
```

#### 6. saga.py

**Propósito:** Implementar patrón Saga para transacciones distribuidas.

**Clase Principal:**

```python
class Saga:
    """Saga pattern for distributed transactions."""
    
    def __init__(self, name: str):
        self.name = name
        self.steps: List[SagaStep] = []
    
    def add_step(
        self,
        action: Callable,
        compensation: Callable,
        name: str
    ):
        """Add step to saga."""
        self.steps.append(SagaStep(action, compensation, name))
    
    async def execute(self) -> bool:
        """Execute saga with compensation on failure."""
        executed_steps = []
        
        try:
            for step in self.steps:
                await step.action()
                executed_steps.append(step)
            return True
        except Exception as e:
            # Compensate in reverse order
            for step in reversed(executed_steps):
                try:
                    await step.compensation()
                except Exception as comp_error:
                    # Log compensation failure
                    pass
            return False
```

**Uso:**

```python
from carpeta_common.saga import Saga

# Transfer saga
saga = Saga(name="transfer_citizen")

saga.add_step(
    action=lambda: generate_sas_urls(),
    compensation=lambda: revoke_sas_urls(),
    name="generate_sas"
)

saga.add_step(
    action=lambda: transfer_data_to_destination(),
    compensation=lambda: delete_data_at_destination(),
    name="transfer_data"
)

saga.add_step(
    action=lambda: confirm_transfer(),
    compensation=lambda: revert_transfer(),
    name="confirm"
)

success = await saga.execute()
```

### Instalación del Paquete Común

**En cada servicio:**

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.13"
carpeta-common = {path = "../common", develop = true}
```

**Uso:**

```python
from carpeta_common.circuit_breaker import CircuitBreaker
from carpeta_common.redis_client import get_redis_client
from carpeta_common.message_broker import publish_event
from carpeta_common.observability import setup_observability
```

---

## 🔧 Microservicios

### 1. Gateway (Puerto 8000)

**Responsabilidad:** API Gateway con rate limiting y autenticación.

**Estructura:**

```
services/gateway/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── middleware.py        # Auth, rate limit
│   ├── rate_limiter.py      # Advanced rate limiter
│   ├── proxy.py             # HTTP proxy
│   └── routers/
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
└── pyproject.toml
```

**Endpoints:**

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |
| GET | `/ops/ratelimit/status` | Rate limiter status |
| * | `/api/{path}` | Proxy to backend services |

**Características Clave:**

1. **Advanced Rate Limiting:**
   - Por rol: ciudadano (60 rpm), operador (200 rpm), transfer (400 rpm)
   - Ventana deslizante en Redis
   - Sistema de penalización: ban tras 5 violaciones
   - Allowlist para IPs del hub

2. **Authentication:**
   - JWT validation (preparado para OIDC)
   - Role extraction
   - Public routes bypass

3. **Service Discovery:**
   - Service map configurable
   - Auto-detection: localhost (dev) vs K8s services (prod)

4. **Observability:**
   - OpenTelemetry traces
   - Métricas: requests, latency, rate limits

**Service Map:**

```python
service_map = {
    "citizens": "http://carpeta-ciudadana-citizen:8000",
    "ingestion": "http://carpeta-ciudadana-ingestion:8000",
    "metadata": "http://carpeta-ciudadana-metadata:8000",
    "transfer": "http://carpeta-ciudadana-transfer:8000",
    "mintic": "http://carpeta-ciudadana-mintic-client:8000",
    "signature": "http://carpeta-ciudadana-signature:8000",
}
```

### 2. Citizen (Puerto 8001)

**Responsabilidad:** Gestión de ciudadanos y afiliación.

**Endpoints:**

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/api/citizens/register` | Registrar ciudadano |
| GET | `/api/citizens/{id}` | Obtener ciudadano |
| GET | `/api/citizens/search` | Buscar ciudadanos |
| PUT | `/api/citizens/{id}` | Actualizar ciudadano |

**Base de Datos:**

```sql
CREATE TABLE citizens (
    id BIGINT PRIMARY KEY,  -- 10 digits
    name VARCHAR(100) NOT NULL,
    address VARCHAR(200) NOT NULL,
    email VARCHAR(100) NOT NULL,
    operator_id VARCHAR(50) NOT NULL,
    operator_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_citizens_email ON citizens(email);
CREATE INDEX idx_citizens_operator ON citizens(operator_id);
```

**Flujo de Registro:**

```
1. Validar datos (10 dígitos ID, email válido)
2. Guardar en DB local
3. Llamar a mintic_client → POST /register-citizen
4. mintic_client → Hub MinTIC (con sanitización PII)
5. Publicar evento: citizen.registered
6. Retornar éxito al frontend
```

### 3. Ingestion (Puerto 8002)

**Responsabilidad:** Upload/download de documentos con presigned URLs.

**Endpoints:**

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/api/documents/upload-url` | Generar presigned PUT URL |
| GET | `/api/documents/{id}/download-url` | Generar presigned GET URL |
| POST | `/api/documents/confirm-upload` | Confirmar upload exitoso |
| DELETE | `/api/documents/{id}` | Eliminar documento |

**Flujo de Upload:**

```
1. Frontend → POST /upload-url
   Body: {citizen_id, filename, content_type}

2. Ingestion:
   - Genera document_id (UUID)
   - Crea blob_name: citizens/{citizen_id}/{uuid}-{filename}
   - Genera presigned PUT URL (Azure SAS, 1 hora)
   - Guarda metadata en DB (status=pending)

3. Frontend → PUT directo a Azure Blob Storage

4. Frontend → POST /confirm-upload
   Body: {document_id, sha256_hash, size_bytes}

5. Ingestion:
   - Actualiza status=uploaded
   - Guarda hash y tamaño
   - Publica evento: document.uploaded
```

**Base de Datos:**

```sql
CREATE TABLE document_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id BIGINT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    blob_name VARCHAR(500) NOT NULL,
    content_type VARCHAR(100),
    size_bytes BIGINT,
    sha256_hash VARCHAR(64),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, uploaded, authenticated
    storage_provider VARCHAR(20) DEFAULT 'azure',
    uploaded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_documents_citizen ON document_metadata(citizen_id);
CREATE INDEX idx_documents_status ON document_metadata(status);
```

### 4. Metadata (Puerto 8003)

**Responsabilidad:** Búsqueda y gestión de metadata con OpenSearch.

**Endpoints:**

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/api/metadata/documents` | Listar documentos de ciudadano |
| GET | `/api/metadata/search` | Búsqueda full-text |
| DELETE | `/api/metadata/{id}` | Soft delete de documento |

**OpenSearch Index:**

```json
{
  "mappings": {
    "properties": {
      "documentId": {"type": "keyword"},
      "citizenId": {"type": "long"},
      "title": {"type": "text", "analyzer": "spanish"},
      "filename": {"type": "text"},
      "issuer": {"type": "keyword"},
      "hash": {"type": "keyword"},
      "tags": {"type": "keyword"},
      "hubAuthAt": {"type": "date"},
      "signatureStatus": {"type": "keyword"},
      "createdAt": {"type": "date"}
    }
  }
}
```

**Indexación:**

```python
async def index_document(doc: dict):
    """Index document in OpenSearch."""
    await opensearch_client.index(
        index="documents",
        id=doc["documentId"],
        body=doc
    )
    
    # Invalidate cache
    await redis_client.publish(
        f"invalidate:search:{doc['citizenId']}",
        "1"
    )
```

**Búsqueda con Cache:**

```python
async def search_documents(query: str, citizen_id: int):
    """Search documents with Redis cache."""
    # Check cache
    cache_key = f"search:{hash(query)}:{citizen_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Search in OpenSearch
    results = await opensearch_client.search(
        index="documents",
        body={
            "query": {
                "bool": {
                    "must": [
                        {"match": {"title": query}},
                        {"term": {"citizenId": citizen_id}}
                    ]
                }
            }
        }
    )
    
    # Cache results (120s TTL)
    await redis_client.setex(cache_key, 120, json.dumps(results))
    
    return results
```

### 5. Transfer (Puerto 8004)

**Responsabilidad:** Transferencias P2P seguras entre operadores.

**Endpoints:**

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/api/operators` | Listar operadores disponibles |
| POST | `/api/transferCitizen` | Iniciar transferencia (desde origen) |
| POST | `/api/transferCitizenConfirm` | Confirmar recepción (desde destino) |

**Estados de Transferencia:**

```
PENDING           → Esperando confirmación del destino
CONFIRMED         → Destino confirmó recepción exitosa
PENDING_UNREGISTER→ Esperando desregistro del hub
SUCCESS           → Completado (desregistrado del hub)
FAILED            → Transfer falló
```

**Flujo Seguro:**

```
Origen:
1. POST /api/transferCitizen al destino
2. Espera confirmación (status=PENDING)

Destino:
3. Recibe datos
4. Guarda en su DB
5. POST /api/transferCitizenConfirm al origen (req_status=1)

Origen:
6. Recibe confirmación (status=CONFIRMED)
7. Con lock distribuido Redis:
   - Borra datos locales (DB + blobs)
   - Status=PENDING_UNREGISTER
8. Llama hub: DELETE /apis/unregisterCitizen
9. Si éxito: status=SUCCESS
10. Si falla: reintenta en background (max 10 veces)
```

**Base de Datos:**

```sql
CREATE TABLE transfers (
    id SERIAL PRIMARY KEY,
    citizen_id BIGINT NOT NULL,
    direction VARCHAR(10) NOT NULL,  -- 'incoming' | 'outgoing'
    source_operator_id VARCHAR(50),
    destination_operator_id VARCHAR(50),
    idempotency_key VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL,
    
    initiated_at TIMESTAMP NOT NULL,
    confirmed_at TIMESTAMP,
    unregistered_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    retry_count INTEGER DEFAULT 0,
    error_message TEXT
);
```

### 6. MinTIC Client (Puerto 8005)

**Responsabilidad:** Cliente del hub MinTIC con sanitización PII.

**Endpoints (Facade):**

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/register-citizen` | Registrar en hub |
| DELETE | `/unregister-citizen` | Desregistrar del hub |
| PUT | `/authenticate-document` | Autenticar documento |
| GET | `/operators` | Listar operadores |

**Características:**

1. **Sanitización PII** (`app/sanitizer.py`):
   - Trunca strings (max 200 chars)
   - Enmascara emails: `***m.com`
   - Enmascara IDs: `***7890`
   - Minimiza datos enviados al hub público

2. **Hub Rate Limiting:**
   - 10 req/min por endpoint (configurable)
   - Si se excede → 202 + queue para retry

3. **Circuit Breaker:**
   - Por endpoint del hub
   - Si OPEN → 202 + queue para retry

4. **Idempotencia:**
   - Redis cache de respuestas terminales (2xx, 204, 501)
   - TTL: 15 minutos
   - Previene llamadas duplicadas

5. **Retry Inteligente:**
   - Solo para 5xx y timeouts
   - NO para 501 (parámetros inválidos) ni 4xx
   - Backoff exponencial + jitter

6. **OpenTelemetry:**
   - Spans: `hub.call` con atributos completos
   - Métricas: calls, latency, success_rate, status_codes

### 7. Signature (Puerto 8006)

**Responsabilidad:** Firma y autenticación de documentos.

**Endpoints:**

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/sign` | Firmar documento |
| POST | `/verify` | Verificar firma |

**Flujo de Autenticación:**

```
1. POST /sign
   Body: {citizen_id, document_id, document_title, file_url}

2. Signature service:
   - Calcula SHA-256 del documento
   - Genera SAS URL temporal (≤15 min)
   - Firma el hash (RSA mock o K8s secret)
   - Llama mintic_client → PUT /authenticate-document
     Body: {idCitizen, UrlDocument (SAS), documentTitle}
   
3. Hub MinTIC:
   - NO descarga el binario (solo valida metadata)
   - Retorna confirmación

4. Signature service:
   - Guarda hash, signedAt, signatureReceipt, hubResponse en DB
   - Publica evento: document.authenticated
```

**IMPORTANTE:**
- Hub NUNCA recibe binarios, solo URLs temporales
- SAS expira en ≤15 minutos
- Minimización de PII (solo citizen_id, URL, title)

### 8. Read Models (Puerto 8007)

**Responsabilidad:** CQRS read models optimizados.

**Características:**

1. Consume eventos de Service Bus
2. Proyecta tablas desnormalizadas
3. Cache en Redis
4. Idempotencia por `eventId`

**Endpoints:**

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/read/documents` | Documentos optimizados |
| GET | `/read/transfers` | Transferencias optimizadas |

**Proyecciones:**

```sql
-- Read model: documentos con ciudadano
CREATE TABLE read_citizen_documents (
    id SERIAL PRIMARY KEY,
    citizen_id BIGINT,
    citizen_name VARCHAR(100),
    document_id UUID,
    title VARCHAR(200),
    status VARCHAR(20),
    signed_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Optimizado para consultas frecuentes
CREATE INDEX idx_read_docs_citizen ON read_citizen_documents(citizen_id, created_at DESC);
```

### 9. Auth (Puerto 8008)

**Responsabilidad:** OIDC provider mínimo viable.

**Endpoints:**

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/token` | Obtener JWT |
| GET | `/.well-known/jwks.json` | JWKS público |
| GET | `/.well-known/openid-configuration` | OIDC discovery |

### 10. IAM (Puerto 8009)

**Responsabilidad:** ABAC (Attribute-Based Access Control).

**Endpoints:**

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/authorize` | Evaluar política de acceso |

**Políticas YAML:**

```yaml
policies:
  - name: download_own_documents
    subject:
      roles: [ciudadano]
    resource:
      type: document
    action: download
    context:
      - citizen_id == resource.owner_id
```

### 11. Notification (Puerto 8010)

**Responsabilidad:** Email y webhooks.

**Características:**

1. Consume eventos: `document.authenticated`, `transfer.confirmed`
2. Envía emails (SMTP o mock)
3. Envía webhooks (POST a URL configurable)
4. Plantillas Jinja2
5. Delivery log en DB

### 12. Sharing (Puerto 8011)

**Responsabilidad:** Compartición de documentos con shortlinks.

**Endpoints:**

| Método | Path | Descripción |
|--------|------|-------------|
| POST | `/api/share` | Crear shortlink |
| GET | `/s/{code}` | Acceder a documento compartido |

---

## 📊 Observabilidad

### Estructura

```
observability/
├── grafana-dashboards/
│   ├── api-latency.json           # Latencia de APIs
│   ├── transfers-saga.json        # Sagas de transferencia
│   ├── queue-health.json          # Salud de colas
│   ├── cache-efficiency.json      # Eficiencia de cache
│   └── hub-protection.json        # Rate limit y circuit breakers
├── alerts/
│   └── prometheus-alerts.yaml     # Alertas de Prometheus
└── azure-monitor/
    └── alert-rules.json           # Alertas de Azure Monitor
```

### Dashboards Grafana

#### 1. api-latency.json

**Propósito:** Monitorear latencia de APIs.

**Paneles:**

1. **Request Rate:**
   - Query: `rate(http_server_request_count[5m])`
   - Grouped by: service, endpoint

2. **Latency p95/p99:**
   - Query: `histogram_quantile(0.95, rate(http_server_request_duration_bucket[5m]))`
   - Alert: p95 > 2s

3. **Error Rate:**
   - Query: `rate(http_server_error_count[5m]) / rate(http_server_request_count[5m])`
   - Alert: > 1%

4. **Status Code Distribution:**
   - Query: `sum by (status_code) (rate(http_server_request_count[5m]))`
   - Stacked area chart

#### 2. transfers-saga.json

**Propósito:** Monitorear transferencias y sagas.

**Paneles:**

1. **Transfer Success Rate:**
   - Query: `rate(transfers_completed{status="success"}[5m])`

2. **Saga Compensation Rate:**
   - Query: `rate(saga_compensation_executed[5m])`

3. **Circuit Breaker States:**
   - Query: `circuit_breaker_state` (0=CLOSED, 1=OPEN)
   - Alert: if OPEN for > 5 min

4. **Transfer Duration:**
   - Query: `histogram_quantile(0.95, rate(transfer_duration_bucket[5m]))`

#### 3. queue-health.json

**Propósito:** Monitorear Service Bus queues.

**Paneles:**

1. **Messages Published vs Consumed:**
   - Query: `rate(queue_message_published[1m])` vs `rate(queue_message_consumed[1m])`

2. **Dead Letter Queue Length:**
   - Query: `queue_dlq_length`
   - Alert: > 10 messages

3. **Processing Failures:**
   - Query: `rate(queue_message_failed[5m])`

4. **Queue Latency:**
   - Query: `queue_processing_duration`

#### 4. cache-efficiency.json

**Propósito:** Monitorear Redis cache.

**Paneles:**

1. **Cache Hit Rate:**
   - Query: `rate(cache_hits[5m]) / (rate(cache_hits[5m]) + rate(cache_misses[5m]))`
   - Target: > 80%

2. **Redis Latency:**
   - Query: `histogram_quantile(0.95, rate(redis_command_duration_bucket[5m]))`

3. **Lock Contention:**
   - Query: `rate(redis_lock_wait[5m])`

4. **Evictions:**
   - Query: `rate(cache_evictions[5m])`

#### 5. hub-protection.json

**Propósito:** Monitorear rate limiting y circuit breakers del hub.

**Paneles:**

1. **Hub Rate Limit - Requests Per Minute:**
   - Query: `rate(hub_rate_limit_exceeded[1m])`

2. **Hub Call Success Rate:**
   - Query: `rate(hub_calls{success="true"}[5m]) / rate(hub_calls[5m])`

3. **Hub Latency p95:**
   - Query: `histogram_quantile(0.95, rate(hub_latency_bucket[5m]))`
   - Alert: > 2s

4. **Specific Status Codes (501, 204, 202):**
   - Query: `sum(increase(hub_status_codes{status_code="501"}[1h]))`

### Alertas Prometheus

**Archivo:** `alerts/prometheus-alerts.yaml`

```yaml
groups:
  - name: api_alerts
    interval: 1m
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_server_request_duration_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API latency p95 > 2s"
      
      - alert: HighErrorRate
        expr: rate(http_server_error_count[5m]) / rate(http_server_request_count[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate > 1%"
      
      - alert: CircuitBreakerOpen
        expr: hub_cb_open == 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker {{ $labels.endpoint }} is OPEN"
      
      - alert: DeadLetterQueueHigh
        expr: queue_dlq_length > 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "DLQ has {{ $value }} messages"
      
      - alert: CacheHitRateLow
        expr: rate(cache_hits[5m]) / (rate(cache_hits[5m]) + rate(cache_misses[5m])) < 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate < 80%"
```

### Métricas Personalizadas

**Exportadas por todos los servicios:**

```python
# HTTP Metrics
http_server_request_count
http_server_request_duration
http_server_error_count

# Cache Metrics
cache_hits
cache_misses
cache_evictions
redis_command_duration

# Queue Metrics
queue_message_published
queue_message_consumed
queue_message_failed
queue_dlq_length
queue_processing_duration

# External Calls
external_call_duration
external_call_errors

# Business Metrics
transfers_completed
saga_compensation_executed
documents_signed
citizens_registered

# Hub Protection
hub_calls
hub_latency
hub_rate_limit_exceeded
hub_rate_limit_remaining
hub_cb_open
hub_status_codes
```

---

## 🎨 Patrones y Estándares

### Estructura de Proyecto

Todos los servicios siguen la misma estructura:

```
service_name/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app with lifespan
│   ├── config.py         # Pydantic Settings
│   ├── database.py       # DB connection (si aplica)
│   ├── models.py         # Pydantic models
│   ├── db_models.py      # SQLAlchemy models (si aplica)
│   ├── routers/          # API routes
│   │   ├── __init__.py
│   │   └── service_routes.py
│   └── services/         # Business logic
│       ├── __init__.py
│       └── service_logic.py
├── tests/
│   ├── __init__.py
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── Dockerfile            # Multi-stage build
├── pyproject.toml        # Poetry dependencies
└── poetry.lock
```

### FastAPI App Template

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from carpeta_common.middleware import setup_cors, setup_logging
from carpeta_common.observability import setup_observability

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    logger.info("Starting service...")
    
    # Setup observability
    tracer, meter, metrics = setup_observability(
        app=app,
        service_name="service-name",
        service_version="1.0.0"
    )
    app.state.tracer = tracer
    app.state.meter = meter
    app.state.metrics = metrics
    
    yield
    
    logger.info("Shutting down service...")

def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = Settings()
    
    app = FastAPI(
        title="Service Name",
        description="Service description",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # Setup CORS
    setup_cors(app)
    
    # Setup logging
    setup_logging("service-name")
    
    # Include routers
    app.include_router(service_router, prefix="/api", tags=["service"])
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    return app

app = create_app()
```

### Configuración con Pydantic

```python
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Service settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
    
    # Environment
    environment: str = Field(default="development")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://...",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    
    # Service Bus
    servicebus_connection: str = Field(
        default="",
        env="SERVICEBUS_CONNECTION_STRING"
    )
```

### Logging Estructurado

```python
import logging

logger = logging.getLogger(__name__)

# Good practices
logger.info(f"Processing document {document_id} for citizen {citizen_id}")
logger.warning(f"Rate limit exceeded for IP {ip_address}")
logger.error(f"Failed to call hub: {error}", exc_info=True)

# With context
logger.info(
    "Transfer completed",
    extra={
        "citizen_id": citizen_id,
        "destination": destination_operator,
        "duration_ms": duration
    }
)
```

---

## 🧪 Testing

### Test Structure

```
tests/
├── unit/                  # Unit tests (fast, isolated)
│   ├── test_client_responses.py
│   ├── test_get_operators.py
│   └── test_idempotency.py
├── integration/          # Integration tests (DB, Redis, etc)
│   ├── test_database.py
│   └── test_message_broker.py
└── contract/            # Contract tests (API contracts)
    └── test_hub_contract.py
```

### Unit Test Example

```python
import pytest
from pytest_httpx import HTTPXMock
from app.client import MinTICClient

@pytest.mark.asyncio
async def test_client_handles_204_no_content(client: MinTICClient, httpx_mock: HTTPXMock):
    """Test that client handles 204 No Content responses."""
    httpx_mock.add_response(
        url="https://test-hub.example.com/apis/unregisterCitizen",
        method="DELETE",
        status_code=204,
        text=""
    )
    
    result = await client.unregister_citizen(request)
    
    assert result.ok is True
    assert result.status == 204
    assert "Sin contenido" in result.message
```

### Test Coverage

**Objetivo:** > 80% coverage en servicios críticos

```bash
# Run tests with coverage
cd services/mintic_client
pytest tests/unit/ -v --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

## 📚 Recursos Adicionales

### Documentación Relacionada

- **[INFRASTRUCTURE_DEPLOYMENT.md](./INFRASTRUCTURE_DEPLOYMENT.md)**: Infraestructura y deployment
- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Arquitectura técnica
- **[GUIA_COMPLETA.md](../GUIA_COMPLETA.md)**: Guía completa del proyecto

---

**Última actualización:** Octubre 2025  
**Mantenido por:** Universidad - Proyecto Carpeta Ciudadana


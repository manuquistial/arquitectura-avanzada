# 🔒 Machine-to-Machine (M2M) Authentication

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

Documentación del protocolo de autenticación M2M para comunicación entre servicios.

---

## 📋 Índice

1. [Descripción General](#descripción-general)
2. [Protocolo de Headers](#protocolo-de-headers)
3. [Generación de Signature](#generación-de-signature)
4. [Validación de Headers](#validación-de-headers)
5. [Replay Protection](#replay-protection)
6. [Integración](#integración)
7. [Configuración](#configuración)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Descripción General

El protocolo M2M autentica las llamadas entre microservicios usando **HMAC-SHA256** con protección contra replay attacks.

### Características

✅ **HMAC-SHA256**: Firma criptográfica de headers + body  
✅ **Replay Protection**: Nonce único + timestamp validation  
✅ **Redis Deduplication**: Nonces almacenados en Redis (TTL 10 minutos)  
✅ **Constant-time comparison**: Previene timing attacks  
✅ **Graceful degradation**: Funciona sin Redis (modo degradado)  

---

## 🔐 Protocolo de Headers

### Headers Requeridos

Todas las llamadas M2M deben incluir 4 headers:

| Header | Descripción | Ejemplo |
|--------|-------------|---------|
| `X-Service-Id` | Identificador del servicio caller | `gateway` |
| `X-Nonce` | Valor único aleatorio (32 bytes hex) | `a1b2c3d4e5f6...` (64 chars) |
| `X-Timestamp` | Unix timestamp (segundos) | `1697155200` |
| `X-Signature` | HMAC-SHA256 signature | `e4f5a6b7c8d9...` (64 chars) |

### Ejemplo de Request

```http
POST /api/citizens HTTP/1.1
Host: citizen-service:8000
Content-Type: application/json
X-Service-Id: gateway
X-Nonce: a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
X-Timestamp: 1697155200
X-Signature: e4f5a6b7c8d9012345678901234567890abcdef1234567890abcdef12345678

{"name": "Carlos Andres", "email": "carlos@example.com"}
```

---

## 🔧 Generación de Signature

### Algoritmo

```
message = service_id + "|" + nonce + "|" + timestamp + "|" + body
signature = HMAC-SHA256(secret_key, message)
```

### Paso a Paso

1. **Generar nonce**: 32 bytes random → hex (64 chars)
2. **Generar timestamp**: `int(time.time())`
3. **Build message**:
   ```python
   message = f"{service_id}|{nonce}|{timestamp}|{json.dumps(body)}".encode()
   ```
4. **Generate HMAC**:
   ```python
   signature = hmac.new(secret_key, message, hashlib.sha256).hexdigest()
   ```

### Ejemplo en Python

```python
from carpeta_common.m2m_auth import M2MAuthGenerator

# Initialize generator
generator = M2MAuthGenerator(
    service_id="gateway",
    secret_key="shared-secret-key-123"
)

# Generate headers
headers = generator.generate_headers(body=b'{"name": "Carlos"}')

# Headers ready to use
# {
#   "X-Service-Id": "gateway",
#   "X-Nonce": "a1b2c3...",
#   "X-Timestamp": "1697155200",
#   "X-Signature": "e4f5a6..."
# }
```

---

## ✅ Validación de Headers

### Proceso de Validación

1. **Check presence**: Todos los headers deben estar presentes
2. **Validate timestamp**: Debe estar dentro de ventana permitida (5 minutos)
3. **Validate nonce**: No debe haber sido usado antes (Redis check)
4. **Validate signature**: HMAC debe coincidir

### Ejemplo en Python

```python
from carpeta_common.m2m_auth import M2MAuthValidator

# Initialize validator
validator = M2MAuthValidator(
    secret_key="shared-secret-key-123",
    redis_client=redis_client,
    max_timestamp_age=300  # 5 minutes
)

# Validate headers
service_id = await validator.validate_headers(
    service_id=request.headers.get("X-Service-Id"),
    nonce=request.headers.get("X-Nonce"),
    timestamp=request.headers.get("X-Timestamp"),
    signature=request.headers.get("X-Signature"),
    body=await request.body()
)

# If we get here, authentication succeeded
print(f"Authenticated service: {service_id}")
```

### Como Dependency FastAPI

```python
from fastapi import Depends
from carpeta_common.m2m_auth import get_m2m_auth

@app.post("/internal/endpoint")
async def internal_endpoint(
    caller_service: str = Depends(get_m2m_auth)
):
    return {"caller": caller_service, "message": "Authenticated"}
```

---

## 🛡️ Replay Protection

### Mecanismo

1. **Nonce Deduplication**: Cada nonce solo puede usarse una vez
2. **Timestamp Window**: Request debe ser reciente (< 5 minutos)
3. **Redis Storage**: Nonces almacenados con TTL de 10 minutos

### Flujo

```
┌──────────────┐
│ Request      │
│ with nonce   │
└──────┬───────┘
       │
       ▼
┌──────────────────────────┐
│ Check nonce in Redis     │
│ Key: m2m:nonce:{service}:{nonce} │
└──────┬───────────────────┘
       │
       ├─ Exists? → ❌ Reject (replay attack)
       │
       └─ Not exists? → ✅ Continue
          │
          ▼
       ┌────────────────┐
       │ Store nonce    │
       │ TTL: 10 min    │
       └────────────────┘
```

### Ventana de Tiempo

```
Current time: 1697155200
Request timestamp: 1697155100 (100 seconds ago)

✅ Valid (< 300 seconds)

Request timestamp: 1697154800 (400 seconds ago)

❌ Invalid (> 300 seconds)
```

---

## 🔌 Integración

### En Servicio Caller (Gateway)

```python
from carpeta_common.http_client import M2MHttpClient

# Initialize client
client = M2MHttpClient(
    service_id="gateway",
    secret_key="shared-secret-key"
)

# Make authenticated request
response = await client.post(
    "http://citizen-service:8000/api/citizens",
    json={"name": "Carlos", "email": "carlos@example.com"}
)

# Headers are added automatically:
# X-Service-Id: gateway
# X-Nonce: <random>
# X-Timestamp: <current>
# X-Signature: <hmac>
```

### En Servicio Receiver (Citizen)

```python
from fastapi import Depends
from carpeta_common.m2m_auth import get_m2m_auth

@router.post("/api/citizens")
async def create_citizen(
    data: CitizenCreate,
    caller_service: str = Depends(get_m2m_auth)
):
    logger.info(f"Request from service: {caller_service}")
    
    # Process request
    # ...
    
    return {"id": 123, "name": data.name}
```

---

## ⚙️ Configuración

### Variables de Entorno

#### Servicio Caller
```env
SERVICE_ID=gateway
M2M_SECRET_KEY=your-shared-secret-key-here
```

#### Servicio Receiver
```env
M2M_SECRET_KEY=your-shared-secret-key-here
M2M_MAX_TIMESTAMP_AGE=300
REDIS_HOST=redis
REDIS_PORT=6379
```

### Kubernetes Secrets

```bash
# Generate secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Create secret
kubectl create secret generic m2m-auth \
  --from-literal=M2M_SECRET_KEY=$SECRET_KEY \
  --namespace carpeta-ciudadana-dev
```

### Helm Values

```yaml
global:
  m2mAuth:
    enabled: true
    secretName: m2m-auth
    maxTimestampAge: 300
    nonceTtl: 600

# Reference in deployment
envFrom:
- secretRef:
    name: m2m-auth
```

---

## 🧪 Testing

### Test Manual

```bash
# 1. Generate headers (Python)
python3 << 'EOF'
from carpeta_common.m2m_auth import M2MAuthGenerator
import json

gen = M2MAuthGenerator("test-service", "secret-key-123")
body = json.dumps({"test": "data"}).encode()
headers = gen.generate_headers(body)

print("Headers:")
for k, v in headers.items():
    print(f"{k}: {v}")
EOF

# 2. Make request with headers
curl -X POST http://citizen-service:8000/api/citizens \
  -H "Content-Type: application/json" \
  -H "X-Service-Id: test-service" \
  -H "X-Nonce: <generated-nonce>" \
  -H "X-Timestamp: <generated-timestamp>" \
  -H "X-Signature: <generated-signature>" \
  -d '{"test": "data"}'
```

### Test Unitarios

```python
import pytest
from carpeta_common.m2m_auth import M2MAuthGenerator, M2MAuthValidator

@pytest.mark.asyncio
async def test_valid_auth():
    secret_key = "test-secret"
    service_id = "test-service"
    
    # Generate
    gen = M2MAuthGenerator(service_id, secret_key)
    nonce = gen.generate_nonce()
    timestamp = gen.generate_timestamp()
    body = b'{"test": "data"}'
    signature = gen.generate_signature(nonce, timestamp, body)
    
    # Validate
    validator = M2MAuthValidator(secret_key)
    result = await validator.validate_headers(
        service_id, nonce, timestamp, signature, body
    )
    
    assert result == service_id

@pytest.mark.asyncio
async def test_replay_attack():
    """Test nonce reuse is rejected"""
    # ... (ver test_m2m_auth.py)
```

---

## 🔍 Troubleshooting

### Error: "Missing M2M headers"

**Causa**: Request sin headers M2M.

**Solución**:
- Usar `M2MHttpClient` en vez de `httpx` directo
- Verificar que headers se están generando

### Error: "Timestamp too old"

**Causa**: Reloj desincronizado entre servicios.

**Solución**:
- Sincronizar relojes (NTP)
- Aumentar `M2M_MAX_TIMESTAMP_AGE` temporalmente
- Verificar timezone de pods

### Error: "Nonce already used"

**Causa**: Nonce reutilizado (replay attack o retry).

**Solución**:
- **Si es retry legítimo**: Generar nuevo nonce
- **Si es replay attack**: Investigar origen del request

### Error: "Invalid signature"

**Causa**: Secret key diferente o body modificado.

**Solución**:
- Verificar que `M2M_SECRET_KEY` es idéntico en caller y receiver
- Verificar que body no está siendo modificado
- Verificar orden de campos en JSON (usar `sort_keys=True`)

### Warning: "Continuing without nonce validation"

**Causa**: Redis no disponible.

**Solución**:
- Verificar Redis está corriendo
- Verificar `REDIS_HOST` y `REDIS_PORT`
- **Nota**: Sistema funciona en modo degradado (sin replay protection)

---

## 📊 Métricas y Monitoring

### Prometheus Metrics (TODO)

```prometheus
# Total M2M requests validated
m2m_auth_requests_total{service_id="gateway", status="success"} 1234

# M2M validation errors
m2m_auth_errors_total{service_id="gateway", error_type="invalid_signature"} 5

# Replay attacks detected
m2m_auth_replay_attacks_total{service_id="gateway"} 2

# Nonce cache hits
m2m_nonce_cache_hits_total 123
```

### Alertas (TODO)

```yaml
- alert: M2MHighErrorRate
  expr: rate(m2m_auth_errors_total[5m]) > 0.1
  annotations:
    summary: "M2M auth error rate > 10%"

- alert: M2MReplayAttacks
  expr: increase(m2m_auth_replay_attacks_total[1h]) > 10
  annotations:
    summary: "Multiple replay attacks detected"
```

---

## 🔑 Seguridad

### Best Practices

✅ **Secret rotation**: Rotar `M2M_SECRET_KEY` periódicamente (90 días)  
✅ **Strong secret**: Mínimo 32 bytes random (usar `openssl rand -hex 32`)  
✅ **Redis HA**: Usar Redis Cluster para alta disponibilidad  
✅ **Monitoring**: Alertas para errores de validación  
✅ **Logging**: Log de replay attacks para investigación  

### Consideraciones

⚠️ **Secret compartido**: Todos los servicios usan el mismo secret  
⚠️ **Body inmutable**: No modificar body después de firmar  
⚠️ **Clock sync**: Servicios deben tener relojes sincronizados (NTP)  
⚠️ **Redis dependency**: Sin Redis, no hay replay protection  

---

## 📚 Ejemplos de Uso

### Ejemplo 1: Gateway → Citizen Service

```python
# Gateway service (caller)
from carpeta_common.http_client import M2MHttpClient

client = M2MHttpClient(
    service_id="gateway",
    secret_key=os.getenv("M2M_SECRET_KEY")
)

response = await client.post(
    "http://citizen-service:8000/api/citizens",
    json={"name": "Carlos", "email": "carlos@example.com"}
)

# Citizen service (receiver)
from fastapi import Depends
from carpeta_common.m2m_auth import get_m2m_auth

@router.post("/api/citizens")
async def create_citizen(
    data: CitizenCreate,
    caller: str = Depends(get_m2m_auth)
):
    logger.info(f"Request from: {caller}")  # "gateway"
    # Process...
```

### Ejemplo 2: Transfer Service → Notification Service

```python
# Transfer service (caller)
from carpeta_common.http_client import m2m_request

response = await m2m_request(
    "POST",
    "http://notification-service:8010/api/notifications",
    json={
        "type": "transfer_completed",
        "recipient": "user@example.com",
        "data": {"transfer_id": "123"}
    }
)

# Notification service (receiver)
@router.post("/api/notifications")
async def send_notification(
    data: NotificationData,
    caller: str = Depends(get_m2m_auth)
):
    logger.info(f"Notification request from: {caller}")
    # Send notification...
```

---

## 🔄 Flujo Completo

```
┌─────────────────────────────────────────────────┐
│ 1. Gateway Service (Caller)                    │
│    - Generate nonce (random 32 bytes)          │
│    - Generate timestamp (current Unix time)    │
│    - Generate signature (HMAC-SHA256)          │
│    - Add headers to request                    │
└─────────────┬───────────────────────────────────┘
              │
              │ HTTP Request with headers:
              │ X-Service-Id: gateway
              │ X-Nonce: a1b2c3...
              │ X-Timestamp: 1697155200
              │ X-Signature: e4f5a6...
              ▼
┌─────────────────────────────────────────────────┐
│ 2. Citizen Service (Receiver)                  │
│    ✅ Check headers present                     │
│    ✅ Validate timestamp (< 5 min old)          │
│    ✅ Check nonce in Redis (not used)           │
│    ✅ Validate signature (HMAC match)           │
│    ✅ Store nonce in Redis (TTL 10 min)         │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────┐
│ 3. Process Request                              │
│    - Authenticated as "gateway"                 │
│    - Process business logic                     │
│    - Return response                            │
└─────────────────────────────────────────────────┘
```

---

## 📦 Componentes

### carpeta_common/m2m_auth.py

**Clases**:
- `M2MAuthGenerator`: Genera headers
- `M2MAuthValidator`: Valida headers
- `M2MAuthMiddleware`: FastAPI dependency

**Funciones**:
- `get_m2m_auth()`: Dependency para FastAPI
- `create_m2m_generator()`: Helper para crear generator
- `create_m2m_validator()`: Helper para crear validator

### carpeta_common/http_client.py

**Clases**:
- `M2MHttpClient`: HTTP client con M2M automático

**Métodos**:
- `get(url)`: GET con M2M auth
- `post(url, json)`: POST con M2M auth
- `put(url, json)`: PUT con M2M auth
- `delete(url)`: DELETE con M2M auth

**Funciones**:
- `m2m_request(method, url, **kwargs)`: Single request helper

---

## 🎓 Best Practices

### 1. Usar M2MHttpClient para Internal Calls

```python
# ❌ NO HACER (sin autenticación)
async with httpx.AsyncClient() as client:
    response = await client.post("http://citizen-service/api/citizens", json=data)

# ✅ HACER (con M2M auth)
from carpeta_common.http_client import M2MHttpClient

client = M2MHttpClient("gateway", secret_key)
response = await client.post("http://citizen-service/api/citizens", json=data)
```

### 2. Proteger Endpoints Internos

```python
from carpeta_common.m2m_auth import get_m2m_auth

# ❌ Endpoint sin protección
@router.post("/internal/process")
async def process():
    # Cualquiera puede llamar
    pass

# ✅ Endpoint protegido con M2M
@router.post("/internal/process")
async def process(caller: str = Depends(get_m2m_auth)):
    # Solo servicios autenticados pueden llamar
    logger.info(f"Called by: {caller}")
    pass
```

### 3. Manejar Errores

```python
try:
    response = await client.post(url, json=data)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        logger.error("M2M authentication failed")
    raise
```

---

## 📋 Checklist de Implementación

- [x] M2MAuthGenerator implementado
- [x] M2MAuthValidator implementado
- [x] M2MHttpClient implementado
- [x] Redis nonce deduplication
- [x] FastAPI dependency (get_m2m_auth)
- [x] Tests unitarios
- [x] Documentación completa
- [ ] Integración en todos los servicios
- [ ] Prometheus metrics
- [ ] Alertas configuradas
- [ ] Load testing
- [ ] Secret rotation automation

---

## 🚀 Roadmap

### Futuras Mejoras

- [ ] **JWT-based M2M**: Usar JWT en vez de HMAC para más flexibilidad
- [ ] **Service mesh**: Considerar Istio/Linkerd para mTLS automático
- [ ] **Rate limiting**: Por service_id
- [ ] **Audit logging**: Log de todas las llamadas M2M
- [ ] **Prometheus metrics**: Métricas detalladas
- [ ] **Distributed tracing**: OpenTelemetry integration

---

## 📚 Referencias

- [HMAC: Keyed-Hashing for Message Authentication (RFC 2104)](https://datatracker.ietf.org/doc/html/rfc2104)
- [Python hmac module](https://docs.python.org/3/library/hmac.html)
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Redis SETEX](https://redis.io/commands/setex/)

---

**Generado**: 2025-10-13 01:30  
**Autor**: Manuel Jurado  
**Versión**: 1.0


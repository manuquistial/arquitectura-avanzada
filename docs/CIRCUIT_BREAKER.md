# ⚡ Circuit Breaker Pattern

**Protección contra Fallos en Cascada**

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Introducción](#introducción)
2. [¿Por qué Circuit Breaker?](#por-qué-circuit-breaker)
3. [Estados del Circuit Breaker](#estados-del-circuit-breaker)
4. [Implementación](#implementación)
5. [Configuración](#configuración)
6. [Ejemplos de Uso](#ejemplos-de-uso)
7. [Fallback Strategies](#fallback-strategies)
8. [Monitoring](#monitoring)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Introducción

El **Circuit Breaker** es un patrón de diseño que previene que una aplicación intente ejecutar operaciones que probablemente fallarán, permitiendo que el sistema se recupere de fallos sin desperdiciar recursos.

### Analogía

Como el circuit breaker eléctrico en tu casa:
- ⚡ **Sobrecarga** → Circuit breaker se abre
- 🔌 **Protege** el sistema de daños
- ⏰ **Espera** un tiempo
- 🔧 **Prueba** si el problema se resolvió
- ✅ **Cierra** el circuito si todo OK

---

## 🤔 ¿Por qué Circuit Breaker?

### Problema: Cascading Failures

```
❌ SIN CIRCUIT BREAKER:

User → Frontend → Gateway → MinTIC Hub (DOWN)
                     ↓
                  Timeout (30s)
                     ↓
                  Retry (30s)
                     ↓
                  Retry (30s)
                     ↓
              Total: 90s per request!
                     ↓
           Thread pool exhausted
                     ↓
         Gateway becomes unresponsive
                     ↓
        Entire system cascades down 🔥
```

```
✅ CON CIRCUIT BREAKER:

User → Frontend → Gateway → Circuit Breaker
                              ↓
                        Detects Hub DOWN
                              ↓
                        Circuit OPEN
                              ↓
                        Fail fast (0s)
                              ↓
                      Return fallback
                              ↓
             Gateway remains responsive ✅
```

### Beneficios

1. **Fail Fast**: No desperdiciar tiempo esperando servicios caídos
2. **Resource Protection**: Prevenir agotamiento de thread pools
3. **Graceful Degradation**: Usar fallbacks cuando servicio está caído
4. **Auto-Recovery**: Probar automáticamente si servicio se recuperó
5. **System Stability**: Prevenir cascading failures

---

## 🔄 Estados del Circuit Breaker

### 1. CLOSED (Normal Operation)

```
┌──────────────────────────────────┐
│    CLOSED (Circuit Breaker)      │
│                                  │
│  All requests → Service          │
│  Monitor failures                │
│                                  │
│  If failures >= threshold:       │
│      → OPEN                      │
└──────────────────────────────────┘
```

**Comportamiento**:
- ✅ Todas las requests pasan
- 📊 Cuenta failures
- ⚠️ Si threshold excedido → OPEN

### 2. OPEN (Circuit Tripped)

```
┌──────────────────────────────────┐
│     OPEN (Circuit Breaker)       │
│                                  │
│  All requests → BLOCKED 🚫       │
│  Return fallback immediately     │
│                                  │
│  After timeout:                  │
│      → HALF_OPEN                 │
└──────────────────────────────────┘
```

**Comportamiento**:
- 🚫 Requests bloqueadas (fail fast)
- 🔄 Usa fallback si disponible
- ⏰ Espera timeout (e.g., 60s)
- ➡️ Transición a HALF_OPEN

### 3. HALF_OPEN (Testing Recovery)

```
┌──────────────────────────────────┐
│  HALF_OPEN (Circuit Breaker)     │
│                                  │
│  Limited requests → Service      │
│  (e.g., 1-3 requests)            │
│                                  │
│  If successes >= threshold:      │
│      → CLOSED ✅                 │
│                                  │
│  If any failure:                 │
│      → OPEN ❌                   │
└──────────────────────────────────┘
```

**Comportamiento**:
- 🧪 Permite requests limitadas
- ✅ Si successes → CLOSED
- ❌ Si failure → OPEN again

---

## 🏗️ Implementación

### Basic Usage

```python
from carpeta_common.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

# Create circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=5,      # Open after 5 failures
    success_threshold=2,      # Close after 2 successes
    timeout=60.0,             # Try half-open after 60s
)

cb = CircuitBreaker("external_service", config)

# Use circuit breaker
try:
    result = cb.call(external_api_call)
except CircuitBreakerError:
    # Circuit is open, use fallback
    result = fallback_value
```

### With Fallback

```python
def fallback_response():
    return {"status": "unavailable", "cached": True}

cb = CircuitBreaker(
    "external_service",
    config,
    fallback=fallback_response
)

# Fallback used automatically when circuit is OPEN
result = cb.call(external_api_call)
# Returns fallback if circuit is OPEN
```

### As Decorator

```python
from carpeta_common.circuit_breaker import circuit_breaker

@circuit_breaker("mintic_hub")
def authenticate_with_hub(doc_id: str):
    response = requests.post(
        f"{HUB_URL}/authenticate",
        json={"document_id": doc_id}
    )
    return response.json()

# Call protected by circuit breaker
result = authenticate_with_hub("doc-123")
```

### With Context Manager

```python
cb = CircuitBreaker("external_service", config)

with cb.protect():
    # Protected code
    result = external_api_call()
```

---

## ⚙️ Configuración

### CircuitBreakerConfig

```python
from carpeta_common.circuit_breaker import CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,          # Failures before opening
    success_threshold=2,          # Successes to close from half-open
    timeout=60.0,                 # Seconds before trying half-open
    expected_exception=Exception, # Exception type to catch
    half_open_max_calls=1,        # Max calls in half-open state
    sliding_window_size=10,       # Rolling window for failure rate
    failure_rate_threshold=0.5    # Failure rate to open (50%)
)
```

### Configuration Guidelines

**Development**:
```python
CircuitBreakerConfig(
    failure_threshold=10,      # More lenient
    timeout=30.0,              # Faster recovery attempts
    failure_rate_threshold=0.7 # Higher tolerance
)
```

**Production**:
```python
CircuitBreakerConfig(
    failure_threshold=5,       # Stricter
    timeout=60.0,              # Slower recovery (avoid flapping)
    failure_rate_threshold=0.5 # Lower tolerance
)
```

**Critical Services** (MinTIC Hub):
```python
CircuitBreakerConfig(
    failure_threshold=3,       # Very strict
    success_threshold=3,       # Require more proofs of recovery
    timeout=120.0,             # Longer wait
    failure_rate_threshold=0.3 # 30% failure rate opens circuit
)
```

---

## 💡 Ejemplos de Uso

### Example 1: MinTIC Hub Client

```python
from carpeta_common.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
import httpx

# Configure circuit breaker for Hub
config = CircuitBreakerConfig(
    failure_threshold=5,
    timeout=60.0
)

def hub_fallback():
    return {"status": "pending", "message": "Hub temporarily unavailable"}

cb = CircuitBreaker("mintic_hub", config, fallback=hub_fallback)

# Protected Hub call
def authenticate_document(doc_id: str):
    def _call():
        response = httpx.post(
            "https://hub.mintic.gov.co/authenticate",
            json={"document_id": doc_id},
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    
    return cb.call(_call)

# Usage
try:
    result = authenticate_document("doc-123")
    if result.get("fallback"):
        # Circuit is open, Hub is down
        # Queue for later or notify user
        pass
except CircuitBreakerError:
    # Circuit is open, no fallback
    # Return error to user
    pass
```

### Example 2: Database Queries

```python
cb = CircuitBreaker("database", config)

@cb
def get_user(user_id: str):
    # Protected database query
    return db.query(User).filter_by(id=user_id).first()

# Usage
try:
    user = get_user("user-123")
except CircuitBreakerError:
    logger.error("Database circuit breaker is OPEN")
    # Use cache or return error
```

### Example 3: External API with Retry

```python
from tenacity import retry, stop_after_attempt, wait_exponential

cb = CircuitBreaker("external_api", config)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def call_api_with_retry():
    response = requests.get("https://api.example.com/data")
    response.raise_for_status()
    return response.json()

# Circuit breaker wraps retry logic
@cb
def call_api():
    return call_api_with_retry()
```

### Example 4: Graceful Degradation

```python
def get_user_recommendations_cached(user_id: str):
    """Fallback: Return cached recommendations."""
    cache_key = f"recommendations:{user_id}"
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)
    return []  # Empty list if no cache

cb = CircuitBreaker(
    "recommendations_service",
    config,
    fallback=get_user_recommendations_cached
)

@cb
def get_user_recommendations(user_id: str):
    """Get recommendations from service."""
    response = requests.get(f"{SERVICE_URL}/recommendations/{user_id}")
    response.raise_for_status()
    return response.json()

# Always returns something (real or cached)
recommendations = get_user_recommendations("user-123")
```

### Example 5: FastAPI Endpoint

```python
from fastapi import APIRouter, HTTPException
from carpeta_common.circuit_breaker import get_circuit_breaker, CircuitBreakerError

router = APIRouter()

# Get circuit breaker from global registry
mintic_cb = get_circuit_breaker("mintic_hub")

@router.post("/documents/{document_id}/sign")
async def sign_document(document_id: str):
    def _sign():
        # Call MinTIC Hub
        response = httpx.post(
            f"{HUB_URL}/sign",
            json={"document_id": document_id}
        )
        response.raise_for_status()
        return response.json()
    
    try:
        result = mintic_cb.call(_sign)
        return result
    
    except CircuitBreakerError:
        raise HTTPException(
            status_code=503,
            detail="Signature service temporarily unavailable"
        )

@router.get("/circuit-breaker/status")
async def circuit_status():
    """Endpoint to check circuit breaker status."""
    return mintic_cb.get_stats()
```

---

## 🔄 Fallback Strategies

### Strategy 1: Cached Data

```python
def get_cached_data(resource_id: str):
    cached = redis.get(f"cache:{resource_id}")
    if cached:
        return json.loads(cached)
    return None

cb = CircuitBreaker("api", config, fallback=get_cached_data)
```

**Use Case**: API calls for data that can be cached

### Strategy 2: Default Values

```python
def default_config():
    return {"theme": "light", "language": "es"}

cb = CircuitBreaker("config_service", config, fallback=default_config)
```

**Use Case**: Configuration services

### Strategy 3: Queued for Later

```python
def queue_for_later(*args, **kwargs):
    # Add to queue for retry when service recovers
    queue.add({"operation": "sign", "args": args, "kwargs": kwargs})
    return {"status": "queued"}

cb = CircuitBreaker("signing_service", config, fallback=queue_for_later)
```

**Use Case**: Operations that can be deferred

### Strategy 4: Degraded Response

```python
def degraded_search(query: str):
    # Return limited results from local index
    return {"results": [], "degraded": True, "message": "Limited results"}

cb = CircuitBreaker("search_service", config, fallback=degraded_search)
```

**Use Case**: Features that can work with reduced functionality

### Strategy 5: Error Response

```python
def error_response(*args, **kwargs):
    raise ServiceUnavailableError("Service temporarily down")

cb = CircuitBreaker("critical_service", config, fallback=error_response)
```

**Use Case**: Critical operations that can't degrade

---

## 📊 Monitoring

### Metrics to Track

```python
# Circuit breaker state (gauge)
circuit_breaker_state{name="mintic_hub"} 0  # CLOSED
circuit_breaker_state{name="mintic_hub"} 1  # OPEN
circuit_breaker_state{name="mintic_hub"} 2  # HALF_OPEN

# Failure count (counter)
circuit_breaker_failures_total{name="mintic_hub"}

# Success count (counter)
circuit_breaker_successes_total{name="mintic_hub"}

# State transitions (counter)
circuit_breaker_state_transitions_total{name="mintic_hub", from="closed", to="open"}

# Calls blocked (counter)
circuit_breaker_calls_blocked_total{name="mintic_hub"}

# Fallback used (counter)
circuit_breaker_fallback_used_total{name="mintic_hub"}
```

### Prometheus Queries

```promql
# Circuit breaker state
circuit_breaker_state{name="mintic_hub"}

# Rate of failures
rate(circuit_breaker_failures_total[5m])

# Percentage of time circuit is OPEN
avg_over_time((circuit_breaker_state{name="mintic_hub"} == 1)[1h])

# Fallback usage rate
rate(circuit_breaker_fallback_used_total[5m])
```

### Grafana Dashboard Panel

```json
{
  "title": "Circuit Breaker Status",
  "type": "stat",
  "targets": [
    {
      "expr": "circuit_breaker_state{name=\"mintic_hub\"}",
      "legendFormat": "MinTIC Hub"
    }
  ],
  "fieldConfig": {
    "overrides": [
      {
        "matcher": {"id": "byValue", "options": 0},
        "properties": [{"id": "color", "value": "green"}]
      },
      {
        "matcher": {"id": "byValue", "options": 1},
        "properties": [{"id": "color", "value": "red"}]
      },
      {
        "matcher": {"id": "byValue", "options": 2},
        "properties": [{"id": "color", "value": "yellow"}]
      }
    ],
    "mappings": [
      {"value": 0, "text": "CLOSED"},
      {"value": 1, "text": "OPEN"},
      {"value": 2, "text": "HALF_OPEN"}
    ]
  }
}
```

### FastAPI Metrics Endpoint

```python
from carpeta_common.circuit_breaker import get_all_circuit_breaker_stats

@app.get("/metrics/circuit-breakers")
async def circuit_breaker_metrics():
    """Expose circuit breaker stats for monitoring."""
    return get_all_circuit_breaker_stats()

# Response:
# {
#   "mintic_hub": {
#     "name": "mintic_hub",
#     "state": "closed",
#     "failure_count": 0,
#     "success_count": 15,
#     "failure_rate": 0.0
#   }
# }
```

---

## 📈 Alerting

### Prometheus Alerts

```yaml
- alert: CircuitBreakerOpen
  expr: circuit_breaker_state == 1
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Circuit breaker {{ $labels.name }} is OPEN"
    description: "Circuit has been OPEN for 5 minutes"
    action: "Check external service health"

- alert: CircuitBreakerHighFailureRate
  expr: |
    rate(circuit_breaker_failures_total[5m])
    /
    rate(circuit_breaker_calls_total[5m])
    > 0.3
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High failure rate for {{ $labels.name }}"
    description: "Failure rate: {{ $value | humanizePercentage }}"

- alert: CircuitBreakerFlapping
  expr: |
    rate(circuit_breaker_state_transitions_total[10m]) > 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Circuit breaker {{ $labels.name }} is flapping"
    description: "Multiple state transitions detected"
    action: "Review thresholds or external service stability"
```

---

## ✅ Best Practices

### DO ✅

1. **Use for external services**
   ```python
   # Good: External API calls
   cb = CircuitBreaker("external_api")
   ```

2. **Set appropriate timeouts**
   ```python
   # Good: Timeout > service recovery time
   config = CircuitBreakerConfig(timeout=60.0)
   ```

3. **Provide fallbacks when possible**
   ```python
   # Good: Graceful degradation
   cb = CircuitBreaker("service", config, fallback=cached_response)
   ```

4. **Monitor circuit breaker state**
   ```python
   # Good: Expose metrics
   @app.get("/metrics/circuit-breakers")
   def cb_stats():
       return get_all_circuit_breaker_stats()
   ```

5. **Use specific exception types**
   ```python
   # Good: Catch specific errors
   config = CircuitBreakerConfig(
       expected_exception=httpx.HTTPError
   )
   ```

### DON'T ❌

1. **Don't use for internal services**
   ```python
   # Bad: Internal DB calls (use retry instead)
   cb = CircuitBreaker("local_database")
   ```

2. **Don't set threshold too low**
   ```python
   # Bad: Opens too easily
   config = CircuitBreakerConfig(failure_threshold=1)
   ```

3. **Don't set timeout too short**
   ```python
   # Bad: Flapping (open → half_open → open → ...)
   config = CircuitBreakerConfig(timeout=5.0)
   ```

4. **Don't ignore circuit state**
   ```python
   # Bad: Bypass circuit breaker
   if cb.is_open:
       result = direct_call()  # Don't do this!
   ```

5. **Don't use for non-idempotent operations without care**
   ```python
   # Bad: Payment processing with circuit breaker
   # (might fail after processing)
   @cb
   def process_payment():
       return charge_credit_card()
   ```

---

## 🔍 Troubleshooting

### Problem: Circuit constantly OPEN

**Symptoms**: Circuit always OPEN, never recovers

**Causes**:
1. External service is actually down
2. Timeout too short (doesn't recover in time)
3. Threshold too strict

**Solutions**:
```python
# Check external service
curl https://external-service.com/health

# Increase timeout
config.timeout = 120.0  # 2 minutes

# Increase failure threshold
config.failure_threshold = 10

# Check logs
logger.info(cb.get_stats())
```

### Problem: Circuit flapping (OPEN ↔ HALF_OPEN)

**Symptoms**: Circuit opens and closes repeatedly

**Causes**:
1. Service is unstable
2. Timeout too short
3. Success threshold too low

**Solutions**:
```python
# Increase timeout
config.timeout = 120.0

# Require more successes to close
config.success_threshold = 5

# Increase half-open calls
config.half_open_max_calls = 3
```

### Problem: Circuit never opens

**Symptoms**: Service failing but circuit stays CLOSED

**Causes**:
1. Wrong exception type
2. Threshold too high
3. Successes resetting counter

**Solutions**:
```python
# Check exception type
config.expected_exception = httpx.HTTPError  # Be specific

# Lower threshold
config.failure_threshold = 3

# Check failure rate
config.failure_rate_threshold = 0.3  # 30%
```

### Problem: Fallback not working

**Symptoms**: CircuitBreakerError raised despite fallback

**Causes**:
1. Fallback not set
2. Fallback raises exception

**Solutions**:
```python
# Set fallback
def safe_fallback():
    try:
        return get_cached_data()
    except:
        return default_value

cb = CircuitBreaker("service", config, fallback=safe_fallback)
```

---

## 📊 Integration with Existing Code

### MinTIC Client Update

```python
# services/mintic_client/app/client.py

from carpeta_common.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

class MinTICHubClient:
    def __init__(self, hub_url: str):
        self.hub_url = hub_url
        
        # Circuit breaker for Hub calls
        config = CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=2,
            timeout=60.0
        )
        
        self.circuit_breaker = CircuitBreaker(
            "mintic_hub",
            config,
            fallback=self._hub_unavailable_fallback
        )
    
    def _hub_unavailable_fallback(self, *args, **kwargs):
        return {
            "status": "pending",
            "message": "MinTIC Hub temporarily unavailable",
            "retry_after": 60
        }
    
    def authenticate(self, document_id: str):
        def _call():
            response = httpx.post(
                f"{self.hub_url}/authenticate",
                json={"document_id": document_id}
            )
            response.raise_for_status()
            return response.json()
        
        return self.circuit_breaker.call(_call)
```

---

## 🎯 Testing Circuit Breaker

### Manual Testing

```python
# Force circuit open
cb.force_open()
assert cb.is_open

# Try call (should raise CircuitBreakerError)
try:
    cb.call(my_function)
except CircuitBreakerError:
    print("Circuit is open as expected")

# Reset
cb.reset()
assert cb.is_closed
```

### Load Testing

```bash
# k6 script to test circuit breaker
import http from 'k6/http';
import { check } from 'k6';

export default function() {
  // Make requests until circuit opens
  const res = http.get('http://api/protected-endpoint');
  
  check(res, {
    'status is 200 or 503': (r) => r.status === 200 || r.status === 503,
  });
}
```

---

## 📚 Referencias

- [Martin Fowler - Circuit Breaker](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Microsoft - Circuit Breaker Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker)
- [Release It! by Michael Nygard](https://pragprog.com/titles/mnee2/release-it-second-edition/)
- [Resilience4j Documentation](https://resilience4j.readme.io/docs/circuitbreaker)

---

## ✅ Resumen

**Circuit Breaker Features**:
- ✅ 3 estados (CLOSED, OPEN, HALF_OPEN)
- ✅ Failure threshold
- ✅ Success threshold
- ✅ Timeout auto-recovery
- ✅ Fallback support
- ✅ Sliding window
- ✅ Failure rate detection
- ✅ Thread-safe
- ✅ Statistics/metrics
- ✅ Manual control (reset, force_open)
- ✅ Global registry
- ✅ Decorator support
- ✅ Context manager

**Use Cases**:
- MinTIC Hub calls
- External APIs
- Database queries (if DB can be down)
- Third-party services
- Microservice calls

**Estado**: 🟢 Production-ready

---

**Generado**: 2025-10-13 06:30  
**Autor**: Manuel Jurado  
**Versión**: 1.0


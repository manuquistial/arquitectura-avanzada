# 🔒 Redis Distributed Locks

**Distributed Locking for Race Condition Prevention**

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Introducción](#introducción)
2. [¿Por qué Distributed Locks?](#por-qué-distributed-locks)
3. [Implementación](#implementación)
4. [API Reference](#api-reference)
5. [Ejemplos de Uso](#ejemplos-de-uso)
6. [Patterns](#patterns)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Introducción

Los **Distributed Locks** son mecanismos de sincronización que permiten coordinar el acceso a recursos compartidos en sistemas distribuidos, previniendo **race conditions** y garantizando **exclusión mutua**.

### Problema que Resuelven

En un sistema distribuido con múltiples instancias de servicios:

```
❌ SIN LOCKS:
Instance 1: Read document owner (user A)
Instance 2: Read document owner (user A)
Instance 1: Transfer to user B
Instance 2: Transfer to user C  ⚠️ RACE CONDITION!
Result: Inconsistent state
```

```
✅ CON LOCKS:
Instance 1: Acquire lock on document
Instance 1: Transfer to user B
Instance 1: Release lock
Instance 2: Acquire lock on document
Instance 2: See updated owner (user B)
Instance 2: Reject transfer (not owner)
Result: Consistent state
```

---

## 🤔 ¿Por qué Distributed Locks?

### Casos de Uso en Carpeta Ciudadana

1. **Document Transfers**
   - Prevenir múltiples transferencias simultáneas
   - Garantizar atomicidad en cambio de propietario
   
2. **Document Updates**
   - Evitar conflictos en actualizaciones concurrentes
   - Serializar operaciones críticas

3. **Nonce Generation**
   - Garantizar unicidad en tokens de autenticación
   - Prevenir replay attacks

4. **Batch Processing**
   - Coordinar workers de KEDA
   - Evitar procesamiento duplicado

5. **User Profile Updates**
   - Serializar cambios de configuración
   - Prevenir overwrites

---

## 🏗️ Implementación

### RedisLock Class

```python
from carpeta_common.redis_lock import RedisLock

lock = RedisLock(
    redis_client=redis,
    resource="my_resource",
    ttl=30,  # Lock expires after 30s
    blocking=False,  # Don't wait if locked
    blocking_timeout=None,  # Max wait time
    retry_interval=0.1  # Time between retries
)
```

### Características

✅ **Atomic Acquisition**: `SET NX EX` (set if not exists with expiration)  
✅ **Safe Release**: Lua script verifies ownership before deleting  
✅ **TTL**: Auto-expiration prevents deadlocks  
✅ **Unique Token**: UUID per lock instance for ownership verification  
✅ **Blocking/Non-blocking**: Configurable wait behavior  
✅ **Context Manager**: Auto-release on exit  
✅ **Lock Extension**: Extend TTL for long operations  
✅ **Async Support**: `AsyncRedisLock` for asyncio  

---

## 📚 API Reference

### RedisLock

#### Constructor

```python
RedisLock(
    redis_client: Redis,
    resource: str,
    ttl: int = 30,
    blocking: bool = False,
    blocking_timeout: Optional[float] = None,
    retry_interval: float = 0.1
)
```

**Parámetros**:
- `redis_client`: Redis client instance
- `resource`: Name of resource to lock
- `ttl`: Lock TTL in seconds (default: 30s)
- `blocking`: If True, wait for lock acquisition
- `blocking_timeout`: Max time to wait (None = forever)
- `retry_interval`: Time between acquisition attempts

#### Methods

##### acquire()

```python
def acquire(
    blocking: Optional[bool] = None,
    timeout: Optional[float] = None
) -> bool
```

Acquire the lock.

**Returns**: `True` if acquired, `False` otherwise

**Raises**: `LockAcquisitionError` if Redis error

##### release()

```python
def release() -> bool
```

Release the lock (only if owned).

**Returns**: `True` if released, `False` if not owned

**Raises**: `LockReleaseError` if Redis error

##### extend()

```python
def extend(additional_time: Optional[int] = None) -> bool
```

Extend lock TTL.

**Parameters**: `additional_time` - Seconds to add (default: original TTL)

**Returns**: `True` if extended, `False` otherwise

##### is_locked()

```python
def is_locked() -> bool
```

Check if this instance holds the lock.

---

### LockManager

High-level convenience methods for common patterns.

```python
from carpeta_common.redis_lock import LockManager

manager = LockManager(redis_client)
```

#### Methods

##### lock_document()

```python
@contextmanager
def lock_document(document_id: str, ttl: int = 30) -> Generator[RedisLock, None, None]
```

Lock a document for exclusive access.

##### lock_transfer()

```python
@contextmanager
def lock_transfer(transfer_id: str, ttl: int = 60) -> Generator[RedisLock, None, None]
```

Lock a transfer operation.

##### lock_user_operation()

```python
@contextmanager
def lock_user_operation(
    user_id: str,
    operation: str,
    ttl: int = 10
) -> Generator[RedisLock, None, None]
```

Lock a user operation.

##### try_lock()

```python
def try_lock(resource: str, ttl: int = 30) -> Optional[RedisLock]
```

Try to acquire lock without blocking.

---

## 💡 Ejemplos de Uso

### Example 1: Basic Usage

```python
from carpeta_common.redis_lock import RedisLock
from redis import Redis

redis_client = Redis(host='localhost', port=6379)
lock = RedisLock(redis_client, "my_resource", ttl=30)

if lock.acquire():
    try:
        # Critical section
        print("Lock acquired, doing work...")
        time.sleep(2)
    finally:
        lock.release()
        print("Lock released")
else:
    print("Could not acquire lock")
```

### Example 2: Context Manager

```python
from carpeta_common.redis_lock import RedisLock

try:
    with RedisLock(redis_client, "my_resource", ttl=30):
        # Critical section
        # Lock is automatically released on exit
        print("Doing protected work...")
except LockAcquisitionError:
    print("Could not acquire lock")
```

### Example 3: Blocking with Timeout

```python
lock = RedisLock(
    redis_client,
    "my_resource",
    ttl=30,
    blocking=True,
    blocking_timeout=10  # Wait max 10 seconds
)

if lock.acquire():
    try:
        print("Lock acquired after waiting")
        # Do work
    finally:
        lock.release()
else:
    print("Timeout: could not acquire lock within 10 seconds")
```

### Example 4: Lock Extension

```python
with RedisLock(redis_client, "long_operation", ttl=10) as lock:
    print("Starting long operation...")
    
    # Do some work
    time.sleep(8)
    
    # Extend lock for another 10 seconds
    lock.extend(10)
    
    # Continue work
    time.sleep(8)
    
    print("Operation complete")
```

### Example 5: LockManager

```python
from carpeta_common.redis_lock import LockManager

manager = LockManager(redis_client)

# Lock document
with manager.lock_document("doc-123", ttl=30):
    print("Updating document...")
    # Update document

# Lock transfer
with manager.lock_transfer("transfer-456", ttl=60):
    print("Processing transfer...")
    # Process transfer

# Lock user operation
with manager.lock_user_operation("user-789", "update_profile", ttl=10):
    print("Updating user profile...")
    # Update profile
```

### Example 6: Non-blocking Try Lock

```python
from carpeta_common.redis_lock import LockManager

manager = LockManager(redis_client)

lock = manager.try_lock("my_resource", ttl=30)
if lock:
    try:
        print("Lock acquired")
        # Do work
    finally:
        lock.release()
else:
    print("Resource is busy, skipping")
```

### Example 7: Async Usage

```python
import asyncio
from carpeta_common.redis_lock import AsyncRedisLock
import redis.asyncio as aioredis

async def process_document(document_id: str):
    redis = await aioredis.from_url("redis://localhost")
    
    async with AsyncRedisLock(redis, f"document:{document_id}", ttl=30):
        print(f"Processing document {document_id}")
        await asyncio.sleep(2)
        print("Done")

asyncio.run(process_document("doc-123"))
```

### Example 8: FastAPI Integration

```python
from fastapi import APIRouter, HTTPException, Depends
from carpeta_common.redis_lock import LockManager, LockAcquisitionError
from app.dependencies import get_redis_client

router = APIRouter()

@router.post("/documents/{document_id}/transfer")
async def transfer_document(
    document_id: str,
    to_user: str,
    redis_client = Depends(get_redis_client)
):
    manager = LockManager(redis_client)
    
    try:
        with manager.lock_document(document_id, ttl=60):
            # Perform transfer
            # ...
            return {"status": "transferred"}
    
    except LockAcquisitionError:
        raise HTTPException(
            status_code=409,
            detail="Document is being transferred by another request"
        )
```

---

## 🎨 Patterns

### Pattern 1: Idempotent Operations

```python
def process_event_idempotent(event_id: str):
    """Process event only once using lock."""
    lock = RedisLock(redis_client, f"event:{event_id}", ttl=300)
    
    if not lock.acquire(blocking=False):
        # Already processed or being processed
        logger.info(f"Event {event_id} already processed")
        return
    
    try:
        # Process event
        logger.info(f"Processing event {event_id}")
        # ...
    finally:
        lock.release()
```

### Pattern 2: Leader Election

```python
def try_become_leader(node_id: str):
    """Try to become leader using lock."""
    lock = RedisLock(redis_client, "cluster_leader", ttl=60)
    
    if lock.acquire(blocking=False):
        logger.info(f"Node {node_id} is now leader")
        
        # Periodically extend lock while leader
        while should_be_leader:
            time.sleep(30)
            if not lock.extend(60):
                logger.warning("Lost leadership")
                break
        
        lock.release()
    else:
        logger.info(f"Node {node_id} is follower")
```

### Pattern 3: Rate Limiting

```python
def rate_limit_user_action(user_id: str, action: str):
    """Allow action only once per time window."""
    lock = RedisLock(
        redis_client,
        f"ratelimit:{user_id}:{action}",
        ttl=60  # 1 action per minute
    )
    
    if not lock.acquire(blocking=False):
        raise Exception("Rate limit exceeded")
    
    # Lock will auto-expire, no need to release
    # (allows action again after TTL)
```

### Pattern 4: Optimistic Locking

```python
def update_with_optimistic_lock(document_id: str, data: dict):
    """Try fast update, fallback to lock on conflict."""
    try:
        # Try optimistic update (no lock)
        result = update_document(document_id, data)
        return result
    
    except ConflictError:
        # Conflict detected, retry with lock
        with RedisLock(redis_client, f"document:{document_id}", ttl=30):
            # Retry with exclusive lock
            result = update_document(document_id, data)
            return result
```

---

## ✅ Best Practices

### DO ✅

1. **Always set appropriate TTL**
   ```python
   # Good: TTL > operation time
   lock = RedisLock(redis, "resource", ttl=60)
   ```

2. **Use context managers**
   ```python
   # Good: Auto-release on exit
   with RedisLock(redis, "resource"):
       # work
   ```

3. **Handle lock acquisition failure**
   ```python
   # Good: Explicit error handling
   try:
       with RedisLock(redis, "resource"):
           # work
   except LockAcquisitionError:
       # handle error
   ```

4. **Use specific resource names**
   ```python
   # Good: Clear, specific
   lock = RedisLock(redis, f"document:{document_id}")
   ```

5. **Set timeouts for blocking locks**
   ```python
   # Good: Prevent infinite wait
   lock = RedisLock(redis, "resource", blocking=True, blocking_timeout=30)
   ```

### DON'T ❌

1. **Don't use locks for everything**
   ```python
   # Bad: Unnecessary lock for read-only operation
   with RedisLock(redis, f"user:{user_id}"):
       user = get_user(user_id)  # Just reading!
   ```

2. **Don't set TTL too short**
   ```python
   # Bad: TTL < operation time = lock expires mid-operation
   lock = RedisLock(redis, "resource", ttl=1)
   time.sleep(2)  # Lock expired!
   ```

3. **Don't forget to release (without context manager)**
   ```python
   # Bad: Lock never released on exception
   lock.acquire()
   do_work()  # May raise exception
   lock.release()  # Never called!
   ```

4. **Don't reuse lock instances**
   ```python
   # Bad: Reusing lock for different resources
   lock = RedisLock(redis, "resource1")
   with lock:
       # work on resource1
   lock.resource = "resource2"  # Don't do this!
   ```

5. **Don't hold locks during I/O**
   ```python
   # Bad: Holding lock during slow external API call
   with RedisLock(redis, "resource"):
       result = requests.get("https://slow-api.com")  # 30s timeout!
   ```

---

## 🔍 Troubleshooting

### Problem: Lock acquisition always fails

**Symptoms**: `acquire()` returns `False`

**Causes**:
1. Another process holds the lock
2. Lock key exists but is stuck (Redis crash)
3. TTL too long, lock not expiring

**Solutions**:
```python
# Check if key exists
redis_client.get("lock:my_resource")

# Check TTL
redis_client.ttl("lock:my_resource")

# Force delete (if stuck)
redis_client.delete("lock:my_resource")

# Use shorter TTL
lock = RedisLock(redis, "resource", ttl=10)
```

### Problem: Deadlock (lock never released)

**Symptoms**: Lock held forever, operations stuck

**Causes**:
1. Process crashed before release
2. Exception raised, release not called
3. Infinite loop inside lock

**Solutions**:
```python
# Always use context manager
with RedisLock(redis, "resource"):
    # work

# Or always use try/finally
lock.acquire()
try:
    # work
finally:
    lock.release()

# Set appropriate TTL (auto-expires)
lock = RedisLock(redis, "resource", ttl=30)
```

### Problem: Lock expires mid-operation

**Symptoms**: Operation completes but lock lost, multiple processes enter

**Causes**:
1. TTL too short
2. Operation takes longer than expected
3. No lock extension for long operations

**Solutions**:
```python
# Increase TTL
lock = RedisLock(redis, "resource", ttl=120)

# Extend lock for long operations
with RedisLock(redis, "resource", ttl=30) as lock:
    # work...
    lock.extend(30)  # Add 30 more seconds
    # more work...
```

### Problem: High contention (many processes waiting)

**Symptoms**: Slow performance, timeouts

**Causes**:
1. Lock held too long
2. Too many concurrent requests
3. Inefficient critical section

**Solutions**:
```python
# Reduce lock hold time
with RedisLock(redis, "resource"):
    # Only critical operations here
    critical_work()
# Non-critical work outside lock
non_critical_work()

# Use non-blocking mode
lock = manager.try_lock("resource")
if not lock:
    return "Resource busy, try again later"

# Shard locks (if possible)
lock = RedisLock(redis, f"resource:{shard_id}")
```

---

## 📊 Monitoring

### Metrics to Track

```python
# Lock acquisition time
lock_acquisition_time = histogram()

start = time.time()
with RedisLock(redis, "resource"):
    lock_acquisition_time.observe(time.time() - start)
    # work

# Lock hold time
lock_hold_time = histogram()

with RedisLock(redis, "resource"):
    start = time.time()
    # work
    lock_hold_time.observe(time.time() - start)

# Lock contention (acquisition failures)
lock_failures = counter()

if not lock.acquire(blocking=False):
    lock_failures.inc()
```

### Prometheus Queries

```promql
# Lock acquisition rate
rate(redis_lock_acquisitions_total[5m])

# Lock acquisition failures (contention)
rate(redis_lock_acquisition_failures_total[5m])

# Average lock hold time
rate(redis_lock_hold_seconds_sum[5m]) / rate(redis_lock_hold_seconds_count[5m])

# P95 lock acquisition time
histogram_quantile(0.95, rate(redis_lock_acquisition_seconds_bucket[5m]))
```

---

## 🔗 References

- [Redis SET command](https://redis.io/commands/set/)
- [Redlock algorithm](https://redis.io/docs/manual/patterns/distributed-locks/)
- [Martin Kleppmann - How to do distributed locking](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html)

---

## ✅ Resumen

**RedisLock Features**:
- ✅ Atomic acquisition (SET NX EX)
- ✅ Safe release (Lua script)
- ✅ TTL (auto-expiration)
- ✅ Unique tokens (ownership)
- ✅ Blocking/non-blocking
- ✅ Context manager
- ✅ Lock extension
- ✅ Async support

**Use Cases**:
- Document transfers
- Document updates
- Nonce generation
- Batch processing
- User operations

**Estado**: 🟢 Production-ready

---

**Generado**: 2025-10-13 06:00  
**Autor**: Manuel Jurado  
**Versión**: 1.0


# 🚦 Rate Limiting Avanzado

**Protección contra Abuso y DDoS**

**Fecha**: 2025-10-13  
**Versión**: 2.0  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Introducción](#introducción)
2. [Arquitectura](#arquitectura)
3. [Rate Limit Tiers](#rate-limit-tiers)
4. [Sliding Window Algorithm](#sliding-window-algorithm)
5. [Per-User Rate Limiting](#per-user-rate-limiting)
6. [Ban System](#ban-system)
7. [Endpoints](#endpoints)
8. [Configuración](#configuración)
9. [Monitoring](#monitoring)
10. [Best Practices](#best-practices)

---

## 🎯 Introducción

El **Rate Limiting** protege la API contra:
- 🛡️ Ataques DDoS
- 🤖 Bots abusivos
- 🐛 Infinite loops en clientes
- 💸 Uso excesivo de recursos

### Features

✅ **Per-User Rate Limiting**: Límites por usuario (no solo por IP)  
✅ **Tiered Limits**: 4 tiers (Free, Basic, Premium, Enterprise)  
✅ **Multiple Windows**: Minute, Hour, Day  
✅ **Sliding Window**: Algoritmo preciso (no fixed window)  
✅ **Burst Allowance**: Permite picos temporales  
✅ **Concurrent Limit**: Máximo requests simultáneos  
✅ **Ban System**: Ban automático por violaciones  
✅ **Allowlist**: Bypass para IPs/users confiables  
✅ **Analytics**: Estadísticas de uso  
✅ **Quota Management**: Visualización de cuotas  

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────┐
│            Client Request                       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  Rate Limiter   │
         │   Middleware    │
         └────────┬────────┘
                  │
          ┌───────┴───────┐
          │               │
          ▼               ▼
    ┌──────────┐    ┌──────────┐
    │ Allowlist│    │   Ban    │
    │  Check   │    │  Check   │
    └────┬─────┘    └────┬─────┘
         │               │
         └───────┬───────┘
                 │
                 ▼
         ┌──────────────┐
         │    Redis     │
         │ Sliding      │
         │   Window     │
         └──────┬───────┘
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
   ┌────────┐      ┌─────────┐
   │ Allow  │      │ Reject  │
   │  (200) │      │  (429)  │
   └────────┘      └─────────┘
```

---

## 🎚️ Rate Limit Tiers

### FREE Tier

```python
requests_per_minute: 60
requests_per_hour: 1,000
requests_per_day: 10,000
burst_size: 10
concurrent_requests: 5
```

**Use Case**: Usuarios gratuitos, desarrollo, testing

### BASIC Tier

```python
requests_per_minute: 120
requests_per_hour: 5,000
requests_per_day: 50,000
burst_size: 20
concurrent_requests: 10
```

**Use Case**: Usuarios básicos, aplicaciones pequeñas

### PREMIUM Tier

```python
requests_per_minute: 300
requests_per_hour: 15,000
requests_per_day: 200,000
burst_size: 50
concurrent_requests: 25
```

**Use Case**: Usuarios premium, aplicaciones medianas

### ENTERPRISE Tier

```python
requests_per_minute: 1,000
requests_per_hour: 50,000
requests_per_day: 1,000,000
burst_size: 100
concurrent_requests: 50
```

**Use Case**: Clientes enterprise, integraciones críticas

### Tier Comparison

| Feature | FREE | BASIC | PREMIUM | ENTERPRISE |
|---------|------|-------|---------|------------|
| **Requests/min** | 60 | 120 | 300 | 1,000 |
| **Requests/hour** | 1K | 5K | 15K | 50K |
| **Requests/day** | 10K | 50K | 200K | 1M |
| **Burst** | 10 | 20 | 50 | 100 |
| **Concurrent** | 5 | 10 | 25 | 50 |

---

## 📊 Sliding Window Algorithm

### Fixed Window vs Sliding Window

#### ❌ Fixed Window Problem

```
Window 1 (00:00-00:59): 60 requests
Window 2 (01:00-01:59): 60 requests

At 00:59: 60 requests ✅
At 01:00: 60 requests ✅
Total in 2 minutes: 120 requests (should be max 120)
But in 1-minute span (00:59-01:01): 120 requests! 🚫
```

#### ✅ Sliding Window Solution

```
Redis Sorted Set:
- Score = timestamp
- Member = request ID

Current time: 01:00:00
Window: Last 60 seconds

ZREMRANGEBYSCORE rl:user-123 0 (current_time - 60)
ZCARD rl:user-123
→ Exact count in last 60 seconds ✅
```

### Implementation

```python
# Remove old entries
await redis.zremrangebyscore(key, 0, current_time - 60)

# Count requests in window
count = await redis.zcard(key)

# Add current request
await redis.zadd(key, {str(current_time): current_time})

# Check limit
if count + 1 > limit:
    return REJECT
else:
    return ALLOW
```

---

## 👤 Per-User Rate Limiting

### User ID > IP Address

**Preferencia**:
1. **User ID** (authenticated users) ✅
2. **IP Address** (anonymous users)
3. **"anonymous"** (fallback)

**Benefits**:
- More accurate (users can change IPs)
- Better UX (not punished for shared IP)
- Fair quotas per user

### Implementation

```python
# Determine identifier
identifier = user_id if user_id else ip_address

# Check rate limit
allowed, info = await limiter.check_limit(
    user_id="user-123",  # Preferred
    ip_address="1.2.3.4",  # Fallback
    tier=RateLimitTier.PREMIUM
)
```

### Shared IP Handling

**Problem**: Multiple users on same IP (office, cafe, etc.)

**Solution**: Per-user limits prevent one user from affecting others

```
User A (1.2.3.4): 50 requests ✅
User B (1.2.3.4): 50 requests ✅
User C (1.2.3.4): 50 requests ✅

Total from IP: 150 requests
But each user within limit ✅
```

---

## 🚫 Ban System

### Automatic Banning

**Trigger**: Excessive rate limit violations

**Configuration**:
```python
BAN_THRESHOLD = 10  # Violations before ban
BAN_DURATION = 300  # 5 minutes
VIOLATION_WINDOW = 600  # Track last 10 minutes
```

**Flow**:
```
Request 1: Over limit → Violation 1
Request 2: Over limit → Violation 2
...
Request 10: Over limit → Violation 10
→ BAN for 5 minutes 🚫
```

### Ban Storage

```python
# Redis key
ban:{user_id} = "1"
TTL = 300 seconds

# Check ban
banned = await redis.exists(f"ban:{user_id}")
```

### Unban

**Automatic**: Ban expires after TTL

**Manual**: Admin endpoint
```python
await redis.delete(f"ban:{user_id}")
```

---

## 📡 Endpoints

### Check Quota (User)

**GET** `/api/users/me/quota`

```json
{
  "user_id": "user-123",
  "tier": "premium",
  "usage": {
    "minute": {
      "used": 45,
      "limit": 300,
      "remaining": 255,
      "percentage": 15.0
    },
    "hour": {
      "used": 1200,
      "limit": 15000,
      "remaining": 13800,
      "percentage": 8.0
    },
    "day": {
      "used": 8500,
      "limit": 200000,
      "remaining": 191500,
      "percentage": 4.25
    }
  },
  "timestamp": 1697200000
}
```

### Reset Limits (Admin)

**POST** `/admin/rate-limit/reset/{user_id}`

```bash
curl -X POST http://api/admin/rate-limit/reset/user-123 \
  -H "Authorization: Bearer <admin_token>"
```

**Response**:
```json
{
  "message": "Rate limits reset for user-123"
}
```

### Analytics (Admin)

**GET** `/admin/rate-limit/analytics?window=60`

```json
{
  "window_minutes": 60,
  "timestamp": 1697200000,
  "stats": {
    "total_violations": 45,
    "active_bans": 3,
    "top_violators": [
      {"identifier": "user-456", "violations": 15},
      {"identifier": "192.168.1.100", "violations": 12},
      {"identifier": "user-789", "violations": 8}
    ]
  }
}
```

---

## ⚙️ Configuración

### Environment Variables

```bash
# Rate limiting
RATE_LIMIT_ENABLED="true"
RATE_LIMIT_REDIS_HOST="redis"
RATE_LIMIT_REDIS_PORT="6379"
RATE_LIMIT_REDIS_DB="2"  # Separate DB for rate limiting

# Allowlist
RATE_LIMIT_ALLOWLIST_IPS="127.0.0.1,34.94.123.45"  # MinTIC Hub
RATE_LIMIT_ALLOWLIST_USERS="admin-user-1,service-account-1"

# Ban configuration
RATE_LIMIT_BAN_THRESHOLD="10"
RATE_LIMIT_BAN_DURATION="300"
```

### Helm Values

```yaml
global:
  rateLimiting:
    enabled: true
    redisDb: 2
    
    # Allowlist
    allowlistIps:
      - "127.0.0.1"
      - "34.94.123.45"  # MinTIC Hub
    
    # Ban config
    banThreshold: 10
    banDuration: 300  # 5 minutes
```

---

## 📊 Monitoring

### Prometheus Metrics

```promql
# Total requests checked
rate_limit_requests_total

# Allowed requests
rate_limit_allowed_total

# Rejected requests
rate_limit_rejected_total{reason="rate_limit"}
rate_limit_rejected_total{reason="banned"}

# Active bans
rate_limit_active_bans_gauge

# Rejection rate
rate(rate_limit_rejected_total[5m]) / rate(rate_limit_requests_total[5m])
```

### Grafana Dashboard

```json
{
  "title": "Rate Limiting",
  "panels": [
    {
      "title": "Request Rate",
      "targets": [
        {
          "expr": "sum(rate(rate_limit_requests_total[5m])) by (tier)"
        }
      ]
    },
    {
      "title": "Rejection Rate",
      "targets": [
        {
          "expr": "sum(rate(rate_limit_rejected_total[5m])) by (reason)"
        }
      ]
    },
    {
      "title": "Active Bans",
      "targets": [
        {
          "expr": "rate_limit_active_bans_gauge"
        }
      ]
    }
  ]
}
```

### Alerts

```yaml
- alert: HighRateLimitRejectionRate
  expr: |
    rate(rate_limit_rejected_total[5m])
    /
    rate(rate_limit_requests_total[5m])
    > 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High rate limit rejection rate"
    description: "{{ $value | humanizePercentage }} of requests rejected"

- alert: TooManyBans
  expr: rate_limit_active_bans_gauge > 10
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Too many active bans"
    description: "{{ $value }} IPs/users currently banned"
```

---

## 💡 Ejemplos de Uso

### Example 1: Basic Usage

```python
from carpeta_common.advanced_rate_limiter import AdvancedRateLimiterV2, RateLimitTier

limiter = AdvancedRateLimiterV2(redis_client)

allowed, info = await limiter.check_limit(
    user_id="user-123",
    tier=RateLimitTier.FREE
)

if not allowed:
    raise HTTPException(429, detail=info)
```

### Example 2: FastAPI Integration

```python
from fastapi import APIRouter, HTTPException, Depends

router = APIRouter()

async def check_rate_limit(current_user: dict):
    tier = RateLimitTier[current_user.get("tier", "FREE").upper()]
    
    allowed, info = await limiter.check_limit(
        user_id=current_user["id"],
        tier=tier
    )
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=info["message"] if "message" in info else info,
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(info["limits"]["minute"]["limit"]),
                "X-RateLimit-Remaining": "0"
            }
        )

@router.get("/documents", dependencies=[Depends(check_rate_limit)])
async def list_documents():
    return {"documents": [...]}
```

### Example 3: Quota Display

```python
@router.get("/users/me/quota")
async def get_my_quota(current_user: dict):
    tier = RateLimitTier[current_user.get("tier", "FREE").upper()]
    
    usage = await limiter.get_quota_usage(
        user_id=current_user["id"],
        tier=tier
    )
    
    return usage

# Response:
# {
#   "usage": {
#     "minute": {"used": 45, "limit": 300, "remaining": 255},
#     "hour": {"used": 1200, "limit": 15000, "remaining": 13800},
#     "day": {"used": 8500, "limit": 200000, "remaining": 191500}
#   }
# }
```

### Example 4: Admin Reset

```python
@router.post("/admin/rate-limit/reset/{user_id}")
async def reset_user_limits(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(403, detail="Admin only")
    
    await limiter.reset_user_limits(user_id)
    
    return {"message": f"Rate limits reset for {user_id}"}
```

---

## 📈 Analytics

### Usage Patterns

```python
# Get analytics
analytics = await limiter.get_analytics(window_minutes=60)

# Response:
# {
#   "window_minutes": 60,
#   "stats": {
#     "total_violations": 45,
#     "active_bans": 3,
#     "top_violators": [
#       {"identifier": "user-456", "violations": 15},
#       {"identifier": "192.168.1.100", "violations": 12}
#     ]
#   }
# }
```

### Top Users by Usage

```promql
topk(10,
  sum(rate(rate_limit_requests_total[1h])) by (user_id)
)
```

### Rejection Rate by Tier

```promql
sum(rate(rate_limit_rejected_total[5m])) by (tier)
/
sum(rate(rate_limit_requests_total[5m])) by (tier)
```

---

## 🔍 Troubleshooting

### User Can't Make Requests (429)

**Symptom**: All requests return 429

**Debug**:
```python
# Check quota usage
GET /api/users/{user_id}/quota

# Check if banned
GET /admin/rate-limit/status/{user_id}
```

**Solutions**:
1. Wait for quota reset
2. Upgrade tier
3. Admin reset (if false positive)

### Too Many False Positives

**Symptom**: Legitimate users getting rate limited

**Causes**:
1. Tier too restrictive
2. Burst size too small
3. Shared IP (office/cafe)

**Solutions**:
```python
# Increase tier limits
TIERS[RateLimitTier.FREE].requests_per_minute = 100

# Increase burst
TIERS[RateLimitTier.FREE].burst_size = 20

# Use per-user instead of per-IP
# (already default in V2)
```

### Redis Performance Issues

**Symptom**: Slow rate limit checks

**Causes**:
1. Too many keys
2. Large sorted sets
3. No TTL cleanup

**Solutions**:
```python
# Set TTL on all keys
await redis.expire(key, window_seconds)

# Periodic cleanup job
# (automatically done by ZREMRANGEBYSCORE)

# Use separate Redis DB
REDIS_DB = 2  # Dedicated to rate limiting
```

---

## ✅ Best Practices

### DO ✅

1. **Use per-user limits**
   ```python
   # Good
   limiter.check_limit(user_id="user-123")
   ```

2. **Set appropriate tiers**
   ```python
   # Good: Match tier to user subscription
   tier = RateLimitTier[user.subscription.upper()]
   ```

3. **Expose quota to users**
   ```python
   # Good: Let users see their usage
   GET /api/users/me/quota
   ```

4. **Monitor analytics**
   ```python
   # Good: Review top violators
   GET /admin/rate-limit/analytics
   ```

5. **Allowlist trusted services**
   ```python
   # Good: Bypass for MinTIC Hub
   ALLOWLIST_IPS = ["34.94.123.45"]
   ```

### DON'T ❌

1. **Don't use fixed windows**
   ```python
   # Bad: Allows burst at window boundaries
   # Use sliding window instead
   ```

2. **Don't ignore burst**
   ```python
   # Bad: Hard limit
   if count > limit: reject
   
   # Good: Allow burst
   if count > limit + burst: reject
   ```

3. **Don't rate limit health checks**
   ```python
   # Bad
   limiter.check_limit(route="/health")
   
   # Good: Exempt health checks
   EXEMPT_ROUTES = ["/health", "/ready"]
   ```

4. **Don't ban without warnings**
   ```python
   # Bad: Ban on first violation
   BAN_THRESHOLD = 1
   
   # Good: Allow some violations
   BAN_THRESHOLD = 10
   ```

---

## 🧪 Testing

### Test Rate Limit

```bash
# Make 61 requests rapidly (FREE tier = 60/min)
for i in {1..61}; do
  curl http://api/documents -H "Authorization: Bearer <token>"
done

# Request 61 should return 429
```

### Test Burst Allowance

```bash
# Make 70 requests (FREE: 60 limit + 10 burst)
# Requests 1-70 should succeed
# Request 71 should fail

for i in {1..71}; do
  curl http://api/documents
done
```

### Test Tier Upgrade

```python
# Upgrade user tier
user.tier = "PREMIUM"

# Check quota
GET /api/users/me/quota

# Should show new limits (300/min instead of 60/min)
```

---

## 📚 Referencias

- [IETF RFC 6585 - Additional HTTP Status Codes](https://tools.ietf.org/html/rfc6585)
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Sliding Window](https://hechao.li/2018/06/25/Rate-Limiter-Part1/)
- [Redis Sliding Window](https://engineering.classdojo.com/blog/2015/02/06/rolling-rate-limiter/)

---

## ✅ Resumen

**Advanced Rate Limiter V2**:
- ✅ Per-user rate limiting
- ✅ 4 tiers (FREE to ENTERPRISE)
- ✅ 3 time windows (minute, hour, day)
- ✅ Sliding window algorithm
- ✅ Burst allowance
- ✅ Concurrent request limiting
- ✅ Automatic ban system
- ✅ Allowlist support
- ✅ Quota management
- ✅ Analytics & monitoring

**Benefits**:
- 🛡️ DDoS protection
- 💰 Fair usage enforcement
- 📊 Usage analytics
- 👥 User-centric limits
- ⚡ High performance (Redis)

**Estado**: 🟢 Production-ready

---

**Generado**: 2025-10-13 07:15  
**Autor**: Manuel Jurado  
**Versión**: 2.0


# ⚡ Load Testing - Performance Validation

**Performance & Scalability Testing**

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Introducción](#introducción)
2. [Test Scenarios](#test-scenarios)
3. [k6 Load Testing](#k6-load-testing)
4. [Locust Load Testing](#locust-load-testing)
5. [SLO Validation](#slo-validation)
6. [Running Tests](#running-tests)
7. [Analyzing Results](#analyzing-results)
8. [CI/CD Integration](#cicd-integration)
9. [Performance Optimization](#performance-optimization)
10. [Best Practices](#best-practices)

---

## 🎯 Introducción

**Load Testing** valida que el sistema puede manejar la carga esperada (y más) manteniendo SLOs.

### Objectives

✅ **Validate SLOs**: Confirmar P95 < 500ms, error rate < 0.1%  
✅ **Find Breaking Point**: Determinar capacidad máxima  
✅ **Test Auto-Scaling**: Verificar KEDA + HPA  
✅ **Identify Bottlenecks**: DB, Redis, Service Bus, etc.  
✅ **Stress Test**: Behavior bajo carga extrema  

### Tools

- **k6**: JavaScript-based, scriptable, Grafana integration
- **Locust**: Python-based, web UI, distributed mode
- **Analysis Script**: Python script para SLO validation

---

## 🧪 Test Scenarios

### 1. Baseline Test

**Purpose**: Establish baseline performance metrics

**Configuration**:
- VUs: 10
- Duration: 5 minutes
- Goal: Collect baseline metrics

**Expected**:
- P95: <200ms
- Error rate: 0%
- RPS: ~50-100

---

### 2. Normal Load Test

**Purpose**: Simulate typical business hours

**Configuration**:
- Start: 0 → 20 VUs (1 min)
- Sustain: 20 VUs (3 min)
- Ramp down: 20 → 0 (1 min)

**Expected**:
- P95: <500ms ✅ SLO
- Error rate: <0.1% ✅ SLO
- RPS: 100-200

---

### 3. Peak Load Test

**Purpose**: Simulate lunch hour / peak traffic

**Configuration**:
- Start: 0 → 100 VUs (2 min)
- Sustain: 100 VUs (5 min)
- Ramp down: 100 → 0 (2 min)

**Expected**:
- P95: <500ms ✅ SLO (may spike to ~800ms)
- Error rate: <0.1%
- RPS: 500-1000
- HPA should scale pods

---

### 4. Stress Test

**Purpose**: Find system breaking point

**Configuration**:
- Ramp: 0 → 100 → 200 → 300 → 400 VUs
- Each stage: 2 minutes
- Monitor: Error rate, latency degradation

**Expected**:
- Breaking point: ~300-400 VUs
- Graceful degradation (rate limiting kicks in)
- No crashes

---

### 5. Spike Test

**Purpose**: Test sudden traffic spike

**Configuration**:
- Normal: 10 VUs
- Spike: 10 → 500 VUs (10 seconds!)
- Hold: 500 VUs (1 minute)
- Drop: 500 → 10 VUs

**Expected**:
- System survives spike ✅
- Auto-scaling responds
- Temporary latency spike OK
- Error rate <10% during spike

---

## 🚀 k6 Load Testing

### Main Test File

**File**: `tests/load/k6-load-test.js`

**4 Scenarios**:
1. normal_load (20 VUs, 5m)
2. peak_load (100 VUs, 9m)
3. stress_test (100 → 400 VUs, 13m)
4. spike_test (0 → 200 VUs in 10s, 1.5m)

**Total Duration**: ~30 minutes

### Custom Metrics

```javascript
const documentUploadDuration = new Trend('document_upload_duration');
const searchDuration = new Trend('search_duration');
const transferDuration = new Trend('transfer_duration');
const rateLimitHits = new Counter('rate_limit_hits');
```

### Thresholds (SLO-based)

```javascript
thresholds: {
  'http_req_duration': ['p(95)<500', 'p(99)<2000'],  // SLO
  'http_req_failed': ['rate<0.001'],                 // SLO: <0.1%
  'document_upload_duration': ['p(95)<3000'],
  'search_duration': ['p(95)<500'],
  'transfer_duration': ['p(95)<2000'],
  'rate_limit_hits': ['count<100'],
}
```

### Running k6

```bash
cd tests/load

# Run all scenarios
k6 run k6-load-test.js

# Run specific scenario
k6 run scenarios/api-baseline.js

# With output to JSON
k6 run k6-load-test.js --out json=results.json

# With summary export
k6 run k6-load-test.js --summary-export=summary.json

# Custom parameters
k6 run k6-load-test.js -e BASE_URL=http://staging-api.example.com
```

---

## 🐝 Locust Load Testing

### locustfile.py

**2 User Classes**:

1. **CarpetaCiudadanaUser**: Realistic user behavior
   - Tasks: upload (5x), search (3x), list (2x), transfer (2x), create_shortlink (1x)
   - Wait time: 1-5 seconds
   - Tracks documents and transfers

2. **StressTestUser**: Aggressive testing
   - Rapid fire requests
   - Minimal wait time (0.1-0.5s)
   - Tests rate limiting

### Running Locust

```bash
cd tests/load

# Web UI (interactive)
locust -f locustfile.py --host=http://localhost:8000
# Open: http://localhost:8089

# Headless (automated)
locust -f locustfile.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless \
  --html=results/locust-report.html \
  --csv=results/locust

# Stress test user class
locust -f locustfile.py \
  --host=http://localhost:8000 \
  --user-classes StressTestUser \
  --users 500 \
  --spawn-rate 50 \
  --run-time 3m \
  --headless
```

---

## 📊 SLO Validation

### SLOs to Validate

| Metric | SLO | Test Validation |
|--------|-----|----------------|
| **Availability** | 99.9% | Error rate < 0.1% |
| **Latency P95** | <500ms | k6 threshold |
| **Latency P99** | <2s | k6 threshold |
| **Throughput** | >100 RPS | Measure actual RPS |

### Validation Script

```bash
python scripts/analyze-load-results.py tests/load/results/summary.json
```

**Output**:
```
📊 K6 LOAD TEST RESULTS ANALYSIS
====================================
⏱️  HTTP Request Duration:
   Average: 245.32ms
   P95: 387.54ms ✅ (SLO: <500ms)
   P99: 1245.87ms ✅ (SLO: <2000ms)

❌ Error Rate:
   0.045% ✅ (SLO: <0.1%)

📈 Throughput:
   Total requests: 12,450
   Requests/sec: 124.50

✅ ALL SLOs MET! System performance is excellent.
```

---

## 🔍 Analyzing Results

### k6 HTML Report

```bash
# Generate HTML report (requires k6-reporter)
k6 run k6-load-test.js --out json=results.json
k6-to-html results.json results.html

# Open report
open results.html
```

### Locust HTML Report

Automatically generated with `--html` flag:

```bash
locust -f locustfile.py --html=report.html
```

**Report Includes**:
- Request statistics
- Response time charts
- Failures breakdown
- Number of users over time

### Grafana Integration

k6 can send metrics to Prometheus/Grafana:

```bash
k6 run k6-load-test.js \
  --out statsd=localhost:8125
```

Then visualize in Grafana dashboard.

---

## 🔄 CI/CD Integration

### GitHub Actions Workflow

**Trigger**:
- Schedule: Nightly at 2 AM UTC
- Manual: workflow_dispatch

**Jobs**:
1. **k6-load-test**: Run k6 scenarios
2. **locust-load-test**: Run Locust headless

**Steps**:
- Start services (docker-compose)
- Run load tests
- Upload results (artifacts, 30 days retention)
- Analyze results (SLO validation)
- Stop services

### Manual Trigger

```bash
# GitHub UI: Actions → Load Tests → Run workflow
# Select scenario: baseline, stress, spike, or full
```

---

## 🚀 Performance Optimization

### If SLOs Not Met

**High Latency (P95 > 500ms)**:

1. **Database Optimization**:
   ```sql
   -- Add indexes
   CREATE INDEX idx_documents_user ON documents (user_id, created_at);
   
   -- Analyze queries
   EXPLAIN ANALYZE SELECT ...;
   ```

2. **Cache More**:
   ```python
   # Cache frequently accessed data
   @cache(ttl=300)
   def get_metadata(doc_id):
       ...
   ```

3. **Increase Replicas**:
   ```yaml
   # HPA
   minReplicas: 3  # Instead of 2
   ```

**High Error Rate (>0.1%)**:

1. **Check Logs**:
   ```bash
   kubectl logs -l app=gateway --tail=1000 | grep ERROR
   ```

2. **Check Resources**:
   ```bash
   kubectl top pods
   kubectl top nodes
   ```

3. **Increase Limits**:
   ```yaml
   resources:
     limits:
       cpu: 1000m  # Instead of 500m
   ```

**Rate Limiting Issues**:

1. **Increase Tier Limits**:
   ```python
   RateLimitTier.FREE.requests_per_minute = 120  # Instead of 60
   ```

2. **Increase Burst**:
   ```python
   burst_size = 20  # Instead of 10
   ```

---

## ✅ Best Practices

### DO ✅

1. **Test realistic scenarios**
   ```javascript
   // Good: Mix of operations
   50% reads, 30% writes, 20% complex
   ```

2. **Use gradual ramp-up**
   ```javascript
   // Good
   stages: [
     { duration: '2m', target: 100 },
     { duration: '5m', target: 100 },
   ]
   ```

3. **Set proper thresholds**
   ```javascript
   // Good: Based on SLOs
   thresholds: {
     'http_req_duration': ['p(95)<500'],
   }
   ```

4. **Monitor during tests**
   ```bash
   # Watch Grafana dashboard
   # Check pod auto-scaling
   kubectl get hpa -w
   ```

### DON'T ❌

1. **Don't test production directly**
   ```bash
   # Bad: Load test production
   # Good: Use staging/dedicated test environment
   ```

2. **Don't ignore warm-up**
   ```javascript
   // Bad: Immediate 100 VUs
   // Good: Ramp from 0 to 100 over 2 minutes
   ```

3. **Don't use single scenario**
   ```javascript
   // Bad: Only peak load
   // Good: Baseline + peak + stress + spike
   ```

4. **Don't skip analysis**
   ```bash
   # Bad: Just run tests
   # Good: Analyze results, validate SLOs
   ```

---

## 📚 Referencias

- [k6 Documentation](https://k6.io/docs/)
- [Locust Documentation](https://docs.locust.io/)
- [Load Testing Best Practices](https://k6.io/docs/testing-guides/load-testing-best-practices/)
- [SLO-based Load Testing](https://www.infoq.com/articles/testing-SLOs/)

---

## ✅ Resumen

**Load Testing Suite**:
- ✅ k6 scenarios (4: normal, peak, stress, spike)
- ✅ Locust user behaviors (2 classes)
- ✅ SLO-based thresholds (P95 < 500ms, error < 0.1%)
- ✅ Custom metrics (upload, search, transfer)
- ✅ CI/CD workflow (nightly + manual)
- ✅ Analysis script (SLO validation)
- ✅ Results upload (artifacts, 30 days)

**Test Coverage**:
- Document upload/search/list
- Transfers (initiate, status)
- Shortlink creation
- Health checks
- Rate limiting validation

**Scenarios**:
- Baseline (10 VUs, 5m)
- Normal load (20 VUs, 5m)
- Peak load (100 VUs, 9m)
- Stress test (100-400 VUs, 13m)
- Spike test (0-200 VUs spike, 1.5m)

**Estado**: 🟢 Production-ready

---

**Generado**: 2025-10-13 08:45  
**Autor**: Manuel Jurado  
**Versión**: 1.0


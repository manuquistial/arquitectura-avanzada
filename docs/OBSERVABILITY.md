# 📊 Observabilidad Completa - Carpeta Ciudadana

**Sistema de Monitoreo, Alertas y Logging**

**Fecha**: 2025-10-13  
**Versión**: 2.0  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Arquitectura de Observabilidad](#arquitectura-de-observabilidad)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Métricas (Prometheus)](#métricas-prometheus)
4. [Logs (Loki + Promtail)](#logs-loki--promtail)
5. [Dashboards (Grafana)](#dashboards-grafana)
6. [Alerting](#alerting)
7. [SLOs & SLIs](#slos--slis)
8. [Distributed Tracing](#distributed-tracing)
9. [Deployment](#deployment)
10. [Best Practices](#best-practices)

---

## 🏗️ Arquitectura de Observabilidad

```
┌─────────────────────────────────────────────────────────────┐
│                    Carpeta Ciudadana                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Gateway  │  │ Citizen  │  │Ingestion │  │   ...    │   │
│  │          │  │          │  │          │  │          │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │              │              │         │
│       └─────────────┴──────────────┴──────────────┘         │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐
    │Prometheus│     │  Loki   │     │ Jaeger  │
    │(Metrics) │     │ (Logs)  │     │(Traces) │
    └────┬────┘     └────┬────┘     └────┬────┘
         │               │                │
         └───────────────┼────────────────┘
                         │
                         ▼
                   ┌──────────┐
                   │ Grafana  │
                   │(Dashboards│
                   │& Alerts) │
                   └────┬─────┘
                        │
                        ▼
                  ┌────────────┐
                  │Alertmanager│
                  │            │
                  └─────┬──────┘
                        │
            ┌───────────┼───────────┐
            │           │           │
            ▼           ▼           ▼
       ┌────────┐  ┌────────┐  ┌────────┐
       │ Email  │  │ Slack  │  │PagerDuty│
       └────────┘  └────────┘  └────────┘
```

---

## 🛠️ Stack Tecnológico

### 1. Prometheus (Métricas)

**Versión**: 2.45+  
**Puerto**: 9090  
**Retention**: 15 días  

**Características**:
- Time-series database
- Pull-based scraping (30s interval)
- PromQL query language
- Service discovery (Kubernetes)
- Recording rules
- Alerting rules

**Deployment**:
```bash
helm install prometheus prometheus-community/kube-prometheus-stack \
  -f observability/prometheus-values.yaml \
  -n monitoring --create-namespace
```

### 2. Grafana (Visualización)

**Versión**: 10.0+  
**Puerto**: 3000  
**Auth**: Azure AD (SSO)  

**Características**:
- 10+ dashboards pre-configurados
- Variables dinámicas
- Annotations
- Alerting integrado
- Data source: Prometheus + Loki + Jaeger

**Dashboards**:
- Overview General
- API Latency
- Cache Performance
- Service Health
- Queue Health (Service Bus)
- Transfers Saga
- Hub Protection
- SLO Compliance

### 3. Loki (Logs)

**Versión**: 2.9+  
**Puerto**: 3100  
**Retention**: 30 días  

**Características**:
- Like Prometheus, but for logs
- Labels for indexing (no full-text search)
- LogQL query language
- Multi-tenancy support
- Object storage backend

### 4. Promtail (Log Shipper)

**Versión**: 2.9+  
**Deployment**: DaemonSet  

**Características**:
- Collects logs from Kubernetes pods
- Pipeline stages (parsing, filtering)
- Label extraction
- Ships to Loki

### 5. OpenTelemetry Collector

**Versión**: 0.88+  
**Port**: 4317 (gRPC), 4318 (HTTP)  

**Características**:
- Receives metrics, logs, traces
- Processors (batch, filter, transform)
- Exporters (Prometheus, Loki, Jaeger)
- Vendor-agnostic

### 6. Alertmanager

**Versión**: 0.26+  
**Port**: 9093  

**Características**:
- Alert aggregation
- Deduplication
- Silencing
- Routing (email, Slack, PagerDuty)
- Inhibition rules

---

## 📊 Métricas (Prometheus)

### Métricas Disponibles

#### HTTP Server Metrics

```promql
# Request count
http_server_requests_total{service_name="gateway", http_route="/api/documents", status_code="200"}

# Request duration histogram
http_server_request_duration_bucket{service_name="gateway", le="0.5"}

# Active requests
http_server_active_requests{service_name="gateway"}
```

#### Database Metrics

```promql
# Connection pool
db_connection_pool_active{service_name="citizen"}
db_connection_pool_idle{service_name="citizen"}
db_connection_pool_max{service_name="citizen"}

# Query duration
db_query_duration_seconds{service_name="citizen", query_type="SELECT"}
```

#### Redis Metrics

```promql
# Cache hits/misses
redis_cache_hits_total{service_name="gateway"}
redis_cache_misses_total{service_name="gateway"}

# Connection status
redis_connected_clients{instance="redis:6379"}
```

#### Service Bus Metrics

```promql
# Queue depth
servicebus_queue_messages_active{queue_name="transfer-events"}
servicebus_queue_messages_deadletter{queue_name="transfer-events"}

# Processing rate
rate(servicebus_messages_processed_total[5m])
```

#### Kubernetes Metrics

```promql
# Pod status
kube_pod_status_phase{namespace="carpeta-ciudadana-dev", phase="Running"}

# HPA status
kube_horizontalpodautoscaler_status_current_replicas
kube_horizontalpodautoscaler_status_desired_replicas

# Node status
kube_node_status_condition{condition="Ready", status="true"}
```

### Queries Útiles

#### P95 Latency por Servicio

```promql
histogram_quantile(0.95,
  sum(rate(http_server_request_duration_bucket[5m])) 
  by (le, service_name)
) * 1000
```

#### Error Rate (%)

```promql
(
  sum(rate(http_server_requests_total{status_code=~"5.."}[5m]))
  /
  sum(rate(http_server_requests_total[5m]))
) * 100
```

#### Availability (%)

```promql
avg(up{job=~".*carpeta.*"}) * 100
```

#### Top 10 Slowest Endpoints

```promql
topk(10,
  histogram_quantile(0.95,
    sum(rate(http_server_request_duration_bucket[5m])) 
    by (le, service_name, http_route)
  )
)
```

---

## 📝 Logs (Loki + Promtail)

### LogQL Queries

#### Buscar errores en los últimos 5 minutos

```logql
{namespace="carpeta-ciudadana-dev", level="error"} |= "exception"
```

#### Filtrar por servicio

```logql
{namespace="carpeta-ciudadana-dev", service_name="gateway"}
```

#### Buscar por trace ID

```logql
{namespace="carpeta-ciudadana-dev"} |= "trace_id=abc123"
```

#### Rate de logs de error

```logql
rate({namespace="carpeta-ciudadana-dev", level="error"}[5m])
```

#### Top 10 errores más frecuentes

```logql
topk(10,
  sum by (error_message) (
    count_over_time({namespace="carpeta-ciudadana-dev", level="error"}[1h])
  )
)
```

### Log Levels

- **DEBUG**: Información detallada (deshabilitado en prod)
- **INFO**: Información general
- **WARNING**: Advertencias
- **ERROR**: Errores manejados
- **CRITICAL**: Errores críticos

### Log Format (JSON)

```json
{
  "timestamp": "2025-10-13T05:00:00.123Z",
  "level": "INFO",
  "service": "gateway",
  "message": "Request processed",
  "trace_id": "abc123...",
  "span_id": "def456...",
  "user_id": "user-123",
  "http_method": "GET",
  "http_path": "/api/documents",
  "http_status": 200,
  "duration_ms": 45
}
```

---

## 📈 Dashboards (Grafana)

### 1. Overview General

**URL**: `/d/overview-general`

**Paneles**:
- 🎯 SLI - Service Availability (Stat)
- ⚡ Request Rate (Stat)
- ❌ Error Rate (Stat)
- ⏱️ P95 Latency (Stat)
- 📊 Request Rate by Service (Timeseries)
- 🐛 Error Rate by Service (Timeseries)
- ⏱️ Latency Distribution (P50, P95, P99)
- 🔥 Top 10 Slowest Endpoints (Table)
- 💾 Database Connection Pool (Timeseries)
- 🔄 Redis Cache Hit Rate (Gauge)
- 📨 Service Bus Queue Depth (Timeseries)
- ☸️ Pod Status by Service (Table)
- 💻 Node Resource Usage (Timeseries)
- 🎯 SLO Compliance (Table)

### 2. API Latency Dashboard

**URL**: `/d/api-latency`

**Paneles**:
- HTTP Request Duration (P95)
- Latency by Endpoint
- Slow Requests (>2s)
- Request Count by Status
- Error Rate Trends

### 3. Cache Performance Dashboard

**URL**: `/d/cache-performance`

**Paneles**:
- Cache Hit Rate
- Cache Size
- Eviction Rate
- Miss Penalty (latency)

### 4. Service Health Dashboard

**URL**: `/d/service-health`

**Paneles**:
- Pod Status
- Restart Count
- Memory Usage
- CPU Usage
- Network I/O

### 5. Queue Health Dashboard

**URL**: `/d/queue-health`

**Paneles**:
- Queue Depth
- Processing Rate
- DLQ Messages
- Message Age

### 6. Transfers Saga Dashboard

**URL**: `/d/transfers-saga`

**Paneles**:
- Transfer States
- Success Rate
- Failure Reasons
- Duration Distribution

### 7. Hub Protection Dashboard

**URL**: `/d/hub-protection`

**Paneles**:
- Request Rate to Hub
- Circuit Breaker Status
- Retry Attempts
- Timeout Rate

### 8. SLO Compliance Dashboard

**URL**: `/d/slo-compliance`

**Paneles**:
- Current SLI Values
- Error Budget Remaining
- 30-day Compliance
- Burn Rate

---

## 🔔 Alerting

### Alert Routing

```yaml
# Alertmanager configuration
route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  
  routes:
  # Critical alerts → PagerDuty + Slack
  - match:
      severity: critical
    receiver: pagerduty-critical
    continue: true
  
  # Critical alerts also to Slack
  - match:
      severity: critical
    receiver: slack-critical
  
  # Warnings → Slack only
  - match:
      severity: warning
    receiver: slack-warnings
  
  # SLO alerts → SRE team
  - match_re:
      alertname: ^SLO_.*
    receiver: sre-team

receivers:
- name: 'default'
  email_configs:
  - to: 'ops@example.com'

- name: 'pagerduty-critical'
  pagerduty_configs:
  - service_key: '<PAGERDUTY_KEY>'

- name: 'slack-critical'
  slack_configs:
  - api_url: '<SLACK_WEBHOOK>'
    channel: '#alerts-critical'
    title: '🚨 CRITICAL ALERT'

- name: 'slack-warnings'
  slack_configs:
  - api_url: '<SLACK_WEBHOOK>'
    channel: '#alerts-warnings'
    title: '⚠️ WARNING'

- name: 'sre-team'
  email_configs:
  - to: 'sre@example.com'
```

### Alert Groups

1. **slo-availability**: SLO availability violations
2. **slo-latency**: SLO latency violations
3. **slo-error-budget**: Error budget alerts
4. **service-health**: Service up/down, resource usage
5. **database**: Connection pool, slow queries
6. **cache**: Hit rate, connection issues
7. **servicebus**: Queue backlog, DLQ messages
8. **storage**: Blob storage latency, errors
9. **kubernetes**: Node/pod status, HPA, PDB
10. **security**: Failed logins, suspicious activity

---

## 🎯 SLOs & SLIs

Consultar documento dedicado: [SLOS_SLIS.md](./SLOS_SLIS.md)

### Quick Summary

| SLI | Target | Error Budget (30d) |
|-----|--------|-------------------|
| Availability | 99.9% | 43.2 minutes |
| Latency (P95) | <500ms | N/A |
| Latency (P99) | <2s | N/A |
| Error Rate | <0.1% | 43,200 errors @ 100 RPS |

---

## 🔍 Distributed Tracing

### OpenTelemetry Instrumentation

**Auto-instrumentation** (Python):
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Auto-instrument requests library
RequestsInstrumentor().instrument()
```

**Manual spans**:
```python
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_document") as span:
    span.set_attribute("document.id", doc_id)
    span.set_attribute("document.type", doc_type)
    
    # Your code here
    
    span.add_event("Document validated")
```

### Trace Context Propagation

**HTTP Headers**:
```
traceparent: 00-abc123...-def456...-01
tracestate: rojo=00f067aa0ba902b7
```

**Propagation**:
- Gateway → Service A → Service B
- Trace ID mantiene consistencia
- Visualización end-to-end en Jaeger

---

## 🚀 Deployment

### 1. Deploy Prometheus Stack

```bash
# Add Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install
helm install prometheus prometheus-community/kube-prometheus-stack \
  -f observability/prometheus-values.yaml \
  -n monitoring --create-namespace

# Verify
kubectl get pods -n monitoring
```

### 2. Deploy Loki Stack

```bash
# Add Helm repo
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Loki
helm install loki grafana/loki-stack \
  -f observability/loki-values.yaml \
  -n monitoring

# Verify
kubectl get pods -n monitoring -l app=loki
```

### 3. Deploy OpenTelemetry Collector

```bash
helm install otel opentelemetry/opentelemetry-collector \
  -f observability/otel-collector-values.yaml \
  -n monitoring

# Verify
kubectl get pods -n monitoring -l app=otel-collector
```

### 4. Configure Dashboards

```bash
# Import dashboards
kubectl create configmap grafana-dashboards \
  --from-file=observability/grafana-dashboards/ \
  -n monitoring

# Restart Grafana
kubectl rollout restart deployment/prometheus-grafana -n monitoring
```

### 5. Configure Alerts

```bash
# Apply PrometheusRule CRDs
kubectl apply -f observability/alerts/slo-alerts.yaml
kubectl apply -f observability/alerts/prometheus-alerts.yaml

# Verify
kubectl get prometheusrules -n monitoring
```

---

## 📚 Best Practices

### Metrics

✅ **DO**:
- Use histograms for latency (not gauges)
- Label cardinality < 1000
- Use rate() for counters
- Use increase() for totals
- Record SLIs as metrics

❌ **DON'T**:
- High cardinality labels (user_id, trace_id)
- Unbounded label values
- String metrics (use labels)
- Gauge for rates (use counter)

### Logs

✅ **DO**:
- Structured logging (JSON)
- Include trace/span IDs
- Use log levels appropriately
- Add context (user_id, request_id)
- Sample debug logs

❌ **DON'T**:
- Log sensitive data (passwords, tokens)
- Log at DEBUG in production
- Excessive logging (performance)
- String concatenation (use params)

### Dashboards

✅ **DO**:
- Start with overview
- Use variables ($service, $namespace)
- Add descriptions/annotations
- Link to runbooks
- Set appropriate refresh interval

❌ **DON'T**:
- Too many panels (>20)
- Complex queries (slow)
- Absolute time ranges
- Pie charts (hard to read)

### Alerts

✅ **DO**:
- Alert on SLOs (user-facing)
- Multi-window alerting
- Include runbook links
- Test alert routing
- Review alert fatigue

❌ **DON'T**:
- Alert on everything
- Missing descriptions
- No escalation path
- Ignore alert fatigue
- Alert without action

---

## 🔗 Quick Links

| Resource | URL | Description |
|----------|-----|-------------|
| Grafana | http://grafana.example.com | Dashboards |
| Prometheus | http://prometheus.example.com | Metrics |
| Alertmanager | http://alertmanager.example.com | Alerts |
| Loki | http://loki.example.com | Logs |
| Jaeger | http://jaeger.example.com | Traces |
| SLO Dashboard | http://grafana.example.com/d/slo-compliance | SLO status |

---

## 📖 Documentation

- **Prometheus**: https://prometheus.io/docs/
- **Grafana**: https://grafana.com/docs/
- **Loki**: https://grafana.com/docs/loki/
- **OpenTelemetry**: https://opentelemetry.io/docs/
- **Google SRE Book**: https://sre.google/sre-book/
- **Alerting Best Practices**: https://prometheus.io/docs/practices/alerting/

---

## ✅ Resumen

**Stack Completo**:
- ✅ Prometheus (métricas)
- ✅ Grafana (dashboards)
- ✅ Loki (logs)
- ✅ Promtail (log shipper)
- ✅ OpenTelemetry (traces)
- ✅ Alertmanager (alerts)

**Dashboards**: 8 completos  
**Alertas**: 40+ reglas  
**SLOs**: 5 definidos  
**Log Retention**: 30 días  
**Metrics Retention**: 15 días  

**Estado**: 🟢 Production-ready

---

**Generado**: 2025-10-13 05:30  
**Autor**: Manuel Jurado  
**Versión**: 2.0


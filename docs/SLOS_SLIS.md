# 📊 SLOs & SLIs - Carpeta Ciudadana

**Service Level Objectives & Service Level Indicators**

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Introducción](#introducción)
2. [SLIs Definidos](#slis-definidos)
3. [SLOs Objetivos](#slos-objetivos)
4. [Error Budgets](#error-budgets)
5. [Alerting Strategy](#alerting-strategy)
6. [Dashboards](#dashboards)
7. [Burn Rate](#burn-rate)
8. [Incident Response](#incident-response)

---

## 🎯 Introducción

Los **SLOs** (Service Level Objectives) definen el nivel de servicio que nos comprometemos a proporcionar a los usuarios. Los **SLIs** (Service Level Indicators) son las métricas que usamos para medir ese servicio.

### Filosofía

Basado en las prácticas de Google SRE:
- **SLI**: *"¿Qué estamos midiendo?"*
- **SLO**: *"¿Qué tan bien debe funcionar?"*
- **Error Budget**: *"¿Cuánto podemos fallar?"*

---

## 📐 SLIs Definidos

### 1. Availability SLI

**Definición**: Porcentaje de requests HTTP exitosos (status code 2xx, 3xx)

**Cálculo**:
```promql
(
  sum(rate(http_server_requests_total{status_code!~"5.."}[30d]))
  /
  sum(rate(http_server_requests_total[30d]))
) * 100
```

**Target**: 99.9% (three nines)

**Measurement Window**: 30 días

---

### 2. Latency SLI

**Definición**: Percentil 95 (P95) de duración de requests HTTP

**Cálculo**:
```promql
histogram_quantile(0.95,
  sum(rate(http_server_request_duration_bucket[5m])) by (le)
) * 1000
```

**Target**: < 500ms

**Measurement Window**: 5 minutos (rolling)

---

### 3. Error Rate SLI

**Definición**: Porcentaje de requests con status code 5xx

**Cálculo**:
```promql
(
  sum(rate(http_server_requests_total{status_code=~"5.."}[5m]))
  /
  sum(rate(http_server_requests_total[5m]))
) * 100
```

**Target**: < 0.1% (1 error per 1000 requests)

**Measurement Window**: 5 minutos (rolling)

---

### 4. Throughput SLI

**Definición**: Requests por segundo (RPS) que el sistema puede manejar

**Cálculo**:
```promql
sum(rate(http_server_requests_total[5m]))
```

**Target**: > 100 RPS (minimum capacity)

**Peak Capacity**: 500 RPS

---

### 5. Data Durability SLI

**Definición**: Porcentaje de documentos recuperables sin pérdida

**Cálculo**:
```promql
(
  sum(blob_storage_successful_operations_total{operation="get"})
  /
  sum(blob_storage_operations_total{operation="get"})
) * 100
```

**Target**: 99.999999999% (11 nines) - Azure Blob Storage SLA

---

## 🎯 SLOs Objetivos

### SLO Summary Table

| SLI | Target | Error Budget (30d) | Monitoring |
|-----|--------|-------------------|------------|
| **Availability** | 99.9% | 43.2 minutes | `up` metric |
| **Latency (P95)** | <500ms | N/A | histogram |
| **Latency (P99)** | <2s | N/A | histogram |
| **Error Rate** | <0.1% | 43,200 errors (at 100 RPS) | status codes |
| **Throughput** | >100 RPS | N/A | rate |
| **Data Durability** | 99.999999999% | N/A | Azure SLA |

---

## 💰 Error Budgets

### ¿Qué es un Error Budget?

El **error budget** es la cantidad de tiempo/errores que podemos "gastar" sin violar nuestro SLO.

**Formula**:
```
Error Budget = 100% - SLO
```

### Availability Error Budget

**SLO**: 99.9% availability  
**Error Budget**: 0.1% downtime  
**En 30 días**: 43.2 minutos  
**En 1 año**: 8.76 horas  

### Error Rate Budget

**SLO**: <0.1% error rate  
**Error Budget**: 0.1% of requests  
**At 100 RPS for 30d**: ~43,200 errors  
**At 100 RPS for 1 year**: ~525,600 errors  

### Budget Consumption

```promql
# Availability budget consumed (%)
(1 - avg_over_time(up{job=~".*carpeta.*"}[30d])) / 0.001 * 100

# Error budget consumed (%)
(
  sum(rate(http_server_requests_total{status_code=~"5.."}[30d]))
  /
  sum(rate(http_server_requests_total[30d]))
) / 0.001 * 100
```

### Budget Policies

| Budget Consumed | Action |
|----------------|--------|
| **0-25%** | 🟢 Normal operations - focus on features |
| **25-50%** | 🟡 Caution - review recent changes |
| **50-75%** | 🟠 Alert - freeze risky deployments |
| **75-100%** | 🔴 Crisis - freeze ALL changes, focus on stability |

---

## 🔔 Alerting Strategy

### Multi-Window, Multi-Burn-Rate Alerts

Basado en Google SRE Workbook, usamos múltiples ventanas de tiempo para detectar diferentes tipos de problemas:

#### Fast Burn (2% in 1 hour)

```yaml
- alert: SLO_AvailabilityBudgetBurning_Fast
  expr: |
    (
      sum(rate(http_server_requests_total{status_code!~"5.."}[1m]))
      /
      sum(rate(http_server_requests_total[1m]))
    ) < 0.999
  for: 2m
  labels:
    severity: critical
    window: fast
```

**Meaning**: Gastando 2% del budget mensual en 1 hora → todo el budget en 2 días

**Action**: Immediate investigation required

#### Slow Burn (5% in 6 hours)

```yaml
- alert: SLO_AvailabilityBudgetBurning_Slow
  expr: |
    (
      sum(rate(http_server_requests_total{status_code!~"5.."}[30m]))
      /
      sum(rate(http_server_requests_total[30m]))
    ) < 0.999
  for: 15m
  labels:
    severity: warning
    window: slow
```

**Meaning**: Gastando 5% del budget mensual en 6 horas → todo el budget en 6 días

**Action**: Investigate and plan remediation

---

## 📊 Dashboards

### 1. SLO Overview Dashboard

**URL**: `/grafana/d/slo-overview`

**Panels**:
- Current SLI values (gauges)
- Error budget remaining (progress bars)
- 30-day SLO compliance (tables)
- Budget burn rate (graphs)

### 2. Detailed SLI Dashboard

**URL**: `/grafana/d/sli-details`

**Panels**:
- Latency distribution (P50, P95, P99)
- Error rate by service
- Request rate trends
- Top slow endpoints

### 3. Error Budget Dashboard

**URL**: `/grafana/d/error-budget`

**Panels**:
- Budget consumption rate
- Historical budget usage
- Projected budget exhaustion
- Budget policy status

---

## 🔥 Burn Rate

### ¿Qué es Burn Rate?

**Burn rate** es la velocidad a la que consumimos el error budget.

**Formula**:
```
Burn Rate = (Actual Error Rate) / (SLO Error Rate)
```

### Burn Rate Examples

| Availability | Error Rate | Burn Rate | Budget Consumed In |
|-------------|------------|-----------|-------------------|
| 99.9% (SLO) | 0.1% | 1x | 30 days (as planned) |
| 99% | 1% | 10x | 3 days ⚠️ |
| 95% | 5% | 50x | 14 hours 🔴 |
| 90% | 10% | 100x | 7 hours 🚨 |

### Burn Rate Alerts

```promql
# Calculate burn rate
(
  (1 - avg_over_time(up{job=~".*carpeta.*"}[1h]))
  /
  0.001  # SLO error rate (0.1%)
)
```

**Interpretation**:
- **1x**: Normal (as expected)
- **2x**: Caution
- **10x**: Alert (budget in 3 days)
- **>50x**: Critical (budget in hours)

---

## 🚨 Incident Response

### SLO Violation Response

#### 1. Detect (Automated)

Alertmanager fires alert → PagerDuty/Slack notification

#### 2. Assess

- Check SLO dashboard
- Identify which SLI is violated
- Calculate remaining error budget
- Determine burn rate

#### 3. Respond

**If budget >50%**:
- Investigate root cause
- Plan fix
- Schedule deployment

**If budget <50%**:
- Immediate incident response
- Freeze non-critical deployments
- Focus on stability

**If budget <25%**:
- Full incident response
- Freeze ALL deployments
- Emergency fix only
- Postmortem required

#### 4. Recover

- Fix deployed
- Monitor SLI recovery
- Update runbooks
- Conduct blameless postmortem

#### 5. Learn

- Document incident
- Update alerts if needed
- Improve monitoring
- Share learnings

---

## 📈 Monitoring Queries

### Check Current SLO Status

```bash
# Availability (30d)
curl -s 'http://prometheus:9090/api/v1/query?query=avg_over_time(up{job=~".*carpeta.*"}[30d])*100'

# P95 Latency (5m)
curl -s 'http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(http_server_request_duration_bucket[5m]))by(le))*1000'

# Error Rate (5m)
curl -s 'http://prometheus:9090/api/v1/query?query=(sum(rate(http_server_requests_total{status_code=~"5.."}[5m]))/sum(rate(http_server_requests_total[5m])))*100'
```

### Error Budget Remaining

```promql
# Availability budget remaining (minutes in 30d)
(0.001 - (1 - avg_over_time(up{job=~".*carpeta.*"}[30d]))) * 43200

# Error budget remaining (errors at 100 RPS for 30d)
(0.001 - (sum(rate(http_server_requests_total{status_code=~"5.."}[30d]))/sum(rate(http_server_requests_total[30d])))) * 259200000
```

---

## 📚 SLO Maintenance

### Quarterly SLO Review

**Agenda**:
1. Review actual performance vs. SLO
2. Analyze error budget consumption patterns
3. Assess if SLOs are:
   - Too strict (always meeting → increase)
   - Too loose (never meeting → decrease or improve system)
   - Just right (meeting 95% of time)
4. Update SLOs if business needs changed
5. Review alert effectiveness

### SLO Documentation

**Maintained in**:
- This document (source of truth)
- Grafana dashboards (live status)
- Runbooks (response procedures)
- Postmortems (historical context)

---

## 🎓 Best Practices

### DO ✅

- **Base SLOs on user experience** (not just technical metrics)
- **Start conservative** (easier to loosen than tighten)
- **Review regularly** (quarterly minimum)
- **Use error budgets** to guide decision-making
- **Alert on burn rate** (not just SLI thresholds)
- **Document everything** (runbooks, postmortems)
- **Iterate** based on incidents and feedback

### DON'T ❌

- **Don't set SLOs at 100%** (unrealistic, no room for innovation)
- **Don't ignore error budgets** (defeats the purpose)
- **Don't alert on SLO violations only** (too late)
- **Don't skip postmortems** (lost learning opportunity)
- **Don't blame individuals** (blameless culture)
- **Don't freeze forever** (use budget wisely)

---

## 📊 SLO Metrics Export

### Prometheus Recording Rules

```yaml
groups:
- name: slo-recording
  interval: 30s
  rules:
  # Availability SLI
  - record: sli:availability:ratio_30d
    expr: |
      avg_over_time(up{job=~".*carpeta.*"}[30d])
  
  # Latency SLI (P95)
  - record: sli:latency_p95:seconds_5m
    expr: |
      histogram_quantile(0.95,
        sum(rate(http_server_request_duration_bucket[5m])) by (le)
      )
  
  # Error Rate SLI
  - record: sli:error_rate:ratio_5m
    expr: |
      sum(rate(http_server_requests_total{status_code=~"5.."}[5m]))
      /
      sum(rate(http_server_requests_total[5m]))
  
  # Error Budget Remaining
  - record: slo:availability:budget_remaining_minutes
    expr: |
      (0.001 - (1 - sli:availability:ratio_30d)) * 43200
```

---

## ✅ Resumen

**SLOs Definidos**: 5  
**Error Budgets**: Calculados  
**Alerting**: Multi-window strategy  
**Dashboards**: 3 creados  
**Review Cycle**: Quarterly  

**SLO Philosophy**:
> "SLOs are the foundation of reliability. They tell us what matters, how well we're doing, and when to take action."

---

**Generado**: 2025-10-13 05:00  
**Autor**: Manuel Jurado  
**Versión**: 1.0  
**Referencias**: Google SRE Book, SRE Workbook


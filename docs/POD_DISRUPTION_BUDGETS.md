# 🛡️ Pod Disruption Budgets (PDBs) - High Availability

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

Documentación de PodDisruptionBudgets para garantizar alta disponibilidad durante operaciones de mantenimiento.

---

## 📋 Índice

1. [Descripción General](#descripción-general)
2. [Por Qué Son Importantes](#por-qué-son-importantes)
3. [PDBs Implementados](#pdbs-implementados)
4. [Configuración](#configuración)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 Descripción General

Los **PodDisruptionBudgets (PDBs)** limitan el número de pods que pueden ser interrumpidos simultáneamente durante operaciones voluntarias de mantenimiento.

### Operaciones Voluntarias

✅ **Draining nodes** (kubectl drain)  
✅ **Cluster upgrades** (Kubernetes version)  
✅ **Node updates** (OS patches)  
✅ **Node scaling down** (reduce node count)  
✅ **Pod evictions** (resource constraints)  

### Operaciones Involuntarias (NO protegidas por PDB)

❌ **Node failures** (hardware crash)  
❌ **Pod crashes** (OOM, app error)  
❌ **Network partitions**  
❌ **Direct pod deletion** (kubectl delete pod)  

---

## 🚨 Por Qué Son Importantes

### Sin PDB

```
Scenario: kubectl drain node-1

1. Kubernetes drains ALL pods from node-1 simultaneously
2. gateway: 3 pods → 0 pods (all on node-1)
3. ❌ SERVICE OUTAGE (no healthy pods)
4. After 30s, new pods scheduled on other nodes
5. ⚠️  30 seconds de downtime
```

### Con PDB (minAvailable: 2)

```
Scenario: kubectl drain node-1

1. Kubernetes attempts to drain node-1
2. gateway: 3 pods total, 2 on node-1, 1 on node-2
3. PDB: "Must keep 2 available"
4. ✅ Drains 1 pod from node-1
5. Waits for new pod to be Ready
6. ✅ Drains remaining pod from node-1
7. ✅ NO DOWNTIME (always 2+ pods available)
```

---

## 📜 PDBs Implementados

### 1. Frontend (minAvailable: 1)

```yaml
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: frontend
```

**Razón**: Next.js frontend, no crítico pero debe estar disponible.  
**Replicas**: 2-10 (HPA)  
**Garantía**: Mínimo 1 pod durante drains

---

### 2. Gateway (minAvailable: 2) ⭐ CRITICAL

```yaml
spec:
  minAvailable: 2  # More strict for critical service
  selector:
    matchLabels:
      app: gateway
```

**Razón**: Gateway es punto de entrada crítico, maneja todo el tráfico.  
**Replicas**: 3-20 (HPA)  
**Garantía**: Mínimo 2 pods siempre (alta disponibilidad)

---

### 3. Citizen (minAvailable: 1)

```yaml
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: citizen
```

**Razón**: CRUD ciudadanos, importante pero no crítico.  
**Replicas**: 2-10 (HPA)

---

### 4. Ingestion (minAvailable: 1)

**Razón**: Genera SAS URLs, no crítico pero debe estar disponible.  
**Replicas**: 2-15 (HPA)

---

### 5. Signature (minAvailable: 1) ⭐ CRITICAL

**Razón**: Activación WORM, operación crítica.  
**Replicas**: 2-10 (HPA)  
**Garantía**: Siempre al menos 1 pod disponible para firmas

---

### 6. Transfer (minAvailable: 1) ⭐ CRITICAL

**Razón**: Saga orchestrator, maneja transacciones complejas.  
**Replicas**: 2-10 (HPA)  
**Garantía**: Mantiene continuidad de sagas en progreso

---

### 7. Metadata (minAvailable: 1)

**Razón**: Búsquedas en OpenSearch.  
**Replicas**: 2-10 (HPA)

---

### 8. MinTIC Client (minAvailable: 1)

**Razón**: Integración con Hub, rate-limited.  
**Replicas**: 2-10 (HPA)

---

### 9. Sharing (minAvailable: 1)

**Razón**: Shortlinks, bajo uso.  
**Replicas**: 2-10 (HPA)

---

### 10. Notification (minAvailable: 1)

**Razón**: Email + webhooks, consumer.  
**Replicas**: 2-10 (HPA)

---

### 11. Read Models (minAvailable: 1)

**Razón**: CQRS queries, importante para UX.  
**Replicas**: 2-10 (HPA)

---

### 12. Transfer Worker (maxUnavailable: 50%) ⚡ SPECIAL

```yaml
spec:
  maxUnavailable: 50%  # Different strategy for KEDA workloads
  selector:
    matchLabels:
      app: transfer-worker
```

**Razón**: KEDA scales 0-30, usar maxUnavailable permite scale to zero.  
**Replicas**: 0-30 (KEDA)  
**Garantía**: Durante operación (>0 pods), máximo 50% disrupted a la vez

**Por qué maxUnavailable y no minAvailable**:
- `minAvailable: 1` bloquearía scale to zero
- `maxUnavailable: 50%` permite 0 replicas cuando queue vacía
- Durante operación normal (ej: 10 pods), puede disruptar máximo 5 a la vez

---

## ⚙️ Configuración

### Habilitar PDBs

```yaml
# values.yaml
podDisruptionBudget:
  enabled: true
  defaultMinAvailable: 1

# Per-service override
gateway:
  podDisruptionBudget:
    minAvailable: 2  # More strict
```

### Deploy

```bash
helm upgrade --install carpeta-ciudadana deploy/helm/carpeta-ciudadana \
  --set podDisruptionBudget.enabled=true \
  --namespace carpeta-ciudadana-dev
```

### Verificar

```bash
# List all PDBs
kubectl get pdb -n carpeta-ciudadana-dev

# Describe specific PDB
kubectl describe pdb gateway -n carpeta-ciudadana-dev

# Check status
kubectl get pdb gateway -n carpeta-ciudadana-dev -o yaml
```

---

## 🧪 Testing

### Test 1: Drain Node with PDB

```bash
# List nodes
kubectl get nodes

# List pods on specific node
kubectl get pods -n carpeta-ciudadana-dev -o wide | grep node-1

# Try to drain (should respect PDB)
kubectl drain node-1 --ignore-daemonsets --delete-emptydir-data

# Expected behavior:
# - Waits for pods to be rescheduled
# - Respects minAvailable constraint
# - Never drops below minAvailable
```

### Test 2: Check PDB Status

```bash
# Check current disruptions allowed
kubectl get pdb -n carpeta-ciudadana-dev

# Output columns:
# NAME       MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
# gateway    2               N/A               1                     5m
# citizen    1               N/A               1                     5m

# ALLOWED DISRUPTIONS = Current replicas - minAvailable
# If gateway has 3 pods and minAvailable=2, allowed=1
```

### Test 3: Force Eviction (Should Block)

```bash
# Get gateway pod
GATEWAY_POD=$(kubectl get pod -n carpeta-ciudadana-dev -l app=gateway -o jsonpath='{.items[0].metadata.name}')

# Try to evict (respects PDB)
kubectl delete pod $GATEWAY_POD -n carpeta-ciudadana-dev

# If this would violate PDB, eviction is delayed until safe

# Check PDB status
kubectl get pdb gateway -n carpeta-ciudadana-dev
```

### Test 4: Cluster Upgrade Simulation

```bash
# Cordon node (mark as unschedulable)
kubectl cordon node-1

# Drain node (should respect all PDBs)
kubectl drain node-1 --ignore-daemonsets --delete-emptydir-data --timeout=10m

# Monitor pod rescheduling
watch kubectl get pods -n carpeta-ciudadana-dev -o wide

# Expected:
# - Pods gradually move to other nodes
# - Service continues running (no downtime)
# - PDBs respected throughout

# Uncordon when done
kubectl uncordon node-1
```

---

## 🔍 Troubleshooting

### Drain bloqueado indefinidamente

**Síntoma**: `kubectl drain` no completa, se queda esperando.

**Causa**: PDB muy restrictivo o pods no pueden relocalizarse.

**Debug**:
```bash
# Check PDB status
kubectl get pdb -n carpeta-ciudadana-dev

# Check events
kubectl get events -n carpeta-ciudadana-dev --sort-by='.lastTimestamp'

# Check pod status
kubectl get pods -n carpeta-ciudadana-dev
```

**Soluciones**:

1. **Aumentar capacity**:
```bash
# Add more nodes first
az aks scale --name carpeta-aks --node-count 4

# Then drain
kubectl drain node-1
```

2. **Relax PDB temporalmente**:
```bash
# Edit PDB
kubectl edit pdb gateway -n carpeta-ciudadana-dev

# Change minAvailable: 2 → 1
# Save and retry drain
```

3. **Use --disable-eviction**:
```bash
# Skip PDB checks (NOT RECOMMENDED for production)
kubectl drain node-1 --disable-eviction --force
```

### PDB shows "ALLOWED DISRUPTIONS: 0"

**Síntoma**: No se pueden disrumpir pods.

**Causa**: Current pods = minAvailable (no hay "spare" pods).

**Ejemplo**:
- gateway: 2 pods corriendo
- PDB: minAvailable: 2
- Allowed disruptions: 2 - 2 = 0

**Solución**:
```bash
# Option 1: Scale up temporarily
kubectl scale deployment gateway --replicas=3 -n carpeta-ciudadana-dev

# Wait for new pod
kubectl wait --for=condition=Ready pod -l app=gateway -n carpeta-ciudadana-dev --timeout=2m

# Now allowed disruptions = 3 - 2 = 1
# Proceed with drain

# Option 2: Lower minAvailable
kubectl edit pdb gateway -n carpeta-ciudadana-dev
# Change minAvailable: 2 → 1
```

### KEDA worker bloqueado en scale down

**Síntoma**: Transfer worker no puede escalar a 0.

**Causa**: PDB con minAvailable: 1 previene scale to zero.

**Solución**:
```yaml
# Use maxUnavailable instead
spec:
  maxUnavailable: 50%  # Allows 0 replicas
  # NOT: minAvailable: 1
```

---

## 📊 Matriz de PDBs

| Servicio | Replicas (min-max) | minAvailable | Allowed Disruptions |
|----------|-------------------|--------------|---------------------|
| frontend | 2-10 | 1 | 1+ |
| gateway | 3-20 | 2 | 1+ |
| citizen | 2-10 | 1 | 1+ |
| ingestion | 2-15 | 1 | 1+ |
| signature | 2-10 | 1 | 1+ |
| metadata | 2-10 | 1 | 1+ |
| transfer | 2-10 | 1 | 1+ |
| sharing | 2-10 | 1 | 1+ |
| notification | 2-10 | 1 | 1+ |
| read-models | 2-10 | 1 | 1+ |
| mintic-client | 2-10 | 1 | 1+ |
| transfer-worker | 0-30 | maxUnavailable: 50% | Variable |

---

## 🎓 Best Practices

### 1. minAvailable vs maxUnavailable

```yaml
# ✅ For normal services: Use minAvailable
spec:
  minAvailable: 1

# ✅ For KEDA/HPA services: Use maxUnavailable (% or number)
spec:
  maxUnavailable: 50%

# ❌ Don't use both
spec:
  minAvailable: 1
  maxUnavailable: 1  # ERROR: Only one allowed
```

### 2. Set Based on Criticality

```yaml
# Critical services (gateway, signature, transfer)
minAvailable: 2  # or 50%

# Normal services
minAvailable: 1

# KEDA services (scale to zero)
maxUnavailable: 50%
```

### 3. Align with Replicas

```yaml
# ❌ BAD: PDB impossible to satisfy
replicaCount: 1
minAvailable: 2  # Can't have 2 if only 1 total

# ✅ GOOD: PDB satisfiable
replicaCount: 3
minAvailable: 2  # Always 2+ available
```

### 4. Consider HPA

```yaml
# If HPA can scale to 1
autoscaling:
  minReplicas: 1
  maxReplicas: 10

# PDB should allow this
podDisruptionBudget:
  minAvailable: 0  # or maxUnavailable: 1
```

### 5. Production vs Development

```yaml
# Development
podDisruptionBudget:
  enabled: false  # Faster deploys

# Production
podDisruptionBudget:
  enabled: true
  minAvailable: 2  # HA guaranteed
```

---

## 📊 Monitoring

### Check PDB Status

```bash
# List PDBs with status
kubectl get pdb -n carpeta-ciudadana-dev -o wide

# Watch PDBs during drain
watch kubectl get pdb -n carpeta-ciudadana-dev
```

### Prometheus Metrics (kube-state-metrics)

```prometheus
# PDB status
kube_poddisruptionbudget_status_current_healthy{namespace="carpeta-ciudadana-dev"}

# Disruptions allowed
kube_poddisruptionbudget_status_pod_disruptions_allowed{namespace="carpeta-ciudadana-dev"}

# Expected pods
kube_poddisruptionbudget_status_desired_healthy{namespace="carpeta-ciudadana-dev"}
```

### Alerts

```yaml
- alert: PDBViolation
  expr: |
    kube_poddisruptionbudget_status_current_healthy
    < kube_poddisruptionbudget_status_desired_healthy
  for: 5m
  annotations:
    summary: "PDB {{ $labels.poddisruptionbudget }} violated"

- alert: PDBNoDisruptionsAllowed
  expr: kube_poddisruptionbudget_status_pod_disruptions_allowed == 0
  for: 30m
  annotations:
    summary: "PDB {{ $labels.poddisruptionbudget }} blocks all disruptions"
```

---

## 🔄 Escenarios Comunes

### Scenario 1: Cluster Upgrade (AKS)

```bash
# AKS automatically respects PDBs during upgrade
az aks upgrade --name carpeta-aks --kubernetes-version 1.28.0

# Process:
# 1. Create new node pool (v1.28)
# 2. Cordon old nodes
# 3. Drain old nodes (respecting PDBs)
# 4. Delete old node pool

# Expected: Zero downtime ✅
```

### Scenario 2: Node Maintenance

```bash
# Mark node for maintenance
kubectl cordon node-1

# Drain gracefully
kubectl drain node-1 --ignore-daemonsets --delete-emptydir-data

# Perform maintenance
# ...

# Restore node
kubectl uncordon node-1
```

### Scenario 3: Emergency Drain (Override PDB)

```bash
# Emergency: Must drain NOW, ignoring PDBs
kubectl drain node-1 --ignore-daemonsets --delete-emptydir-data --disable-eviction --force

# ⚠️  WARNING: May cause service disruption
# Use only in emergencies (hardware failure, security incident)
```

---

## 📋 Checklist de Implementación

- [x] PDB para frontend
- [x] PDB para gateway (minAvailable: 2)
- [x] PDB para citizen
- [x] PDB para ingestion
- [x] PDB para signature
- [x] PDB para metadata
- [x] PDB para transfer
- [x] PDB para sharing
- [x] PDB para notification
- [x] PDB para read-models
- [x] PDB para mintic-client
- [x] PDB para transfer-worker (maxUnavailable)
- [ ] Test drain scenarios
- [ ] Configure alerts
- [ ] Document in runbook

---

## 🚀 Deployment

```bash
# Deploy with PDBs enabled
helm upgrade --install carpeta-ciudadana deploy/helm/carpeta-ciudadana \
  --set podDisruptionBudget.enabled=true \
  --namespace carpeta-ciudadana-dev

# Verify PDBs created
kubectl get pdb -n carpeta-ciudadana-dev

# Expected: 12 PDBs
```

---

## 📚 Referencias

- [Kubernetes PodDisruptionBudget](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [AKS Cluster Upgrades](https://learn.microsoft.com/en-us/azure/aks/upgrade-cluster)

---

## ✅ Resumen

**12 PodDisruptionBudgets** implementados para garantizar alta disponibilidad:

| Servicio | Strategy | Value | Reason |
|----------|----------|-------|--------|
| frontend | minAvailable | 1 | Normal HA |
| gateway | minAvailable | 2 | Critical service |
| citizen | minAvailable | 1 | Normal HA |
| ingestion | minAvailable | 1 | Normal HA |
| signature | minAvailable | 1 | WORM critical |
| metadata | minAvailable | 1 | Normal HA |
| transfer | minAvailable | 1 | Saga critical |
| sharing | minAvailable | 1 | Normal HA |
| notification | minAvailable | 1 | Normal HA |
| read-models | minAvailable | 1 | Normal HA |
| mintic-client | minAvailable | 1 | Normal HA |
| transfer-worker | maxUnavailable | 50% | KEDA scale-to-zero |

**Principio**: Prevenir downtime durante mantenimiento voluntario.

---

**Generado**: 2025-10-13 03:00  
**Autor**: Manuel Jurado  
**Versión**: 1.0


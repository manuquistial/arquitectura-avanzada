# 🔒 Network Policies - Zero-Trust Networking

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

Documentación de NetworkPolicies para implementar zero-trust networking en Carpeta Ciudadana.

---

## 📋 Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura de Red](#arquitectura-de-red)
3. [Políticas Implementadas](#políticas-implementadas)
4. [Configuración](#configuración)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 Descripción General

Las **NetworkPolicies** implementan **zero-trust networking** en Kubernetes, controlando el tráfico de red a nivel de pod.

### Principios

✅ **Deny by default**: Todo tráfico bloqueado por defecto  
✅ **Allow específico**: Solo tráfico necesario permitido  
✅ **Least privilege**: Mínimos permisos necesarios  
✅ **Defense in depth**: Capa adicional de seguridad  
✅ **Microsegmentation**: Control granular por servicio  

### Beneficios

- 🔒 **Seguridad**: Previene movimiento lateral de atacantes
- 🛡️ **Compliance**: Cumple con zero-trust requirements
- 📊 **Visibility**: Documenta comunicación entre servicios
- 🚫 **Blast radius**: Limita impacto de compromiso
- ✅ **Defense in depth**: Múltiples capas de seguridad

---

## 🏗️ Arquitectura de Red

### Flujo de Tráfico Permitido

```
┌─────────────────────────────────────────────────┐
│  Internet / Users                               │
└────────────────┬────────────────────────────────┘
                 │
                 │ HTTPS
                 ▼
┌─────────────────────────────────────────────────┐
│  Ingress Controller (nginx-ingress)             │
└────────────┬────────────────┬───────────────────┘
             │                │
             │ HTTP           │ HTTP
             ▼                ▼
┌──────────────────┐   ┌──────────────────┐
│  Frontend        │   │  Gateway         │
│  (Next.js)       │   │  (Proxy)         │
└────────┬─────────┘   └──────┬───────────┘
         │                    │
         │ HTTPS              │ HTTP (M2M)
         │                    ▼
         │           ┌─────────────────────┐
         │           │  Internal Services  │
         │           │  ├── citizen        │
         │           │  ├── ingestion      │
         │           │  ├── metadata       │
         │           │  ├── transfer       │
         │           │  ├── signature      │
         │           │  ├── sharing        │
         │           │  ├── notification   │
         │           │  ├── read-models    │
         │           │  └── mintic-client  │
         │           └──────┬──────────────┘
         │                  │
         │                  │ PostgreSQL/ServiceBus/Storage
         │                  ▼
         └─────────────> External Services
                         ├── Azure PostgreSQL
                         ├── Azure Service Bus
                         ├── Azure Blob Storage
                         ├── Azure AD B2C
                         └── MinTIC Hub
```

### Niveles de Acceso

| Servicio | Público | Gateway | Interno | External |
|----------|---------|---------|---------|----------|
| frontend | ✅ | ✅ | ❌ | ✅ (B2C) |
| gateway | ✅ (Ingress) | N/A | ✅ | ✅ (Hub) |
| citizen | ❌ | ✅ | ❌ | ✅ (DB) |
| ingestion | ❌ | ✅ | ❌ | ✅ (Blob) |
| metadata | ❌ | ✅ | ❌ | ✅ (Search) |
| transfer | ❌ | ✅ | ✅ (notification) | ✅ (DB+Bus) |
| signature | ❌ | ✅ | ✅ (mintic) | ✅ (DB+Hub) |
| sharing | ❌ | ✅ | ❌ | ✅ (DB) |
| notification | ❌ | ❌ | ✅ (transfer) | ✅ (SMTP) |
| read-models | ❌ | ✅ | ❌ | ✅ (DB+Bus) |
| mintic-client | ❌ | ❌ | ✅ (signature) | ✅ (Hub) |
| transfer-worker | ❌ | ❌ | ✅ (citizen) | ✅ (DB+Bus) |

---

## 📜 Políticas Implementadas

### 1. Frontend (`networkpolicy-frontend.yaml`)

**Ingress**:
- ✅ Ingress Controller (nginx)
- ✅ Prometheus (observability)
- ✅ Internet (público)

**Egress**:
- ✅ DNS (kube-dns)
- ✅ Gateway (API calls)
- ✅ Azure AD B2C (HTTPS)
- ✅ External CDNs

---

### 2. Gateway (`networkpolicy-gateway.yaml`)

**Ingress**:
- ✅ Ingress Controller
- ✅ Frontend
- ✅ Prometheus

**Egress**:
- ✅ DNS
- ✅ All internal services (citizen, ingestion, metadata, etc.)
- ✅ Redis (rate limiting)
- ✅ External APIs (HTTPS)

**Razón**: Gateway es proxy, necesita acceso a todos los servicios internos.

---

### 3. Citizen (`networkpolicy-citizen.yaml`)

**Ingress**:
- ✅ Gateway only
- ✅ Prometheus

**Egress**:
- ✅ DNS
- ✅ PostgreSQL
- ✅ Service Bus
- ✅ Redis

**Razón**: Servicio interno, solo accesible vía gateway.

---

### 4. Ingestion (`networkpolicy-ingestion.yaml`)

**Ingress**:
- ✅ Gateway only
- ✅ Prometheus

**Egress**:
- ✅ DNS
- ✅ PostgreSQL
- ✅ Azure Storage (HTTPS)
- ✅ Service Bus
- ✅ Redis

---

### 5. Metadata (`networkpolicy-services.yaml`)

**Ingress**:
- ✅ Gateway only
- ✅ Prometheus

**Egress**:
- ✅ DNS
- ✅ PostgreSQL
- ✅ OpenSearch
- ✅ Redis

---

### 6. Transfer (`networkpolicy-services.yaml`)

**Ingress**:
- ✅ Gateway only
- ✅ Prometheus

**Egress**:
- ✅ DNS
- ✅ PostgreSQL
- ✅ Service Bus (HTTPS)
- ✅ Notification service (interno)
- ✅ Redis

**Razón**: Puede llamar a notification para enviar emails.

---

### 7. Signature (`networkpolicy-services.yaml`)

**Ingress**:
- ✅ Gateway only
- ✅ Prometheus

**Egress**:
- ✅ DNS
- ✅ PostgreSQL
- ✅ MinTIC Client (interno)
- ✅ Azure Storage (HTTPS)
- ✅ Redis

**Razón**: Llama a mintic-client para autenticar con Hub.

---

### 8. MinTIC Client (`networkpolicy-services.yaml`)

**Ingress**:
- ✅ Signature only (llamadas M2M)
- ✅ Prometheus

**Egress**:
- ✅ DNS
- ✅ MinTIC Hub (HTTPS)
- ✅ Redis (rate limiting)

**Razón**: Servicio interno dedicado, solo signature lo llama.

---

### 9. Notification (`networkpolicy-services.yaml`)

**Ingress**:
- ✅ Transfer service
- ✅ Transfer Worker
- ✅ Prometheus

**Egress**:
- ✅ DNS
- ✅ PostgreSQL
- ✅ SMTP servers (ports 25, 587)
- ✅ Service Bus (HTTPS)

**Razón**: Consumer de eventos, llamado por transfer/transfer-worker.

---

### 10. Read Models (`networkpolicy-services.yaml`)

**Ingress**:
- ✅ Gateway only
- ✅ Prometheus

**Egress**:
- ✅ DNS
- ✅ PostgreSQL
- ✅ Service Bus (consumer)
- ✅ Redis

**Razón**: CQRS read side, consume eventos.

---

### 11. Sharing (`networkpolicy-services.yaml`)

**Ingress**:
- ✅ Gateway only
- ✅ Prometheus

**Egress**:
- ✅ DNS
- ✅ PostgreSQL
- ✅ Redis

---

### 12. Transfer Worker (`networkpolicy-transfer-worker.yaml`)

**Ingress**:
- ✅ Prometheus only (no HTTP traffic)

**Egress**:
- ✅ DNS
- ✅ PostgreSQL
- ✅ Service Bus (consumer)
- ✅ Redis
- ✅ Citizen service (orchestration)
- ✅ Notification service (emails)

**Razón**: Worker dedicado, no recibe HTTP traffic (solo Service Bus messages).

---

## ⚙️ Configuración

### Habilitar NetworkPolicies en AKS

```bash
# NetworkPolicies requieren network plugin Azure CNI
# Ya configurado en Terraform module AKS

# Verificar soporte
kubectl get networkpolicies -A
```

### Habilitar en Helm

```yaml
# values.yaml
networkPolicies:
  enabled: true
  denyAllByDefault: true
  allowDNS: true
  allowObservability: true
```

### Deploy

```bash
helm upgrade --install carpeta-ciudadana deploy/helm/carpeta-ciudadana \
  --set networkPolicies.enabled=true \
  --namespace carpeta-ciudadana-dev
```

### Verificar Aplicación

```bash
# List all NetworkPolicies
kubectl get networkpolicies -n carpeta-ciudadana-dev

# Describe specific policy
kubectl describe networkpolicy gateway -n carpeta-ciudadana-dev

# Check pod labels
kubectl get pods -n carpeta-ciudadana-dev --show-labels
```

---

## 🧪 Testing

### Test 1: Gateway → Citizen (Should Allow)

```bash
# Get gateway pod
GATEWAY_POD=$(kubectl get pod -n carpeta-ciudadana-dev -l app=gateway -o jsonpath='{.items[0].metadata.name}')

# Try to call citizen service (should work)
kubectl exec -n carpeta-ciudadana-dev $GATEWAY_POD -- \
  curl -s -o /dev/null -w "%{http_code}" \
  http://citizen:8000/health

# Expected: 200
```

### Test 2: Frontend → Citizen (Should Deny)

```bash
# Get frontend pod
FRONTEND_POD=$(kubectl get pod -n carpeta-ciudadana-dev -l app=frontend -o jsonpath='{.items[0].metadata.name}')

# Try to call citizen service directly (should fail)
kubectl exec -n carpeta-ciudadana-dev $FRONTEND_POD -- \
  curl -s -m 5 http://citizen:8000/health || echo "Connection blocked ✅"

# Expected: Connection timeout or blocked
```

### Test 3: Transfer → Notification (Should Allow)

```bash
TRANSFER_POD=$(kubectl get pod -n carpeta-ciudadana-dev -l app=transfer -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n carpeta-ciudadana-dev $TRANSFER_POD -- \
  curl -s http://notification:8010/health

# Expected: 200
```

### Test 4: Citizen → PostgreSQL (Should Allow)

```bash
CITIZEN_POD=$(kubectl get pod -n carpeta-ciudadana-dev -l app=citizen -o jsonpath='{.items[0].metadata.name}')

# Try to connect to PostgreSQL
kubectl exec -n carpeta-ciudadana-dev $CITIZEN_POD -- \
  nc -zv <postgres-host> 5432

# Expected: Connection succeeded
```

### Test 5: Complete Matrix

```bash
# Create test script
cat > test-network-policies.sh << 'EOF'
#!/bin/bash

NAMESPACE="carpeta-ciudadana-dev"

test_connection() {
  local from_app=$1
  local to_service=$2
  local to_port=$3
  local expected=$4
  
  FROM_POD=$(kubectl get pod -n $NAMESPACE -l app=$from_app -o jsonpath='{.items[0].metadata.name}')
  
  if [ -z "$FROM_POD" ]; then
    echo "❌ $from_app pod not found"
    return
  fi
  
  RESULT=$(kubectl exec -n $NAMESPACE $FROM_POD -- \
    curl -s -m 3 -o /dev/null -w "%{http_code}" \
    http://$to_service:$to_port/health 2>&1 || echo "FAIL")
  
  if [[ "$expected" == "allow" && "$RESULT" == "200" ]]; then
    echo "✅ $from_app → $to_service:$to_port (allowed)"
  elif [[ "$expected" == "deny" && "$RESULT" == "FAIL" ]]; then
    echo "✅ $from_app → $to_service:$to_port (denied)"
  else
    echo "❌ $from_app → $to_service:$to_port (unexpected: $RESULT)"
  fi
}

echo "Testing NetworkPolicies..."
echo ""

# Should allow
test_connection "gateway" "citizen" "8000" "allow"
test_connection "gateway" "ingestion" "8000" "allow"
test_connection "transfer" "notification" "8010" "allow"
test_connection "signature" "mintic-client" "8000" "allow"

echo ""

# Should deny
test_connection "frontend" "citizen" "8000" "deny"
test_connection "citizen" "ingestion" "8000" "deny"
test_connection "metadata" "transfer" "8000" "deny"

echo ""
echo "Testing complete!"
EOF

chmod +x test-network-policies.sh
./test-network-policies.sh
```

---

## 🔍 Troubleshooting

### Pods no pueden comunicarse

**Síntoma**: Timeouts entre servicios.

**Debug**:
```bash
# Check NetworkPolicy exists
kubectl get networkpolicies -n carpeta-ciudadana-dev

# Check pod labels match
kubectl get pod gateway-xxx -n carpeta-ciudadana-dev --show-labels

# Verify NetworkPolicy targeting correct pods
kubectl describe networkpolicy gateway -n carpeta-ciudadana-dev
```

**Solución**:
- Verificar labels en podSelector
- Verificar namespace labels
- Verificar ports coinciden

### DNS no funciona

**Síntoma**: Pods no pueden resolver nombres.

**Solución**:
```yaml
# Agregar egress para DNS en TODAS las NetworkPolicies
egress:
- to:
  - namespaceSelector:
      matchLabels:
        name: kube-system
  - podSelector:
      matchLabels:
        k8s-app: kube-dns
  ports:
  - protocol: UDP
    port: 53
```

### Prometheus no puede scrape

**Síntoma**: Métricas no aparecen en Prometheus.

**Solución**:
```yaml
# Agregar ingress desde observability namespace
ingress:
- from:
  - namespaceSelector:
      matchLabels:
        name: observability
  ports:
  - protocol: TCP
    port: 8000  # Metrics port
```

### Conexión a Azure services bloqueada

**Síntoma**: No puede conectar a PostgreSQL, Service Bus, etc.

**Solución**:
```yaml
# Permitir egress HTTPS (443) sin restricción de destino
egress:
- ports:
  - protocol: TCP
    port: 443
```

---

## 📊 Matriz de Conectividad

### Ingress (Quién puede llamar a quién)

| Servicio | Ingress Controller | Gateway | Transfer | Signature | Prometheus |
|----------|-------------------|---------|----------|-----------|------------|
| frontend | ✅ | ✅ | ❌ | ❌ | ✅ |
| gateway | ✅ | N/A | ❌ | ❌ | ✅ |
| citizen | ❌ | ✅ | ❌ | ❌ | ✅ |
| ingestion | ❌ | ✅ | ❌ | ❌ | ✅ |
| metadata | ❌ | ✅ | ❌ | ❌ | ✅ |
| transfer | ❌ | ✅ | ❌ | ❌ | ✅ |
| signature | ❌ | ✅ | ❌ | ❌ | ✅ |
| sharing | ❌ | ✅ | ❌ | ❌ | ✅ |
| notification | ❌ | ❌ | ✅ | ❌ | ✅ |
| read-models | ❌ | ✅ | ❌ | ❌ | ✅ |
| mintic-client | ❌ | ❌ | ❌ | ✅ | ✅ |
| transfer-worker | ❌ | ❌ | ❌ | ❌ | ✅ |

### Egress (A qué pueden conectar)

| Servicio | PostgreSQL | Service Bus | Redis | Azure Storage | MinTIC Hub | OpenSearch |
|----------|------------|-------------|-------|---------------|------------|------------|
| gateway | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| citizen | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| ingestion | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| metadata | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ |
| transfer | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| signature | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| sharing | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| notification | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| read-models | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| mintic-client | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| transfer-worker | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 🎓 Best Practices

### 1. Deny All by Default

```yaml
# Default deny policy (applied first)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}  # Apply to all pods
  policyTypes:
  - Ingress
  - Egress
  # No rules = deny all
```

### 2. Always Allow DNS

```yaml
# Every NetworkPolicy should allow DNS
egress:
- to:
  - namespaceSelector:
      matchLabels:
        name: kube-system
  - podSelector:
      matchLabels:
        k8s-app: kube-dns
  ports:
  - protocol: UDP
    port: 53
```

### 3. Label Namespaces

```bash
# Label namespaces for NetworkPolicy selectors
kubectl label namespace kube-system name=kube-system
kubectl label namespace ingress-nginx name=ingress-nginx
kubectl label namespace observability name=observability
kubectl label namespace search name=search
```

### 4. Use Specific Ports

```yaml
# ❌ Too permissive
egress:
- to:
  - podSelector: {}

# ✅ Specific ports
egress:
- to:
  - podSelector:
      matchLabels:
        app: citizen
  ports:
  - protocol: TCP
    port: 8000
```

### 5. Document Intent

```yaml
metadata:
  annotations:
    description: "Allows gateway to proxy to citizen service"
```

---

## 📋 Checklist de Implementación

- [x] NetworkPolicy para frontend
- [x] NetworkPolicy para gateway
- [x] NetworkPolicy para citizen
- [x] NetworkPolicy para ingestion
- [x] NetworkPolicy para metadata
- [x] NetworkPolicy para transfer
- [x] NetworkPolicy para signature
- [x] NetworkPolicy para sharing
- [x] NetworkPolicy para notification
- [x] NetworkPolicy para read-models
- [x] NetworkPolicy para mintic-client
- [x] NetworkPolicy para transfer-worker
- [ ] Label all namespaces
- [ ] Test matrix completo
- [ ] Monitor denials (iptables logs)
- [ ] Alertas para blocked connections

---

## 🚀 Deployment

### Paso 1: Label Namespaces

```bash
kubectl label namespace kube-system name=kube-system --overwrite
kubectl label namespace ingress-nginx name=ingress-nginx --overwrite
kubectl label namespace observability name=observability --overwrite
kubectl label namespace search name=search --overwrite
kubectl label namespace carpeta-ciudadana-dev name=carpeta-ciudadana-dev --overwrite
```

### Paso 2: Deploy NetworkPolicies

```bash
helm upgrade --install carpeta-ciudadana deploy/helm/carpeta-ciudadana \
  --set networkPolicies.enabled=true \
  --namespace carpeta-ciudadana-dev
```

### Paso 3: Verificar

```bash
# List policies
kubectl get networkpolicies -n carpeta-ciudadana-dev

# Count policies
kubectl get networkpolicies -n carpeta-ciudadana-dev --no-headers | wc -l

# Expected: 12 policies
```

### Paso 4: Test Connectivity

```bash
# Run test matrix
./test-network-policies.sh

# Expected: All tests pass ✅
```

---

## 📚 Referencias

- [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Azure CNI NetworkPolicy](https://learn.microsoft.com/en-us/azure/aks/use-network-policies)
- [Calico NetworkPolicy](https://docs.tigera.io/calico/latest/network-policy/)

---

## ✅ Resumen

**12 NetworkPolicies** implementadas para **zero-trust networking**:

1. ✅ Frontend - Público, llama gateway
2. ✅ Gateway - Proxy a todos los servicios internos
3. ✅ Citizen - Solo gateway, DB access
4. ✅ Ingestion - Solo gateway, Storage access
5. ✅ Metadata - Solo gateway, OpenSearch access
6. ✅ Transfer - Solo gateway, puede llamar notification
7. ✅ Signature - Solo gateway, llama mintic-client
8. ✅ Sharing - Solo gateway, DB access
9. ✅ Notification - Transfer/worker, SMTP egress
10. ✅ Read Models - Solo gateway, consumer
11. ✅ MinTIC Client - Solo signature, Hub access
12. ✅ Transfer Worker - Consumer, orchestration

**Principio**: Deny all by default, allow específico.

---

**Generado**: 2025-10-13 02:30  
**Autor**: Manuel Jurado  
**Versión**: 1.0


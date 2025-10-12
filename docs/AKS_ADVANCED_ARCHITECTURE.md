# 🏗️ AKS Advanced Architecture - Multi-Zone, Multi-Nodepool

**Fecha**: 2025-10-13  
**Versión**: 2.0  
**Autor**: Manuel Jurado

Documentación de la arquitectura avanzada de AKS con zonal deployment, nodepools optimizados y configuraciones de producción.

---

## 📋 Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura Multi-Zone](#arquitectura-multi-zone)
3. [Nodepools Strategy](#nodepools-strategy)
4. [Network Configuration](#network-configuration)
5. [High Availability](#high-availability)
6. [Cost Optimization](#cost-optimization)
7. [Deployment](#deployment)
8. [Maintenance](#maintenance)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Descripción General

La arquitectura avanzada de AKS implementa:

✅ **Multi-Zone Deployment**: 3 availability zones para HA  
✅ **3 Nodepools**: System, User, Spot (optimización costo/performance)  
✅ **Azure CNI**: Soporte nativo para NetworkPolicies  
✅ **Workload Identity**: Integración segura con Azure services  
✅ **Cluster Autoscaler**: Scaling automático de nodes  
✅ **Maintenance Windows**: Upgrades controlados  

---

## 🏗️ Arquitectura Multi-Zone

### Distribución en Availability Zones

```
┌─────────────────────────────────────────────────────┐
│  Azure Region (e.g., North Central US)              │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Zone 1    │  │   Zone 2    │  │   Zone 3    │ │
│  │             │  │             │  │             │ │
│  │ System Node │  │ System Node │  │ System Node │ │
│  │  (controller│  │  (backup)   │  │  (backup)   │ │
│  │             │  │             │  │             │ │
│  │ User Node 1 │  │ User Node 2 │  │ User Node 3 │ │
│  │  (apps)     │  │  (apps)     │  │  (apps)     │ │
│  │             │  │             │  │             │ │
│  │ Spot Node 1 │  │ Spot Node 2 │  │ Spot Node 3 │ │
│  │  (workers)  │  │  (workers)  │  │  (workers)  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Beneficios Multi-Zone

✅ **99.99% SLA**: vs 99.95% single-zone  
✅ **Zone failure resilience**: Cluster sobrevive fallo de zona  
✅ **Automatic pod distribution**: K8s distribuye pods automáticamente  
✅ **No application changes**: Transparente para apps  

### Pod Distribution Example

```
gateway deployment (3 replicas):
- gateway-pod-1 → Zone 1
- gateway-pod-2 → Zone 2
- gateway-pod-3 → Zone 3

If Zone 1 fails:
- gateway-pod-1 → LOST
- gateway-pod-2 → RUNNING (Zone 2) ✅
- gateway-pod-3 → RUNNING (Zone 3) ✅
- New pod scheduled → Zone 2 or 3
```

---

## 🔧 Nodepools Strategy

### 1. System Nodepool (default)

**Purpose**: K8s control plane components only

**Characteristics**:
- **VM Size**: `Standard_B2s` (2 vCPU, 4GB RAM)
- **Count**: 1-3 nodes (autoscaling)
- **Zones**: 1, 2, 3
- **Taint**: `CriticalAddonsOnly=true:NoSchedule`
- **OS Disk**: Ephemeral (faster, cheaper)

**Workloads**:
- kube-proxy
- kube-dns (CoreDNS)
- metrics-server
- cluster-autoscaler
- azure-cni
- azure-cloud-node-manager

**Why separate**:
- Prevents user workloads from competing for resources
- Guarantees control plane stability
- Smaller, cheaper nodes for system components

---

### 2. User Nodepool

**Purpose**: Application workloads (frontend, gateway, services)

**Characteristics**:
- **VM Size**: `Standard_D2s_v3` (2 vCPU, 8GB RAM)
- **Count**: 2-10 nodes (autoscaling)
- **Zones**: 1, 2, 3
- **Labels**: `workload=applications`
- **OS Disk**: Ephemeral SSD

**Workloads**:
- frontend (Next.js)
- gateway (proxy)
- citizen, ingestion, metadata, etc.
- All user-facing services

**Why D-series**:
- General purpose, balanced CPU/Memory
- SSD storage (better I/O)
- Good for web workloads

---

### 3. Spot Nodepool

**Purpose**: KEDA workers (transfer-worker, batch jobs)

**Characteristics**:
- **VM Size**: `Standard_D2s_v3` (same as user)
- **Count**: 0-10 nodes (can scale to zero)
- **Priority**: Spot (70-90% cheaper)
- **Eviction Policy**: Delete
- **Zones**: 1, 2, 3
- **Taint**: `kubernetes.azure.com/scalesetpriority=spot:NoSchedule`
- **Labels**: `workload=workers`, `scalesetpriority=spot`

**Workloads**:
- transfer-worker (KEDA)
- Batch jobs
- Non-critical background tasks

**Cost Savings**:
```
Regular: $70/month per node
Spot:    $20/month per node
Savings: 70% ✅
```

**Trade-offs**:
- ⚠️ Can be preempted with 30s notice
- ✅ KEDA re-schedules automatically
- ✅ Stateless workloads ideal
- ✅ Tolerations required

---

## 🌐 Network Configuration

### Azure CNI (vs Kubenet)

```yaml
network_profile:
  network_plugin: "azure"  # Azure CNI
  network_policy: "azure"  # NetworkPolicy support
```

**Beneficios de Azure CNI**:
- ✅ Pods get IP from VNet subnet
- ✅ Direct pod-to-pod communication
- ✅ NetworkPolicy support nativo
- ✅ Better for hybrid scenarios
- ✅ No NAT overhead

**Consideraciones**:
- ⚠️ Consume más IPs del subnet
- ⚠️ Subnet debe ser suficientemente grande
- ✅ Subnet sizing: nodes * max_pods_per_node

### Subnet Sizing

```
Subnet: 10.0.1.0/24 (256 IPs)

System nodes: 3 * 30 pods = 90 IPs
User nodes:  10 * 30 pods = 300 IPs (⚠️ Necesita /23)
Spot nodes:  10 * 30 pods = 300 IPs

Recommended: /22 (1024 IPs) or /21 (2048 IPs)
```

### Service CIDR

```
service_cidr = "10.1.0.0/16"  # Internal K8s services
dns_service_ip = "10.1.0.10"  # CoreDNS

# Must NOT overlap with:
# - VNet CIDR (10.0.0.0/16)
# - Pod CIDR (10.0.1.0/24)
```

---

## 🛡️ High Availability

### SLA Tiers

| Configuration | SLA | Cost | Recommendation |
|---------------|-----|------|----------------|
| Single zone + Free tier | 99.5% | $0 | Dev only |
| Multi-zone + Free tier | 99.9% | $0 | Testing |
| Single zone + Standard tier | 99.95% | $73/month | Staging |
| Multi-zone + Standard tier | 99.99% | $73/month | Production ✅ |

### HA Components

```yaml
# System nodes
system_node_min: 1
system_node_max: 3
zones: ["1", "2", "3"]

# User nodes
user_node_min: 2
user_node_max: 10
zones: ["1", "2", "3"]

# Result:
# - Minimum 3 nodes total (1 system + 2 user)
# - Distributed across 3 zones
# - Survives 1 zone failure ✅
```

---

## 💰 Cost Optimization

### Nodepool Cost Comparison

**Development** (minimal):
```
System: 1 x B2s     = $30/month
User:   2 x D2s_v3  = $140/month
Spot:   0 nodes     = $0/month (scales to zero)
Total: ~$170/month
```

**Production** (optimized):
```
System: 3 x B2s     = $90/month  (multi-zone)
User:   6 x D2s_v3  = $420/month (2 per zone)
Spot:   5 x D2s_v3  = $100/month (spot pricing)
Total: ~$610/month
```

**Production** (standard, no optimization):
```
Regular: 15 x D2s_v3 = $1,050/month
Savings with spot: ~$440/month (42%) ✅
```

### Cost Optimization Strategies

1. **Spot instances for workers**: 70% savings
2. **B-series for system**: Cheaper, sufficient for controllers
3. **Cluster autoscaler**: Pay only for used capacity
4. **KEDA scale to zero**: No cost when idle
5. **Ephemeral OS disks**: No storage cost

---

## 🚀 Deployment

### terraform.tfvars Example

```hcl
# AKS Advanced Configuration
aks_kubernetes_version = "1.28"
aks_automatic_upgrade  = "patch"
aks_sku_tier           = "Standard"  # Production
aks_private_cluster    = false  # true for production

# Availability zones
aks_availability_zones = ["1", "2", "3"]

# System nodepool
aks_system_vm_size  = "Standard_B2s"
aks_system_node_min = 1
aks_system_node_max = 3

# User nodepool
aks_user_vm_size  = "Standard_D2s_v3"
aks_user_node_min = 2
aks_user_node_max = 10

# Spot nodepool
aks_enable_spot    = true
aks_spot_vm_size   = "Standard_D2s_v3"
aks_spot_node_min  = 0
aks_spot_node_max  = 10
aks_spot_max_price = -1  # Up to regular price

# Maintenance window
aks_maintenance_day   = "Sunday"
aks_maintenance_hours = [2, 3, 4]  # 2am-5am
```

### Apply

```bash
cd infra/terraform

terraform init
terraform plan
terraform apply

# Verify nodepools
az aks nodepool list \
  --cluster-name carpeta-ciudadana-dev \
  --resource-group carpeta-ciudadana-dev-rg \
  --output table
```

---

## 🔄 Maintenance & Upgrades

### Automatic Upgrades

```hcl
automatic_channel_upgrade = "patch"
```

**Channels**:
- `none`: Manual upgrades only
- `patch`: Auto-upgrade to latest patch (e.g., 1.28.3 → 1.28.5)
- `stable`: Auto-upgrade to N-1 minor (e.g., 1.27 → 1.28)
- `rapid`: Auto-upgrade to latest minor
- `node-image`: OS updates only

**Recommendation**: `patch` for production (security fixes)

### Maintenance Window

```hcl
maintenance_window {
  allowed {
    day   = "Sunday"
    hours = [2, 3, 4]  # 2am-5am
  }
}
```

**Comportamiento**:
- Upgrades solo durante ventana
- PDBs respetados
- Gradual node drain
- Zero downtime ✅

### Manual Upgrade

```bash
# Check available versions
az aks get-upgrades \
  --name carpeta-ciudadana-dev \
  --resource-group carpeta-ciudadana-dev-rg

# Upgrade cluster
az aks upgrade \
  --name carpeta-ciudadana-dev \
  --resource-group carpeta-ciudadana-dev-rg \
  --kubernetes-version 1.29.0

# Upgrade specific nodepool
az aks nodepool upgrade \
  --cluster-name carpeta-ciudadana-dev \
  --name user \
  --resource-group carpeta-ciudadana-dev-rg \
  --kubernetes-version 1.29.0
```

---

## 📊 Workload Placement

### Nodepool Selection

```yaml
# System pods (automatic)
# - No selector needed
# - Automatically scheduled to system pool

# User pods (default)
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      # No nodeSelector = goes to user pool
      # (system pool is tainted)

# Spot pods (KEDA workers)
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      nodeSelector:
        workload: "workers"
        kubernetes.azure.com/scalesetpriority: "spot"
      tolerations:
      - key: "kubernetes.azure.com/scalesetpriority"
        operator: "Equal"
        value: "spot"
        effect: "NoSchedule"
```

### Zone Anti-Affinity

```yaml
# Spread pods across zones (automatic with PDBs + multi-zone)
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: gateway
```

---

## 🧪 Testing

### Test 1: Verify Nodepools

```bash
# List nodepools
kubectl get nodes -L agentpool,topology.kubernetes.io/zone,kubernetes.azure.com/scalesetpriority

# Expected output:
# NAME                STATUS   AGENTPOOL   ZONE   PRIORITY
# aks-system-xxx      Ready    system      1      -
# aks-user-xxx        Ready    user        1      -
# aks-user-yyy        Ready    user        2      -
# aks-spot-xxx        Ready    spot        1      spot
```

### Test 2: Verify Pod Distribution

```bash
# Check gateway pods distribution
kubectl get pods -n carpeta-ciudadana-dev -l app=gateway -o wide

# Should see pods across different zones
```

### Test 3: Zone Failure Simulation

```bash
# Cordon all nodes in Zone 1
kubectl get nodes -l topology.kubernetes.io/zone=1 -o name | \
  xargs -I {} kubectl cordon {}

# Check pods still running
kubectl get pods -n carpeta-ciudadana-dev -o wide

# Expected: Pods on Zone 2 and 3 still running ✅

# Uncordon
kubectl get nodes -l topology.kubernetes.io/zone=1 -o name | \
  xargs -I {} kubectl uncordon {}
```

### Test 4: Spot Node Preemption

```bash
# Check spot nodes
kubectl get nodes -l kubernetes.azure.com/scalesetpriority=spot

# Simulate preemption (drain spot node)
kubectl drain aks-spot-xxx --ignore-daemonsets --delete-emptydir-data

# Check KEDA re-schedules worker
kubectl get pods -n carpeta-ciudadana-dev -l app=transfer-worker -o wide

# Expected: Worker rescheduled to another spot node ✅
```

---

## 🔍 Troubleshooting

### Pods no se distribuyen en zones

**Síntoma**: Todos los pods en Zone 1.

**Causa**: Anti-affinity no configurada o PDB insuficiente.

**Solución**:
```yaml
# Add topologySpreadConstraints
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway  # or DoNotSchedule
```

### Spot nodes no escalan

**Síntoma**: Worker pods pending, spot nodes en 0.

**Debug**:
```bash
# Check cluster autoscaler logs
kubectl logs -n kube-system -l app=cluster-autoscaler

# Check pending pods
kubectl describe pod -n carpeta-ciudadana-dev <pending-pod>

# Check node pool
az aks nodepool show \
  --cluster-name carpeta-ciudadana-dev \
  --name spot \
  --resource-group carpeta-ciudadana-dev-rg
```

### System pool saturado

**Síntoma**: System pods evicted, cluster unstable.

**Causa**: Too many system pods, insufficient resources.

**Solución**:
```hcl
# Increase system pool
aks_system_node_min = 2  # Instead of 1
aks_system_vm_size  = "Standard_B4ms"  # Larger VM
```

---

## 📋 Checklist de Migración

### From Single Pool to Multi-Pool

- [x] Backup cluster config
```bash
kubectl get all --all-namespaces -o yaml > cluster-backup.yaml
```

- [x] Update Terraform
```hcl
# Add user and spot nodepools
```

- [x] Apply Terraform
```bash
terraform apply
```

- [x] Verify nodepools
```bash
kubectl get nodes -L agentpool
```

- [x] Label system nodepool
```bash
# Already done by Terraform
```

- [x] Migrate workloads
```bash
# Workloads automatically rescheduled to user pool
# (system pool tainted)
```

- [ ] Test zone failure
```bash
# Cordon zone, verify services
```

- [ ] Monitor for 24h
```bash
# Check stability
```

- [ ] Cleanup old configuration
```bash
# Remove old variables if needed
```

---

## 📊 Monitoring

### Prometheus Metrics

```prometheus
# Nodes per pool
kube_node_labels{label_agentpool="system"} 1
kube_node_labels{label_agentpool="user"} 6
kube_node_labels{label_agentpool="spot"} 3

# Nodes per zone
kube_node_labels{label_topology_kubernetes_io_zone="1"} 3
kube_node_labels{label_topology_kubernetes_io_zone="2"} 4
kube_node_labels{label_topology_kubernetes_io_zone="3"} 3

# Spot nodes
kube_node_labels{label_kubernetes_azure_com_scalesetpriority="spot"} 3
```

### Alerts

```yaml
- alert: ZoneImbalance
  expr: |
    count by (zone) (kube_node_info)
    / count (kube_node_info) * 100 > 50
  annotations:
    summary: "More than 50% nodes in single zone"

- alert: SpotNodePreemptionRate
  expr: rate(kube_node_evictions{nodepool="spot"}[1h]) > 0.1
  annotations:
    summary: "High spot node preemption rate"
```

---

## 📚 Referencias

- [AKS Availability Zones](https://learn.microsoft.com/en-us/azure/aks/availability-zones)
- [AKS Node Pools](https://learn.microsoft.com/en-us/azure/aks/use-multiple-node-pools)
- [Azure Spot VMs](https://learn.microsoft.com/en-us/azure/virtual-machines/spot-vms)
- [Azure CNI](https://learn.microsoft.com/en-us/azure/aks/configure-azure-cni)

---

## ✅ Resumen

**Arquitectura implementada**:

- ✅ **3 Nodepools**: System, User, Spot
- ✅ **3 Availability Zones**: Multi-AZ HA
- ✅ **Azure CNI**: NetworkPolicy support
- ✅ **Workload Identity**: OIDC issuer enabled
- ✅ **Cluster Autoscaler**: Automatic scaling
- ✅ **Spot instances**: 70% cost savings
- ✅ **Maintenance Windows**: Controlled upgrades
- ✅ **SKU Tier**: Configurable (Free/Standard)

**Beneficios**:
- 🛡️ 99.99% SLA (multi-zone + Standard tier)
- 💰 70% savings en workers (spot)
- 🚀 Auto-scaling (0-30 nodes)
- ⚡ Zero downtime upgrades
- 🔒 Network isolation (Azure CNI)

---

**Generado**: 2025-10-13 03:15  
**Autor**: Manuel Jurado  
**Versión**: 2.0


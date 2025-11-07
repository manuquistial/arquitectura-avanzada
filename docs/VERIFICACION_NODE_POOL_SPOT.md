# Verificación: Node Pool Spot - Configuración

## 📋 Resumen

Este documento verifica si el node pool Spot está correctamente configurado en Terraform y Azure.

---

## 🔍 Configuración Esperada

### Configuración en Terraform:

```terraform
# Spot node pool - For KEDA workers (70% cost savings)
resource "azurerm_kubernetes_cluster_node_pool" "spot" {
  name                  = "spot"
  priority              = "Spot"
  eviction_policy       = "Delete"
  spot_max_price        = -1  # Pagar hasta precio regular
  node_count            = 1   # Mínimo 1 nodo (cambió de 0 a 1)
  
  node_labels = {
    "nodepool"                              = "spot"
    "workload"                              = "workers"
    "kubernetes.azure.com/scalesetpriority" = "spot"
  }
  
  node_taints = [
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"
  ]
}
```

### Valores Esperados:

| Parámetro | Valor Esperado | Descripción |
|-----------|---------------|-------------|
| **priority** | `Spot` | Prioridad Spot para ahorro de costos |
| **eviction_policy** | `Delete` | Eliminar nodo si Azure lo requiere |
| **spot_max_price** | `-1` | Pagar hasta precio regular |
| **node_count** | `1` | Mínimo 1 nodo (para disponibilidad) |
| **vm_size** | `Standard_B2ms` | Tamaño de VM |
| **node_labels** | `nodepool=spot, workload=workers` | Labels para identificación |
| **node_taints** | `spot:NoSchedule` | Taints para workloads tolerantes |

---

## ✅ Verificación de Configuración

### 1. Estado en Azure

**Comando:**
```bash
az aks nodepool show --resource-group carpeta-ciudadana-production-rg \
  --cluster-name carpeta-ciudadana-production --name spot
```

**Verificar:**
- ✅ `priority: Spot`
- ✅ `evictionPolicy: Delete`
- ✅ `spotMaxPrice: -1`
- ✅ `count: 1` (o mínimo el esperado)
- ✅ `labels: nodepool=spot, workload=workers`
- ✅ `taints: kubernetes.azure.com/scalesetpriority=spot:NoSchedule`

### 2. Estado en Terraform

**Comando:**
```bash
terraform state show 'module.aks.azurerm_kubernetes_cluster_node_pool.spot[0]'
```

**Verificar:**
- ✅ `priority = "Spot"`
- ✅ `eviction_policy = "Delete"`
- ✅ `spot_max_price = -1`
- ✅ `node_count = 1` (o el valor esperado)
- ✅ `node_labels` con `nodepool = "spot"` y `workload = "workers"`
- ✅ `node_taints` con `spot:NoSchedule`

### 3. Nodos en Kubernetes

**Comando:**
```bash
kubectl get nodes -l nodepool=spot
```

**Verificar:**
- ✅ Nodos Spot disponibles
- ✅ Nodos en estado `Ready`
- ✅ Labels correctos (`nodepool=spot`)

---

## ⚠️ Problemas Comunes

### Problema 1: `node_count = 0` en Azure

**Síntoma:**
- Azure muestra `count: 0`
- Terraform muestra `node_count = 1`
- No hay nodos Spot disponibles

**Causa:**
- Terraform no aplicó el cambio correctamente
- Azure no actualizó el `node_count` después del cambio

**Solución:**
```bash
# Opción 1: Aplicar Terraform nuevamente
terraform apply -target=module.aks.azurerm_kubernetes_cluster_node_pool.spot

# Opción 2: Actualizar directamente en Azure (y luego sync Terraform)
az aks nodepool scale \
  --resource-group carpeta-ciudadana-production-rg \
  --cluster-name carpeta-ciudadana-production \
  --name spot \
  --node-count 1
```

### Problema 2: Nodos Spot no aparecen en Kubernetes

**Síntoma:**
- Azure muestra `count: 1`
- Kubernetes no muestra nodos Spot
- `kubectl get nodes -l nodepool=spot` retorna vacío

**Causa:**
- Nodo aún creándose (puede tardar 2-5 minutos)
- Nodo fue evictado
- Problema de conectividad

**Solución:**
```bash
# Esperar a que el nodo esté listo
kubectl wait --for=condition=Ready nodes -l nodepool=spot --timeout=5m

# Verificar estado en Azure
az aks nodepool show \
  --resource-group carpeta-ciudadana-production-rg \
  --cluster-name carpeta-ciudadana-production \
  --name spot \
  --query '{count:count,provisioningState:provisioningState,powerState:powerState.code}'
```

### Problema 3: Configuración incorrecta

**Síntoma:**
- `priority != "Spot"`
- `eviction_policy != "Delete"`
- `spot_max_price != -1`

**Solución:**
- Corregir en Terraform y aplicar
- Verificar que no haya valores hardcodeados incorrectos

---

## 🔧 Checklist de Verificación

### Configuración Terraform:
- [ ] `priority = "Spot"`
- [ ] `eviction_policy = "Delete"`
- [ ] `spot_max_price = -1`
- [ ] `node_count = 1` (o el mínimo deseado)
- [ ] `node_labels` correctos
- [ ] `node_taints` correctos

### Estado en Azure:
- [ ] `priority: Spot`
- [ ] `evictionPolicy: Delete`
- [ ] `spotMaxPrice: -1`
- [ ] `count: 1` (o el mínimo deseado)
- [ ] `labels` correctos
- [ ] `taints` correctos

### Estado en Kubernetes:
- [ ] Nodos Spot disponibles (`kubectl get nodes -l nodepool=spot`)
- [ ] Nodos en estado `Ready`
- [ ] Labels correctos en nodos

### Sincronización:
- [ ] Terraform state coincide con Azure
- [ ] No hay drift entre configuración y realidad
- [ ] Cambios aplicados correctamente

---

## 📊 Comandos de Verificación

### Verificar en Azure:
```bash
az aks nodepool show \
  --resource-group carpeta-ciudadana-production-rg \
  --cluster-name carpeta-ciudadana-production \
  --name spot \
  --query '{name,count,priority:scaleSetPriority,evictionPolicy:scaleSetEvictionPolicy,maxPrice:spotMaxPrice,labels:nodeLabels,taints:nodeTaints,provisioningState,powerState:powerState.code}' \
  -o json
```

### Verificar en Terraform:
```bash
cd infra/terraform/layers/platform
terraform state show 'module.aks.azurerm_kubernetes_cluster_node_pool.spot[0]'
```

### Verificar en Kubernetes:
```bash
# Listar nodos Spot
kubectl get nodes -l nodepool=spot

# Ver detalles de nodo Spot
kubectl describe node <spot-node-name>

# Verificar labels y taints
kubectl get nodes -l nodepool=spot --show-labels
kubectl describe node <spot-node-name> | grep Taints
```

### Verificar plan de Terraform:
```bash
cd infra/terraform/layers/platform
terraform plan -target=module.aks.azurerm_kubernetes_cluster_node_pool.spot
```

---

## 🎯 Resultados Esperados

### Configuración Correcta:

```json
{
  "name": "spot",
  "count": 1,
  "priority": "Spot",
  "evictionPolicy": "Delete",
  "spotMaxPrice": -1,
  "labels": {
    "nodepool": "spot",
    "workload": "workers",
    "kubernetes.azure.com/scalesetpriority": "spot"
  },
  "taints": [
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"
  ],
  "provisioningState": "Succeeded",
  "powerState": "Running"
}
```

### Nodos en Kubernetes:

```bash
$ kubectl get nodes -l nodepool=spot
NAME                             STATUS   ROLES    AGE   VERSION
aks-spot-13429841-vmss000000    Ready    <none>   5m    v1.31.11
```

---

## 📝 Notas Importantes

1. **Creación de Nodos**: Puede tardar 2-5 minutos después de cambiar `node_count`
2. **Evictions**: Los nodos Spot pueden ser eliminados por Azure en cualquier momento
3. **Sincronización**: Verificar que Terraform state esté sincronizado con Azure
4. **Taints**: Los pods deben tener tolerations para ejecutarse en Spot
5. **Labels**: Los nodos deben tener `nodepool=spot` para que el scheduler los identifique










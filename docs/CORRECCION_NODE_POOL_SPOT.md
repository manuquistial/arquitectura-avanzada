# Corrección: Node Pool Spot - Problemas y Soluciones

## 📋 Resumen

El node pool Spot tiene **problemas de configuración** que impiden que funcione correctamente. Este documento identifica los problemas y proporciona soluciones.

---

## ❌ Problemas Identificados

### Problema 1: `priority: null` en Azure

**Síntoma:**
- Azure muestra `priority: null`
- Debería mostrar `priority: Spot`

**Causa:**
- Terraform no aplicó correctamente el cambio
- El node pool puede haber sido creado antes de la configuración Spot

**Impacto:**
- El node pool no tiene prioridad Spot configurada
- No se obtienen los beneficios de Spot (70% ahorro)

### Problema 2: `eviction_policy: null` en Azure

**Síntoma:**
- Azure muestra `evictionPolicy: null`
- Debería mostrar `evictionPolicy: Delete`

**Causa:**
- Similar a problema 1
- Terraform no aplicó la configuración correctamente

**Impacto:**
- Comportamiento de eviction no definido

### Problema 3: `node_count: 0` en Azure y Terraform

**Síntoma:**
- Azure muestra `count: 0`
- Terraform state muestra `node_count = 0`
- Debería ser `1` (según `aks_spot_node_min = 1`)

**Causa:**
- El cambio en `variables.tf` (default: 1) no se aplicó
- Terraform state tiene `0` y no detecta el cambio

**Impacto:**
- No hay nodos Spot disponibles
- Los pods no pueden moverse a Spot

### Problema 4: Paradoja - Nodo Spot en Kubernetes

**Síntoma:**
- Hay 1 nodo Spot visible en Kubernetes
- Azure muestra `count: 0`
- Terraform state muestra `node_count = 0`

**Causa:**
- El nodo puede haber sido creado manualmente o por otro proceso
- Hay un desajuste entre Azure y Kubernetes

**Impacto:**
- Estado inconsistente
- Dificultad para gestionar

---

## ✅ Configuración Correcta Esperada

### En Terraform:

```terraform
resource "azurerm_kubernetes_cluster_node_pool" "spot" {
  name                  = "spot"
  priority              = "Spot"        # ✅ Correcto en código
  eviction_policy       = "Delete"     # ✅ Correcto en código
  spot_max_price        = -1           # ✅ Correcto en código
  node_count            = 1            # ✅ Debería ser 1 (código dice 1)
  
  node_labels = {
    "nodepool" = "spot"
    "workload" = "workers"
    "kubernetes.azure.com/scalesetpriority" = "spot"
  }
  
  node_taints = [
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"
  ]
}
```

### En Azure (Esperado):

```json
{
  "name": "spot",
  "count": 1,
  "scaleSetPriority": "Spot",
  "scaleSetEvictionPolicy": "Delete",
  "spotMaxPrice": -1,
  "labels": {
    "nodepool": "spot",
    "workload": "workers",
    "kubernetes.azure.com/scalesetpriority": "spot"
  },
  "taints": [
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"
  ]
}
```

---

## 🔧 Soluciones

### Solución 1: Aplicar Terraform con Target Específico

```bash
cd infra/terraform/layers/platform
terraform apply -target=module.aks.azurerm_kubernetes_cluster_node_pool.spot
```

**Esto debería:**
- Actualizar `priority` a `Spot`
- Actualizar `eviction_policy` a `Delete`
- Actualizar `node_count` a `1`

### Solución 2: Actualizar Directamente en Azure (Si Terraform falla)

```bash
# Actualizar priority y eviction policy (si es posible)
az aks nodepool update \
  --resource-group carpeta-ciudadana-production-rg \
  --cluster-name carpeta-ciudadana-production \
  --name spot \
  --node-count 1
```

**Nota**: Algunos atributos como `priority` y `eviction_policy` pueden requerir recrear el node pool.

### Solución 3: Recrear el Node Pool Spot (Si es necesario)

Si los atributos `priority` y `eviction_policy` no se pueden actualizar, recrear el node pool:

```bash
# 1. Eliminar node pool Spot
az aks nodepool delete \
  --resource-group carpeta-ciudadana-production-rg \
  --cluster-name carpeta-ciudadana-production \
  --name spot

# 2. Aplicar Terraform para recrear
cd infra/terraform/layers/platform
terraform apply -target=module.aks.azurerm_kubernetes_cluster_node_pool.spot
```

**Advertencia**: Esto eliminará los pods ejecutándose en Spot (pero se reschedulean automáticamente).

---

## 📊 Verificación de Estado

### Comando de Verificación:

```bash
# Verificar en Azure
az aks nodepool show \
  --resource-group carpeta-ciudadana-production-rg \
  --cluster-name carpeta-ciudadana-production \
  --name spot \
  -o json | jq '{name,count,priority:scaleSetPriority,evictionPolicy:scaleSetEvictionPolicy,maxPrice:spotMaxPrice}'

# Verificar en Terraform
cd infra/terraform/layers/platform
terraform state show 'module.aks.azurerm_kubernetes_cluster_node_pool.spot[0]' | grep -E "node_count|priority|eviction_policy|spot_max_price"

# Verificar en Kubernetes
kubectl get nodes -l nodepool=spot
```

### Estado Esperado Después de Corrección:

```json
{
  "name": "spot",
  "count": 1,
  "priority": "Spot",
  "evictionPolicy": "Delete",
  "maxPrice": -1
}
```

---

## 🎯 Checklist de Verificación

### Antes de Corregir:
- [ ] Identificar problemas específicos
- [ ] Verificar estado actual en Azure
- [ ] Verificar estado actual en Terraform
- [ ] Verificar nodos en Kubernetes

### Después de Corregir:
- [ ] `priority: Spot` en Azure
- [ ] `evictionPolicy: Delete` en Azure
- [ ] `count: 1` en Azure
- [ ] `node_count = 1` en Terraform
- [ ] Nodos Spot disponibles en Kubernetes
- [ ] Pods pueden moverse a Spot

---

## ⚠️ Notas Importantes

1. **Atributos Inmutables**: Algunos atributos como `priority` y `eviction_policy` pueden requerir recrear el node pool si no se configuraron desde el inicio.

2. **Tiempo de Creación**: La creación de nodos Spot puede tardar 2-5 minutos.

3. **Evictions**: Los nodos Spot pueden ser eliminados por Azure en cualquier momento (normal en Spot).

4. **Sincronización**: Siempre verificar que Terraform state esté sincronizado con Azure después de cambios manuales.

---

## 🔄 Próximos Pasos

1. **Aplicar Terraform**: Ejecutar `terraform apply` para sincronizar configuración
2. **Verificar Estado**: Confirmar que `priority` y `eviction_policy` están correctos
3. **Esperar Nodos**: Los nodos Spot pueden tardar 2-3 minutos en crearse
4. **Verificar Pods**: Confirmar que los pods se mueven a Spot cuando está disponible










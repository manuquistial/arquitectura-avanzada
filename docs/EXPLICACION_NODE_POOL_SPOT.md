# Explicación: Node Pool Spot (AKS Spot Nodes)

## 📋 Resumen

El nodo `aks-spot-13429841-vmss` es parte del **Node Pool "spot"** configurado en el AKS cluster. Este node pool está diseñado para ejecutar workloads **tolerantes a interrupciones** con un **ahorro de hasta 70% en costos**.

---

## 🎯 Propósito del Node Pool Spot

### Objetivo Principal:
- **Ejecutar workers tolerantes a interrupciones** (consumidores de eventos, workers de procesamiento)
- **Reducir costos** aprovechando Spot VMs (hasta 70% más barato que VMs regulares)
- **Escalar dinámicamente** según demanda sin comprometer servicios críticos

### Configuración Actual:

```terraform
# Spot node pool - For KEDA workers (70% cost savings)
resource "azurerm_kubernetes_cluster_node_pool" "spot" {
  name                  = "spot"
  priority              = "Spot"              # Prioridad Spot
  eviction_policy       = "Delete"             # Eliminar nodo si Azure lo requiere
  spot_max_price        = -1                  # Pagar hasta precio regular (-1 = ilimitado)
  node_count            = 0                   # Mínimo: 0 (puede escalar a cero)
  
  # Taints: solo workloads tolerantes pueden ejecutarse
  node_taints = [
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"
  ]
  
  # Labels
  node_labels = {
    "nodepool" = "spot"
    "workload" = "workers"
  }
}
```

---

## 📊 Estado Actual

### Nodos Existentes:
```
aks-system-30703993-vmss000000   → System node pool (K8s controllers)
aks-user-38094841-vmss000000     → User node pool (aplicaciones)
```

### Node Pool Spot:
- **Estado**: Configurado pero **sin nodos activos**
- **Count**: 0 nodos (configurado con `spot_node_min = 0`)
- **Razón**: El mínimo está en 0, por lo que el cluster no crea nodos spot automáticamente

### ¿Por qué el nodo `aks-spot-13429841-vmss` no existe?

1. **Mínimo = 0**: El node pool puede escalar a cero
2. **Sin pods tolerantes**: No hay deployments configurados con tolerations para Spot
3. **Eviction previa**: Si existió antes, Azure pudo haberlo eliminado (eviction)

---

## ⚙️ Cómo Funciona Spot VMs

### Características:

1. **Prioridad Spot**:
   - Azure puede **eliminar (evict)** el nodo en cualquier momento
   - Cuando Azure necesita la capacidad para VMs regulares
   - Aviso típico: 30 segundos antes de eviction

2. **Eviction Policy: Delete**:
   - El nodo es **eliminado completamente** al ser evictado
   - Los pods se **desprograman** y se pueden reschedule en otros nodos
   - No hay datos persistentes (todo se pierde)

3. **Precio**:
   - **Hasta 70% más barato** que VMs regulares
   - `spot_max_price = -1` significa "pagar hasta precio regular"
   - Si el precio Spot sube por encima del regular, el nodo se elimina

4. **Taints**:
   - `kubernetes.azure.com/scalesetpriority=spot:NoSchedule`
   - **Solo pods con toleration** pueden ejecutarse
   - Protege servicios críticos de ejecutarse en Spot

---

## 🎯 ¿Qué Workloads Deberían Usar Spot?

### ✅ Candidatos Ideales:

1. **Workers de Eventos** (tolerantes a interrupciones):
   - ✅ `metadata` (consumidor de `document-events`)
   - ✅ `notification` (consumidor de `citizen-events`)
   - ✅ `signature` (worker de firmas)

2. **Características Necesarias**:
   - Procesamiento asíncrono (no request/response)
   - Tolerantes a pérdidas temporales
   - Con capacidad de retry/recovery
   - Stateless o con state externalizado (BD, Redis)

### ❌ NO Deben Usar Spot:

1. **Servicios Críticos**:
   - ❌ `auth` (autenticación crítica)
   - ❌ `ingestion` (subida de documentos)
   - ❌ `transfer` (transferencias críticas)
   - ❌ `citizen` (API crítica)
   - ❌ `frontend` (interfaz de usuario)

2. **Razones**:
   - Requieren alta disponibilidad
   - Procesan requests síncronos
   - Latencia crítica

---

## 🔧 Cómo Habilitar Spot para un Servicio

### Paso 1: Agregar Toleration

En el deployment (`deployment-metadata.yaml`, `deployment-notification.yaml`, etc.):

```yaml
spec:
  template:
    spec:
      tolerations:
      - key: "kubernetes.azure.com/scalesetpriority"
        operator: "Equal"
        value: "spot"
        effect: "NoSchedule"
```

### Paso 2: Agregar NodeSelector (Opcional)

Para **forzar** ejecución en Spot:

```yaml
spec:
  template:
    spec:
      nodeSelector:
        nodepool: "spot"
```

O usar **nodeAffinity** para **preferir** Spot pero permitir fallback:

```yaml
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: nodepool
                operator: In
                values:
                - spot
```

### Paso 3: Ajustar Node Pool Mínimo (Opcional)

Si quieres que siempre haya nodos Spot disponibles:

```terraform
variable "aks_spot_node_min" {
  default = 1  # Cambiar de 0 a 1
}
```

---

## 📈 Ventajas y Desventajas

### ✅ Ventajas:

1. **Ahorro de Costos**: Hasta 70% más barato
2. **Escalabilidad**: Escala automáticamente según demanda
3. **Flexibilidad**: Puede escalar a cero cuando no se necesita

### ⚠️ Desventajas:

1. **Evictions**: Azure puede eliminar nodos en cualquier momento
2. **Pérdida de Estado**: Todo se pierde en eviction
3. **Latencia**: Puede haber retrasos al recrear nodos
4. **Complejidad**: Requiere configurar tolerations correctamente

---

## 🎯 Recomendación

### Para los Servicios Actuales:

1. **metadata** y **notification** (workers):
   - ✅ **Candidatos ideales** para Spot
   - ✅ Procesan eventos asíncronos
   - ✅ Tolerantes a interrupciones
   - ✅ Con retry en Service Bus

2. **signature** (worker):
   - ⚠️ **Considerar** si el procesamiento puede tolerar evictions
   - ⚠️ Verificar que el state esté en BD (no en memoria)

3. **Servicios API** (auth, ingestion, transfer, citizen):
   - ❌ **NO usar Spot**
   - ❌ Requieren alta disponibilidad
   - ❌ Procesan requests síncronos

### Implementación Sugerida:

```yaml
# Para metadata y notification
spec:
  template:
    spec:
      tolerations:
      - key: "kubernetes.azure.com/scalesetpriority"
        operator: "Equal"
        value: "spot"
        effect: "NoSchedule"
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: nodepool
                operator: In
                values:
                - spot
```

Esto permite que los pods se ejecuten en Spot cuando esté disponible, pero pueden ejecutarse en nodos regulares si Spot no está disponible.

---

## 📝 Resumen Final

### El nodo `aks-spot-13429841-vmss`:

- **Es parte** del node pool "spot" configurado
- **Propósito**: Ejecutar workers tolerantes a interrupciones
- **Ahorro**: Hasta 70% en costos
- **Estado actual**: 0 nodos (mínimo configurado en 0)
- **Cómo activar**: Configurar tolerations en deployments de workers

### Próximos Pasos:

1. Decidir qué servicios habilitar para Spot (metadata, notification)
2. Agregar tolerations a los deployments
3. (Opcional) Aumentar `spot_node_min` si se requiere disponibilidad constante
4. Monitorear evictions y comportamiento

---

## 🔗 Referencias

- [Azure Spot VMs Documentation](https://docs.microsoft.com/azure/aks/spot-node-pool)
- [Kubernetes Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
- [Terraform AKS Spot Node Pool](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/kubernetes_cluster_node_pool#spot)










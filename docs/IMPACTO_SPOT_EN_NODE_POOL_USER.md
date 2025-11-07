# Impacto de Spot en Node Pool "user"

## 📋 Resumen

Sí, **la configuración de Spot reduce significativamente la carga en el node pool "user"** al mover workloads tolerantes (metadata, notification, signature) a nodos Spot cuando están disponibles.

---

## 📊 Estado Actual (Sin Spot)

### Distribución Actual de Pods:

```
Node Pool "user" (aks-user-38094841-vmss000000):
  ├── auth (crítico)
  ├── citizen (crítico)
  ├── frontend (crítico)
  ├── ingestion (crítico)
  ├── mintic-client (crítico)
  ├── transfer (crítico)
  ├── metadata (worker tolerante) ← Se moverá a Spot
  ├── notification (worker tolerante) ← Se moverá a Spot
  └── signature (worker tolerante) ← Se moverá a Spot
```

### Recursos Actuales en "user":

| Servicio | Memory Request | CPU Request | Tipo |
|----------|---------------|-------------|------|
| metadata | 32Mi | 5m | Worker tolerante |
| notification | 32Mi | 5m | Worker tolerante |
| signature | 64Mi | 10m | Worker tolerante |
| **TOTAL (tolerantes)** | **128Mi** | **20m** | **3 servicios** |

---

## 📈 Estado Esperado (Con Spot)

### Distribución Esperada de Pods:

```
Node Pool "user" (aks-user-38094841-vmss000000):
  ├── auth (crítico)
  ├── citizen (crítico)
  ├── frontend (crítico)
  ├── ingestion (crítico)
  ├── mintic-client (crítico)
  └── transfer (crítico)

Node Pool "spot" (aks-spot-XXXXX-vmss000000):
  ├── metadata (worker tolerante) ✅
  ├── notification (worker tolerante) ✅
  └── signature (worker tolerante) ✅
```

### Recursos Liberados en "user":

| Recurso | Antes (total) | Después (solo críticos) | Liberado |
|---------|---------------|------------------------|----------|
| Memory | ~1000Mi+ | ~870Mi | **128Mi** |
| CPU | ~1000m+ | ~980m | **20m** |

---

## 💰 Impacto en Recursos

### Reducción de Carga en "user":

1. **Memory**: **128Mi liberados** (~13-15% menos)
2. **CPU**: **20m liberados** (~2-3% menos)
3. **Pods**: **3 pods menos** en node pool "user"

### Beneficios:

1. **Más Capacidad para Servicios Críticos**:
   - Más recursos disponibles para auth, citizen, ingestion, transfer
   - Mejor distribución de carga
   - Menor contención de recursos

2. **Mejor Escalabilidad**:
   - Node pool "user" puede soportar más servicios críticos
   - Menos necesidad de escalar el node pool "user"

3. **Ahorro de Costos**:
   - Workers en Spot: **~70% más barato**
   - Menor necesidad de escalar node pool "user"

---

## 🎯 Impacto en Capabilities del Node Pool "user"

### Antes (Sin Spot):

```
Node Pool "user":
  - Capacidad total: ~2000m CPU / ~8000Mi Memory
  - En uso: ~1000m CPU / ~1000Mi Memory (estimado)
  - Disponible: ~1000m CPU / ~7000Mi Memory
  - 3 workers tolerantes ocupando recursos
```

### Después (Con Spot):

```
Node Pool "user":
  - Capacidad total: ~2000m CPU / ~8000Mi Memory
  - En uso: ~980m CPU / ~870Mi Memory (estimado)
  - Disponible: ~1020m CPU / ~7130Mi Memory
  - 0 workers tolerantes (todos en Spot)
  
Node Pool "spot":
  - Workers tolerantes: 128Mi Memory / 20m CPU
  - Costo: ~70% menos que en "user"
```

### Diferencia:

- **+20m CPU** disponible en "user"
- **+128Mi Memory** disponible en "user"
- **3 pods menos** compitiendo por recursos

---

## 📊 Escenarios

### Escenario 1: Sin Nodos Spot Disponibles

**Comportamiento**: Los pods se ejecutan en "user" (fallback)

**Impacto**: 
- Sin cambio inmediato
- Pero listo para usar Spot cuando esté disponible
- No hay degradación de servicio

### Escenario 2: Nodos Spot Disponibles

**Comportamiento**: Los pods se mueven automáticamente a Spot

**Impacto**:
- ✅ **128Mi + 20m CPU liberados** en "user"
- ✅ **Ahorro de ~70%** en costos de workers
- ✅ **Mejor distribución** de carga

### Escenario 3: Eviction de Nodos Spot

**Comportamiento**: Los pods se reschedulean en "user" automáticamente

**Impacto**:
- ⚠️ Carga temporal en "user" durante el rescheduling
- ✅ Service Bus tiene retry automático (no hay pérdida de trabajo)
- ✅ Los pods vuelven a Spot cuando hay disponibilidad

---

## 🎯 Conclusión

### ✅ Sí, la configuración de Spot ayuda a reducir cargas en AKS "user"

**Beneficios directos:**

1. **Reducción de Carga**:
   - 128Mi Memory liberados (~13-15%)
   - 20m CPU liberados (~2-3%)
   - 3 pods menos en "user"

2. **Mejor Distribución**:
   - Servicios críticos tienen más recursos disponibles
   - Menos contención entre servicios

3. **Escalabilidad**:
   - Node pool "user" puede soportar más carga crítica
   - Menos necesidad de escalar

4. **Ahorro de Costos**:
   - Workers en Spot: ~70% más barato
   - Mejor uso de recursos

### ⚠️ Notas Importantes:

1. **Fallback**: Si no hay nodos Spot, los pods siguen ejecutándose en "user"
2. **Evictions**: Los pods pueden volver a "user" si hay evictions
3. **Service Bus**: Tiene retry automático, no hay pérdida de trabajo

---

## 📈 Métricas Recomendadas

Para monitorear el impacto:

```bash
# Ver distribución de pods
kubectl get pods -n carpeta-ciudadana -o wide

# Ver recursos en node pool "user"
kubectl describe node aks-user-38094841-vmss000000 | grep "Allocated resources"

# Ver recursos en node pool "spot" (cuando esté disponible)
kubectl get nodes -l nodepool=spot
kubectl describe node <spot-node> | grep "Allocated resources"
```

---

## 🔄 Próximos Pasos

1. **Aplicar configuración**: `helm upgrade`
2. **Verificar distribución**: Los pods deberían moverse a Spot cuando haya nodos disponibles
3. **Monitorear**: Verificar que los recursos en "user" se reducen
4. **Ajustar si es necesario**: Considerar aumentar `spot_node_min` si se requiere disponibilidad constante











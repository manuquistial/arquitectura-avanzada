# Secrets Opcionales vs Obligatorios en Kubernetes

## ¿Qué significa `optional: true`?

### Sin `optional` (por defecto es `false` - obligatorio):
```yaml
- secretRef:
    name: database-credentials
    # optional: false (por defecto)
```

**Comportamiento**:
- ✅ Si el secret **existe**: Se carga normalmente como variable de entorno
- ❌ Si el secret **NO existe**: Kubernetes **NO puede crear el contenedor**
- **Error**: `CreateContainerConfigError: secret "database-credentials" not found`
- **Resultado**: El pod **NO puede iniciar** hasta que el secret exista

### Con `optional: true`:
```yaml
- secretRef:
    name: database-credentials
    optional: true
```

**Comportamiento**:
- ✅ Si el secret **existe**: Se carga normalmente como variable de entorno
- ✅ Si el secret **NO existe**: Kubernetes **SÍ puede crear el contenedor**
- **Sin error**: El pod puede iniciar sin el secret
- **Variable de entorno**: No se establece (vacía o undefined)
- **Resultado**: El pod **puede iniciar** incluso sin el secret

## ¿Requiere desplegar 2 veces?

**NO**, no requiere desplegar dos veces. Se hace así:

### Opción 1: Helm Upgrade (Recomendado)
```bash
# Aplicar cambios en el código del Helm chart
helm upgrade carpeta-ciudadana ./carpeta-ciudadana -n carpeta-ciudadana
```

**Qué pasa**:
1. Helm actualiza los deployments con `optional: true`
2. Kubernetes detecta el cambio en el deployment
3. Crea nuevos pods con la configuración actualizada
4. Los pods antiguos se terminan gradualmente (rolling update)
5. Los nuevos pods pueden iniciar sin el secret (si no existe)

### Opción 2: Si ya hiciste cambios manuales con `kubectl patch`
```bash
# Ya aplicaste cambios manualmente con:
kubectl patch deployment ...

# Ahora para alinearlo con código:
helm upgrade carpeta-ciudadana ./carpeta-ciudadana -n carpeta-ciudadana
```

**Qué pasa**:
- Helm actualiza los deployments a la configuración del código
- Los cambios manuales se sobrescriben con la configuración del código
- Los pods se actualizan automáticamente

## Flujo Actual del Problema

### Situación Actual:
1. **ExternalSecrets NO están sincronizando** (error con SecretStore)
2. **Secret `database-credentials` NO existe** en Kubernetes
3. **Pods NO pueden iniciar** porque requieren el secret (sin optional)

### Con `optional: true`:
1. **Pods SÍ pueden iniciar** sin el secret
2. **Aplicación puede funcionar** sin DATABASE_URL (si está diseñada para eso)
3. **Cuando ExternalSecrets se sincronice**, el secret aparecerá
4. **Los pods se actualizarán automáticamente** para obtener la variable de entorno

## ¿Cuándo quitar `optional: true`?

Una vez que:
1. ✅ ExternalSecrets se sincronicen correctamente
2. ✅ El secret `database-credentials` exista en Kubernetes
3. ✅ Los pods funcionen correctamente con el secret
4. ✅ Quieras asegurar que el secret SIEMPRE esté presente

Entonces puedes quitar `optional: true` para hacerlo obligatorio nuevamente.

## Resumen

| Aspecto | Sin optional (obligatorio) | Con optional: true |
|---------|---------------------------|-------------------|
| Secret existe | ✅ Se carga | ✅ Se carga |
| Secret NO existe | ❌ Pod NO inicia | ✅ Pod SÍ inicia |
| Variable de entorno | ✅ Siempre presente | ⚠️ Puede estar vacía |
| Requiere 2 deploys | ❌ No | ❌ No |
| Aplicación funciona | ✅ Sí (si tiene secret) | ⚠️ Depende del diseño |

**Recomendación actual**: Usar `optional: true` temporalmente hasta que ExternalSecrets se sincronicen correctamente.


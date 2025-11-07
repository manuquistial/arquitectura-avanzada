# Cambios en Lógica de Retención - Documentos Firmados

> **Fecha:** 2025-11-06  
> **Cambio:** Documentos firmados ahora se retienen ETERNAMENTE (retention_until = NULL)

---

## Resumen del Cambio

### Antes
- Documentos **FIRMADOS (SIGNED)**: Retención de 5 años (`retention_until = signed_at + 5 años`)
- Documentos **NO FIRMADOS (UNSIGNED)**: Retención de 30 días (`retention_until = created_at + 30 días`)

### Ahora
- Documentos **FIRMADOS (SIGNED)**: Retención **ETERNAL** (`retention_until = NULL`)
- Documentos **NO FIRMADOS (UNSIGNED)**: Retención de 30 días (`retention_until = created_at + 30 días`)

---

## Archivos Modificados

### 1. Signature Service
- **Archivo:** `services/signature/app/routers/signature.py`
- **Cambio:** `retention_until = None` para documentos firmados
- **Línea:** 167
- **Estado:** ✅ Reconstruido y desplegado

### 2. Ingestion Service
- **Archivo:** `services/ingestion/app/routers/documents.py`
- **Cambio:** `retention_until = created_at + 30 días` para documentos no firmados
- **Línea:** 80, 92
- **Estado:** ✅ Reconstruido y desplegado

### 3. Migración de Base de Datos
- **Archivo:** `services/ingestion/alembic/versions/001_add_worm_retention_fields.py`
- **Cambio:** Trigger actualizado para establecer `retention_until = NULL` en documentos SIGNED
- **Línea:** 90-116
- **Estado:** ✅ Actualizado

### 4. Modelos
- **Archivo:** `services/ingestion/app/models.py`
- **Cambio:** Comentarios actualizados
- **Línea:** 48, 63
- **Estado:** ✅ Actualizado

### 5. Documentación
- **Archivos:**
  - `docs/ANALISIS_ARQUITECTURA.md`
  - `docs/VERIFICACION_FUNCIONAL.md`
- **Cambio:** Todas las referencias a "5 años" actualizadas a "ETERNAL"
- **Estado:** ✅ Actualizado

---

## Scripts Creados

### 1. Script SQL
- **Archivo:** `scripts/update-retention-signed-docs.sql`
- **Propósito:** Actualizar documentos existentes en BD
- **Estado:** ✅ Creado

### 2. Script Python
- **Archivo:** `scripts/update-retention-signed-docs.py`
- **Propósito:** Actualizar documentos existentes desde pod
- **Estado:** ✅ Creado y ejecutado

---

## Verificación

### Servicios Desplegados
- ✅ **Ingestion Service**: Reconstruido y desplegado
  - Imagen: `manuelquistial/carpeta-ingestion:latest`
  - Rollout: Exitoso
  
- ✅ **Signature Service**: Reconstruido y desplegado
  - Imagen: `manuelquistial/carpeta-signature:latest`
  - Rollout: Exitoso

### Tests Ejecutados
- ✅ **CU3: Subir Documentos**: PASS
  - Endpoint: `POST /api/documents/upload-url` → HTTP 200
  - Retención: 30 días para documentos no firmados
  
- ✅ **CU4: Firmar Documentos**: PASS
  - Endpoint: `POST /api/signature/sign` → HTTP 200
  - Retención: ETERNAL (NULL) para documentos firmados

---

## Comportamiento Esperado

### Documentos Nuevos No Firmados
1. Se crea documento → `state = "UNSIGNED"`
2. Se establece → `retention_until = created_at + 30 días`
3. Después de 30 días → Puede ser eliminado (si no está firmado)

### Documentos Firmados
1. Se firma documento → `state = "SIGNED"`, `worm_locked = true`
2. Se establece → `retention_until = NULL` (ETERNAL)
3. **Nunca expira** → Retención permanente

---

## Notas Importantes

1. **Documentos Existentes**: El script de actualización se ejecutó pero no había documentos firmados para actualizar (0 documentos actualizados).

2. **Trigger de BD**: El trigger `set_retention_on_sign()` ahora establece automáticamente `retention_until = NULL` cuando un documento cambia a estado SIGNED.

3. **WORM**: Los documentos firmados siguen siendo inmutables (WORM), pero ahora con retención eterna en lugar de 5 años.

4. **Legal Hold**: El campo `legal_hold` sigue previniendo borrado incluso después de que expire la retención (aunque ahora solo aplica a documentos no firmados).

---

## Próximos Pasos Recomendados

1. **Monitorear**: Verificar que los nuevos documentos se creen con la retención correcta
2. **Auditar**: Revisar documentos existentes firmados y actualizar manualmente si es necesario
3. **Documentar**: Actualizar políticas de retención en documentación de negocio

---

**Estado Final:** ✅ **COMPLETADO**


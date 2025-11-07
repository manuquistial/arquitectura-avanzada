# Análisis de Implementación WORM

> **Fecha**: 2025-11-01  
> **Objetivo**: Evaluar si WORM está correctamente implementado o si faltan elementos

---

## 📋 Resumen Ejecutivo

**Estado General**: ⚠️ **Parcialmente Implementado** - Falta protección en la capa de aplicación y en Azure Storage.

**Hallazgos**:
- ✅ **Base de Datos**: Protección correcta con triggers
- ❌ **Aplicación**: Falta validación previa en endpoints
- ❌ **Azure Storage**: No hay política de inmutabilidad a nivel de blob
- ⚠️ **Endpoints**: No validan WORM antes de operaciones críticas

---

## ✅ Lo que SÍ está bien implementado

### 1. **Base de Datos - Triggers PostgreSQL** ✅

**Ubicación**: `services/ingestion/alembic/versions/001_add_worm_retention_fields.py`

```sql
CREATE TRIGGER enforce_worm_immutability
BEFORE UPDATE ON document_metadata
FOR EACH ROW
EXECUTE FUNCTION prevent_worm_update();
```

**Protección**:
- ✅ Previene modificación de campos protegidos cuando `worm_locked = True`
- ✅ Protege campos críticos: `state`, `signed_at`, `retention_until`, `sha256_hash`, `blob_name`
- ✅ Previene eliminación cuando `legal_hold = True`
- ✅ Aplica protección incluso si se accede directamente a la BD

**Estado**: ✅ **Correcto**

---

### 2. **Campos WORM en Modelo** ✅

**Ubicación**: `services/ingestion/app/models.py`

```python
state: Mapped[str] = mapped_column(String(20), default="UNSIGNED", index=True)
worm_locked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
retention_until: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
hub_signature_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
legal_hold: Mapped[bool] = mapped_column(Boolean, default=False)
```

**Estado**: ✅ **Correcto**

---

### 3. **Activación de WORM al Firmar** ✅

**Ubicación**: `services/signature/app/routers/signature.py` (línea 145-175)

```python
if hub_result["success"]:
    update_stmt = (
        update(DocumentMetadata)
        .where(DocumentMetadata.id == request.document_id)
        .values(
            state="SIGNED",
            worm_locked=True,
            signed_at=datetime.utcnow(),
            retention_until=retention_date,
            hub_signature_ref=hub_sig_ref,
        )
    )
```

**Estado**: ✅ **Correcto** - Se activa WORM automáticamente después de autenticación exitosa con Hub MinTIC

---

### 4. **Cálculo Automático de Retención** ✅

**Ubicación**: `services/ingestion/alembic/versions/001_add_worm_retention_fields.py` (línea 90-117)

```sql
CREATE FUNCTION set_retention_on_sign()
-- Cuando state cambia a SIGNED, auto-calcula retention (5 años)
IF NEW.state = 'SIGNED' AND OLD.state != 'SIGNED' THEN
    NEW.retention_until := CURRENT_DATE + INTERVAL '5 years';
```

**Estado**: ✅ **Correcto**

---

## ❌ Lo que FALTA o está MAL

### 1. **Endpoint DELETE no valida WORM** ❌ CRÍTICO

**Ubicación**: `services/ingestion/app/routers/documents.py` (línea 500-551)

**Problema**: El endpoint `DELETE /api/documents/{document_id}` **NO verifica** si el documento está bloqueado WORM antes de intentar eliminar.

```python
@router.delete("/{document_id}")
async def delete_document(...):
    metadata = result.scalar_one_or_none()
    
    # ❌ FALTA: if metadata.worm_locked:
    # ❌ FALTA:     raise HTTPException(..., "Cannot delete WORM-locked document")
    
    # Soft delete
    metadata.is_deleted = True  # Esto fallará en BD por el trigger, pero debería validarse antes
    await db.commit()
```

**Impacto**:
- ❌ El usuario recibe un error genérico de BD en lugar de un mensaje claro
- ❌ No hay validación previa (solo en BD)
- ❌ Se intenta una operación que sabemos que va a fallar

**Solución Requerida**:
```python
@router.delete("/{document_id}")
async def delete_document(...):
    metadata = result.scalar_one_or_none()
    
    # Validar WORM antes de intentar eliminar
    if metadata.worm_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot delete WORM-locked document. Document ID: {document_id}. "
                   "Signed documents cannot be deleted until retention period expires."
        )
    
    # Validar legal hold
    if metadata.legal_hold:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot delete document under legal hold. Document ID: {document_id}."
        )
    
    # Continuar con soft delete
    metadata.is_deleted = True
```

**Prioridad**: 🔴 **ALTA**

---

### 2. **Falta Validación Previa en UPDATE** ⚠️ MEDIA

**Problema**: No hay validación en la aplicación antes de intentar actualizar un documento bloqueado WORM.

**Impacto**:
- ⚠️ El usuario solo ve el error después de intentar la operación
- ⚠️ No hay mensaje de error claro desde la aplicación
- ⚠️ Se depende únicamente del trigger de BD

**Solución Requerida**:
Crear un helper function para validar WORM antes de operaciones:

```python
def check_worm_allows_operation(document: DocumentMetadata, operation: str) -> None:
    """Check if WORM policy allows the operation."""
    if document.worm_locked:
        if operation == "delete":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot delete WORM-locked document {document.id}"
            )
        elif operation == "update":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot update WORM-locked document {document.id}"
            )
```

**Prioridad**: 🟡 **MEDIA**

---

### 3. **Azure Blob Storage - No hay Política de Inmutabilidad** ❌ CRÍTICO

**Problema**: Los blobs en Azure Storage **NO tienen política de inmutabilidad** a nivel de almacenamiento.

**Ubicación**: `infra/terraform/layers/platform/modules/storage/storage/main.tf`

**Estado Actual**:
- ✅ `versioning_enabled = true` - Versionado habilitado
- ❌ **NO hay** `immutability_policy` para blobs
- ❌ **NO hay** `legal_hold` a nivel de blob storage

**Impacto**:
- ❌ Los blobs pueden ser **modificados o eliminados directamente en Azure Storage**
- ❌ Bypass de la protección WORM en BD si alguien tiene acceso al Storage Account
- ❌ No hay protección a nivel de infraestructura

**Solución Requerida**:
Agregar política de inmutabilidad para blobs SIGNED:

```terraform
# Para cada blob SIGNED, aplicar política de inmutabilidad
resource "azurerm_storage_blob" "document" {
  # ...
  
  immutability_policy {
    policy_type = "Unlocked"  # o "Locked" para mayor protección
    period_in_days = 1825  # 5 años
  }
}
```

**Nota**: Esto debe aplicarse **después** de que el documento sea firmado (SIGNED), no antes.

**Prioridad**: 🔴 **ALTA** (Seguridad crítica)

---

### 4. **Falta Validación en Endpoint de Actualización de Metadata** ⚠️ MEDIA

**Problema**: Si existe un endpoint para actualizar metadata (título, descripción), no valida WORM antes de permitir actualizaciones.

**Solución Requerida**:
Si existe `PUT /api/documents/{document_id}`, debe validar:

```python
if metadata.worm_locked:
    # Solo permitir actualizar campos no protegidos
    if "description" in update_data or "tags" in update_data:
        # Permitir (estos campos no están protegidos por WORM)
        pass
    else:
        # Rechazar actualización de campos protegidos
        raise HTTPException(...)
```

**Prioridad**: 🟡 **MEDIA**

---

### 5. **Retención para UNSIGNED no se Calcula Automáticamente** ⚠️ BAJA

**Problema**: Según el comentario en el modelo:
```python
# Auto-calculated: UNSIGNED=created+30d, SIGNED=signed+5y
```

Pero **NO hay trigger** que calcule automáticamente `retention_until = created_at + 30 días` para documentos UNSIGNED.

**Impacto**:
- ⚠️ Los documentos UNSIGNED no tienen fecha de retención automática
- ⚠️ Depende de la aplicación calcularla manualmente

**Solución Requerida**:
Agregar trigger o función para calcular retención de UNSIGNED:

```sql
CREATE FUNCTION set_retention_on_create()
RETURNS TRIGGER AS $$
BEGIN
    -- Si es UNSIGNED y no tiene retention_until, calcular 30 días
    IF NEW.state = 'UNSIGNED' AND NEW.retention_until IS NULL THEN
        NEW.retention_until := CURRENT_DATE + INTERVAL '30 days';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_set_retention_on_create
BEFORE INSERT ON document_metadata
FOR EACH ROW
EXECUTE FUNCTION set_retention_on_create();
```

**Prioridad**: 🟢 **BAJA**

---

### 6. **Falta Endpoint para Verificar Estado WORM** ⚠️ BAJA

**Problema**: No hay endpoint para verificar si un documento está bloqueado WORM antes de intentar operaciones.

**Solución Sugerida**:
```python
@router.get("/{document_id}/worm-status")
async def get_worm_status(document_id: str, ...):
    """Get WORM status of a document."""
    metadata = await get_document_metadata(document_id)
    return {
        "document_id": document_id,
        "worm_locked": metadata.worm_locked,
        "state": metadata.state,
        "signed_at": metadata.signed_at,
        "retention_until": metadata.retention_until,
        "legal_hold": metadata.legal_hold,
        "can_modify": not metadata.worm_locked,
        "can_delete": not metadata.worm_locked and not metadata.legal_hold
    }
```

**Prioridad**: 🟢 **BAJA** (Mejora de UX)

---

## 📊 Matriz de Prioridades

| Problema | Prioridad | Impacto | Estado |
|----------|-----------|---------|--------|
| Endpoint DELETE no valida WORM | 🔴 ALTA | Usuario recibe error confuso | ❌ Falta |
| Azure Storage sin inmutabilidad | 🔴 ALTA | Seguridad crítica - bypass posible | ❌ Falta |
| Falta validación previa en UPDATE | 🟡 MEDIA | Mejora UX pero BD protege | ⚠️ Mejorable |
| Retención UNSIGNED no automática | 🟢 BAJA | Funcionalidad menor | ⚠️ Mejorable |
| Falta endpoint de estado WORM | 🟢 BAJA | Mejora UX | ⚠️ Opcional |

---

## 🔧 Plan de Corrección Recomendado

### Fase 1: Correcciones Críticas (Semana 1)

1. ✅ **Validar WORM en endpoint DELETE**
   - Agregar verificación antes de `is_deleted = True`
   - Retornar error HTTP 403 con mensaje claro

2. ✅ **Implementar Política de Inmutabilidad en Azure Blob Storage**
   - Crear Azure Function o script que aplique inmutabilidad después de firmar
   - O usar `azurerm_storage_blob` con `immutability_policy` para nuevos blobs SIGNED

### Fase 2: Mejoras de Validación (Semana 2)

3. ⏳ **Crear helper function para validación WORM**
   - Función reutilizable: `check_worm_allows_operation()`
   - Usar en todos los endpoints que modifican documentos

4. ⏳ **Validar WORM en cualquier endpoint de actualización**
   - Si existe `PUT /api/documents/{document_id}`, agregar validación
   - Permitir solo campos no protegidos (description, tags)

### Fase 3: Mejoras Adicionales (Backlog)

5. ⏸️ **Automatizar retención para UNSIGNED**
   - Agregar trigger `auto_set_retention_on_create`
   - Calcular 30 días automáticamente

6. ⏸️ **Agregar endpoint de estado WORM**
   - `GET /api/documents/{document_id}/worm-status`
   - Mejora UX para el frontend

---

## ✅ Checklist de Implementación Correcta

### Base de Datos
- [x] Trigger `enforce_worm_immutability` implementado
- [x] Función `prevent_worm_update()` protege campos críticos
- [x] Trigger `auto_set_retention` calcula retención para SIGNED
- [ ] Trigger `auto_set_retention_on_create` para UNSIGNED (opcional)

### Aplicación
- [x] Campos WORM definidos en modelo
- [x] WORM se activa automáticamente al firmar
- [ ] Endpoint DELETE valida WORM antes de intentar eliminar ❌
- [ ] Endpoint UPDATE valida WORM antes de intentar actualizar ❌
- [ ] Helper function para validación WORM reutilizable ❌

### Azure Storage
- [x] Versionado habilitado (`versioning_enabled = true`)
- [ ] Política de inmutabilidad para blobs SIGNED ❌
- [ ] Legal hold a nivel de blob storage ❌

### Endpoints y UX
- [ ] Endpoint para verificar estado WORM (opcional)
- [ ] Mensajes de error claros cuando WORM bloquea operaciones

---

## 📝 Recomendaciones Finales

### 🔴 Críticas (Deben implementarse)

1. **Validar WORM en endpoint DELETE**: Evitar intentos de eliminación que sabemos que fallarán
2. **Política de Inmutabilidad en Azure Storage**: Protección a nivel de infraestructura

### 🟡 Importantes (Mejoran seguridad y UX)

3. **Helper function de validación WORM**: Código más limpio y reutilizable
4. **Validación previa en todos los UPDATE**: Mejor experiencia de usuario

### 🟢 Opcionales (Mejoras adicionales)

5. **Automatizar retención UNSIGNED**: Completitud de funcionalidad
6. **Endpoint de estado WORM**: Mejora UX para el frontend

---

## 🔗 Referencias

- [Azure Blob Storage Immutability Policies](https://learn.microsoft.com/en-us/azure/storage/blobs/immutability-policies-overview)
- [Azure Blob Storage Legal Hold](https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview#legal-holds)
- [PostgreSQL Triggers Documentation](https://www.postgresql.org/docs/current/triggers.html)

---

*Documento generado el 2025-11-01*


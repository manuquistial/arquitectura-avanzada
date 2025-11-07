# WORM - Write Once Read Many

> **Explicación del concepto WORM y su implementación en Carpeta Ciudadana**

---

## 📚 ¿Qué es WORM?

**WORM** significa **"Write Once Read Many"** (Escribir Una Vez, Leer Muchas Veces).

Es una **política de almacenamiento** que garantiza que un documento, una vez escrito/guardado, **no puede ser modificado ni eliminado** durante un período determinado. Solo se puede **leer** (consultar, descargar).

---

## 🎯 ¿Por qué es importante WORM?

### 1. **Cumplimiento Legal y Normativo**
- Garantiza que los documentos oficiales no sean alterados después de ser firmados
- Cumple con regulaciones gubernamentales (ej: retención de documentos por 5 años)
- Proporciona evidencia legal inmutable en caso de disputas

### 2. **Integridad de Documentos**
- Previene modificaciones accidentales o maliciosas
- Protege contra corrupción de datos
- Garantiza autenticidad de documentos firmados

### 3. **Auditoría y Trazabilidad**
- Registra el momento exacto en que un documento fue "bloqueado" (firmado)
- Proporciona un historial completo de cambios (antes del bloqueo)
- Permite verificación de integridad en cualquier momento

---

## 🔧 ¿Cómo funciona WORM en Carpeta Ciudadana?

### Estados del Documento

En el sistema, un documento puede estar en uno de dos estados:

#### 1. **UNSIGNED** (No Firmado)
- ✅ **Editable**: Se puede modificar o eliminar
- ⏱️ **TTL**: 30 días (después se puede eliminar automáticamente)
- 🔓 **WORM desactivado**: `worm_locked = False`
- 📝 **Estado**: `state = "UNSIGNED"`

#### 2. **SIGNED** (Firmado)
- 🔒 **Inmutable**: NO se puede modificar ni eliminar
- ⏱️ **Retención**: 5 años desde la fecha de firma
- 🔐 **WORM activado**: `worm_locked = True`
- 📝 **Estado**: `state = "SIGNED"`

---

## 📋 Campos WORM en el Modelo

### Campos Principales

```python
# Estado del documento
state: str = "UNSIGNED" | "SIGNED"

# ¿Está bloqueado WORM?
worm_locked: bool = False | True

# Fecha y hora de firma
signed_at: datetime | None

# Fecha hasta la cual debe retenerse
retention_until: date | None

# Referencia del Hub MinTIC (cuando se firma)
hub_signature_ref: str | None

# Bloqueo legal (previene eliminación incluso después de retención)
legal_hold: bool = False
```

### Ejemplo de Transición

```python
# Documento recién subido
state = "UNSIGNED"
worm_locked = False
signed_at = None
retention_until = None  # Se calcularía como created_at + 30 días

# Después de firmar con el Hub MinTIC
state = "SIGNED"
worm_locked = True  # 🔒 BLOQUEADO
signed_at = datetime(2025-01-15, 10:30:00)
retention_until = date(2030-01-15)  # 5 años después
hub_signature_ref = "HUB_REF_123456"
```

---

## 🛡️ Protección WORM en Base de Datos

El sistema implementa **protección a nivel de base de datos** usando **triggers de PostgreSQL**.

### Función de Protección

```sql
CREATE OR REPLACE FUNCTION prevent_worm_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Si el documento está bloqueado WORM
    IF OLD.worm_locked = TRUE THEN
        -- Verificar si se intenta modificar campos protegidos
        IF (NEW.worm_locked = FALSE OR
            NEW.state != OLD.state OR
            NEW.retention_until != OLD.retention_until OR
            NEW.hub_signature_ref IS DISTINCT FROM OLD.hub_signature_ref OR
            NEW.signed_at IS DISTINCT FROM OLD.signed_at OR
            NEW.sha256_hash != OLD.sha256_hash OR
            NEW.blob_name != OLD.blob_name) THEN
            
            -- ❌ BLOQUEO: Lanzar excepción
            RAISE EXCEPTION 
                'Cannot modify WORM-locked document. Document ID: %. Protected fields are immutable.', 
                OLD.id
                USING HINT = 'WORM (Write Once Read Many) policy prevents modification of signed documents';
        END IF;
        
        -- Protección adicional: Legal Hold previene eliminación
        IF OLD.legal_hold = TRUE AND NEW.is_deleted = TRUE THEN
            RAISE EXCEPTION 
                'Cannot delete document under legal hold. Document ID: %', 
                OLD.id
                USING HINT = 'Remove legal hold before attempting deletion';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Trigger de Aplicación

```sql
CREATE TRIGGER enforce_worm_immutability
BEFORE UPDATE ON document_metadata
FOR EACH ROW
EXECUTE FUNCTION prevent_worm_update();
```

**Esto significa que**:
- ✅ Cualquier intento de modificar un documento bloqueado WORM **fallará automáticamente**
- ✅ La protección está en la **base de datos**, no solo en la aplicación
- ✅ Incluso si alguien accede directamente a la BD, no puede modificar el documento

---

## 🔄 Flujo de Trabajo WORM

### 1. **Documento Subido (UNSIGNED)**
```
Usuario sube documento
  ↓
state = "UNSIGNED"
worm_locked = False
retention_until = created_at + 30 días
  ↓
✅ Puede editar, eliminar, reemplazar
```

### 2. **Documento Firmado (SIGNED)**
```
Usuario solicita firmar documento
  ↓
Servicio Signature llama al Hub MinTIC
  ↓
Hub MinTIC autentica y devuelve referencia
  ↓
state = "SIGNED"
worm_locked = True  🔒
signed_at = datetime.now()
retention_until = signed_at + 5 años
hub_signature_ref = "HUB_REF_..."
  ↓
🔒 INMUTABLE: No se puede modificar ni eliminar
```

### 3. **Intento de Modificación (SIGNED)**
```
Usuario intenta modificar documento SIGNED
  ↓
Aplicación intenta UPDATE en BD
  ↓
Trigger detecta worm_locked = True
  ↓
❌ EXCEPCIÓN: "Cannot modify WORM-locked document"
  ↓
Operación falla automáticamente
```

---

## 📊 Campos Protegidos por WORM

Cuando `worm_locked = True`, los siguientes campos **NO pueden modificarse**:

| Campo | Descripción | ¿Por qué está protegido? |
|-------|-------------|---------------------------|
| `worm_locked` | Estado de bloqueo WORM | Previene desbloqueo accidental |
| `state` | Estado del documento (UNSIGNED/SIGNED) | Mantiene integridad del estado |
| `retention_until` | Fecha de retención | Protege período de retención legal |
| `hub_signature_ref` | Referencia del Hub MinTIC | Evidencia de autenticación |
| `signed_at` | Timestamp de firma | Prueba de cuándo se firmó |
| `sha256_hash` | Hash de integridad | Verifica que el contenido no cambió |
| `blob_name` | Nombre del blob en Storage | Previene reemplazo del archivo |

**Campos que SÍ se pueden modificar** (incluso con WORM activo):
- `description`: Descripción del documento
- `tags`: Tags de clasificación
- `updated_at`: Timestamp de última actualización (actualizado automáticamente)

---

## 🔍 Legal Hold (Bloqueo Legal)

Además de WORM, existe el concepto de **Legal Hold**:

```python
legal_hold: bool = False  # Bloqueo legal
```

**Legal Hold**:
- 🔒 Previene **eliminación** incluso después de que expire `retention_until`
- 🏛️ Usado para documentos en litigios o investigaciones legales
- ⏸️ Se puede activar manualmente por un administrador
- ✅ Solo se puede desactivar con permisos especiales

**Ejemplo**:
```
Documento SIGNED con retention_until = 2030-01-15
  ↓
legal_hold = True (activado por admin)
  ↓
Después de 2030-01-15, el documento NO se puede eliminar
  ↓
Solo cuando legal_hold = False se puede eliminar
```

---

## 📈 Beneficios de WORM en Carpeta Ciudadana

### 1. **Cumplimiento Normativo**
✅ Garantiza retención de 5 años para documentos firmados  
✅ Previene eliminación accidental de documentos importantes  
✅ Cumple con estándares gubernamentales

### 2. **Integridad**
✅ Documentos firmados no pueden ser alterados  
✅ Hash SHA-256 verifica integridad del contenido  
✅ Referencia del Hub MinTIC proporciona trazabilidad

### 3. **Seguridad**
✅ Protección a nivel de base de datos (triggers)  
✅ Incluso acceso directo a BD no puede modificar documentos bloqueados  
✅ Auditoría completa de todos los intentos de modificación

### 4. **Confianza**
✅ Los usuarios pueden confiar en que sus documentos oficiales son inmutables  
✅ Las transferencias entre operadores pueden verificar integridad  
✅ Evidencia legal válida en disputas

---

## 🔗 Relación con Otros Conceptos

### WORM vs. Retención (Retention)
- **WORM**: Previene **modificación** del documento
- **Retención**: Define **cuánto tiempo** debe conservarse el documento
- **Juntos**: Garantizan inmutabilidad durante el período de retención

### WORM vs. Legal Hold
- **WORM**: Previene **modificación** del documento
- **Legal Hold**: Previene **eliminación** incluso después de retención
- **Juntos**: Documento completamente protegido (ni modificación ni eliminación)

### WORM vs. Estado (State)
- **`state`**: Indica el estado del documento (`UNSIGNED` o `SIGNED`)
- **`worm_locked`**: Indica si el documento está bloqueado WORM
- **Relación**: Cuando `state = "SIGNED"`, normalmente `worm_locked = True`

---

## 📝 Resumen

**WORM (Write Once Read Many)** es una política crítica que:

1. 🔒 **Bloquea** documentos firmados contra modificaciones
2. ⏱️ **Garantiza** retención durante el período legal (5 años)
3. 🛡️ **Protege** la integridad mediante triggers de base de datos
4. 📋 **Proporciona** trazabilidad y evidencia legal

**En Carpeta Ciudadana**:
- Los documentos **UNSIGNED** son editables (30 días)
- Los documentos **SIGNED** son inmutables (5 años)
- La protección está en la **base de datos**, no solo en la aplicación
- El **Legal Hold** puede extender la protección indefinidamente

---

*Documento generado el 2025-11-01*


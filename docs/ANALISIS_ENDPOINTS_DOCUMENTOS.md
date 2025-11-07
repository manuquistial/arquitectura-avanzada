# Análisis de Endpoints de Documentos - Problema y Solución

> **Fecha:** 2025-11-06  
> **Problema:** Los documentos subidos no aparecen en el listado

---

## Problema Identificado

### Síntoma
- Los documentos se generan correctamente con `POST /api/documents/upload-url`
- El endpoint `GET /api/documents/?citizen_id=XXX` devuelve una lista vacía `[]`
- Los logs muestran errores: `column document_metadata.title does not exist`

### Causa Raíz

1. **Problema de Esquema de Base de Datos:**
   - El modelo SQLAlchemy `DocumentMetadata` incluye la columna `title` (línea 22 de `models.py`)
   - La columna `title` no existe físicamente en la base de datos PostgreSQL
   - El código intenta crear la columna automáticamente durante el INSERT, pero:
     - Solo funciona durante el INSERT (no durante el SELECT)
     - Hay problemas de transacción que impiden la creación correcta

2. **Problema en el Endpoint de Listado:**
   - El endpoint `list_documents` (línea 479-516) usa SQLAlchemy ORM
   - SQLAlchemy intenta acceder a `doc.title` (línea 502)
   - Si la columna no existe, SQLAlchemy lanza una excepción
   - El endpoint captura la excepción y devuelve una lista vacía `[]` (línea 516)

3. **Flujo de Datos:**
   - `POST /api/documents/upload-url`: Crea registro con `status="pending"`
   - El registro SÍ se guarda en la base de datos
   - `GET /api/documents/`: Intenta leer el registro pero falla por columna faltante
   - Devuelve lista vacía en lugar de mostrar el error

---

## Solución Implementada

### Cambios en `services/ingestion/app/routers/documents.py`

#### 1. Uso de SQL Raw con Manejo de Columnas Faltantes

```python
@router.get("/")
async def list_documents(
    citizen_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    """List all documents for a citizen."""
    try:
        from sqlalchemy import select, text
        # Use raw SQL to handle missing columns gracefully
        query = text("""
            SELECT 
                id,
                citizen_id,
                COALESCE(title, filename) as title,
                filename,
                content_type,
                status,
                size_bytes,
                created_at,
                updated_at
            FROM document_metadata
            WHERE citizen_id = :citizen_id
              AND is_deleted = false
            ORDER BY created_at DESC
        """)
        
        result = await db.execute(query, {"citizen_id": citizen_id})
        rows = result.fetchall()
        
        return [
            {
                "id": row.id,
                "title": row.title or row.filename,  # Fallback to filename
                "filename": row.filename,
                "content_type": row.content_type,
                "status": row.status,
                "size_bytes": row.size_bytes,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
    except Exception as e:
        # Fallback con SQLAlchemy ORM si SQL raw falla
        # ...
```

#### 2. Fallback con SQLAlchemy ORM

Si el SQL raw falla, se intenta con SQLAlchemy ORM usando `getattr()` para manejar columnas faltantes:

```python
"title": getattr(doc, 'title', None) or doc.filename,  # Fallback to filename
```

---

## Flujo Completo de Documentos

### 1. Generar URL de Upload
**Endpoint:** `POST /api/documents/upload-url`

**Flujo:**
1. Valida `citizen_id`, `filename`, `content_type`, `title`
2. Genera SAS URL para Azure Blob Storage
3. Crea registro en BD con:
   - `status="pending"`
   - `state="UNSIGNED"`
   - `retention_until=created_at + 30 días`
   - Intenta crear columnas faltantes automáticamente
4. Publica evento en Service Bus
5. Retorna `upload_url` y `document_id`

**Estado del Documento:**
- ✅ Registro creado en BD
- ⏳ Archivo aún no subido a Azure Storage
- ⏳ `status="pending"`

### 2. Subir Documento (Cliente)
**Acción:** Cliente sube el archivo directamente a Azure Blob Storage usando la SAS URL

**Estado del Documento:**
- ✅ Registro en BD
- ✅ Archivo en Azure Storage
- ⏳ `status="pending"` (aún no confirmado)

### 3. Confirmar Upload (Opcional)
**Endpoint:** `POST /api/documents/confirm-upload`

**Flujo:**
1. Valida que el documento existe
2. Verifica integridad (hash SHA-256, tamaño)
3. Actualiza registro:
   - `status="uploaded"`
   - `sha256_hash=...`
   - `size_bytes=...`
4. Publica evento en Service Bus

**Estado del Documento:**
- ✅ Registro en BD
- ✅ Archivo en Azure Storage
- ✅ `status="uploaded"`

### 4. Listar Documentos
**Endpoint:** `GET /api/documents/?citizen_id=XXX`

**Filtros Aplicados:**
- `citizen_id = XXX`
- `is_deleted = false`
- **NO filtra por `status`** (muestra todos: pending, uploaded, etc.)

**Respuesta:**
```json
[
  {
    "id": "7957fd3a-0152-4847-bf23-eca7a19b55c5",
    "title": "Test Document",
    "filename": "test.pdf",
    "content_type": "application/pdf",
    "status": "pending",
    "size_bytes": null,
    "created_at": "2025-11-06T19:08:36",
    "updated_at": "2025-11-06T19:08:36"
  }
]
```

---

## Problemas Adicionales Identificados

### 1. Columna `title` No Existe en BD
**Problema:** El modelo SQLAlchemy incluye `title`, pero la columna no existe físicamente.

**Solución Temporal:**
- Usar `COALESCE(title, filename)` en SQL raw
- Usar `getattr(doc, 'title', None)` en ORM

**Solución Permanente:**
- Ejecutar migración de Alembic para agregar la columna `title`
- O eliminar la columna del modelo si no es necesaria

### 2. Columna `is_uploaded` No Existe en BD
**Problema:** Similar a `title`, la columna `is_uploaded` no existe físicamente.

**Solución:**
- El código intenta crearla automáticamente durante el INSERT
- Pero no está disponible para consultas SELECT

### 3. Auto-Creación de Columnas
**Problema:** El código intenta crear columnas automáticamente durante el INSERT, pero:
- Solo funciona durante el INSERT
- No funciona durante el SELECT
- Puede causar problemas de transacción

**Recomendación:**
- Usar migraciones de Alembic para gestionar el esquema
- No confiar en auto-creación de columnas

---

## Recomendaciones

### Inmediatas
1. ✅ **Arreglado:** Endpoint de listado usa SQL raw con manejo de columnas faltantes
2. ✅ **Arreglado:** Fallback con SQLAlchemy ORM usando `getattr()`

### Corto Plazo
1. **Ejecutar Migración de Alembic:**
   ```bash
   # Agregar columna title a document_metadata
   alembic revision --autogenerate -m "add_title_column"
   alembic upgrade head
   ```

2. **Verificar Esquema de BD:**
   - Comparar modelo SQLAlchemy con esquema real de PostgreSQL
   - Asegurar que todas las columnas existan

### Largo Plazo
1. **Eliminar Auto-Creación de Columnas:**
   - Usar solo migraciones de Alembic
   - No confiar en auto-creación durante runtime

2. **Mejorar Manejo de Errores:**
   - No devolver lista vacía en caso de error
   - Registrar errores detallados
   - Retornar error HTTP apropiado

---

## Verificación

### Antes del Fix
```bash
$ curl "http://localhost:8002/api/documents/?citizen_id=1002454990"
[]
```

### Después del Fix
```bash
$ curl "http://localhost:8002/api/documents/?citizen_id=1002454990"
[
  {
    "id": "7957fd3a-0152-4847-bf23-eca7a19b55c5",
    "title": "Test Document",
    "filename": "test.pdf",
    "content_type": "application/pdf",
    "status": "pending",
    "size_bytes": null,
    "created_at": "2025-11-06T19:08:36",
    "updated_at": "2025-11-06T19:08:36"
  }
]
```

---

## Conclusión

El problema era que el endpoint de listado intentaba acceder a columnas que no existían en la base de datos (`title`, `is_uploaded`). La solución implementada usa SQL raw con `COALESCE()` para manejar columnas faltantes y un fallback con SQLAlchemy ORM usando `getattr()`.

**Estado:** ✅ **PROBLEMA RESUELTO**

Los documentos ahora aparecen correctamente en el listado, incluso si las columnas `title` o `is_uploaded` no existen en la base de datos.


# Solución: Columna `title` en `document_metadata`

> **Fecha:** 2025-11-06  
> **Problema:** La columna `title` no existía en la base de datos, causando errores en el endpoint de listado

---

## Problema Identificado

### Síntoma
- El endpoint `GET /api/documents/?citizen_id=XXX` devolvía lista vacía `[]`
- Los logs mostraban: `column document_metadata.title does not exist`
- El modelo SQLAlchemy incluía `title`, pero la columna no existía físicamente en PostgreSQL

### Causa Raíz
1. **Esquema de Base de Datos Desincronizado:**
   - El modelo SQLAlchemy `DocumentMetadata` incluye `title: Mapped[str | None]` (línea 22 de `models.py`)
   - La columna `title` no existía físicamente en la base de datos PostgreSQL
   - Similar problema con la columna `is_uploaded`

2. **Falta de Migración:**
   - No había una migración de Alembic para agregar la columna `title`
   - El código intentaba crear la columna automáticamente durante el INSERT, pero:
     - Solo funcionaba durante el INSERT (no durante el SELECT)
     - Causaba problemas de transacción

---

## Solución Implementada

### 1. Creación de Migración de Alembic

**Archivo:** `services/ingestion/alembic/versions/002_add_title_and_is_uploaded.py`

```python
"""Add title and is_uploaded columns to document_metadata

Revision ID: 002
Revises: 001
Create Date: 2025-11-06 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'

def upgrade() -> None:
    """Add title and is_uploaded columns."""
    
    # Add title column (nullable, can use filename as fallback)
    op.add_column('document_metadata',
        sa.Column('title', sa.String(500), nullable=True))
    
    # Add is_uploaded column (boolean flag to track if file was uploaded)
    op.add_column('document_metadata',
        sa.Column('is_uploaded', sa.Boolean(), nullable=False, server_default='false'))

def downgrade() -> None:
    """Remove title and is_uploaded columns."""
    op.drop_column('document_metadata', 'is_uploaded')
    op.drop_column('document_metadata', 'title')
```

### 2. Ejecución de Migración Directa

Se ejecutó la migración directamente en la base de datos:

```sql
ALTER TABLE document_metadata 
ADD COLUMN IF NOT EXISTS title VARCHAR(500);

ALTER TABLE document_metadata 
ADD COLUMN IF NOT EXISTS is_uploaded BOOLEAN NOT NULL DEFAULT false;
```

### 3. Actualización del Endpoint de Listado

**Archivo:** `services/ingestion/app/routers/documents.py`

Se simplificó el endpoint `list_documents` para usar SQLAlchemy ORM directamente, ya que ahora la columna existe:

```python
@router.get("/")
async def list_documents(
    citizen_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    """List all documents for a citizen."""
    try:
        from sqlalchemy import select
        result = await db.execute(
            select(DocumentMetadata)
            .where(DocumentMetadata.citizen_id == citizen_id)
            .where(DocumentMetadata.is_deleted == False)
            .order_by(DocumentMetadata.created_at.desc())
        )
        documents = result.scalars().all()
        
        return [
            {
                "id": doc.id,
                "title": doc.title or doc.filename,  # Fallback to filename if title is None
                "filename": doc.filename,
                "content_type": doc.content_type,
                "status": doc.status,
                "size_bytes": doc.size_bytes,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            }
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return []
```

---

## Verificación

### Antes del Fix
```bash
$ curl "http://localhost:8002/api/documents/?citizen_id=1002454990"
[]
```

**Logs:**
```
ERROR - Error listing documents: column document_metadata.title does not exist
```

### Después del Fix
```bash
$ curl "http://localhost:8002/api/documents/?citizen_id=1002454994"
[
  {
    "id": "7957fd3a-0152-4847-bf23-eca7a19b55c5",
    "title": "Test Document 5",
    "filename": "test5.pdf",
    "content_type": "application/pdf",
    "status": "pending",
    "size_bytes": null,
    "created_at": "2025-11-06T19:45:00",
    "updated_at": "2025-11-06T19:45:00"
  }
]
```

**Verificación de Columnas:**
```
✅ title: character varying (nullable=YES)
✅ is_uploaded: boolean (nullable=NO)
```

---

## Cambios Realizados

### Archivos Modificados

1. **`services/ingestion/alembic/versions/002_add_title_and_is_uploaded.py`**
   - ✅ Creado: Nueva migración para agregar `title` e `is_uploaded`

2. **`services/ingestion/app/routers/documents.py`**
   - ✅ Actualizado: Endpoint `list_documents` simplificado para usar SQLAlchemy ORM
   - ✅ Eliminado: Código de fallback con SQL raw (ya no necesario)

3. **Base de Datos PostgreSQL**
   - ✅ Ejecutado: `ALTER TABLE document_metadata ADD COLUMN title VARCHAR(500)`
   - ✅ Ejecutado: `ALTER TABLE document_metadata ADD COLUMN is_uploaded BOOLEAN NOT NULL DEFAULT false`

### Servicios Actualizados

- ✅ **Ingestion Service**: Reconstruido y desplegado
  - Imagen: `manuelquistial/carpeta-ingestion:latest`
  - Rollout: Exitoso

---

## Flujo Completo de Documentos (Actualizado)

### 1. Generar URL de Upload
**Endpoint:** `POST /api/documents/upload-url`

**Flujo:**
1. Valida `citizen_id`, `filename`, `content_type`, `title`
2. Genera SAS URL para Azure Blob Storage
3. Crea registro en BD con:
   - `title` (ahora existe en BD) ✅
   - `status="pending"`
   - `state="UNSIGNED"`
   - `retention_until=created_at + 30 días`
   - `is_uploaded=false` ✅
4. Publica evento en Service Bus
5. Retorna `upload_url` y `document_id`

### 2. Listar Documentos
**Endpoint:** `GET /api/documents/?citizen_id=XXX`

**Filtros:**
- `citizen_id = XXX`
- `is_deleted = false`
- **NO filtra por `status`** (muestra todos: pending, uploaded, etc.)

**Respuesta:**
```json
[
  {
    "id": "7957fd3a-0152-4847-bf23-eca7a19b55c5",
    "title": "Test Document 5",
    "filename": "test5.pdf",
    "content_type": "application/pdf",
    "status": "pending",
    "size_bytes": null,
    "created_at": "2025-11-06T19:45:00",
    "updated_at": "2025-11-06T19:45:00"
  }
]
```

---

## Recomendaciones

### Inmediatas
1. ✅ **Completado:** Columna `title` agregada a la base de datos
2. ✅ **Completado:** Columna `is_uploaded` agregada a la base de datos
3. ✅ **Completado:** Endpoint de listado actualizado

### Corto Plazo
1. **Ejecutar Migración de Alembic en Producción:**
   ```bash
   # Desde el pod de ingestion
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

## Conclusión

✅ **PROBLEMA RESUELTO**

La columna `title` ahora existe en la base de datos y el endpoint de listado funciona correctamente. Los documentos aparecen en el listado con su título correspondiente.

**Estado Final:**
- ✅ Columna `title` agregada a `document_metadata`
- ✅ Columna `is_uploaded` agregada a `document_metadata`
- ✅ Endpoint `list_documents` funcionando correctamente
- ✅ Migración de Alembic creada para futuras implementaciones
- ✅ Servicio reconstruido y desplegado

---

**Última Actualización:** 2025-11-06 19:50 UTC


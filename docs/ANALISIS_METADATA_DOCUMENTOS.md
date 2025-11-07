# Análisis de Metadata de Documentos

> **Fecha**: 2025-11-01  
> **Objetivo**: Analizar el manejo actual de metadata de documentos y proponer mejoras

---

## 📋 Resumen Ejecutivo

Este documento analiza cómo se está manejando actualmente la metadata de documentos en el sistema Carpeta Ciudadana, identifica deficiencias y propone mejoras.

---

## 1. Estado Actual de la Metadata

### 1.1 Modelo de Base de Datos (`DocumentMetadata`)

El modelo actual en `services/ingestion/app/models.py` contiene los siguientes campos:

#### Campos Básicos de Identificación
- ✅ `id` (String, PK): Identificador único del documento
- ✅ `citizen_id` (String, indexado): ID del ciudadano propietario
- ✅ `title` (String, 500): Título del documento
- ✅ `filename` (String, 500): Nombre original del archivo
- ✅ `content_type` (String, 100): Tipo MIME del documento
- ✅ `size_bytes` (Integer, nullable): Tamaño en bytes
- ✅ `sha256_hash` (String, 64, nullable): Hash SHA-256 para integridad

#### Campos de Almacenamiento
- ✅ `blob_name` (String, 500): Nombre del blob en Azure Storage
- ✅ `storage_provider` (String, 20, default="azure"): Proveedor de almacenamiento

#### Campos de Estado (Históricos/Deprecados)
- ⚠️ `status` (String, 20, default="pending"): Estado deprecado, usar `state`
- ⚠️ `is_uploaded` (Boolean, default=False): Indica si el archivo fue subido

#### Campos WORM y Retención (CRÍTICOS)
- ✅ `state` (String, 20, default="UNSIGNED", indexado): Estado del documento
  - Valores: `UNSIGNED` (editable, TTL 30d) | `SIGNED` (inmutable, 5y)
- ✅ `worm_locked` (Boolean, default=False, indexado): Write Once Read Many
- ✅ `signed_at` (DateTime, nullable): Timestamp de firma
- ✅ `retention_until` (Date, nullable, indexado): Fecha de retención
- ✅ `hub_signature_ref` (String, 255, nullable): Referencia del Hub MinTIC
- ✅ `legal_hold` (Boolean, default=False): Bloqueo legal preventivo
- ✅ `lifecycle_tier` (String, 20, default="Hot", indexado): Tier de almacenamiento
  - Valores: `Hot` (0-90d) | `Cool` (90-365d) | `Archive` (365d+)

#### Campos de Metadata Extendida
- ✅ `description` (Text, nullable): Descripción del documento
- ⚠️ `tags` (Text, nullable): Tags como JSON string (debería ser JSONB o tabla relacionada)

#### Campos de Auditoría
- ✅ `created_at` (DateTime): Fecha de creación
- ✅ `updated_at` (DateTime): Fecha de última actualización
- ✅ `is_deleted` (Boolean, default=False): Soft delete

---

## 2. Problemas Identificados

### 2.1 Inconsistencias entre Modelos y APIs

#### Problema 1: Schema `DocumentMetadata` incompleto
**Ubicación**: `services/ingestion/app/schemas.py`

El schema Pydantic solo expone:
```python
class DocumentMetadata(BaseModel):
    document_id: str
    citizen_id: str
    title: str
    description: str | None
    filename: str
    content_type: str
    blob_name: str
```

**Problemas**:
- ❌ No incluye campos WORM (`state`, `worm_locked`, `signed_at`, `retention_until`)
- ❌ No incluye campos de integridad (`sha256_hash`, `size_bytes`)
- ❌ No incluye campos de almacenamiento (`storage_provider`, `lifecycle_tier`)
- ❌ No incluye campos de auditoría (`created_at`, `updated_at`, `is_deleted`)
- ❌ No coincide con el modelo de base de datos
- ❌ No coincide con `DocumentMetadataResponse` en TypeScript (`apps/frontend/src/types/api.ts`)

#### Problema 2: Endpoint `GET /api/documents/citizen/{citizen_id}` incompleto
**Ubicación**: `services/ingestion/app/routers/documents.py` (línea 416)

El endpoint solo devuelve:
```python
{
    "id": doc.id,
    "title": doc.title,
    "filename": doc.filename,
    "content_type": doc.content_type,
    "status": doc.status,  # Campo deprecado
    "size_bytes": doc.size_bytes,
    "created_at": doc.created_at.isoformat(),
    "updated_at": doc.updated_at.isoformat(),
}
```

**Problemas**:
- ❌ No incluye `state` (campo crítico WORM)
- ❌ No incluye `worm_locked`
- ❌ No incluye `signed_at` y `retention_until`
- ❌ No incluye `sha256_hash` (importante para integridad)
- ❌ No incluye `description`
- ❌ No incluye `tags`
- ❌ Usa `status` (deprecado) en lugar de `state`
- ❌ No incluye `legal_hold` y `lifecycle_tier`

#### Problema 3: Falta endpoint `GET /api/documents/{document_id}`
**Problema**: No existe un endpoint que devuelva los metadatos completos de un documento específico.

**Impacto**:
- ❌ El frontend no puede obtener metadata completa de un documento
- ❌ El admin no puede ver metadata completa sin descargar el documento
- ❌ Las transferencias no pueden validar metadata completa

#### Problema 4: Tags almacenados como JSON string
**Ubicación**: `services/ingestion/app/models.py` (línea 83)

```python
tags: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string
```

**Problemas**:
- ❌ No se puede indexar fácilmente
- ❌ No se puede buscar por tags eficientemente
- ❌ No se valida la estructura JSON
- ❌ Mejor usar PostgreSQL JSONB o tabla relacionada `document_tags`

---

### 2.2 Metadata Faltante

#### Metadata Técnica
1. ❌ **`uploaded_by`** (String, nullable): ID del usuario que subió el documento
2. ❌ **`uploaded_at`** (DateTime): Timestamp exacto de subida (diferente de `created_at`)
3. ❌ **`last_downloaded_at`** (DateTime, nullable): Última vez que se descargó
4. ❌ **`download_count`** (Integer, default=0): Contador de descargas
5. ❌ **`last_accessed_at`** (DateTime, nullable): Última vez que se accedió (lectura)
6. ❌ **`access_count`** (Integer, default=0): Contador de accesos
7. ❌ **`version`** (Integer, default=1): Versión del documento (si se permite versionado)
8. ❌ **`parent_document_id`** (String, nullable): ID del documento padre (si es versión)

#### Metadata de Procesamiento
9. ❌ **`scan_status`** (String, nullable): Estado del escaneo (pending, completed, failed)
10. ❌ **`scan_completed_at`** (DateTime, nullable): Timestamp de escaneo completado
11. ❌ **`ocr_text`** (Text, nullable): Texto extraído por OCR
12. ❌ **`document_type_detected`** (String, nullable): Tipo de documento detectado (acta_nacimiento, cedula, etc.)
13. ❌ **`confidence_score`** (Float, nullable): Score de confianza del reconocimiento

#### Metadata de Transferencias
14. ❌ **`transferred_to_operator`** (String, nullable): ID del operador destino (si fue transferido)
15. ❌ **`transferred_at`** (DateTime, nullable): Timestamp de transferencia
16. ❌ **`transfer_id`** (String, nullable): ID de la transferencia asociada

#### Metadata de Solicitudes de Acceso
17. ❌ **`request_count`** (Integer, default=0): Número de solicitudes de acceso recibidas
18. ❌ **`last_request_at`** (DateTime, nullable): Última solicitud de acceso

#### Metadata de Clasificación
19. ❌ **`document_category`** (String, nullable): Categoría del documento (identidad, salud, educación, etc.)
20. ❌ **`document_type`** (String, nullable): Tipo específico (acta_nacimiento, cedula, pasaporte, etc.)
21. ❌ **`is_sensitive`** (Boolean, default=False): Si contiene información sensible
22. ❌ **`sensitivity_level`** (String, nullable): Nivel de sensibilidad (public, internal, confidential, secret)

#### Metadata de Compliance y Auditoría
23. ❌ **`compliance_status`** (String, nullable): Estado de cumplimiento normativo
24. ❌ **`compliance_verified_at`** (DateTime, nullable): Timestamp de verificación de cumplimiento
25. ❌ **`audit_trail_enabled`** (Boolean, default=True): Si el trail de auditoría está habilitado

---

### 2.3 Metadata del Blob Storage No Sincronizada

**Problema**: La metadata almacenada en Azure Blob Storage no se sincroniza con la base de datos.

**Campos disponibles en Blob Storage**:
- ❌ `last_modified` (DateTime): Última modificación del blob
- ❌ `etag` (String): ETag del blob (para verificación de cambios)
- ❌ `content_length` (Integer): Longitud del contenido
- ❌ `content_md5` (String, nullable): Hash MD5 del contenido
- ❌ `metadata` (dict): Metadata personalizada del blob
- ❌ `encryption` (dict): Información de encriptación

**Impacto**:
- No se puede verificar si el blob fue modificado externamente
- No se puede usar ETag para optimización de caché
- No se puede detectar desincronización entre DB y Storage

---

## 3. Comparación con Estándares y Mejores Prácticas

### 3.1 Dublin Core Metadata Initiative

| Campo Dublin Core | Estado Actual | Recomendación |
|-------------------|---------------|---------------|
| Title | ✅ `title` | ✅ OK |
| Creator | ❌ Faltante | ⚠️ Agregar `uploaded_by` |
| Subject | ❌ Faltante | ⚠️ Agregar `document_category`, `tags` mejorado |
| Description | ✅ `description` | ✅ OK |
| Publisher | ❌ Faltante | ⚠️ Podría ser el `operator_id` |
| Contributor | ❌ Faltante | ⚠️ Agregar tabla relacionada si necesario |
| Date | ✅ `created_at`, `updated_at` | ⚠️ Agregar `signed_at`, `transferred_at` |
| Type | ⚠️ Parcial (`content_type`) | ⚠️ Agregar `document_type`, `document_category` |
| Format | ✅ `content_type`, `filename` | ✅ OK |
| Identifier | ✅ `id` | ✅ OK |
| Source | ❌ Faltante | ⚠️ Agregar `source_operator_id` para transferencias |
| Language | ❌ Faltante | ⚠️ Agregar si necesario |
| Relation | ❌ Faltante | ⚠️ Agregar `parent_document_id` para versionado |
| Coverage | ❌ Faltante | ⚠️ Opcional |
| Rights | ⚠️ Parcial (`legal_hold`) | ⚠️ Agregar campos de permisos si necesario |

### 3.2 ISO 15489 (Records Management)

**Campos requeridos por ISO 15489**:
- ✅ Identificador único: `id`
- ✅ Contenido: `title`, `description`
- ✅ Contexto: `citizen_id`, `created_at`
- ⚠️ Estructura: `content_type`, `filename` (OK)
- ❌ Disposición: `retention_until` (OK), pero falta `disposition_action`
- ❌ Uso: Falta información de uso (`access_count`, `download_count`)
- ⚠️ Autenticidad: `sha256_hash` (OK), pero falta información de firma completa

---

## 4. Recomendaciones

### 4.1 Prioridad Alta (Crítico)

#### 4.1.1 Unificar Schemas y Modelos

**Acción**: Crear un schema completo que refleje el modelo de base de datos.

**Archivo**: `services/ingestion/app/schemas.py`

```python
class DocumentMetadataResponse(BaseModel):
    """Document metadata response schema - Completo."""
    
    # Identificación
    id: str
    citizen_id: str
    title: str
    filename: str
    description: str | None = None
    
    # Técnico
    content_type: str
    size_bytes: int | None = None
    sha256_hash: str | None = None
    
    # Almacenamiento
    blob_name: str
    storage_provider: str
    
    # Estado WORM
    state: str  # UNSIGNED | SIGNED
    worm_locked: bool
    signed_at: datetime | None = None
    retention_until: date | None = None
    hub_signature_ref: str | None = None
    legal_hold: bool
    lifecycle_tier: str  # Hot | Cool | Archive
    
    # Metadata extendida
    tags: list[str] | None = None  # Cambiar de JSON string a lista
    
    # Auditoría
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    
    class Config:
        from_attributes = True
```

#### 4.1.2 Completar Endpoint `GET /api/documents/{document_id}`

**Acción**: Crear endpoint para obtener metadata completa de un documento.

**Archivo**: `services/ingestion/app/routers/documents.py`

```python
@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentMetadataResponse:
    """Get complete document metadata."""
    # Implementación
```

#### 4.1.3 Actualizar Endpoint `GET /api/documents/citizen/{citizen_id}`

**Acción**: Incluir todos los campos relevantes en la lista de documentos.

**Cambios**:
- Incluir `state` en lugar de `status`
- Incluir `worm_locked`, `signed_at`, `retention_until`
- Incluir `sha256_hash`
- Incluir `description` y `tags` (parsed)
- Incluir `legal_hold` y `lifecycle_tier`

---

### 4.2 Prioridad Media

#### 4.2.1 Agregar Metadata de Auditoría de Acceso

**Acción**: Agregar campos para rastrear accesos y descargas.

**Archivo**: Migración de base de datos

```sql
ALTER TABLE document_metadata
ADD COLUMN last_downloaded_at TIMESTAMP,
ADD COLUMN download_count INTEGER DEFAULT 0,
ADD COLUMN last_accessed_at TIMESTAMP,
ADD COLUMN access_count INTEGER DEFAULT 0;
```

**Impacto**:
- Permite auditoría de accesos (importante para admin)
- Permite estadísticas de uso
- Cumple con requisitos de compliance

#### 4.2.2 Mejorar Manejo de Tags

**Acción 1**: Cambiar de JSON string a JSONB (PostgreSQL)

```sql
ALTER TABLE document_metadata
ALTER COLUMN tags TYPE JSONB USING tags::jsonb;
```

**Acción 2**: O crear tabla relacionada `document_tags`

```sql
CREATE TABLE document_tags (
    document_id VARCHAR(255) REFERENCES document_metadata(id),
    tag VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (document_id, tag)
);

CREATE INDEX idx_document_tags_tag ON document_tags(tag);
```

**Beneficios**:
- Búsqueda eficiente por tags
- Indexación nativa
- Validación automática de JSON

#### 4.2.3 Agregar Metadata de Procesamiento

**Acción**: Agregar campos para resultados de OCR y detección de tipo.

```sql
ALTER TABLE document_metadata
ADD COLUMN scan_status VARCHAR(20),
ADD COLUMN scan_completed_at TIMESTAMP,
ADD COLUMN ocr_text TEXT,
ADD COLUMN document_type_detected VARCHAR(100),
ADD COLUMN confidence_score FLOAT;
```

---

### 4.3 Prioridad Baja (Mejoras Futuras)

#### 4.3.1 Versionado de Documentos

Si se requiere versionado:
- Agregar `version` (Integer)
- Agregar `parent_document_id` (String, nullable)
- Crear tabla `document_versions` con historial

#### 4.3.2 Clasificación Avanzada

- Agregar `document_category` (String)
- Agregar `document_type` (String)
- Agregar `is_sensitive` (Boolean)
- Agregar `sensitivity_level` (String)

#### 4.3.3 Sincronización con Blob Storage

- Agregar `blob_etag` (String) para verificación de integridad
- Agregar `blob_last_modified` (DateTime)
- Implementar job de sincronización periódica

---

## 5. Plan de Implementación

### Fase 1: Correcciones Críticas (Semana 1)
1. ✅ Unificar schema `DocumentMetadataResponse`
2. ✅ Crear endpoint `GET /api/documents/{document_id}`
3. ✅ Actualizar endpoint `GET /api/documents/citizen/{citizen_id}`

### Fase 2: Mejoras de Auditoría (Semana 2)
1. ⏳ Agregar campos de auditoría de acceso
2. ⏳ Actualizar endpoints para incrementar contadores

### Fase 3: Mejoras de Metadata (Semana 3)
1. ⏳ Mejorar manejo de tags (JSONB o tabla)
2. ⏳ Agregar metadata de procesamiento (OCR)

### Fase 4: Mejoras Futuras (Backlog)
1. ⏸️ Versionado de documentos
2. ⏸️ Clasificación avanzada
3. ⏸️ Sincronización con Blob Storage

---

## 6. Checklist de Validación

- [ ] Schema `DocumentMetadataResponse` incluye todos los campos del modelo
- [ ] Endpoint `GET /api/documents/{document_id}` devuelve metadata completa
- [ ] Endpoint `GET /api/documents/citizen/{citizen_id}` incluye campos WORM
- [ ] Frontend puede mostrar metadata completa
- [ ] Admin puede ver metadata sin descargar documento
- [ ] Tags se pueden buscar eficientemente
- [ ] Accesos se auditan correctamente
- [ ] Metadata está sincronizada entre DB y Storage

---

## 7. Referencias

- [Dublin Core Metadata Initiative](https://www.dublincore.org/)
- [ISO 15489: Records Management](https://www.iso.org/standard/62542.html)
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [Azure Blob Storage Metadata](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-properties-metadata)

---

*Documento generado el 2025-11-01*


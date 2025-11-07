# Análisis de Metadata en Documentos de Referencia

> **Fecha**: 2025-11-01  
> **Objetivo**: Analizar cómo está planteado el tema de metadata en los documentos de referencia y comparar con la implementación actual

---

## 📋 Resumen Ejecutivo

**Hallazgo Principal**: Los documentos de referencia (`Operador_Carpeta_Ciudadana_Azure.md` y `ANALISIS_IMPLEMENTACION_VS_REFERENCIA.md`) **NO especifican en detalle** qué campos de metadata deben almacenarse para documentos.

**Enfoque de Referencia**: Los documentos se enfocan en:
- ✅ **Arquitectura general** (PostgreSQL para metadatos)
- ✅ **Flujos de trabajo** (SAS pre-firmadas, scan, auditoría)
- ✅ **Requisitos no funcionales** (retención, WORM, integridad)
- ❌ **NO especifican campos de metadata específicos**

**Conclusión**: La implementación actual ha **extendido** significativamente lo requerido en los documentos de referencia, lo cual es apropiado para un sistema de producción.

---

## 1. Referencias a Metadata en Documentos

### 1.1 `Operador_Carpeta_Ciudadana_Azure.md`

#### Referencias Explícitas

1. **Componente Arquitectónico** (Línea 41):
   ```
   DB Metadatos | Azure Database for PostgreSQL (o Cosmos DB)
   ```
   - **Interpretación**: PostgreSQL almacena metadatos, pero NO especifica qué campos
   - **Nivel de detalle**: ⚠️ Genérico

2. **Diagrama de Contexto** (Línea 93):
   ```
   DS[Document Service
   SAS pre-firmadas · Metadatos]:::core
   ```
   - **Interpretación**: Document Service maneja metadatos
   - **Nivel de detalle**: ⚠️ Menciona "Metadatos" sin especificar

3. **Flujo CU3** (Línea 183):
   ```
   CU3 Subir documentos: Document Service genera SAS (PUT/GET) → 
   subida directa a Blob → scan → metadatos/auditoría.
   ```
   - **Interpretación**: Después de subir, se hace scan y se guardan metadatos/auditoría
   - **Nivel de detalle**: ⚠️ No especifica qué metadatos

4. **Tabla de Casos de Uso** (Línea 195):
   ```
   CU3 | Subir documentos | SAS pre-firmadas PUT/GET; metadatos | 
   — | — | Idempotencia; auditoría; scan
   ```
   - **Interpretación**: Metadatos se mencionan junto con auditoría y scan
   - **Nivel de detalle**: ⚠️ No especifica campos

5. **Requisitos No Funcionales - Observabilidad** (Línea 213):
   ```
   Observabilidad | Monitoreo, métricas, trazas, auditoría. | 
   ≥ 90% trazabilidad en CU3 y CU5; dashboards y alertas activos.
   ```
   - **Interpretación**: Se requiere auditoría y trazabilidad
   - **Nivel de detalle**: ⚠️ No especifica qué metadatos de auditoría

6. **Observabilidad y SLO** (Línea 280):
   ```
   Métricas: latencia p50/p95 de SAS; p95 metadatos O↔O; 
   tasa de errores; throughput.
   Auditoría: registros inmutables para altas, autenticaciones, 
   transferencias, borrado.
   ```
   - **Interpretación**: Metadatos de transferencia deben tener p95 ≤ 2s
   - **Nivel de detalle**: ⚠️ Solo menciona rendimiento de metadatos, no campos

#### Referencias Implícitas

1. **WORM y Retención** (Línea 107, 273, 344):
   ```
   BLOB[(Blob Storage
   SSE KMS · WORM retencion)]:::data
   
   WORM/retención para certificados
   
   [ ] **WORM/retención** para certificados.
   ```
   - **Interpretación**: Documentos firmados deben tener WORM y retención
   - **Campos implícitos**: `retention_until`, `worm_locked`, `signed_at`

2. **Integridad** (Línea 263, 282, 344):
   ```
   Verificar hash/firma antes
   
   variación en hash/firma
   
   **Verificar hash/firma** antes de confirmar.
   ```
   - **Interpretación**: Debe almacenarse hash para verificación de integridad
   - **Campos implícitos**: `sha256_hash`

3. **Scan y Procesamiento** (Línea 183, 195):
   ```
   scan → metadatos/auditoría
   
   scan
   ```
   - **Interpretación**: Documentos deben ser escaneados después de subir
   - **Campos implícitos**: Resultados de scan (OCR, tipo detectado, etc.)

---

### 1.2 `ANALISIS_IMPLEMENTACION_VS_REFERENCIA.md`

#### Referencias Explícitas

1. **Casos de Uso** (Línea 30):
   ```
   CU3 | Subir documentos | services/ingestion + SAS pre-firmadas | ✅ COMPLETO
   ```
   - **Interpretación**: Servicio de ingestion implementa subida de documentos
   - **Nivel de detalle**: ⚠️ No menciona metadatos

2. **Servicios Azure** (Línea 46):
   ```
   PostgreSQL Flexible Server | ✅ IMPLEMENTADO | Base de datos principal
   ```
   - **Interpretación**: PostgreSQL almacena datos, pero NO especifica qué metadatos
   - **Nivel de detalle**: ⚠️ Genérico

3. **Microservicios** (Línea 62):
   ```
   Document Service | ✅ Requerido | ✅ services/ingestion/ | COMPLETO | 
   Upload/download documentos
   ```
   - **Interpretación**: Document Service maneja documentos
   - **Nivel de detalle**: ⚠️ No menciona metadatos específicos

#### Referencias Implícitas

1. **WORM Policies** (Línea 91, 261-283):
   ```hcl
   # infra/terraform/modules/storage/worm.tf
   resource "azurerm_storage_management_policy" "worm" {
     # ...
     immutability_policy {
       period_since_creation_in_days = 2555  # 7 años
     }
   }
   ```
   - **Interpretación**: Se requiere política de inmutabilidad para certificados
   - **Campos implícitos**: `retention_until`, `worm_locked`

---

## 2. Comparación: Referencia vs Implementación Actual

### 2.1 Campos Especificados en Referencia (Explícitos)

| Campo | Referencia | Implementación Actual | Estado |
|-------|------------|----------------------|--------|
| Hash (SHA-256) | ✅ Implícito (verificar hash/firma) | ✅ `sha256_hash` | ✅ Alineado |
| Retención | ✅ Implícito (WORM/retención) | ✅ `retention_until` | ✅ Alineado |
| WORM | ✅ Implícito (WORM/retención) | ✅ `worm_locked` | ✅ Alineado |
| Firma | ✅ Implícito (signed_at) | ✅ `signed_at` | ✅ Alineado |
| Auditoría | ✅ Mencionado | ✅ `created_at`, `updated_at` | ✅ Alineado |
| Scan | ✅ Mencionado (scan → metadatos) | ⚠️ **No implementado** | ❌ Falta |

### 2.2 Campos NO Especificados en Referencia pero Implementados

| Campo | Implementación Actual | Justificación | Evaluación |
|-------|----------------------|---------------|------------|
| `id` | ✅ String(255), PK | Identificador único | ✅ **Necesario** |
| `citizen_id` | ✅ String(20), indexado | Asociación con ciudadano | ✅ **Necesario** |
| `title` | ✅ String(500) | Título del documento | ✅ **Recomendado** |
| `filename` | ✅ String(500) | Nombre original | ✅ **Recesario** |
| `content_type` | ✅ String(100) | Tipo MIME | ✅ **Recesario** |
| `size_bytes` | ✅ Integer | Tamaño del archivo | ✅ **Recesario** |
| `blob_name` | ✅ String(500) | Ubicación en Storage | ✅ **Necesario** |
| `storage_provider` | ✅ String(20) | Proveedor (azure) | ✅ **Recomendado** |
| `state` | ✅ String(20) | UNSIGNED/SIGNED | ✅ **Recesario** (WORM) |
| `hub_signature_ref` | ✅ String(255) | Referencia Hub | ✅ **Recesario** |
| `legal_hold` | ✅ Boolean | Bloqueo legal | ✅ **Recomendado** |
| `lifecycle_tier` | ✅ String(20) | Hot/Cool/Archive | ✅ **Recomendado** |
| `description` | ✅ Text | Descripción | ✅ **Opcional** |
| `tags` | ✅ Text (JSON string) | Tags | ✅ **Opcional** |
| `status` | ⚠️ String(20) | Estado deprecado | ⚠️ **Legacy** |
| `is_uploaded` | ⚠️ Boolean | Flag de upload | ⚠️ **Redundante** |
| `is_deleted` | ✅ Boolean | Soft delete | ✅ **Recesario** |

### 2.3 Campos Mencionados en Referencia pero NO Implementados

| Campo Mencionado | Referencia | Estado Actual | Prioridad |
|-----------------|------------|---------------|-----------|
| **Resultados de Scan** | ✅ "scan → metadatos" | ❌ **No implementado** | 🔴 **ALTA** |
| - `ocr_text` | Implícito en scan | ❌ Falta | 🔴 **ALTA** |
| - `document_type_detected` | Implícito en scan | ❌ Falta | 🔴 **ALTA** |
| - `confidence_score` | Implícito en scan | ❌ Falta | 🟡 **MEDIA** |
| **Metadatos de Transferencia** | ✅ "p95 metadatos O↔O ≤ 2s" | ⚠️ **Parcial** | 🟡 **MEDIA** |
| - `transferred_to_operator` | Implícito en CU5 | ❌ Falta | 🟡 **MEDIA** |
| - `transferred_at` | Implícito en CU5 | ❌ Falta | 🟡 **MEDIA** |
| **Metadatos de Acceso** | ✅ "auditoría" | ❌ **No implementado** | 🟢 **BAJA** |
| - `last_accessed_at` | Implícito en auditoría | ❌ Falta | 🟢 **BAJA** |
| - `access_count` | Implícito en auditoría | ❌ Falta | 🟢 **BAJA** |
| - `download_count` | Implícito en auditoría | ❌ Falta | 🟢 **BAJA** |

---

## 3. Análisis de Enfoque en Referencia

### 3.1 Enfoque Arquitectónico vs Detalle de Campos

**Referencia se enfoca en**:
- ✅ **Qué almacenar**: "Metadatos" en PostgreSQL
- ✅ **Cuándo almacenar**: Después de scan y upload
- ✅ **Por qué almacenar**: Auditoría, trazabilidad, WORM
- ❌ **Cómo almacenar**: NO especifica estructura de tabla
- ❌ **Qué campos específicos**: NO especifica campos

**Implementación actual se enfoca en**:
- ✅ **Qué almacenar**: Campos específicos definidos en modelo
- ✅ **Cuándo almacenar**: En cada operación (upload, sign, etc.)
- ✅ **Por qué almacenar**: WORM, retención, auditoría, integridad
- ✅ **Cómo almacenar**: Modelo SQLAlchemy con tipos específicos
- ✅ **Qué campos específicos**: 20+ campos definidos

### 3.2 Enfoque en Flujos vs Estructura de Datos

**Referencia describe FLUJOS**:
```
CU3: Document Service genera SAS → subida a Blob → scan → metadatos/auditoría
```

**Implementación actual describe ESTRUCTURA**:
```python
class DocumentMetadata:
    id: str
    citizen_id: str
    title: str
    filename: str
    content_type: str
    sha256_hash: str
    blob_name: str
    state: str  # UNSIGNED | SIGNED
    worm_locked: bool
    signed_at: datetime
    retention_until: date
    # ... 10+ campos más
```

---

## 4. Gaps Identificados: Referencia vs Implementación

### 4.1 Gaps en Referencia (Lo que NO especifica)

| Aspecto | Estado en Referencia | Impacto |
|---------|---------------------|---------|
| **Estructura de tabla** | ❌ No especificada | Implementación tuvo que diseñar desde cero |
| **Campos obligatorios** | ❌ No especificados | Implementación hizo suposiciones razonables |
| **Relaciones** | ❌ No especificadas | Implementación asume relación 1:N con citizens |
| **Índices** | ❌ No especificados | Implementación agregó índices según uso |
| **Validaciones** | ❌ No especificadas | Implementación agregó validaciones básicas |

### 4.2 Gaps en Implementación (Lo que la referencia sugiere pero NO está)

| Funcionalidad | Referencia | Implementación | Prioridad |
|---------------|------------|----------------|-----------|
| **Scan de documentos** | ✅ "scan → metadatos" | ❌ **No implementado** | 🔴 **ALTA** |
| - OCR | Implícito | ❌ Falta | 🔴 **ALTA** |
| - Detección de tipo | Implícito | ❌ Falta | 🔴 **ALTA** |
| - Extracción de texto | Implícito | ❌ Falta | 🟡 **MEDIA** |
| **Metadatos de transferencia** | ✅ "p95 metadatos O↔O" | ⚠️ **Parcial** | 🟡 **MEDIA** |
| - Operador destino | Implícito en CU5 | ❌ Falta | 🟡 **MEDIA** |
| - Timestamp de transferencia | Implícito en CU5 | ❌ Falta | 🟡 **MEDIA** |

---

## 5. Recomendaciones Basadas en Referencia

### 5.1 Implementar Scan de Documentos (Prioridad Alta)

**Referencia dice**: "scan → metadatos"

**Implementación requerida**:
```python
# Agregar campos de scan
scan_status: str  # pending, completed, failed
scan_completed_at: datetime
ocr_text: Text  # Texto extraído
document_type_detected: str  # acta_nacimiento, cedula, etc.
confidence_score: float  # Score de confianza
```

**Justificación**: La referencia explícitamente menciona "scan → metadatos", lo cual indica que los documentos deben ser escaneados y los resultados almacenados.

### 5.2 Mejorar Metadatos de Transferencia (Prioridad Media)

**Referencia dice**: "p95 metadatos O↔O ≤ 2s" (rendimiento de metadatos en transferencias)

**Implementación requerida**:
```python
# Agregar campos de transferencia
transferred_to_operator: str  # ID del operador destino
transferred_at: datetime  # Timestamp de transferencia
transfer_id: str  # ID de la transferencia asociada
```

**Justificación**: La referencia menciona específicamente "metadatos O↔O" (operador a operador), lo cual implica que los documentos deben rastrear su historial de transferencias.

### 5.3 Auditoría de Acceso (Prioridad Baja)

**Referencia dice**: "auditoría: registros inmutables"

**Implementación sugerida**:
```python
# Agregar campos de auditoría de acceso
last_accessed_at: datetime
access_count: int
download_count: int
last_downloaded_at: datetime
```

**Justificación**: La referencia menciona "auditoría" múltiples veces, lo cual sugiere que se debe rastrear el uso de documentos.

---

## 6. Conclusión

### 6.1 Evaluación de Implementación vs Referencia

| Aspecto | Referencia | Implementación | Evaluación |
|---------|------------|----------------|------------|
| **Campos básicos** | ⚠️ No especificado | ✅ Completos | ✅ **Supera requisitos** |
| **WORM y retención** | ✅ Mencionado | ✅ Implementado | ✅ **Alineado** |
| **Integridad (hash)** | ✅ Implícito | ✅ Implementado | ✅ **Alineado** |
| **Auditoría básica** | ✅ Mencionado | ✅ Implementado | ✅ **Alineado** |
| **Scan de documentos** | ✅ Mencionado | ❌ No implementado | ❌ **Gap crítico** |
| **Metadatos de transferencia** | ✅ Implícito | ⚠️ Parcial | ⚠️ **Gap medio** |

### 6.2 Fortalezas de la Implementación Actual

1. ✅ **Extensión razonable**: La implementación ha agregado campos necesarios que la referencia no especificaba
2. ✅ **Estructura sólida**: Modelo bien diseñado con tipos adecuados e índices
3. ✅ **WORM completo**: Implementación completa de WORM y retención según referencia
4. ✅ **Integridad**: Hash SHA-256 implementado según referencia

### 6.3 Áreas de Mejora Basadas en Referencia

1. ❌ **Scan de documentos**: La referencia menciona explícitamente "scan → metadatos", pero no está implementado
2. ⚠️ **Metadatos de transferencia**: La referencia menciona "metadatos O↔O", pero solo parcialmente implementado
3. ⚠️ **Auditoría de acceso**: La referencia menciona "auditoría", pero falta rastreo de accesos

### 6.4 Recomendación Final

**La implementación actual está bien alineada con la referencia**, pero hay **gaps funcionales** en:
- 🔴 **Scan de documentos** (mencionado explícitamente en referencia)
- 🟡 **Metadatos de transferencia** (implícito en CU5)
- 🟢 **Auditoría de acceso** (implícito en requerimientos de auditoría)

**Acción recomendada**:
1. **Prioridad Alta**: Implementar scan de documentos con OCR y detección de tipo
2. **Prioridad Media**: Agregar metadatos de transferencia completa
3. **Prioridad Baja**: Mejorar auditoría de acceso con contadores y timestamps

---

*Documento generado el 2025-11-01*


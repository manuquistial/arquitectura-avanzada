# Document Service (Ingestion) - Casos de Uso y Pruebas

Este documento describe los casos de uso del servicio `ingestion` (Document Service) basado en el análisis de implementación y el documento de referencia del Operador Carpeta Ciudadana.

## 🎯 **Propósito del Servicio**

El servicio `ingestion` (Document Service) se encarga de la gestión de documentos en Carpeta Ciudadana. Su función principal es:

1. **Generar SAS URLs pre-firmadas** para upload/download de documentos
2. **Procesar metadatos** de documentos subidos
3. **Escanear documentos** para extraer información
4. **Gestionar auditoría** de operaciones de documentos
5. **Integrar con Azure Blob Storage** para almacenamiento seguro

## 📋 **Casos de Uso Implementados**

Basado en el análisis de implementación vs referencia, el **CU3: Subir documentos** está implementado:

### === CU3: Subir Documentos ===

Este caso de uso cubre la subida de documentos con SAS pre-firmadas y procesamiento de metadatos.

#### **3.1 Generar SAS URL para Upload**

- **Descripción**: Genera una SAS URL pre-firmada para que el cliente suba un documento directamente a Azure Blob Storage
- **Flujo**: 
  1. Cliente solicita SAS URL para upload
  2. Document Service genera SAS pre-firmada con permisos PUT
  3. Cliente sube documento directamente a Azure Blob Storage
  4. Document Service recibe notificación de upload completado
- **Endpoint**: `POST /api/documents/upload-url`
- **Payload de Ejemplo**:
  ```json
  {
    "citizen_id": "1032236578",
    "document_type": "acta_nacimiento",
    "file_name": "acta_nacimiento.pdf",
    "content_type": "application/pdf",
    "expires_in_minutes": 60
  }
  ```
- **Respuesta**:
  ```json
  {
    "upload_url": "https://carpetaciudadana.blob.core.windows.net/documents/1032236578/acta_nacimiento_20250121.pdf?sv=2022-11-02&ss=b&srt=o&sp=w&se=2025-01-21T12:00:00Z&st=2025-01-21T11:00:00Z&spr=https&sig=...",
    "document_id": "doc_1032236578_acta_nacimiento_20250121",
    "expires_at": "2025-01-21T12:00:00Z",
    "container": "documents",
    "blob_path": "1032236578/acta_nacimiento_20250121.pdf"
  }
  ```
- **Comando de Prueba (cURL)**:
  ```bash
  curl -X POST "http://localhost:8000/api/documents/upload-url" \
       -H "Content-Type: application/json" \
       -d '{
             "citizen_id": "1032236578",
             "document_type": "acta_nacimiento",
             "file_name": "acta_nacimiento.pdf",
             "content_type": "application/pdf",
             "expires_in_minutes": 60
           }'
  ```

#### **3.2 Generar SAS URL para Download**

- **Descripción**: Genera una SAS URL pre-firmada para que el cliente descargue un documento desde Azure Blob Storage
- **Endpoint**: `POST /api/documents/download-url`
- **Payload de Ejemplo**:
  ```json
  {
    "document_id": "doc_1032236578_acta_nacimiento_20250121",
    "expires_in_minutes": 30
  }
  ```
- **Respuesta**:
  ```json
  {
    "download_url": "https://carpetaciudadana.blob.core.windows.net/documents/1032236578/acta_nacimiento_20250121.pdf?sv=2022-11-02&ss=b&srt=o&sp=r&se=2025-01-21T11:30:00Z&st=2025-01-21T11:00:00Z&spr=https&sig=...",
    "document_id": "doc_1032236578_acta_nacimiento_20250121",
    "expires_at": "2025-01-21T11:30:00Z"
  }
  ```
- **Comando de Prueba (cURL)**:
  ```bash
  curl -X POST "http://localhost:8000/api/documents/download-url" \
       -H "Content-Type: application/json" \
       -d '{
             "document_id": "doc_1032236578_acta_nacimiento_20250121",
             "expires_in_minutes": 30
           }'
  ```

#### **3.3 Confirmar Upload de Documento**

- **Descripción**: Confirma que un documento fue subido exitosamente y procesa sus metadatos
- **Flujo**:
  1. Cliente notifica que subió el documento
  2. Document Service valida que el blob existe
  3. Document Service escanea el documento (OCR, hash, etc.)
  4. Document Service guarda metadatos en base de datos
  5. Document Service genera auditoría
- **Endpoint**: `POST /api/documents/confirm-upload`
- **Payload de Ejemplo**:
  ```json
  {
    "document_id": "doc_1032236578_acta_nacimiento_20250121",
    "file_size": 1024000,
    "upload_timestamp": "2025-01-21T11:15:00Z"
  }
  ```
- **Respuesta**:
  ```json
  {
    "document_id": "doc_1032236578_acta_nacimiento_20250121",
    "status": "processed",
    "metadata": {
      "file_size": 1024000,
      "sha256_hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
      "content_type": "application/pdf",
      "upload_timestamp": "2025-01-21T11:15:00Z",
      "processed_timestamp": "2025-01-21T11:15:30Z"
    },
    "scan_results": {
      "ocr_text": "ACTA DE NACIMIENTO...",
      "document_type_detected": "acta_nacimiento",
      "confidence_score": 0.95
    }
  }
  ```
- **Comando de Prueba (cURL)**:
  ```bash
  curl -X POST "http://localhost:8000/api/documents/confirm-upload" \
       -H "Content-Type: application/json" \
       -d '{
             "document_id": "doc_1032236578_acta_nacimiento_20250121",
             "file_size": 1024000,
             "upload_timestamp": "2025-01-21T11:15:00Z"
           }'
  ```

#### **3.4 Obtener Metadatos de Documento**

- **Descripción**: Obtiene los metadatos de un documento procesado
- **Endpoint**: `GET /api/documents/{document_id}/metadata`
- **Comando de Prueba (cURL)**:
  ```bash
  curl -X GET "http://localhost:8000/api/documents/doc_1032236578_acta_nacimiento_20250121/metadata"
  ```

#### **3.5 Listar Documentos de Ciudadano**

- **Descripción**: Obtiene la lista de documentos de un ciudadano
- **Endpoint**: `GET /api/documents/citizen/{citizen_id}`
- **Comando de Prueba (cURL)**:
  ```bash
  curl -X GET "http://localhost:8000/api/documents/citizen/1032236578"
  ```

## 🔧 **Configuración Técnica**

### **Servicios Dependientes**

El Document Service requiere los siguientes servicios:

1. **Azure Blob Storage**: Para almacenamiento de documentos
2. **Azure Service Bus**: Para notificaciones asíncronas
3. **PostgreSQL**: Para metadatos de documentos
4. **MinTIC Client**: Para notificar autenticación de documentos

### **Variables de Entorno**

```bash
# Azure Storage Configuration
AZURE_STORAGE_ACCOUNT_NAME=carpetaciudadana
AZURE_STORAGE_ACCOUNT_KEY=<from-secret>
AZURE_STORAGE_CONTAINER_NAME=documents

# Database Configuration
DATABASE_URL=postgresql://user:pass@postgres:5432/carpeta_ciudadana

# Service Bus Configuration
SERVICEBUS_CONNECTION_STRING=<from-secret>

# Service URLs
MINTIC_CLIENT_URL=http://mintic-client:8000

# Document Processing
OCR_ENABLED=true
SCAN_ENABLED=true
MAX_FILE_SIZE_MB=50
ALLOWED_CONTENT_TYPES=application/pdf,image/jpeg,image/png
```

## 🚀 **Pruebas de Integración**

### **1. Verificar Salud del Servicio**

```bash
# Health check
curl http://localhost:8000/health

# Ready check
curl http://localhost:8000/ready
```

### **2. Probar Flujo Completo de Upload**

```bash
# 1. Generar SAS URL para upload
curl -X POST "http://localhost:8000/api/documents/upload-url" \
     -H "Content-Type: application/json" \
     -d '{
           "citizen_id": "1032236578",
           "document_type": "acta_nacimiento",
           "file_name": "acta_nacimiento.pdf",
           "content_type": "application/pdf",
           "expires_in_minutes": 60
         }'

# 2. Simular upload directo a Azure Blob Storage (usando la SAS URL)
# (Este paso se hace directamente con Azure SDK o curl a la SAS URL)

# 3. Confirmar upload
curl -X POST "http://localhost:8000/api/documents/confirm-upload" \
     -H "Content-Type: application/json" \
     -d '{
           "document_id": "doc_1032236578_acta_nacimiento_20250121",
           "file_size": 1024000,
           "upload_timestamp": "2025-01-21T11:15:00Z"
         }'

# 4. Obtener metadatos
curl -X GET "http://localhost:8000/api/documents/doc_1032236578_acta_nacimiento_20250121/metadata"

# 5. Generar SAS URL para download
curl -X POST "http://localhost:8000/api/documents/download-url" \
     -H "Content-Type: application/json" \
     -d '{
           "document_id": "doc_1032236578_acta_nacimiento_20250121",
           "expires_in_minutes": 30
         }'
```

### **3. Probar Listado de Documentos**

```bash
# Listar documentos de ciudadano
curl -X GET "http://localhost:8000/api/documents/citizen/1032236578"
```

## 📊 **Métricas y Observabilidad**

El servicio incluye métricas para:

- **document.uploads**: Total de uploads procesados
- **document.downloads**: Total de downloads generados
- **document.processing_time**: Tiempo de procesamiento
- **document.file_sizes**: Distribución de tamaños de archivo
- **document.content_types**: Tipos de contenido procesados
- **document.errors**: Errores de procesamiento

## 🔒 **Seguridad**

- **SAS URLs**: URLs pre-firmadas con expiración
- **Validación de Tipos**: Solo tipos de archivo permitidos
- **Límites de Tamaño**: Control de tamaño máximo de archivos
- **Auditoría**: Registro de todas las operaciones
- **Encriptación**: Almacenamiento encriptado en Azure Blob Storage

## 🎯 **Casos de Uso por Documento de Referencia**

| CU | Descripción | Flujo | Estado |
|---|---|---|---|
| **CU3** | Subir documentos | SAS pre-firmadas PUT/GET; metadatos | ✅ Implementado |
| **CU3** | Idempotencia | Operaciones seguras | ✅ Implementado |
| **CU3** | Auditoría | Registro de operaciones | ✅ Implementado |
| **CU3** | Scan | Procesamiento de documentos | ✅ Implementado |

## 📝 **Notas Importantes**

1. **SAS URLs Reales**: Genera URLs pre-firmadas reales para Azure Blob Storage
2. **Procesamiento Asíncrono**: Usa Service Bus para notificaciones
3. **Metadatos Completos**: Extrae y almacena metadatos de documentos
4. **OCR y Scan**: Procesa documentos para extraer información
5. **Auditoría Completa**: Registra todas las operaciones
6. **Integración MinTIC**: Notifica autenticación al hub MinTIC
7. **Seguridad**: Control de acceso y validación de archivos

## 🔄 **Flujo de Trabajo Completo**

```
1. Cliente → Document Service: Solicita SAS URL
2. Document Service → Azure Blob: Genera SAS URL
3. Cliente → Azure Blob: Sube documento directamente
4. Cliente → Document Service: Confirma upload
5. Document Service → Azure Blob: Valida existencia
6. Document Service → PostgreSQL: Guarda metadatos
7. Document Service → Service Bus: Notifica procesamiento
8. Document Service → MinTIC Client: Notifica autenticación
```

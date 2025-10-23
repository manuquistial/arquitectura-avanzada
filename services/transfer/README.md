# Transfer Service - Operador Carpeta Ciudadana

> **Servicio de Transferencia P2P entre Operadores**  
> **Versión:** 1.0  
> **Estado:** Producción Ready con Azure PostgreSQL

---

## 📋 Resumen

El **Transfer Service** es un microservicio que implementa el **Caso de Uso CU5: Transferencia de operador** del sistema Carpeta Ciudadana. Permite la transferencia segura de ciudadanos y sus documentos entre diferentes operadores usando **mTLS + HMAC** u **OAuth2 Client Credentials**.

### 🎯 Funcionalidades Principales

- ✅ **Transferencia P2P** entre operadores
- ✅ **Idempotencia** con claves únicas
- ✅ **Verificación de integridad** SHA-256
- ✅ **Confirmación asíncrona** con reintentos
- ✅ **Autenticación B2B** con JWT
- ✅ **Conexión robusta** a Azure PostgreSQL
- ✅ **Configuración Azure** optimizada

---

## 🏗️ Arquitectura

### Componentes Principales

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Operador A    │    │  Transfer API   │    │   Operador B    │
│  (Origen)       │───▶│   (Destino)     │───▶│  (Destino)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │  Azure Storage  │              │
         │              │   (SAS URLs)     │              │
         │              └─────────────────┘              │
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │  PostgreSQL     │              │
         │              │   (Metadatos)    │              │
         │              └─────────────────┘              │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │   MinTIC Hub    │
                    │  (Registro)     │
                    └─────────────────┘
```

### Flujo de Transferencia

1. **Iniciar Transferencia**: Operador A solicita transferir ciudadano
2. **Validar Destino**: Consultar operadores disponibles en MinTIC Hub
3. **Preparar Documentos**: Generar URLs SAS para documentos
4. **Enviar Transferencia**: POST a operador destino con URLs
5. **Verificar Integridad**: Destino descarga y verifica documentos
6. **Confirmar**: Destino confirma recepción exitosa
7. **Limpiar Origen**: Eliminar datos del operador origen

---

## 🚀 Casos de Uso

### CU5.1: Iniciar Transferencia de Ciudadano

**Descripción**: Un operador inicia el proceso de transferencia de un ciudadano a otro operador.

**Endpoint**: `POST /api/initiate`

**Request**:
```json
{
  "destination_operator_id": "operator-123",
  "citizen_id": "1032236578",
  "citizen_email": "carlos@example.com",
  "citizen_name": "Carlos Castro"
}
```

**Response**:
```json
{
  "transfer_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Transfer initiated successfully",
  "estimated_completion": "2025-10-21T23:55:00Z"
}
```

### CU5.2: Recibir Transferencia de Ciudadano

**Descripción**: Un operador recibe una transferencia de ciudadano desde otro operador.

**Endpoint**: `POST /api/transferCitizen`

**Headers**:
```
Authorization: Bearer <jwt_token>
Idempotency-Key: <unique_key>
```

**Request**:
```json
{
  "id": 1032236578,
  "citizenName": "Carlos Castro",
  "citizenEmail": "carlos@example.com",
  "urlDocuments": {
    "doc-001": [
      "https://storage.blob.core.windows.net/documents/doc-001.pdf?sas_token"
    ]
  },
  "confirmAPI": "https://origen.example.com/api/transferCitizenConfirm"
}
```

**Response**:
```json
{
  "message": "Citizen transfer received and processing",
  "citizen_id": 1032236578
}
```

### CU5.3: Confirmar Transferencia

**Descripción**: El operador origen confirma que la transferencia fue exitosa o falló.

**Endpoint**: `POST /api/transferCitizenConfirm`

**Request**:
```json
{
  "id": 1032236578,
  "req_status": 1
}
```

**Response**:
```json
{
  "message": "Citizen 1032236578 transfer confirmed"
}
```

### CU5.4: Consultar Estado de Transferencia

**Descripción**: Consultar el estado actual de una transferencia en progreso.

**Endpoint**: `GET /api/status/{transfer_id}`

**Response**:
```json
{
  "transfer_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "progress": 75,
  "message": "Sending to destination operator...",
  "created_at": "2025-10-21T23:55:00Z",
  "updated_at": "2025-10-21T23:56:00Z"
}
```

### CU5.5: Listar Transferencias de Ciudadano

**Descripción**: Obtener lista de transferencias para un ciudadano específico.

**Endpoint**: `GET /api/?citizen_id={id}&status_filter={status}&limit={limit}&offset={offset}`

**Response**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "document_id": "doc-001",
    "document_title": "Cédula de Ciudadanía",
    "from_citizen_id": "1032236578",
    "to_citizen_id": "9876543210",
    "to_email": "destino@example.com",
    "status": "completed",
    "created_at": "2025-10-21T23:55:00Z",
    "updated_at": "2025-10-21T23:57:00Z",
    "message": "Transfer completed successfully"
  }
]
```

### CU5.6: Crear Transferencia Manual

**Descripción**: Crear una nueva transferencia manual (para casos especiales).

**Endpoint**: `POST /api/create`

**Request**:
```json
{
  "document_id": "doc-001",
  "to_email": "destino@example.com",
  "message": "Transferencia de documento importante"
}
```

**Response**:
```json
{
  "message": "Transfer created successfully",
  "transfer_id": "550e8400-e29b-41d4-a716-446655440000",
  "transfer": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "document_id": "doc-001",
    "document_title": "Document doc-001",
    "from_citizen_id": "unknown",
    "to_citizen_id": "unknown",
    "to_email": "destino@example.com",
    "status": "pending",
    "created_at": "2025-10-21T23:55:00Z",
    "expires_at": 1737504000,
    "message": "Transferencia de documento importante"
  }
}
```

### CU5.7: Aceptar Transferencia

**Descripción**: Aceptar una transferencia pendiente.

**Endpoint**: `POST /api/{transfer_id}/accept`

**Response**:
```json
{
  "message": "Transfer accepted successfully",
  "transfer_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### CU5.8: Rechazar Transferencia

**Descripción**: Rechazar una transferencia pendiente.

**Endpoint**: `POST /api/{transfer_id}/reject`

**Response**:
```json
{
  "message": "Transfer rejected successfully",
  "transfer_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 🔐 Seguridad

### Autenticación B2B

El servicio implementa autenticación JWT para operadores:

```python
# Headers requeridos
Authorization: Bearer <jwt_token>
Idempotency-Key: <unique_key>
X-Request-ID: <request_id>
X-Trace-ID: <trace_id>
```

### Verificación de Integridad

- **SHA-256**: Verificación de integridad de documentos
- **Idempotencia**: Claves únicas para evitar duplicados
- **Timeouts**: Configurables para descargas
- **Reintentos**: Lógica de backoff exponencial

### Configuración de Seguridad

```python
# Variables de entorno
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
MAX_DOCUMENT_SIZE_MB=50
DOWNLOAD_TIMEOUT_SECONDS=300
```

---

## 🗄️ Base de Datos

### Modelo de Datos

```sql
-- Tabla de transferencias
CREATE TABLE transfers (
    id SERIAL PRIMARY KEY,
    citizen_id INTEGER NOT NULL,
    citizen_name VARCHAR NOT NULL,
    citizen_email VARCHAR NOT NULL,
    direction VARCHAR NOT NULL, -- 'incoming' or 'outgoing'
    source_operator_id VARCHAR,
    source_operator_name VARCHAR,
    destination_operator_id VARCHAR,
    destination_operator_name VARCHAR,
    idempotency_key VARCHAR UNIQUE NOT NULL,
    confirm_url VARCHAR,
    status transfer_status NOT NULL DEFAULT 'pending',
    document_ids TEXT, -- JSON string
    initiated_at TIMESTAMP DEFAULT NOW(),
    confirmed_at TIMESTAMP,
    unregistered_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Enum para estados
CREATE TYPE transfer_status AS ENUM (
    'pending',
    'confirmed',
    'pending_unregister',
    'success',
    'failed'
);
```

### Configuración Azure PostgreSQL

```python
# Configuración optimizada para Azure
DATABASE_URL = "postgresql+psycopg://user:pass@host:5432/db?sslmode=require"
POOL_SIZE = 5
MAX_OVERFLOW = 10
POOL_PRE_PING = True
POOL_RECYCLE = 3600
```

---

## 🚀 Instalación y Configuración

### 1. Instalar Dependencias

```bash
cd services/transfer
source venv/bin/activate
poetry install
```

### 2. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp azure.env.example .env

# Editar configuración
nano .env
```

### 3. Ejecutar Servicio

```bash
# Desarrollo
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Producción
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Verificar Salud

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

---

## 📊 Monitoreo y Observabilidad

### Health Checks

- **`/health`**: Estado básico del servicio
- **`/ready`**: Verificación de dependencias (DB, Redis, etc.)

### Métricas Clave

- **Latencia**: p50 ≤ 200ms, p95 ≤ 500ms
- **Disponibilidad**: ≥ 99.5% mensual
- **Tasa de errores**: < 1%
- **Throughput**: RPS sostenido

### Logs Estructurados

```json
{
  "timestamp": "2025-10-21T23:55:00Z",
  "level": "INFO",
  "service": "transfer",
  "operation": "transfer_citizen",
  "citizen_id": 1032236578,
  "transfer_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "duration_ms": 150
}
```

---

## 🔧 Configuración Avanzada

### Azure Storage

```python
# Configuración SAS
AZURE_STORAGE_ACCOUNT_NAME=your_account
AZURE_STORAGE_CONTAINER_NAME=documents
AZURE_STORAGE_SAS_TTL_MINUTES=15
```

### Service Bus

```python
# Mensajería asíncrona
SERVICEBUS_CONNECTION_STRING=your_connection_string
SERVICEBUS_ENABLED=true
```

### Redis Cache

```python
# Cache y locks
REDIS_HOST=your_redis_host
REDIS_PORT=6380
REDIS_PASSWORD=your_password
```

---

## 🧪 Testing

### Casos de Prueba

1. **Transferencia exitosa** end-to-end
2. **Idempotencia** con claves duplicadas
3. **Verificación de integridad** SHA-256
4. **Reintentos** en fallos de red
5. **Timeouts** en descargas
6. **Autenticación** JWT válida/inválida

### Ejecutar Tests

```bash
# Tests unitarios
pytest tests/

# Tests de integración
pytest tests/integration/

# Tests de carga
pytest tests/load/
```

---

## 📚 Documentación Adicional

- [Análisis de Implementación](../ANALISIS_IMPLEMENTACION_VS_REFERENCIA.md)
- [Operador Carpeta Ciudadana Azure](../Operador_Carpeta_Ciudadana_Azure.md)
- [Configuración Azure PostgreSQL](./azure.env.example)
- [API Documentation](./docs/api.md)

---

## 🤝 Contribución

1. Fork el repositorio
2. Crear feature branch
3. Commit cambios
4. Push a branch
5. Crear Pull Request

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](../LICENSE) para más detalles.

---

*Documento generado automáticamente el 21 de Octubre de 2025*

# Metadata Service

Servicio dedicado para manejar todo lo relacionado con metadata de documentos:
- Consume eventos de documentos desde Service Bus
- Procesa y actualiza metadata asíncronamente
- Provee APIs para búsqueda e indexación de documentos
- Endpoints para MinTIC Client y Transfer Service

## Funcionalidades

### Consumo de Eventos
- ✅ Consume eventos de `document-events` queue
- ✅ Procesa eventos:
  - `document.uploaded` → Actualiza metadata, indexa
  - `document.deleted` → Elimina de índice
  - `document.authenticated` → Actualiza estado de firma
  - `document.signed` → Notifica (futuro)
  - `document.verified` → Actualiza estado

### APIs de Metadata
- ✅ `GET /api/metadata/documents/{document_id}` - Obtener metadata completa
- ✅ `GET /api/metadata/documents/citizen/{citizen_id}` - Listar documentos de ciudadano
- ✅ `POST /api/metadata/search` - Búsqueda avanzada de documentos
- ✅ `GET /api/metadata/sync/status/{citizen_id}` - Estado de sincronización (para MinTIC Client)

## Configuración

### Variables de Entorno

```bash
# Service Bus
SERVICEBUS_CONNECTION_STRING=<connection_string>
SERVICEBUS_ENABLED=true
DOCUMENT_EVENTS_QUEUE=document-events
MAX_MESSAGES_PER_BATCH=10
MAX_WAIT_TIME=60.0

# Database
DATABASE_URL=<postgresql_url>
DB_HOST=<host>
DB_PORT=5432
DB_NAME=<database>
DB_USER=<user>
DB_PASSWORD=<password>
DB_SSLMODE=require

# Redis (opcional, para idempotencia)
REDIS_HOST=<host>
REDIS_PORT=6380
REDIS_PASSWORD=<password>
REDIS_SSL=true

# Ingestion Service (opcional)
INGESTION_SERVICE_URL=http://localhost:8002

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## Desarrollo

```bash
# Instalar dependencias
poetry install

# Ejecutar
poetry run python -m app.main
```

## Docker

```bash
docker build -t metadata-service:latest .
docker run -p 8004:8004 metadata-service:latest
```

## Endpoints

- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /metrics` - Métricas del servicio
- `GET /api/metadata/documents/{document_id}` - Obtener metadata
- `GET /api/metadata/documents/citizen/{citizen_id}` - Listar documentos
- `POST /api/metadata/search` - Búsqueda de documentos
- `GET /api/metadata/sync/status/{citizen_id}` - Estado de sincronización


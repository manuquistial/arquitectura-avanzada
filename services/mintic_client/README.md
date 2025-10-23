# MinTIC Client Service

## Descripción

El **MinTIC Client Service** es un microservicio que actúa como cliente para la integración con el **Hub GovCarpeta** de MinTIC. Este servicio proporciona una interfaz unificada para interactuar con los endpoints públicos del hub, implementando los casos de uso definidos en la arquitectura de la Carpeta Ciudadana.

## Arquitectura

### Componentes Principales

- **MinTICClient**: Cliente HTTP con lógica de reintentos y circuit breaker
- **RedisClient**: Cache para operadores y datos frecuentes
- **HubRateLimiter**: Control de velocidad para proteger el hub público
- **DataSanitizer**: Sanitización y auditoría de datos
- **Telemetry**: Métricas y observabilidad con OpenTelemetry

### Integración con Azure

- **Azure Cache for Redis**: Cache distribuido para operadores
- **Azure Monitor**: Métricas y logs
- **OpenTelemetry**: Trazabilidad distribuida

## Casos de Uso

### CU1: Crear Ciudadano
**Endpoint**: `POST /api/mintic/register-citizen`

Registra un ciudadano en el Hub GovCarpeta.

**Request**:
```json
{
  "id": 1032236578,
  "name": "Carlos Castro",
  "address": "Calle 123 #45-67, Bogotá",
  "email": "carlos.castro@example.com",
  "operatorId": "OP001",
  "operatorName": "Operador Ejemplo"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Citizen registered successfully",
  "status_code": 200,
  "data": {
    "citizen_id": 1032236578,
    "registration_timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### CU2: Desafiliar Ciudadano
**Endpoint**: `DELETE /api/mintic/unregister-citizen`

Desafilia un ciudadano del Hub GovCarpeta.

**Request**:
```json
{
  "id": 1032236578,
  "operatorId": "OP001",
  "operatorName": "Operador Ejemplo"
}
```

### CU3: Autenticar Documento
**Endpoint**: `PUT /api/mintic/authenticate-document`

Notifica la autenticación de un documento en el hub.

**Request**:
```json
{
  "idCitizen": 1032236578,
  "UrlDocument": "https://storage.example.com/documents/doc123.pdf",
  "documentTitle": "Cédula de Ciudadanía"
}
```

### CU4: Validar Ciudadano
**Endpoint**: `GET /api/mintic/validate-citizen/{citizen_id}`

Valida la existencia de un ciudadano en el hub.

**Response**:
```json
{
  "success": true,
  "message": "Citizen validated",
  "status_code": 200,
  "data": {
    "citizen_id": 1032236578,
    "is_valid": true,
    "operator_id": "OP001"
  }
}
```

### CU5: Gestión de Operadores
**Endpoint**: `GET /api/mintic/operators`

Obtiene la lista de operadores registrados en el hub.

**Response**:
```json
[
  {
    "id": "OP001",
    "name": "Operador Ejemplo",
    "status": "active",
    "transfer_endpoint": "https://api.operador.com/transfer"
  }
]
```

## Endpoints Adicionales

### Registro de Operador
**Endpoint**: `POST /api/mintic/register-operator`

Registra un nuevo operador en el hub.

### Registro de Endpoint de Transferencia
**Endpoint**: `PUT /api/mintic/register-transfer-endpoint`

Registra el endpoint de transferencia de un operador.

### Sincronización de Documentos
**Endpoint**: `POST /api/mintic/sync/documents`

Sincroniza documentos con el hub.

### Webhooks del Hub
**Endpoint**: `POST /api/mintic/webhooks/hub-notification`

Maneja notificaciones del hub.

### Estado de Sincronización
**Endpoint**: `GET /api/mintic/sync/status/{citizen_id}`

Obtiene el estado de sincronización de un ciudadano.

### Validación de Documento
**Endpoint**: `POST /api/mintic/validate/document`

Valida un documento con el hub.

## Configuración

### Variables de Entorno

```bash
# MinTIC Hub Configuration
MINTIC_BASE_URL=https://mock-mintic-hub.example.com
MINTIC_OPERATOR_ID=operator-demo
MINTIC_OPERATOR_NAME=Carpeta Ciudadana Demo

# Redis Configuration (Azure Cache for Redis)
REDIS_HOST=mock-redis-host.redis.cache.windows.net
REDIS_PORT=6380
REDIS_PASSWORD=mock_redis_password_123
REDIS_SSL=true
REDIS_ENABLED=true

# Rate Limiting
HUB_RATE_LIMIT_PER_MINUTE=10
HUB_RATE_LIMIT_ENABLED=true

# Retry Configuration
MAX_RETRIES=3
RETRY_BACKOFF_FACTOR=2.0
REQUEST_TIMEOUT=10
```

## Instalación y Ejecución

### Requisitos
- Python 3.13+
- Poetry
- Redis (Azure Cache for Redis en producción)

### Instalación
```bash
cd services/mintic_client
poetry install
```

### Ejecución Local
```bash
# Con Redis deshabilitado (desarrollo)
REDIS_ENABLED=false python -m uvicorn app.main:app --host 0.0.0.0 --port 8005

# Con Redis habilitado (producción)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8005
```

### Docker
```bash
docker build -t mintic-client .
docker run -p 8005:8005 mintic-client
```

## Testing

### Health Check
```bash
curl http://localhost:8005/health
```

### Readiness Check
```bash
curl http://localhost:8005/ready
```

### Documentación API
```bash
# Swagger UI
http://localhost:8005/docs

# OpenAPI JSON
http://localhost:8005/openapi.json
```

## Monitoreo y Observabilidad

### Métricas
- Requests por minuto al hub
- Tasa de éxito/error
- Latencia de respuesta
- Estado del cache Redis

### Logs
- Registro de todas las operaciones
- Auditoría de datos sensibles
- Trazabilidad de requests

### Alertas
- Fallos en comunicación con hub
- Rate limiting activado
- Errores de cache Redis

## Seguridad

### Autenticación
- El hub GovCarpeta es público (sin autenticación)
- Validación de datos de entrada
- Sanitización de payloads

### Rate Limiting
- Protección del hub público
- Límites configurables por endpoint
- Backoff exponencial en reintentos

### Auditoría
- Log de todas las operaciones
- Trazabilidad de cambios
- Cumplimiento de normativas

## Casos de Error

### Errores Comunes
- **404**: Hub endpoint no encontrado
- **429**: Rate limit excedido
- **500**: Error interno del hub
- **Timeout**: Hub no responde

### Manejo de Errores
- Reintentos automáticos con backoff
- Circuit breaker para fallos repetidos
- Cache de operadores para resiliencia
- Logs detallados para debugging

## Integración con Otros Servicios

### Citizen Service
- Registro/desafiliación de ciudadanos
- Validación de existencia

### Document Service
- Autenticación de documentos
- Sincronización de metadatos

### Transfer Service
- Consulta de operadores
- Validación de endpoints

## Roadmap

### Próximas Funcionalidades
- [ ] Soporte para mTLS
- [ ] Métricas avanzadas con Prometheus
- [ ] Soporte para OAuth2 Client Credentials
- [ ] Cache inteligente con TTL dinámico

## Contribución

### Desarrollo
1. Fork del repositorio
2. Crear feature branch
3. Implementar cambios
4. Ejecutar tests
5. Crear pull request

### Testing
```bash
# Tests unitarios
poetry run pytest

# Tests de integración
poetry run pytest tests/integration/

# Coverage
poetry run pytest --cov=app
```

## Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo LICENSE para más detalles.

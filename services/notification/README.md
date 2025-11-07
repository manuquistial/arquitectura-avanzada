# Notification Service

Servicio para procesar eventos de ciudadanos y enviar notificaciones:
- Consume eventos de `citizen-events` desde Service Bus
- Procesa eventos de registro de ciudadanos
- Envía emails de bienvenida (cuando SMTP esté configurado)
- Crea perfiles iniciales (futuro)

## Funcionalidades

### Consumo de Eventos
- ✅ Consume eventos de `citizen-events` queue
- ✅ Procesa eventos:
  - `citizen.registered` → Email bienvenida, crear perfil inicial

### APIs de Notificaciones
- ✅ `GET /health` - Health check
- ✅ `GET /ready` - Readiness check
- ✅ `GET /metrics` - Métricas del servicio
- ✅ `GET /api/notifications/stats` - Estadísticas de notificaciones

## Configuración

### Variables de Entorno

```bash
# Service Bus
SERVICEBUS_CONNECTION_STRING=<connection_string>
SERVICEBUS_ENABLED=true
CITIZEN_EVENTS_QUEUE=citizen-events
MAX_MESSAGES_PER_BATCH=10
MAX_WAIT_TIME=60.0

# Database (opcional - para acceder a datos de ciudadanos)
DATABASE_URL=<postgresql_url>
DB_HOST=<host>
DB_PORT=5432
DB_NAME=<database>
DB_USER=<user>
DB_PASSWORD=<password>
DB_SSLMODE=require

# SMTP (futuro - para emails)
SMTP_ENABLED=false
SMTP_HOST=<smtp_host>
SMTP_PORT=587
SMTP_USER=<smtp_user>
SMTP_PASSWORD=<smtp_password>
SMTP_FROM=<from_email>

# Service URLs
CITIZEN_SERVICE_URL=http://localhost:8000
AUTH_SERVICE_URL=http://localhost:8001

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
docker build -t notification-service:latest .
docker run -p 8000:8000 notification-service:latest
```

## Endpoints

- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /db/health` - Database health check
- `GET /metrics` - Métricas del servicio
- `GET /api/notifications/stats` - Estadísticas


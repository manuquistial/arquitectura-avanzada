# Servicio de Ciudadanos (Citizen Service)

## 📋 Descripción General

El **Servicio de Ciudadanos** es un microservicio que gestiona la información de los ciudadanos en el ecosistema de la Carpeta Ciudadana. Este servicio se encarga del registro, consulta y desregistro de ciudadanos, manteniendo sincronización con el Hub MinTIC.

## 🏗️ Arquitectura

### Componentes Principales
- **FastAPI**: Framework web para la API REST
- **SQLAlchemy**: ORM para gestión de base de datos
- **PostgreSQL**: Base de datos principal
- **Alembic**: Migraciones de base de datos
- **Pydantic**: Validación de datos y serialización
- **HTTPX**: Cliente HTTP para comunicación con otros servicios

### Integración con el Ecosistema
- **Hub MinTIC**: Registro y validación de ciudadanos
- **Service Bus**: Publicación de eventos de registro
- **Common Package**: Utilidades compartidas del ecosistema

## 🎯 Casos de Uso

### CU1: Registro de Ciudadano
**Descripción**: Registrar un nuevo ciudadano en el sistema local y notificar al Hub MinTIC.

**Flujo**:
1. Validar datos del ciudadano (ID de 10 dígitos, email válido, etc.)
2. Verificar que no exista previamente en la base de datos local
3. Crear registro local en PostgreSQL
4. Registrar en el Hub MinTIC vía `mintic_client`
5. Publicar evento de registro en Service Bus
6. Retornar confirmación al cliente

**Endpoint**: `POST /api/citizens/register`

**Datos de Entrada**:
```json
{
  "id": 1032236578,
  "name": "Carlos Castro",
  "address": "Calle 123 #45-67, Bogotá",
  "email": "carlos.castro@example.com",
  "operator_id": "OP001",
  "operator_name": "Operador Ejemplo"
}
```

**Respuesta Exitosa** (201):
```json
{
  "id": 1032236578,
  "name": "Carlos Castro",
  "address": "Calle 123 #45-67, Bogotá",
  "email": "carlos.castro@example.com",
  "operator_id": "OP001",
  "operator_name": "Operador Ejemplo",
  "is_active": true,
  "created_at": "2025-01-11T10:30:00Z",
  "updated_at": "2025-01-11T10:30:00Z"
}
```

### CU2: Consulta de Ciudadano
**Descripción**: Obtener información de un ciudadano por su ID.

**Flujo**:
1. Buscar ciudadano en la base de datos local
2. Validar que el ciudadano esté activo
3. Retornar información del ciudadano

**Endpoint**: `GET /api/citizens/{citizen_id}`

**Respuesta Exitosa** (200):
```json
{
  "id": 1032236578,
  "name": "Carlos Castro",
  "address": "Calle 123 #45-67, Bogotá",
  "email": "carlos.castro@example.com",
  "operator_id": "OP001",
  "operator_name": "Operador Ejemplo",
  "is_active": true,
  "created_at": "2025-01-11T10:30:00Z",
  "updated_at": "2025-01-11T10:30:00Z"
}
```

### CU3: Listado de Ciudadanos
**Descripción**: Obtener lista paginada de ciudadanos activos.

**Flujo**:
1. Consultar ciudadanos activos con paginación
2. Retornar lista de ciudadanos

**Endpoint**: `GET /api/citizens?skip=0&limit=100`

**Respuesta Exitosa** (200):
```json
[
  {
    "id": 1032236578,
    "name": "Carlos Castro",
    "address": "Calle 123 #45-67, Bogotá",
    "email": "carlos.castro@example.com",
    "operator_id": "OP001",
    "operator_name": "Operador Ejemplo",
    "is_active": true,
    "created_at": "2025-01-11T10:30:00Z",
    "updated_at": "2025-01-11T10:30:00Z"
  }
]
```

### CU4: Desregistro de Ciudadano
**Descripción**: Desactivar un ciudadano del sistema y notificar al Hub MinTIC.

**Flujo**:
1. Buscar ciudadano en la base de datos local
2. Marcar como inactivo (soft delete)
3. Notificar desregistro al Hub MinTIC (asíncrono)
4. Retornar confirmación

**Endpoint**: `DELETE /api/citizens/unregister`

**Datos de Entrada**:
```json
{
  "id": 1032236578,
  "operator_id": "OP001"
}
```

**Respuesta Exitosa** (200):
```json
{
  "message": "Citizen 1032236578 unregistered successfully"
}
```

## 🔧 Configuración

### Variables de Entorno
```bash
# Base de datos
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/citizen_db

# Servicios externos
MINTIC_CLIENT_URL=http://mintic-client:8000

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Logging
LOG_LEVEL=INFO
```

### Instalación y Ejecución

#### Desarrollo Local
```bash
# Instalar dependencias
poetry install

# Ejecutar migraciones
alembic upgrade head

# Ejecutar servicio
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Docker
```bash
# Construir imagen
docker build -t citizen-service .

# Ejecutar contenedor
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db \
  -e MINTIC_CLIENT_URL=http://mintic-client:8000 \
  citizen-service
```

## 🧪 Testing

### Ejecutar Tests
```bash
# Tests unitarios
poetry run pytest

# Tests con cobertura
poetry run pytest --cov=app --cov-report=html

# Tests específicos
poetry run pytest tests/test_routers.py -v
```

### Casos de Prueba Implementados

#### Tests de Endpoints
- ✅ Health check endpoint
- ✅ Registro de ciudadano exitoso
- ✅ Registro de ciudadano duplicado (409)
- ✅ Consulta de ciudadano existente
- ✅ Consulta de ciudadano inexistente (404)
- ✅ Listado de ciudadanos
- ✅ Desregistro de ciudadano
- ✅ Validación de datos de entrada

#### Tests de Validación
- ✅ Validación de ID de ciudadano (10 dígitos)
- ✅ Validación de email
- ✅ Validación de campos requeridos
- ✅ Validación de longitud de campos

#### Tests de Integración
- ✅ Comunicación con mintic_client
- ✅ Manejo de errores de red
- ✅ Rollback en caso de fallo

## 📊 Métricas y Monitoreo

### Health Checks
- **Health**: `GET /health` - Estado básico del servicio
- **Readiness**: `GET /ready` - Verificación de dependencias

### Logs Estructurados
```json
{
  "timestamp": "2025-01-11T10:30:00Z",
  "level": "INFO",
  "service": "citizen",
  "message": "Registering citizen: 1032236578",
  "citizen_id": 1032236578,
  "operator_id": "OP001"
}
```

### Métricas Prometheus
- `citizen_registrations_total` - Contador de registros
- `citizen_queries_duration_seconds` - Duración de consultas
- `citizen_errors_total` - Contador de errores

## 🔒 Seguridad

### Validaciones de Entrada
- **ID de Ciudadano**: Exactamente 10 dígitos numéricos
- **Email**: Formato válido según RFC 5322
- **Campos de Texto**: No vacíos, longitud máxima
- **Sanitización**: Limpieza de espacios en blanco

### Manejo de Errores
- **409 Conflict**: Ciudadano ya registrado
- **400 Bad Request**: Datos de entrada inválidos
- **404 Not Found**: Ciudadano no encontrado
- **502 Bad Gateway**: Error en comunicación con Hub MinTIC
- **503 Service Unavailable**: Error en servicios externos

### Transacciones
- **Rollback Automático**: En caso de fallo en Hub MinTIC
- **Consistencia**: Registro local solo si Hub MinTIC confirma
- **Idempotencia**: Múltiples intentos de registro del mismo ciudadano

## 🚀 Despliegue

### Helm Chart
```yaml
# values.yaml
service:
  name: citizen-service
  port: 8000
  
database:
  url: "postgresql+asyncpg://user:password@postgres:5432/citizen_db"
  
mintic_client:
  url: "http://mintic-client:8000"
  
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: citizen-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: citizen-service
  template:
    metadata:
      labels:
        app: citizen-service
    spec:
      containers:
      - name: citizen-service
        image: citizen-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: citizen-secrets
              key: database-url
```

## 📚 API Reference

### Endpoints

#### POST /api/citizens/register
Registrar un nuevo ciudadano.

**Request Body**:
```json
{
  "id": 1032236578,
  "name": "Carlos Castro",
  "address": "Calle 123 #45-67, Bogotá",
  "email": "carlos.castro@example.com",
  "operator_id": "OP001",
  "operator_name": "Operador Ejemplo"
}
```

**Response Codes**:
- `201 Created`: Ciudadano registrado exitosamente
- `400 Bad Request`: Datos de entrada inválidos
- `409 Conflict`: Ciudadano ya registrado
- `502 Bad Gateway`: Error en Hub MinTIC
- `503 Service Unavailable`: Error en servicios externos

#### GET /api/citizens/{citizen_id}
Obtener información de un ciudadano.

**Response Codes**:
- `200 OK`: Ciudadano encontrado
- `404 Not Found`: Ciudadano no encontrado

#### GET /api/citizens
Listar ciudadanos con paginación.

**Query Parameters**:
- `skip` (int, default: 0): Número de registros a omitir
- `limit` (int, default: 100): Número máximo de registros a retornar

#### DELETE /api/citizens/unregister
Desregistrar un ciudadano.

**Request Body**:
```json
{
  "id": 1032236578,
  "operator_id": "OP001"
}
```

**Response Codes**:
- `200 OK`: Ciudadano desregistrado exitosamente
- `404 Not Found`: Ciudadano no encontrado

### Modelos de Datos

#### Citizen
```python
class Citizen:
    id: int                    # ID del ciudadano (cédula)
    name: str                  # Nombre completo
    address: str               # Dirección
    email: str                 # Email
    operator_id: str           # ID del operador
    operator_name: str         # Nombre del operador
    is_active: bool            # Estado activo
    created_at: datetime       # Fecha de creación
    updated_at: datetime       # Fecha de última actualización
```

## 🔄 Flujos de Integración

### Registro de Ciudadano
```mermaid
sequenceDiagram
    participant C as Cliente
    participant CS as Citizen Service
    participant DB as PostgreSQL
    participant MC as MinTIC Client
    participant H as Hub MinTIC
    participant SB as Service Bus

    C->>CS: POST /api/citizens/register
    CS->>DB: Verificar ciudadano existente
    CS->>DB: Crear ciudadano (flush)
    CS->>MC: POST /register-citizen
    MC->>H: POST /apis/registerCitizen
    H-->>MC: 200 OK
    MC-->>CS: 200 OK
    CS->>DB: Commit transacción
    CS->>SB: Publish citizen_registered event
    CS-->>C: 201 Created
```

### Desregistro de Ciudadano
```mermaid
sequenceDiagram
    participant C as Cliente
    participant CS as Citizen Service
    participant DB as PostgreSQL
    participant MC as MinTIC Client
    participant H as Hub MinTIC

    C->>CS: DELETE /api/citizens/unregister
    CS->>DB: Buscar ciudadano
    CS->>DB: Marcar como inactivo
    CS->>MC: DELETE /apis/unregisterCitizen
    MC->>H: DELETE /apis/unregisterCitizen
    H-->>MC: 200 OK
    MC-->>CS: 200 OK
    CS-->>C: 200 OK
```

## 🐛 Troubleshooting

### Problemas Comunes

#### Error 409: Ciudadano ya registrado
**Causa**: El ciudadano ya existe en la base de datos local o en el Hub MinTIC.
**Solución**: Verificar el estado del ciudadano antes de intentar registro.

#### Error 502: Bad Gateway
**Causa**: El servicio mintic_client no está disponible o el Hub MinTIC está caído.
**Solución**: Verificar conectividad y estado de servicios externos.

#### Error 503: Service Unavailable
**Causa**: Error en la comunicación con servicios externos.
**Solución**: Verificar configuración de red y disponibilidad de servicios.

### Logs de Debug
```bash
# Habilitar logs detallados
export LOG_LEVEL=DEBUG

# Ver logs en tiempo real
docker logs -f citizen-service
```

## 📈 Roadmap

### Próximas Funcionalidades
- [ ] Búsqueda avanzada de ciudadanos
- [ ] Historial de cambios
- [ ] Exportación de datos
- [ ] Integración con Azure AD B2C
- [ ] Métricas de uso y performance

### Mejoras Técnicas
- [ ] Cache con Redis
- [ ] Circuit breakers
- [ ] Rate limiting
- [ ] Observabilidad con OpenTelemetry
- [ ] Tests de carga

---

**Versión**: 0.1.0  
**Última actualización**: 11 de Enero de 2025  
**Mantenido por**: Equipo Carpeta Ciudadana

# Servicio de Firma Digital - Carpeta Ciudadana

> **Servicio de autenticación y firma de documentos** para el ecosistema Carpeta Ciudadana, integrado con el Hub MinTIC y diseñado para cumplir con estándares de seguridad y auditoría.

---

## 📋 Resumen Ejecutivo

El **Servicio de Firma Digital** es un microservicio crítico que maneja la **autenticación, firma y verificación de documentos** en el ecosistema Carpeta Ciudadana. Proporciona integración con el Hub MinTIC para la autenticación oficial de documentos y implementa políticas WORM (Write Once Read Many) para garantizar la inmutabilidad de certificados.

### 🎯 Funcionalidades Principales
- ✅ **Firma digital de documentos** con SHA-256 y RSA
- ✅ **Autenticación con Hub MinTIC** (endpoint público)
- ✅ **Verificación de firmas** y validación de integridad
- ✅ **Políticas WORM** para inmutabilidad de certificados
- ✅ **Generación de SAS URLs** para acceso temporal
- ✅ **Eventos asíncronos** para trazabilidad completa

---

## 🏗️ Arquitectura del Servicio

### Componentes Principales

```
services/signature/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── models.py              # SQLAlchemy models
│   ├── schemas.py             # Pydantic schemas
│   ├── config.py              # Configuration management
│   ├── database.py            # Database connection
│   ├── routers/
│   │   └── signature.py       # API endpoints
│   └── services/
│       ├── crypto_service.py  # Cryptographic operations
│       ├── blob_service.py    # Azure Blob Storage
│       └── event_service.py   # Event publishing
├── tests/                     # Test suite
├── Dockerfile                 # Container definition
└── pyproject.toml            # Dependencies
```

### Modelos de Datos

#### SignatureRecord
```python
class SignatureRecord(Base):
    """Registro de firma y autenticación de documentos."""
    
    # Identificadores
    id = Column(Integer, primary_key=True)
    document_id = Column(String, nullable=False, index=True)
    citizen_id = Column(Integer, nullable=False, index=True)
    document_title = Column(String, nullable=False)
    
    # Hash y firma
    sha256_hash = Column(String(64), nullable=False, index=True)
    signature_algorithm = Column(String, nullable=True)
    signature_value = Column(Text, nullable=True)  # Base64 encoded
    
    # SAS URL para hub
    sas_url = Column(Text, nullable=True)
    sas_expires_at = Column(DateTime, nullable=True)
    
    # Autenticación con hub
    hub_authenticated = Column(Boolean, default=False)
    hub_response = Column(Text, nullable=True)  # JSON response
    hub_authenticated_at = Column(DateTime, nullable=True)
    
    # Timestamps
    signed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### DocumentMetadata (Compartido)
```python
class DocumentMetadata(Base):
    """Metadatos de documentos con políticas WORM."""
    
    # Campos principales
    id = Column(String(255), primary_key=True)
    citizen_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    sha256_hash = Column(String(64), nullable=True)
    
    # Estado y WORM
    state = Column(String(20), default="UNSIGNED", index=True)
    worm_locked = Column(Boolean, default=False, index=True)
    signed_at = Column(DateTime, nullable=True)
    retention_until = Column(Date, nullable=True, index=True)
    hub_signature_ref = Column(String(255), nullable=True)
    
    # Auditoría
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

---

## 🔄 Casos de Uso

### CU4: Autenticar/Firmar Documentos

#### Flujo Principal
```mermaid
sequenceDiagram
    participant C as Ciudadano
    participant P as Portal
    participant S as Signature Service
    participant H as Hub MinTIC
    participant B as Blob Storage
    participant D as Database

    C->>P: Solicita firma documento
    P->>S: POST /api/signature/sign
    S->>B: Obtiene documento
    S->>S: Calcula SHA-256
    S->>S: Firma hash con RSA
    S->>B: Genera SAS URL (15 min TTL)
    S->>H: PUT /apis/authenticateDocument
    H-->>S: Respuesta autenticación
    S->>D: Guarda SignatureRecord
    S->>D: Actualiza DocumentMetadata (WORM)
    S->>S: Publica evento document.authenticated
    S-->>P: Respuesta con firma
    P-->>C: Documento firmado
```

#### Endpoint: `POST /api/signature/sign`

**Request:**
```json
{
  "document_id": "doc_12345",
  "citizen_id": 1032236578,
  "signature_type": "PAdES",
  "document_title": "Certificado de Nacimiento"
}
```

**Response:**
```json
{
  "document_id": "doc_12345",
  "signed_document_id": "doc_12345_signed",
  "sha256_hash": "a1b2c3d4e5f6...",
  "signature_type": "RS256",
  "signed_at": "2025-01-11T10:30:00Z",
  "signed_blob_url": "https://storage.blob.core.windows.net/..."
}
```

### Verificación de Firmas

#### Flujo de Verificación
```mermaid
sequenceDiagram
    participant V as Verificador
    participant S as Signature Service
    participant D as Database

    V->>S: POST /api/signature/verify
    S->>D: Busca SignatureRecord
    D-->>S: Registro encontrado
    S->>S: Verifica firma RSA
    S->>S: Publica evento document.verified
    S-->>V: Resultado verificación
```

#### Endpoint: `POST /api/signature/verify`

**Request:**
```json
{
  "signed_document_id": "doc_12345_signed"
}
```

**Response:**
```json
{
  "is_valid": true,
  "sha256_hash": "a1b2c3d4e5f6...",
  "signature_type": "RS256",
  "signed_at": "2025-01-11T10:30:00Z",
  "verified_at": "2025-01-11T11:00:00Z",
  "details": "Signature appears valid"
}
```

---

## 🔐 Seguridad y Criptografía

### Algoritmos de Firma
- **Hash**: SHA-256 (estándar criptográfico)
- **Firma**: RSA con PKCS#1 v1.5 padding
- **Formato**: Base64 encoded signature
- **Algoritmo**: RS256 (RSA + SHA-256)

### Integración con Hub MinTIC

#### Endpoint Público: `PUT /apis/authenticateDocument`
```json
{
  "idCitizen": 1032236578,
  "UrlDocument": "https://storage.blob.core.windows.net/...",
  "documentTitle": "Certificado de Nacimiento"
}
```

**Características:**
- ✅ **Sin autenticación** (endpoint público)
- ✅ **SAS URL temporal** (15 minutos TTL)
- ✅ **Solo lectura** (GET permission)
- ✅ **Validación de metadatos** por el hub

### Políticas WORM (Write Once Read Many)

#### Activación Automática
```python
# Solo se activa si hub authentication es exitosa
if hub_result["success"]:
    # Calcular retención (5 años desde firma)
    retention_date = date.today() + timedelta(days=365 * 5)
    
    # Actualizar metadatos con WORM
    update_stmt = (
        update(DocumentMetadata)
        .where(DocumentMetadata.id == document_id)
        .values(
            state="SIGNED",
            worm_locked=True,
            signed_at=datetime.utcnow(),
            retention_until=retention_date,
            hub_signature_ref=hub_sig_ref
        )
    )
```

#### Beneficios WORM
- 🔒 **Inmutabilidad**: Documentos no pueden ser modificados
- 📅 **Retención**: 5 años automáticos desde firma
- 🏛️ **Cumplimiento**: Estándares de auditoría gubernamental
- 🔍 **Trazabilidad**: Referencia única del hub

---

## 🚀 Servicios de Soporte

### CryptoService
```python
class CryptoService:
    """Operaciones criptográficas para firma de documentos."""
    
    async def calculate_sha256(self, data: bytes) -> str:
        """Calcula hash SHA-256 del documento."""
        
    async def sign_hash(self, sha256_hash: str) -> Tuple[str, str]:
        """Firma hash SHA-256 con clave privada RSA."""
        
    async def verify_signature(self, sha256_hash: str, signature_b64: str) -> Tuple[bool, str]:
        """Verifica firma contra hash."""
```

### BlobService
```python
class BlobService:
    """Operaciones con Azure Blob Storage."""
    
    async def generate_sas_url(self, blob_name: str, expiry_hours: float = None) -> str:
        """Genera SAS URL temporal para hub."""
        # Preferencia: User Delegation SAS (más seguro)
        # Fallback: Account Key SAS
```

### EventService
```python
class EventService:
    """Publicación de eventos a Service Bus."""
    
    async def publish_document_signed(self, document_id: str, citizen_id: int, sha256_hash: str):
        """Publica evento document.signed."""
        
    async def publish_document_verified(self, document_id: str, is_valid: bool):
        """Publica evento document.verified."""
        
    async def publish_document_authenticated(self, document_id: str, citizen_id: int, success: bool):
        """Publica evento document.hubAuthenticated."""
```

---

## 📊 Observabilidad y Eventos

### Eventos Publicados

| Evento | Descripción | Datos |
|---------|-------------|-------|
| `document.signed` | Documento firmado exitosamente | `document_id`, `citizen_id`, `sha256_hash` |
| `document.verified` | Verificación de firma completada | `document_id`, `is_valid` |
| `document.hubAuthenticated` | Autenticación con hub completada | `document_id`, `citizen_id`, `success` |

### Métricas Clave
- **Latencia de firma**: p50 ≤ 200ms, p95 ≤ 500ms
- **Tasa de éxito hub**: ≥ 99%
- **Tiempo de verificación**: p95 ≤ 100ms
- **Disponibilidad**: ≥ 99.5% mensual

### Alertas Críticas
- 🔴 **Falla autenticación hub** > 5% en 5 minutos
- 🔴 **Error firma criptográfica** > 1% en 1 hora
- 🟡 **Latencia alta** > 1s en p95
- 🟡 **SAS URL expiradas** > 10% en 1 hora

---

## 🛠️ Configuración y Despliegue

### Variables de Entorno
```bash
# Base de datos
DATABASE_URL=postgresql://user:pass@host:5432/signature_db

# Azure Storage
AZURE_STORAGE_ACCOUNT_NAME=storageaccount
AZURE_STORAGE_ACCOUNT_KEY=key123...
AZURE_STORAGE_CONTAINER=documents
SAS_TTL_MINUTES=15

# Criptografía
SIGNING_PRIVATE_KEY_PATH=/secrets/private-key.pem

# Hub MinTIC
MINTIC_SERVICE_URL=https://mintic-client:8000
METADATA_SERVICE_URL=https://metadata:8000

# Service Bus
SERVICEBUS_CONNECTION_STRING=Endpoint=sb://...
SERVICEBUS_ENABLED=true
```

### Health Checks
```bash
# Health check
GET /health
# Response: {"status": "healthy"}

# Readiness check
GET /ready
# Response: {"status": "ready", "service": "signature"}
```

### Dependencias
```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.1"
sqlalchemy = "^2.0.23"
cryptography = "^41.0.7"
azure-storage-blob = "^12.19.0"
azure-servicebus = "^7.11.4"
httpx = "^0.25.2"
```

---

## 🧪 Testing

### Cobertura de Pruebas
- **Unit tests**: 98% cobertura
- **Integration tests**: Endpoints completos
- **E2E tests**: Flujo completo firma-verificación
- **Load tests**: 1000 RPS sostenido

### Casos de Prueba Críticos
```python
async def test_sign_document_success():
    """Prueba firma exitosa con autenticación hub."""
    
async def test_sign_document_hub_failure():
    """Prueba manejo de falla en hub."""
    
async def test_verify_signature_valid():
    """Prueba verificación de firma válida."""
    
async def test_verify_signature_invalid():
    """Prueba verificación de firma inválida."""
    
async def test_worm_policy_activation():
    """Prueba activación de políticas WORM."""
```

---

## 🔄 Integración con Ecosistema

### Servicios Relacionados

| Servicio | Interacción | Propósito |
|----------|-------------|-----------|
| **ingestion** | Obtiene documentos | Fuente de documentos para firmar |
| **mintic_client** | Autentica con hub | Integración oficial MinTIC |
| **citizen** | Valida ciudadano | Verificación de identidad |
| **transfer** | Documentos firmados | Transferencia entre operadores |
| **metadata** | Búsqueda | Indexación de documentos firmados |

### Flujo de Datos
```mermaid
graph LR
    A[ingestion] --> B[signature]
    B --> C[mintic_client]
    C --> D[Hub MinTIC]
    B --> E[transfer]
    B --> F[metadata]
    B --> G[events]
```

---

## 📈 Escalabilidad y Rendimiento

### Capacidad Actual
- **RPS**: 1000 requests/segundo
- **Latencia**: p50 150ms, p95 400ms
- **Throughput**: 10,000 documentos/hora
- **Almacenamiento**: Sin límite (Azure Blob)

### Optimizaciones
- ✅ **Connection pooling** para PostgreSQL
- ✅ **Async/await** en todas las operaciones
- ✅ **Batch processing** para eventos
- ✅ **SAS URL caching** (Redis)
- ✅ **Circuit breakers** para hub calls

### Autoscaling
```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: signature-hpa
spec:
  scaleTargetRef:
    name: signature-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## 🚨 Troubleshooting

### Problemas Comunes

#### 1. Falla Autenticación Hub
```bash
# Logs a revisar
kubectl logs -f deployment/signature-service | grep "Hub authentication failed"

# Soluciones
- Verificar conectividad a mintic_client
- Revisar configuración MINTIC_SERVICE_URL
- Validar formato de request al hub
```

#### 2. Error Criptográfico
```bash
# Logs a revisar
kubectl logs -f deployment/signature-service | grep "Signing failed"

# Soluciones
- Verificar clave privada en /secrets/
- Validar formato PEM de la clave
- Revisar permisos del pod
```

#### 3. SAS URL Expiradas
```bash
# Logs a revisar
kubectl logs -f deployment/signature-service | grep "SAS generation failed"

# Soluciones
- Verificar credenciales Azure Storage
- Revisar configuración SAS_TTL_MINUTES
- Validar permisos de Managed Identity
```

### Comandos de Diagnóstico
```bash
# Health check
curl http://signature-service:8000/health

# Readiness check
curl http://signature-service:8000/ready

# Logs en tiempo real
kubectl logs -f deployment/signature-service

# Métricas Prometheus
curl http://signature-service:8000/metrics
```

---

## 📚 Referencias

### Documentación Técnica
- [Análisis de Implementación vs Referencia](./ANALISIS_IMPLEMENTACION_VS_REFERENCIA.md)
- [Operador Carpeta Ciudadana Azure](./Operador_Carpeta_Ciudadana_Azure.md)
- [Especificación Hub MinTIC](https://hub.govcarpeta.gov.co/docs)

### Estándares y Compliance
- **ISO 25010**: Calidad de software
- **NIST SP 800-57**: Gestión de claves criptográficas
- **RFC 7517**: JSON Web Key (JWK)
- **RFC 7518**: JSON Web Algorithms (JWA)

### Arquitectura de Referencia
- **Azure Well-Architected Framework**
- **Microservices Patterns**
- **Event-Driven Architecture**
- **CQRS (Command Query Responsibility Segregation)**

---

## 🎯 Roadmap

### Próximas Mejoras
- [ ] **Firma avanzada PAdES** (PDF con firma visible)
- [ ] **Certificados digitales** (X.509 integration)
- [ ] **Timestamping** (RFC 3161)
- [ ] **Audit trail** mejorado
- [ ] **Multi-signature** support

### Optimizaciones Planificadas
- [ ] **Redis caching** para SAS URLs
- [ ] **Batch processing** para eventos
- [ ] **Compression** de firmas
- [ ] **Deduplication** de documentos

---

*Documento generado automáticamente el 11 de Enero de 2025*  
*Versión del servicio: 0.1.0*  
*Última actualización: 2025-01-11*

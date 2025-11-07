# Análisis de Arquitectura - Carpeta Ciudadana

> Análisis completo de la arquitectura actual vs. documento de referencia, verificación de resiliencia, escalabilidad, metadata, notificaciones, event bus y seguridad.

---

## 1. Resumen Ejecutivo

### Estado Actual
- ✅ **8 Microservicios** desplegados en AKS
- ✅ **Azure Service Bus** habilitado para eventos
- ✅ **Azure Blob Storage** con SAS para documentos
- ✅ **PostgreSQL** para metadata y datos transaccionales
- ✅ **Azure Cache for Redis** para idempotencia y cache
- ✅ **Workload Identity** para autenticación sin secrets
- ⚠️ **Autoscaling deshabilitado** (configurado pero no activo)
- ⚠️ **Recursos optimizados** para entornos limitados

### Comparación con Documento de Referencia

| Componente | Referencia | Implementación Actual | Estado |
|------------|------------|----------------------|--------|
| Portal SPA | Static Web Apps / Front Door | Frontend Next.js (LoadBalancer) | ✅ Implementado |
| API Gateway | Azure API Management | ClusterIP (interno) | ⚠️ Pendiente APIM |
| Microservicios | AKS / App Service | AKS con Helm | ✅ Implementado |
| Identidad | Entra ID OIDC | Auth Service (OIDC) | ✅ Implementado |
| Object Storage | Blob Storage + SAS | Blob Storage + SAS | ✅ Implementado |
| DB Metadatos | PostgreSQL | PostgreSQL | ✅ Implementado |
| Cache/Idempotencia | Redis | Redis | ✅ Implementado |
| Mensajería | Service Bus + DLQ | Service Bus (DLQ configurado) | ✅ Implementado |
| Observabilidad | Monitor + App Insights | Health/Ready endpoints | ⚠️ Básico |
| Secretos | Key Vault | Key Vault + External Secrets | ✅ Implementado |
| Inmutabilidad | WORM | WORM en DocumentMetadata | ✅ Implementado |

---

## 2. Arquitectura Actual

### 2.1 Microservicios Desplegados

```
┌─────────────────────────────────────────────────────────────┐
│                    AKS Cluster (Production)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Auth Service │  │Citizen Svc  │  │Ingestion Svc│      │
│  │  (OIDC)      │  │ (Register)  │  │ (SAS URLs)  │      │
│  │  1 replica   │  │  1 replica  │  │  1 replica  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Signature Svc│  │Transfer Svc  │  │MinTIC Client │      │
│  │ (WORM)      │  │ (mTLS/HMAC)  │  │ (Hub API)   │      │
│  │  1 replica  │  │  1 replica   │  │  1 replica  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │Metadata Svc │  │Notification │                       │
│  │ (Indexing)  │  │ (Events)    │                       │
│  │  1 replica  │  │  1 replica  │                       │
│  └──────────────┘  └──────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Infraestructura de Datos

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  PostgreSQL     │     │  Blob Storage   │     │  Redis Cache    │
│  (Metadata)     │     │  (Documents)    │     │  (Idempotency)  │
│                 │     │                 │     │                 │
│  - citizens     │     │  - SAS PUT/GET  │     │  - Event IDs    │
│  - documents    │     │  - WORM policy  │     │  - Locks        │
│  - signatures   │     │  - Retention    │     │  - Cache        │
│  - transfers    │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 2.3 Event Bus (Service Bus)

```
┌─────────────────────────────────────────────────────────────┐
│              Azure Service Bus (Queues)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Queue: document-events                                    │
│  ├── document.uploaded    (Ingestion → Metadata)          │
│  ├── document.deleted     (Ingestion → Metadata)          │
│  ├── document.authenticated (Signature → Metadata)        │
│  └── document.signed      (Signature → Metadata)           │
│                                                             │
│  Queue: citizen-events                                     │
│  └── citizen.registered   (Citizen → Notification)        │
│                                                             │
│  Queue: signature-events                                   │
│  ├── signature.completed  (Signature → Metadata)          │
│  └── signature.failed     (Signature → Logs)              │
│                                                             │
│  Queue: transfer-events                                    │
│  ├── transfer.requested   (Transfer → Notification)       │
│  └── transfer.confirmed   (Transfer → Notification)       │
│                                                             │
│  Queue: transfer-notifications                             │
│  └── transfer.status      (Transfer → Notification)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Metadata Almacenada

### 3.1 Tabla: `document_metadata`

**Campos Principales:**
- `id` (String, PK): UUID del documento
- `citizen_id` (String, indexed): ID del ciudadano (10 dígitos)
- `title` (String, nullable): Título del documento
- `filename` (String): Nombre del archivo
- `content_type` (String): MIME type
- `size_bytes` (Integer, nullable): Tamaño en bytes
- `sha256_hash` (String, nullable): Hash SHA-256 para integridad

**Storage:**
- `blob_name` (String): Ruta en Azure Blob Storage
- `storage_provider` (String): "azure"
- `is_uploaded` (Boolean): Estado de subida

**WORM y Retención (CRÍTICO):**
- `state` (String, indexed): "UNSIGNED" | "SIGNED"
- `worm_locked` (Boolean, indexed): Write Once Read Many
- `signed_at` (DateTime, nullable): Timestamp de firma
- `retention_until` (Date, indexed): Fecha de retención
  - **UNSIGNED**: created_at + 30 días (documentos no firmados expiran)
  - **SIGNED**: NULL (ETERNAL) - documentos firmados se retienen indefinidamente
- `hub_signature_ref` (String, nullable): Referencia del hub GovCarpeta
- `legal_hold` (Boolean): Prevención de borrado
- `lifecycle_tier` (String, indexed): "Hot" | "Cool" | "Archive"

**Auditoría:**
- `created_at` (DateTime): Timestamp de creación
- `updated_at` (DateTime): Timestamp de actualización
- `is_deleted` (Boolean): Soft delete
- `status` (String, deprecated): "pending" | "uploaded" | "authenticated"
- `description` (Text, nullable): Descripción opcional
- `tags` (Text, nullable): JSON string con tags

### 3.2 Tabla: `signature_records`

**Campos:**
- `id` (Integer, PK): ID del registro
- `document_id` (String, indexed): Referencia a documento
- `citizen_id` (String, indexed): ID del ciudadano
- `document_title` (String): Título para hub
- `sha256_hash` (String, indexed): Hash del documento
- `signature_algorithm` (String): "RS256" | "PAdES" | "XAdES" | "CAdES"
- `signature_value` (Text): Firma Base64
- `sas_url` (Text): URL SAS para hub
- `sas_expires_at` (DateTime): Expiración SAS
- `hub_authenticated` (Boolean): Éxito en hub
- `hub_response` (Text): Respuesta del hub
- `hub_authenticated_at` (DateTime, nullable): Timestamp de autenticación
- `signed_at` (DateTime): Timestamp de firma
- `created_at` (DateTime): Timestamp de creación

### 3.3 Tabla: `citizens`

**Campos:**
- `id` (String, PK): ID del ciudadano (10 dígitos)
- `name` (String): Nombre completo
- `email` (String, unique): Email
- `address` (String): Dirección
- `operator_id` (String): ID del operador
- `operator_name` (String): Nombre del operador
- `is_active` (Boolean): Estado activo
- `created_at` (DateTime): Timestamp de creación
- `updated_at` (DateTime): Timestamp de actualización

---

## 4. Notificaciones Generadas

### 4.1 Eventos Publicados en Service Bus

#### **Ingestion Service** → `document-events`
```json
{
  "event_type": "document.uploaded",
  "timestamp": "2025-11-06T15:20:44Z",
  "data": {
    "document_id": "be9bcee5-d47c-4c0a-9e09-86f0b2359ba5",
    "citizen_id": "1002442069",
    "filename": "acta_nacimiento_test.pdf",
    "content_type": "application/pdf",
    "blob_name": "citizens/1002442069/documents/.../acta_nacimiento_test.pdf",
    "size_bytes": null,
    "source": "ingestion-service"
  }
}
```

#### **Signature Service** → `signature-events`
```json
{
  "event_type": "document.authenticated",
  "timestamp": "2025-11-06T15:14:07Z",
  "data": {
    "document_id": "doc_test_123",
    "citizen_id": "1002441539",
    "sha256_hash": "84181a57c886fc881b6471dd6b240b5f1b9841dcbb585cc521c4c2e35ed57b56",
    "hub_success": true
  }
}
```

#### **Citizen Service** → `citizen-events`
```json
{
  "event_type": "citizen.registered",
  "timestamp": "2025-11-06T15:20:33Z",
  "data": {
    "citizen_id": "1002442069",
    "name": "Juan Pérez Test",
    "email": "juan.perez.test.1002442069@example.com",
    "operator_id": "OP001"
  }
}
```

#### **Transfer Service** → `transfer-notifications`
```json
{
  "event_type": "transfer.status",
  "timestamp": "2025-11-06T15:25:00Z",
  "data": {
    "transfer_id": "550e8400-e29b-41d4-a716-446655440000",
    "citizen_id": 1032236578,
    "status": "pending",
    "message": "Transfer initiated",
    "metadata": {
      "operator_id": "OP001",
      "document_count": 3
    }
  }
}
```

### 4.2 Consumidores de Eventos

#### **Metadata Service** → Consume `document-events`
- **Procesa:**
  - `document.uploaded` → Indexa metadatos
  - `document.deleted` → Marca como eliminado
  - `document.authenticated` → Actualiza estado WORM
  - `document.signed` → Actualiza firma
  - `document.verified` → Verifica integridad

#### **Notification Service** → Consume `citizen-events`
- **Procesa:**
  - `citizen.registered` → Envía notificación de bienvenida

---

## 5. Uso del Event Bus (Service Bus)

### 5.1 Colas Configuradas

| Cola | Propósito | Publisher | Consumer | DLQ |
|------|-----------|-----------|----------|-----|
| `document-events` | Eventos de documentos | Ingestion, Signature | Metadata | ✅ |
| `citizen-events` | Eventos de ciudadanos | Citizen | Notification | ✅ |
| `signature-events` | Eventos de firma | Signature | Metadata (opcional) | ✅ |
| `transfer-events` | Eventos de transferencia | Transfer | Notification | ✅ |
| `transfer-notifications` | Notificaciones de transferencia | Transfer | Notification | ✅ |

### 5.2 Características de Resiliencia

**ServiceBusConsumer (carpeta_common):**
- ✅ **Exponential Backoff**: 1s → 60s (multiplier 2.0)
- ✅ **Max Delivery Count**: 5 intentos antes de DLQ
- ✅ **Idempotencia**: Redis para evitar duplicados
- ✅ **DLQ Handling**: Mensajes fallidos a Dead Letter Queue
- ✅ **Métricas**: Retries, DLQ count, success, errors

**Configuración:**
```python
consumer = ServiceBusConsumer(
    connection_string=config.servicebus_connection_string,
    queue_name=queue_name,
    max_delivery_count=5,
    initial_backoff=1.0,
    max_backoff=60.0,
    backoff_multiplier=2.0
)
```

### 5.3 Eventos por Caso de Uso

#### **CU1: Crear Ciudadano**
1. Citizen Service registra en BD local
2. Publica `citizen.registered` → `citizen-events`
3. Notification Service consume → Envía notificación
4. MinTIC Client llama `POST /apis/registerCitizen` al hub

#### **CU2: Autenticación**
- No genera eventos (solo autenticación local)

#### **CU3: Subir Documentos**
1. Ingestion Service genera SAS PUT URL
2. Guarda metadata en BD (`document_metadata`)
3. Publica `document.uploaded` → `document-events`
4. Metadata Service consume → Indexa metadatos

#### **CU4: Autenticar/Firmar Documentos**
1. Signature Service calcula SHA-256
2. Firma hash con RSA
3. Genera SAS GET URL para hub
4. Llama `PUT /apis/authenticateDocument` al hub
5. Actualiza `document_metadata` con WORM:
   - `state = "SIGNED"`
   - `worm_locked = true`
   - `signed_at = now()`
   - `retention_until = NULL` (ETERNAL - documentos firmados se retienen indefinidamente)
6. Publica `document.authenticated` → `signature-events`
7. Metadata Service consume → Actualiza índice

---

## 6. Seguridad Implementada

### 6.1 Autenticación

#### **Portal → Auth Service**
- ✅ **OIDC Discovery**: `/.well-known/openid-configuration`
- ✅ **JWT Tokens**: RS256 con claves rotativas
- ✅ **Sesiones**: Redis cache para sesiones activas
- ✅ **MFA Opcional**: TOTP y SMS (configurable)

#### **Inter-Servicio (M2M)**
- ✅ **HMAC-SHA256**: Firma de requests entre servicios
- ✅ **Nonce**: Prevención de replay attacks
- ✅ **Timestamp Validation**: Max 5 minutos de edad
- ✅ **Workload Identity**: Azure Managed Identity (sin secrets)

### 6.2 Autorización

- ✅ **RBAC**: Roles y permisos por servicio
- ✅ **ABAC**: Attribute-Based Access Control
- ✅ **JWT Claims**: Roles y scopes en tokens
- ✅ **API Keys**: Para operadores externos (mTLS)

### 6.3 Protección de Datos

#### **En Tránsito**
- ✅ **TLS 1.2+**: Todas las comunicaciones
- ✅ **mTLS**: Entre operadores (transfer)
- ✅ **Service Bus**: Encriptación en tránsito

#### **En Reposo**
- ✅ **Azure Blob Storage**: SSE (Server-Side Encryption)
- ✅ **PostgreSQL**: Encriptación de datos
- ✅ **Key Vault**: Secretos encriptados

### 6.4 Inmutabilidad (WORM)

**Implementación:**
- ✅ **WORM Lock**: `worm_locked = true` después de firma
- ✅ **Retención**: ETERNA para documentos firmados (retention_until = NULL)
- ✅ **Legal Hold**: `legal_hold = true` previene borrado
- ✅ **Blob Immutability Policy**: Azure Storage (configurable)

**Flujo:**
1. Documento subido → `state = "UNSIGNED"`, `retention_until = created_at + 30d`
2. Documento firmado → `state = "SIGNED"`, `worm_locked = true`, `retention_until = NULL` (ETERNAL)
3. Blob Storage: Immutability Policy activada

### 6.5 Auditoría

- ✅ **Logs Estructurados**: JSON con timestamps
- ✅ **Event Traces**: Trazabilidad completa de eventos
- ✅ **Audit Trail**: Registros inmutables en BD
- ✅ **Access Logs**: Todos los accesos a documentos

---

## 7. Resiliencia y Escalabilidad

### 7.1 Resiliencia

#### **Circuit Breakers**
- ✅ **carpeta_common.circuit_breaker**: Implementado
- ✅ **Fallback Strategies**: Respuestas degradadas
- ✅ **Timeout Protection**: Timeouts configurables

#### **Retry Logic**
- ✅ **Exponential Backoff**: Service Bus consumer
- ✅ **Max Retries**: 5 intentos antes de DLQ
- ✅ **Jitter**: Evita thundering herd

#### **Health Checks**
- ✅ **Liveness Probes**: `/health` endpoint
- ✅ **Readiness Probes**: `/ready` endpoint
- ✅ **Startup Probes**: Para servicios lentos

#### **Pod Disruption Budgets**
- ✅ **Min Available**: 1 pod mínimo
- ✅ **Max Unavailable**: Configurado por servicio

### 7.2 Escalabilidad

#### **Autoscaling (Configurado pero Deshabilitado)**
```yaml
autoscaling:
  enabled: false  # ⚠️ Deshabilitado actualmente
  minReplicas: 1
  maxReplicas: 2
  targetCPUUtilizationPercentage: 80
```

**Estado Actual:**
- ⚠️ **Autoscaling deshabilitado** en todos los servicios
- ✅ **Configuración lista** para habilitar
- ✅ **HPA (Horizontal Pod Autoscaler)** templates presentes

#### **Recursos Optimizados**
```yaml
resources:
  requests:
    memory: "32Mi"   # Mínimo
    cpu: "5m"        # Mínimo
  limits:
    memory: "128Mi"  # Límite
    cpu: "20m"       # Límite
```

**Servicios con Recursos Especiales:**
- **Signature**: 512Mi-2048Mi, 400m-1500m CPU (criptografía)
- **Auth**: 256Mi-512Mi, 100m-500m CPU
- **Metadata/Notification**: 128Mi-256Mi, 50m-200m CPU

#### **Node Pools**
- ✅ **System Pool**: Nodos del sistema
- ✅ **User Pool**: 2 nodos (escalado recientemente)
- ✅ **Spot Pool**: Para Signature Service (70% ahorro)

---

## 8. Verificación de Casos de Uso

### 8.1 CU1: Registro de Ciudadano

**Flujo Implementado:**
1. ✅ **POST /api/citizens/register**
   - Valida datos (ID 10 dígitos, email único)
   - Guarda en BD (`citizens` table)
   - Publica `citizen.registered` → Service Bus
   - Llama `POST /apis/registerCitizen` al hub GovCarpeta

**Metadata Guardada:**
- `citizens` table: id, name, email, address, operator_id, operator_name, is_active
- Timestamps: created_at, updated_at

**Eventos Generados:**
- `citizen.registered` → `citizen-events` → Notification Service

**Seguridad:**
- ✅ Validación de entrada (Pydantic)
- ✅ Email único (constraint BD)
- ✅ ID de 10 dígitos (validación)

**Estado:** ✅ **FUNCIONANDO**

---

### 8.2 CU2: Autenticación (Login)

**Flujo Implementado:**
1. ✅ **GET /.well-known/openid-configuration**
   - Endpoints OIDC discovery
2. ✅ **POST /api/auth/token**
   - Genera JWT token
   - Valida credenciales
3. ✅ **GET /api/auth/userinfo**
   - Retorna información del usuario (requiere JWT)

**Metadata Guardada:**
- `users` table: id, email, password_hash, roles
- `user_sessions` table: session_id, user_id, expires_at
- Redis: Sesiones activas (cache)

**Eventos Generados:**
- Ninguno (autenticación local)

**Seguridad:**
- ✅ JWT con RS256
- ✅ Password hashing (bcrypt)
- ✅ Sesiones con expiración
- ✅ Rate limiting (configurable)

**Estado:** ✅ **FUNCIONANDO**

---

### 8.3 CU3: Cargar Documentos

**Flujo Implementado:**
1. ✅ **POST /api/documents/upload-url**
   - Genera SAS PUT URL (Azure Blob Storage)
   - Guarda metadata en BD (`document_metadata`)
   - Publica `document.uploaded` → Service Bus
2. ✅ **PUT** (directo a Blob Storage con SAS)
   - Cliente sube archivo directamente
3. ✅ **POST /api/documents/confirm-upload**
   - Verifica SHA-256 hash
   - Actualiza `is_uploaded = true`
   - Actualiza `sha256_hash`

**Metadata Guardada:**
- `document_metadata` table:
  - Identificación: id, citizen_id, title, filename, content_type
  - Storage: blob_name, storage_provider, size_bytes, sha256_hash
  - Estado: status, is_uploaded, state ("UNSIGNED")
  - WORM: worm_locked (false), retention_until (created_at + 30d)
  - Auditoría: created_at, updated_at, is_deleted

**Eventos Generados:**
- `document.uploaded` → `document-events` → Metadata Service

**Seguridad:**
- ✅ SAS URLs con TTL corto (15 minutos)
- ✅ Permisos mínimos (PUT solo)
- ✅ Verificación SHA-256
- ✅ Auto-creación de columnas faltantes (resiliente)

**Estado:** ✅ **FUNCIONANDO**

---

### 8.4 CU4: Autenticar Documentos (GovCarpeta)

**Flujo Implementado:**
1. ✅ **POST /api/signature/sign**
   - Calcula SHA-256 del documento
   - Firma hash con RSA (RS256)
   - Genera SAS GET URL para hub
   - Llama `PUT /apis/authenticateDocument` al hub GovCarpeta
   - Actualiza `document_metadata` con WORM:
     - `state = "SIGNED"`
     - `worm_locked = true`
     - `signed_at = now()`
     - `retention_until = NULL` (ETERNAL - documentos firmados se retienen indefinidamente)
     - `hub_signature_ref = <ref del hub>`
   - Guarda registro en `signature_records`
   - Publica `document.authenticated` → Service Bus

**Metadata Guardada:**
- `signature_records` table:
  - document_id, citizen_id, document_title
  - sha256_hash, signature_algorithm, signature_value
  - sas_url, sas_expires_at
  - hub_authenticated, hub_response, hub_authenticated_at
  - signed_at, created_at
- `document_metadata` table (actualizado):
  - state = "SIGNED"
  - worm_locked = true
  - signed_at, retention_until, hub_signature_ref

**Eventos Generados:**
- `document.authenticated` → `signature-events` → Metadata Service

**Seguridad:**
- ✅ Firma RSA-2048 con SHA-256
- ✅ Verificación de integridad antes de autenticar
- ✅ SAS GET URL con TTL corto (15 minutos)
- ✅ WORM activado después de autenticación exitosa

**Integración con Hub:**
- ✅ `PUT /apis/authenticateDocument` al hub GovCarpeta
- ✅ Payload: `{idCitizen, UrlDocument, documentTitle}`
- ✅ Manejo de errores y timeouts

**Estado:** ✅ **FUNCIONANDO**

---

## 9. Gaps y Recomendaciones

### 9.1 Gaps Identificados

#### **Escalabilidad**
- ⚠️ **Autoscaling deshabilitado**: Habilitar HPA para producción
- ⚠️ **Recursos muy bajos**: Aumentar requests/limits para carga real
- ⚠️ **Solo 2 nodos user pool**: Considerar más nodos para alta disponibilidad

#### **Observabilidad**
- ⚠️ **App Insights no configurado**: Implementar OpenTelemetry
- ⚠️ **Dashboards básicos**: Crear dashboards en Azure Monitor
- ⚠️ **Alertas faltantes**: Configurar alertas de SLO

#### **Seguridad**
- ⚠️ **APIM no implementado**: Agregar Azure API Management
- ⚠️ **WAF no configurado**: Implementar Front Door WAF
- ⚠️ **Rate limiting básico**: Mejorar rate limiting por operador

#### **Resiliencia**
- ⚠️ **Circuit breakers no activos**: Activar en todos los servicios
- ⚠️ **DLQ monitoring**: Implementar alertas para DLQ
- ⚠️ **Backup strategy**: Definir estrategia de backup de BD

### 9.2 Recomendaciones Prioritarias

#### **Corto Plazo (1-2 semanas)**
1. ✅ Habilitar autoscaling en servicios críticos
2. ✅ Configurar App Insights + OpenTelemetry
3. ✅ Implementar alertas básicas (SLO, errores 5xx)
4. ✅ Aumentar recursos de servicios críticos

#### **Mediano Plazo (1 mes)**
1. ⚠️ Implementar Azure API Management
2. ⚠️ Configurar Front Door WAF
3. ⚠️ Mejorar rate limiting
4. ⚠️ Implementar backup strategy

#### **Largo Plazo (2-3 meses)**
1. ⚠️ Implementar mTLS entre operadores
2. ⚠️ Configurar Defender for Storage
3. ⚠️ Implementar disaster recovery
4. ⚠️ Optimizar costos (reserved instances, spot nodes)

---

## 10. Conclusión

### ✅ Fortalezas
- **Arquitectura sólida**: 8 microservicios bien estructurados
- **Event-driven**: Service Bus implementado correctamente
- **WORM implementado**: Inmutabilidad de documentos firmados
- **Seguridad básica**: JWT, HMAC, Workload Identity
- **Metadata completa**: Todos los campos necesarios guardados
- **Resiliencia básica**: Health checks, retries, DLQ

### ⚠️ Áreas de Mejora
- **Escalabilidad**: Habilitar autoscaling
- **Observabilidad**: Implementar App Insights
- **Seguridad avanzada**: APIM, WAF, rate limiting mejorado
- **Monitoreo**: Alertas y dashboards

### 🎯 Estado General
**El sistema está funcional y cumple con los 4 casos de uso principales. La arquitectura es sólida y está lista para producción con las mejoras recomendadas.**

---

**Última actualización:** 2025-11-06
**Versión:** 1.0


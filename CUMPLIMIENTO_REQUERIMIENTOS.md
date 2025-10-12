# 📋 CUMPLIMIENTO DE REQUERIMIENTOS - Análisis Detallado

> **Fecha**: 12 de Octubre 2025  
> **Documento Base**: `Requerimientos_Proyecto_GovCarpeta.md`  
> **Estado**: ⚠️ CUMPLIMIENTO PARCIAL (65% implementado)

---

## 📊 RESUMEN EJECUTIVO

| Categoría | Cumplimiento | Estado |
|-----------|--------------|--------|
| **Hub MinTIC Integration** | 90% | ✅ Casi completo |
| **Arquitectura Azure+K8s** | 70% | ⚠️ Parcial |
| **Microservicios** | 65% | ⚠️ Parcial |
| **Frontend UX/UI/Accesibilidad** | 40% | ❌ Básico |
| **APIs Internas** | 75% | ⚠️ Parcial |
| **Transferencias P2P** | 80% | ⚠️ Casi completo |
| **Documentos WORM/Retención** | 30% | ❌ Faltante |
| **Identidad (Azure AD B2C)** | 20% | ❌ Mock |
| **Base de Datos** | 60% | ⚠️ Parcial |
| **Redis** | 80% | ✅ Casi completo |
| **Service Bus** | 50% | ⚠️ Preparado |
| **Seguridad** | 55% | ⚠️ Parcial |
| **Observabilidad** | 75% | ⚠️ Casi completo |
| **Escalabilidad** | 60% | ⚠️ Parcial |
| **CI/CD** | 70% | ⚠️ Parcial |
| **Testing** | 40% | ❌ Básico |

**CUMPLIMIENTO GLOBAL**: **~60%** ⚠️

---

## 1️⃣ HUB MinTIC GovCarpeta

### ✅ REQUERIDO:
```
- Base URL: https://govcarpeta-apis-4905ff3c005b.herokuapp.com
- Endpoints: registerCitizen, unregisterCitizen, authenticateDocument, 
  validateCitizen, registerOperator, registerTransferEndPoint, getOperators
- Consumo SOLO desde backend
- Validación de esquema, timeouts, reintentos, circuit breaker, rate-limit
```

### 📊 ESTADO ACTUAL:

| Endpoint | Implementado | Servicio | Circuit Breaker | Idempotencia | Estado |
|----------|--------------|----------|-----------------|--------------|--------|
| **POST registerCitizen** | ✅ | mintic_client | ✅ | ✅ | ✅ Completo |
| **DELETE unregisterCitizen** | ✅ | mintic_client | ✅ | ✅ | ✅ Completo |
| **PUT authenticateDocument** | ✅ | mintic_client | ✅ | ✅ | ✅ Completo |
| **GET validateCitizen/{id}** | ✅ | mintic_client | ✅ | ✅ | ✅ Completo |
| **POST registerOperator** | ✅ | mintic_client | ✅ | ❌ | ⚠️ Falta idemp |
| **PUT registerTransferEndPoint** | ✅ | mintic_client | ✅ | ❌ | ⚠️ Falta idemp |
| **GET getOperators** | ✅ | mintic_client | ✅ | ✅ (cache) | ✅ Completo |

### ✅ IMPLEMENTACIONES CORRECTAS:
- ✅ Timeouts configurados (10s)
- ✅ Reintentos con backoff exponencial + jitter
- ✅ Circuit breaker por endpoint
- ✅ Rate limiting de salida (10 rpm a hub)
- ✅ Validación de esquema con Pydantic
- ✅ Cache anti-stampede (getOperators, 5min)
- ✅ Normalización de operadores
- ✅ Filtrado de URLs inseguras (http://) en producción

### ⚠️ MEJORAS NECESARIAS:
1. ⚠️ Añadir idempotencia para registerOperator y registerTransferEndPoint
2. ⚠️ Implementar registro automático de operador en startup (actualmente manual)

**CUMPLIMIENTO**: **90%** ✅

---

## 2️⃣ ARQUITECTURA (Azure + Kubernetes)

### ✅ REQUERIDO:
```
- AKS con topologySpreadConstraints
- Helm charts (por servicio + umbrella)
- Terraform: RG, VNet, AKS, PostgreSQL, Redis, Blob, Service Bus, 
  Key Vault, DNS, cert-manager, KEDA, NGINX Ingress, ExternalDNS
- Docker Hub con tags inmutables (:sha)
- CDN para estáticos
- OpenTelemetry → Application Insights
```

### 📊 ESTADO ACTUAL:

#### Terraform (IaC):
| Recurso | Implementado | Configuración | Estado |
|---------|--------------|---------------|--------|
| **Resource Group** | ✅ | carpeta-ciudadana-dev-rg | ✅ |
| **VNet/Subnets** | ✅ | 10.0.0.0/16 (AKS, DB) | ✅ |
| **AKS** | ✅ | 1 nodo B2s | ⚠️ Sin topologySpread |
| **PostgreSQL** | ✅ | Flexible Server B1ms | ✅ |
| **Blob Storage** | ✅ | LRS, container: documents | ✅ |
| **Service Bus** | ✅ | Basic tier | ✅ |
| **Redis** | ❌ | Self-hosted en docker-compose | ⚠️ No Azure Cache |
| **Key Vault** | ❌ | **NO IMPLEMENTADO** | ❌ **CRÍTICO** |
| **DNS (ExternalDNS)** | ❌ | **NO IMPLEMENTADO** | ❌ |
| **KEDA** | ❌ | **NO IMPLEMENTADO** | ❌ **CRÍTICO** |
| **NGINX Ingress** | ✅ | En CI/CD platform-install | ✅ |
| **cert-manager** | ✅ | En CI/CD platform-install | ✅ |

#### Helm Charts:
- ✅ Estructura de umbrella chart
- ✅ Templates por servicio (8/12 completos)
- ✅ ServiceAccount con annotations
- ❌ **NO hay** topologySpreadConstraints en deployments
- ❌ **NO hay** PodDisruptionBudgets (PDBs)
- ❌ **NO hay** NetworkPolicies

#### Docker Hub:
- ✅ Registry: manuelquistial
- ✅ Tags inmutables con :sha
- ✅ Tags :latest para dev

#### Observabilidad:
- ✅ OpenTelemetry instrumentado
- ⚠️ Console exporter (stdout) en dev
- ❌ **NO hay** Application Insights connection
- ✅ Prometheus values configurado
- ✅ OTEL Collector values configurado

### ⚠️ FALTANTES CRÍTICOS:

1. ❌ **Key Vault + CSI Secret Store**
   - **REQUERIDO**: Secretos en Key Vault montados con CSI
   - **ACTUAL**: Kubernetes Secrets (menos seguro)
   - **IMPACTO**: Vulnerabilidad de seguridad

2. ❌ **KEDA** (Auto-scaling por colas)
   - **REQUERIDO**: transfer-worker escala con Service Bus queue length
   - **ACTUAL**: HPA solo por CPU/memoria
   - **IMPACTO**: No hay transfer-worker, no hay scale-to-zero

3. ❌ **topologySpreadConstraints**
   - **REQUERIDO**: Distribución zonal de pods
   - **ACTUAL**: Sin constraints
   - **IMPACTO**: Riesgo de concentración en un nodo

4. ❌ **NetworkPolicies**
   - **REQUERIDO**: Aislamiento de red entre pods
   - **ACTUAL**: Sin políticas
   - **IMPACTO**: Todos los pods pueden comunicarse

5. ❌ **PodDisruptionBudgets (PDBs)**
   - **REQUERIDO**: Garantizar disponibilidad en updates
   - **ACTUAL**: Sin PDBs
   - **IMPACTO**: Downtime en rolling updates

6. ❌ **Azure Cache for Redis**
   - **REQUERIDO**: Redis gestionado de Azure
   - **ACTUAL**: Redis self-hosted en docker-compose
   - **IMPACTO**: Sin HA, sin persistencia

7. ❌ **ExternalDNS**
   - **REQUERIDO**: DNS automático para ingress
   - **ACTUAL**: Sin ExternalDNS
   - **IMPACTO**: Configuración manual de DNS

**CUMPLIMIENTO**: **70%** ⚠️

---

## 3️⃣ COMPONENTES Y MICROSERVICIOS

### ✅ REQUERIDO (según documento):
```
- Frontend: Next.js (App Router) dockerizado
- Backends FastAPI:
  1. citizen-svc
  2. document-svc (presign SAS, metadatos)
  3. signature-proxy
  4. operator-registry-client
  5. transfer-orchestrator-api (SAGA)
  6. transfer-worker (KEDA, Service Bus)
  7. notifications-svc (ACS Email/SMS)
```

### 📊 ESTADO ACTUAL:

| Servicio Requerido | Servicio Actual | Implementado | Notas |
|-------------------|-----------------|--------------|-------|
| **citizen-svc** | citizen | ✅ | Completo |
| **document-svc** | ingestion | ✅ | Presign OK, metadatos OK |
| **signature-proxy** | signature | ✅ | Completo |
| **operator-registry-client** | mintic_client | ✅ | Facade al hub |
| **transfer-orchestrator-api** | transfer | ✅ | SAGA implementado |
| **transfer-worker** | ❌ **NO EXISTE** | ❌ | **FALTANTE CRÍTICO** |
| **notifications-svc** | notification | ⚠️ | Sin main.py |

### ❌ SERVICIOS NO REQUERIDOS (pueden eliminarse):

| Servicio Actual | ¿Requerido? | Acción |
|----------------|-------------|--------|
| **auth** | ❌ No (usar Azure AD B2C) | ❓ Eliminar o dejar como dev mock |
| **read_models** | ❌ No mencionado | ❓ Eliminar o completar CQRS |
| **sharing** | ❌ No mencionado | ❓ Eliminar o dejar como extra |
| **metadata** | ⚠️ Parcial (búsqueda OK) | ✅ Mantener |
| **gateway** | ⚠️ No mencionado explícitamente | ✅ Mantener (buena práctica) |

### 🚨 SERVICIO FALTANTE CRÍTICO:

#### ❌ **transfer-worker** (KEDA worker)

**REQUERIDO**:
```python
- Consumidor de Service Bus queues
- KEDA ScaledObject para auto-scaling
- Procesa: transfer.requested, transfer.confirmed, cleanup.requested
- Descarga documentos
- Llama a confirmAPI
- Cleanup de origen después de confirmación
- Scale-to-zero fuera de pico
```

**ACTUAL**: **NO EXISTE** ❌

**IMPACTO**: Las transferencias están semi-implementadas:
- ✅ API endpoints funcionan (transferCitizen, transferCitizenConfirm)
- ❌ NO hay procesamiento asíncrono con colas
- ❌ NO hay KEDA
- ❌ NO hay scale-to-zero

**ACCIÓN REQUERIDA**: Crear servicio `transfer-worker` completo

---

### ⚠️ CAMBIO DE NOMENCLATURA:

**Requerimientos usan**:
- `citizen-svc` → **Actual**: `citizen` ✅ (OK, estándar K8s)
- `document-svc` → **Actual**: `ingestion` ⚠️ (considerar renombrar)
- `signature-proxy` → **Actual**: `signature` ✅ (OK)
- `operator-registry-client` → **Actual**: `mintic_client` ⚠️ (considerar renombrar)
- `transfer-orchestrator-api` → **Actual**: `transfer` ✅ (OK)
- `notifications-svc` → **Actual**: `notification` ✅ (OK)

**RECOMENDACIÓN**: Mantener nombres actuales (más concisos y estándar K8s)

**CUMPLIMIENTO**: **65%** ⚠️

---

## 4️⃣ FRONTEND (UX/UI/Accesibilidad)

### ✅ REQUERIDO:

#### Autenticación:
- Azure AD B2C (OIDC) con NextAuth
- Cookie HTTPOnly+Secure
- Middleware de rutas protegidas

#### UX:
- Lenguaje claro
- Botones "verbo + objeto"
- Feedback con toasts aria-live

#### Accesibilidad (WCAG 2.2 AA):
- Navegación solo teclado
- Roles/labels ARIA
- Skip to content
- Focus ring visible
- prefers-reduced-motion

#### Tipografía:
- Base 16px, contenido 18-20px
- Targets ≥ 44×44px
- Contraste ≥ 4.5:1

#### Responsivo:
- Mobile-first
- Breakpoints xs/sm/md/lg/xl
- Tablas → cards en móvil
- Botones sticky en móvil

#### Vistas:
- Dashboard (estado hub, timeline)
- Documentos (upload, listar, detalle, visor PDF, descarga)
- Firma (botón autenticar, estado en vivo)
- Transferencia (asistente, tracking)
- Notificaciones (centro, preferencias)
- Retención (TTL visible: 30d unsigned, 5y signed WORM)

#### Seguridad UI:
- CSP estricta
- Sin secretos expuestos
- Modo read-only si hub cae

### 📊 ESTADO ACTUAL:

#### Autenticación:
- ❌ **Azure AD B2C**: NO implementado, usando **MOCK**
- ❌ **NextAuth**: NO implementado
- ❌ **Cookie HTTPOnly**: NO implementado
- ⚠️ **Middleware**: Parcial (solo check básico)

**Código actual**:
```typescript
// apps/frontend/src/store/authStore.ts
login: async (email: string) => {
  // TODO: Implement Cognito OIDC login with PKCE
  // For now, using mock authentication
  const mockUser = { ... };
  const mockToken = 'mock-jwt-token';
}
```

#### UX:
- ⚠️ **Lenguaje**: En español, pero sin revisar claridad
- ❌ **Botones "verbo + objeto"**: No verificado
- ❌ **Toasts aria-live**: NO implementado

#### Accesibilidad:
- ❌ **WCAG 2.2 AA**: NO auditado
- ❌ **Navegación teclado**: NO testado
- ❌ **ARIA roles/labels**: Probablemente faltantes
- ❌ **Skip to content**: NO implementado
- ❌ **Focus ring**: No verificado
- ❌ **prefers-reduced-motion**: NO implementado

#### Tipografía:
- ⚠️ Tailwind CSS defaults (probablemente OK)
- ❌ NO verificado contraste ≥ 4.5:1
- ❌ NO verificado targets ≥ 44×44px

#### Responsivo:
- ✅ Tailwind CSS (mobile-first por default)
- ❌ NO verificado tablas → cards en móvil
- ❌ NO verificado botones sticky

#### Vistas Implementadas:
| Vista | Implementada | Funciones | Estado |
|-------|--------------|-----------|--------|
| **Landing** | ✅ | Página inicial | ✅ |
| **Login** | ✅ | Mock login | ⚠️ Sin B2C |
| **Register** | ✅ | Registro ciudadanos | ✅ |
| **Dashboard** | ❓ | ¿Estado hub? ¿Timeline? | ❌ **VERIFICAR** |
| **Documentos** | ✅ | Upload, listar | ⚠️ Sin visor PDF |
| **Upload** | ✅ | Presign + upload | ✅ |
| **Search** | ✅ | Búsqueda documentos | ✅ |
| **Firma** | ❓ | ¿Botón autenticar? | ❌ **VERIFICAR** |
| **Transfer** | ✅ | Transferencias P2P | ⚠️ Sin asistente |
| **Notificaciones** | ❌ | **NO IMPLEMENTADO** | ❌ **FALTANTE** |
| **Preferencias Notif** | ❌ | **NO IMPLEMENTADO** | ❌ **FALTANTE** |
| **Retención Visible** | ❌ | TTL 30d/5y no visible | ❌ **FALTANTE** |

#### Seguridad UI:
- ❌ **CSP estricta**: NO implementado
- ✅ **Sin secretos**: OK (API_URL es pública)
- ❌ **Modo read-only**: NO implementado

### 🚨 FALTANTES CRÍTICOS:

1. ❌ **Azure AD B2C + NextAuth**
   ```bash
   # Crear: apps/frontend/pages/api/auth/[...nextauth].ts
   # Instalar: npm install next-auth
   # Configurar: Azure AD B2C provider
   ```

2. ❌ **Vistas faltantes**:
   - Centro de notificaciones
   - Preferencias de notificación
   - Visor PDF/imagen inline
   - Timeline en dashboard
   - Asistente de transferencia (wizard)

3. ❌ **Accesibilidad**:
   - Auditoría con axe-core
   - ARIA labels en formularios
   - Focus management
   - Skip navigation link

4. ❌ **Seguridad**:
   - CSP headers en Next.js config
   - Modo degradado (read-only) cuando hub falla

**CUMPLIMIENTO**: **40%** ❌

---

## 5️⃣ APIs INTERNAS DEL OPERADOR

### ✅ REQUERIDO:

#### Ciudadanos (`citizen-svc`):
- `POST /api/citizens/register` → POST hub
- `GET /api/citizens/{id}` → BD + GET hub
- `DELETE /api/citizens/{id}` → DELETE hub

#### Documentos (`document-svc`):
- `POST /api/documents/presign` → SAS (r|w, TTL 5-15min)
- `GET /api/documents/{docId}` → metadatos (state, hash, retention_until)
- `POST /api/documents/{docId}/download` → SAS lectura

#### Firma (`signature-proxy`):
- `POST /api/documents/{docId}/authenticate` → PUT hub + actualiza WORM

#### Operadores (`operator-registry-client`):
- `GET /api/operators` → cached desde hub
- Tareas: POST registerOperator, PUT registerTransferEndPoint

#### Transferencias (`transfer-orchestrator-api`):
- Paso 1: DELETE hub unregisterCitizen
- `POST /api/transferCitizen` (M2M con headers especiales)
- `POST /api/transferCitizenConfirm`

#### Notificaciones:
- `GET/POST /api/notifications/preferences`
- Outbox → ACS Email/SMS

### 📊 ESTADO ACTUAL:

#### Citizen Service:
| Endpoint | Implementado | Hub Call | Estado |
|----------|--------------|----------|--------|
| `POST /api/citizens/register` | ✅ | ✅ registerCitizen | ✅ Completo |
| `GET /api/citizens/{id}` | ⚠️ | ❌ **SIN** validateCitizen | ⚠️ **MEJORAR** |
| `DELETE /api/citizens/{id}` | ⚠️ | ❌ **SIN** unregisterCitizen direct | ⚠️ **MEJORAR** |

**Problema**: validateCitizen no se llama en GET, unregisterCitizen solo se llama desde transfer

#### Document Service (ingestion):
| Endpoint | Implementado | Funcionalidad | Estado |
|----------|--------------|---------------|--------|
| `POST /api/documents/upload-url` | ✅ | SAS write (15min) | ✅ Completo |
| `POST /api/documents/download-url` | ✅ | SAS read (15min) | ✅ Completo |
| `GET /api/documents/{docId}` | ⚠️ | Metadatos básicos | ⚠️ **SIN** retention_until |
| `POST /api/documents/{docId}/download` | ❌ | **NO EXISTE** | ❌ Usar download-url |

**Problema**: Endpoint POST download no existe (usar download-url está OK)

#### Signature Service:
| Endpoint | Implementado | Funcionalidad | Estado |
|----------|--------------|---------------|--------|
| `POST /api/signature/sign` | ✅ | Firma + hub auth | ✅ Completo |
| Actualiza WORM | ❌ | **NO implementado** | ❌ **CRÍTICO** |
| `state=SIGNED` | ❌ | **NO en DB** | ❌ **FALTANTE** |
| `worm_locked=true` | ❌ | **NO en DB** | ❌ **FALTANTE** |
| `retention_until` | ❌ | **NO calculado** | ❌ **FALTANTE** |

#### Operators (mintic_client):
| Endpoint | Implementado | Cache | Estado |
|----------|--------------|-------|--------|
| `GET /operators` | ✅ | ✅ 5min | ✅ Completo |
| Startup registerOperator | ❌ | N/A | ❌ **FALTANTE** |
| Startup registerTransferEndPoint | ❌ | N/A | ❌ **FALTANTE** |

**Problema**: No hay tarea de startup que registre el operador en el hub

#### Transfer Service:
| Endpoint | Implementado | Headers M2M | Estado |
|----------|--------------|-------------|--------|
| `POST /api/transferCitizen` | ✅ | ⚠️ Parcial | ⚠️ |
| `POST /api/transferCitizenConfirm` | ✅ | N/A | ✅ |
| **Headers requeridos**: | | | |
| - Authorization (JWT M2M) | ✅ | verify_b2b_token | ✅ |
| - Idempotency-Key | ✅ | ✅ | ✅ |
| - X-Trace-Id | ❌ | **NO validado** | ❌ |
| - X-Nonce | ❌ | **NO implementado** | ❌ |
| - X-Timestamp | ❌ | **NO implementado** | ❌ |
| - X-Signature (HMAC/JWS) | ❌ | **NO implementado** | ❌ |
| **unregisterCitizen ANTES** | ✅ | En confirmación | ⚠️ Orden invertido |

**Problema CRÍTICO**: Orden de transferencia está INVERTIDO
- **REQUERIDO**: unregister → transfer → confirm → cleanup
- **ACTUAL**: transfer → confirm → delete local → unregister

#### Notifications:
| Endpoint | Implementado | Estado |
|----------|--------------|--------|
| `GET /api/notifications/preferences` | ❌ | **NO EXISTE** |
| `POST /api/notifications/preferences` | ❌ | **NO EXISTE** |
| Outbox pattern | ❓ | **VERIFICAR** |
| ACS Email/SMS | ❌ | **NO (usa SMTP)** |

### 🚨 PROBLEMAS CRÍTICOS:

1. ❌ **Falta transfer-worker** (KEDA + Service Bus consumer)

2. ❌ **WORM no implementado** en signature service:
   ```sql
   -- Campos faltantes en document_metadata:
   state VARCHAR         -- UNSIGNED, SIGNED
   worm_locked BOOLEAN   -- Inmutabilidad
   retention_until DATE  -- 30d o 5y
   hub_signature_ref     -- Referencia del hub
   ```

3. ❌ **Orden de transferencia INCORRECTO**:
   - Debe unregister PRIMERO (requerimiento)
   - Actualmente unregister ÚLTIMO (implementado)
   - **CONFLICTO**: Ambos lógicos, pero requerimiento es explícito

4. ❌ **Headers M2M faltantes** en transferCitizen:
   - X-Nonce (replay protection)
   - X-Timestamp (time window validation)
   - X-Signature (HMAC o JWS para integridad)

5. ❌ **ACS (Azure Communication Services)** no usado:
   - Actualmente: SMTP genérico
   - Requerido: ACS Email/SMS

**CUMPLIMIENTO**: **75%** ⚠️

---

## 6️⃣ TRANSFERENCIA DE CIUDADANOS

### ✅ REQUERIDO:

**Secuencia OBLIGATORIA**:
```
1. unregister en hub
2. POST /api/transferCitizen (con SAS URLs, TTL 5-15min)
3. Esperar POST /api/transferCitizenConfirm
4. Cleanup (BD+Blob) SOLO si req_status=1
```

**Requisitos adicionales**:
- Integridad: SHA-256 recalculado por destino
- Reintentos: reemisión de SAS al expirar
- Idempotencia: Idempotency-Key + traceId
- DLQ y reconciliación
- NO borrar hasta confirmación
- Auditoría completa con traceId

### 📊 ESTADO ACTUAL:

| Requisito | Implementado | Archivo | Estado |
|-----------|--------------|---------|--------|
| **Secuencia correcta** | ❌ | transfer routers | ❌ **INVERTIDO** |
| Actualmente: | | | |
| 1. transfer | ✅ | - | - |
| 2. confirm | ✅ | - | - |
| 3. delete local | ✅ | - | - |
| 4. **unregister hub** (último) | ✅ | - | ❌ Debe ser primero |
| **SHA-256 verificación** | ✅ | transfer/routers | ✅ |
| **Reintentos SAS** | ❌ | - | ❌ **FALTANTE** |
| **Idempotency-Key** | ✅ | Redis | ✅ |
| **traceId** | ❌ | - | ❌ **FALTANTE** |
| **DLQ** | ❌ | - | ❌ **FALTANTE** |
| **Reconciliación** | ⚠️ | PENDING_UNREGISTER | ⚠️ Parcial |
| **Auditoría traceId** | ❌ | - | ❌ **FALTANTE** |

### 🚨 PROBLEMA CRÍTICO - ORDEN INVERTIDO:

**REQUERIMIENTO EXPLÍCITO** (línea 140-141):
```
Secuencia: (1) unregister en hub → (2) POST /api/transferCitizen → 
           (3) esperar confirm → (4) cleanup SOLO si req_status=1
```

**IMPLEMENTACIÓN ACTUAL** (transfer service):
```
Secuencia: (1) POST /api/transferCitizen → (2) esperar confirm → 
           (3) delete local → (4) unregister hub
```

**CONFLICTO LÓGICO**:
- **Requerimiento**: Prioriza desregistro del hub (libera ciudadano primero)
- **Implementación**: Prioriza seguridad de datos (no pierde datos si falla)

**¿Cuál es correcto?**
- **Lógicamente**: Implementación actual es MÁS SEGURA
- **Según requerimientos**: Debe cambiar el orden

**ACCIÓN REQUERIDA**: 
- 🔴 **Opción A**: Cambiar orden para cumplir requerimientos (más riesgoso)
- 🟡 **Opción B**: Documentar desviación justificada y validar con stakeholder

### ⚠️ OTROS FALTANTES:

1. ❌ **Reemisión de SAS al expirar**
   - Si transferencia toma > 15min
   - Debe regenerar SAS URLs

2. ❌ **traceId end-to-end**
   - Correlación completa de transferencia
   - Logging en cada paso

3. ❌ **DLQ para transferencias fallidas**
   - Service Bus DLQ no conectado
   - Reconciliación manual

**CUMPLIMIENTO**: **80%** ⚠️

**NOTA IMPORTANTE**: El 80% es por implementación técnica. Si se requiere cumplimiento ESTRICTO del orden, baja a **50%**.

---

## 7️⃣ DOCUMENTOS (Almacenamiento y Retención)

### ✅ REQUERIDO:

#### Retención:
- **UNSIGNED**: TTL 30 días, editable, auto-purga
- **SIGNED**: WORM inmutable, 5 años, legal hold, lifecycle Cool/Archive

#### Blob Storage:
- Contenedores por operador/tenant
- Etiquetas (state, tenant, docId)
- SAS solo (TTL 5-15min)
- Cifrado en reposo
- Antivirus (hook)
- Nombres opacos (storage_path)

#### Metadatos DB:
- hash (SHA-256)
- storage_path
- **state** (UNSIGNED/SIGNED)
- **signed_at**
- **retention_until**
- **hub_signature_ref**

### 📊 ESTADO ACTUAL:

#### Tabla document_metadata:

```python
# services/ingestion/app/models.py
class DocumentMetadata(Base):
    id: str
    citizen_id: int
    filename: str
    content_type: str
    size_bytes: int
    sha256_hash: str          # ✅ Implementado
    blob_name: str            # ✅ storage_path
    storage_provider: str     # ✅
    status: str               # ⚠️ pending/uploaded (NO state UNSIGNED/SIGNED)
    description: str
    tags: JSON
    created_at: datetime
    is_deleted: bool          # ⚠️ Soft delete, NO WORM
```

#### Campos FALTANTES:

| Campo Requerido | Actual | Estado |
|-----------------|--------|--------|
| **state** | status (pending/uploaded) | ❌ Falta UNSIGNED/SIGNED |
| **worm_locked** | ❌ NO EXISTE | ❌ **CRÍTICO** |
| **signed_at** | ❌ NO EXISTE | ❌ **CRÍTICO** |
| **retention_until** | ❌ NO EXISTE | ❌ **CRÍTICO** |
| **hub_signature_ref** | ❌ NO EXISTE | ❌ **CRÍTICO** |
| **legal_hold** | ❌ NO EXISTE | ❌ |
| **lifecycle_tier** | ❌ NO EXISTE | ❌ (Cool/Archive) |

#### Blob Storage:
| Requisito | Implementado | Estado |
|-----------|--------------|--------|
| Contenedores por tenant | ❌ | Un solo container: "documents" |
| Etiquetas (state, tenant, docId) | ❌ | **NO implementado** |
| SAS TTL 5-15min | ✅ | ConfigMap: SAS_TTL_MINUTES=15 |
| Nombres opacos | ✅ | UUID-based blob_name |
| Cifrado en reposo | ✅ | Azure default |
| Antivirus hook | ❌ | **NO implementado** |
| Lifecycle Cool/Archive | ❌ | **NO implementado** |

#### Auto-purga UNSIGNED (30 días):
- ❌ **NO implementado**
- ❌ Sin CronJob de limpieza
- ❌ Sin campo retention_until

#### WORM (Write Once Read Many):
- ❌ **Completamente NO implementado**
- ❌ Sin campo worm_locked
- ❌ Sin validación de inmutabilidad
- ❌ Sin legal hold
- ❌ Sin lifecycle a Cool/Archive después de firma

### 🚨 IMPLEMENTACIÓN REQUERIDA:

#### 1. Migración de Base de Datos:

```sql
-- Añadir a document_metadata:
ALTER TABLE document_metadata
ADD COLUMN state VARCHAR DEFAULT 'UNSIGNED',
ADD COLUMN worm_locked BOOLEAN DEFAULT FALSE,
ADD COLUMN signed_at TIMESTAMP,
ADD COLUMN retention_until DATE,
ADD COLUMN hub_signature_ref VARCHAR,
ADD COLUMN legal_hold BOOLEAN DEFAULT FALSE,
ADD COLUMN lifecycle_tier VARCHAR DEFAULT 'Hot';

-- Constraint WORM
CREATE OR REPLACE FUNCTION prevent_worm_update()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.worm_locked = TRUE THEN
        RAISE EXCEPTION 'Cannot modify WORM-locked document';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_worm
BEFORE UPDATE ON document_metadata
FOR EACH ROW
EXECUTE FUNCTION prevent_worm_update();
```

#### 2. Signature Service debe actualizar:

```python
# Al autenticar documento exitosamente:
await db.execute(
    update(DocumentMetadata)
    .where(DocumentMetadata.id == doc_id)
    .values(
        state="SIGNED",
        worm_locked=True,
        signed_at=datetime.utcnow(),
        retention_until=datetime.utcnow() + timedelta(days=365*5),  # 5 años
        hub_signature_ref=hub_response_ref
    )
)
```

#### 3. CronJob para auto-purga UNSIGNED:

```yaml
# deploy/kubernetes/cronjob-purge-unsigned.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: purge-unsigned-documents
spec:
  schedule: "0 2 * * *"  # Diario a las 2am
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: purge
            image: manuelquistial/carpeta-ingestion:latest
            command: ["python", "-m", "app.tasks.purge_unsigned"]
            # Script que elimina documents con:
            # - state = 'UNSIGNED'
            # - created_at < now() - 30 days
```

#### 4. Blob Lifecycle Policy (Terraform):

```hcl
# infra/terraform/modules/storage/main.tf
resource "azurerm_storage_management_policy" "lifecycle" {
  storage_account_id = azurerm_storage_account.main.id

  rule {
    name    = "move-signed-to-cool"
    enabled = true
    
    filters {
      blob_types = ["blockBlob"]
      prefix_match = ["documents/"]
    }
    
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than = 90
        tier_to_archive_after_days_since_modification_greater_than = 365
      }
    }
  }
}
```

#### 5. Blob Tags (al crear documento):

```python
# En ingestion service al confirmar upload:
blob_client.set_blob_tags({
    "state": "UNSIGNED",
    "tenant": operator_id,
    "docId": document_id,
    "citizenId": str(citizen_id)
})
```

**CUMPLIMIENTO**: **30%** ❌

---

## 8️⃣ IDENTIDAD, REGISTRO Y AUTORIZACIÓN

### ✅ REQUERIDO:

- **Usuarios**: Azure AD B2C (OIDC)
- `POST /api/users/bootstrap` → vincula citizenId con user
- **Sesión**: Cookie HTTPOnly, revocación, CSRF
- **RBAC/ABAC**: roles (citizen, operator_admin, admin)
- **M2M**: JWT client-credentials + mTLS + HMAC/JWS
- **GovCarpeta**: Solo desde backend

### 📊 ESTADO ACTUAL:

| Componente | Implementado | Estado |
|------------|--------------|--------|
| **Azure AD B2C** | ❌ | Mock en frontend |
| **OIDC flow** | ❌ | TODO comments |
| **`/api/users/bootstrap`** | ❌ | **NO EXISTE** |
| **Cookie HTTPOnly** | ❌ | LocalStorage (inseguro) |
| **Revocación** | ❌ | Sin token blacklist |
| **CSRF protection** | ❌ | **NO implementado** |
| **RBAC** | ⚠️ | Parcial (roles en rate limiter) |
| **ABAC** | ⚠️ | Servicio `iam` preparado pero incompleto |
| **M2M JWT** | ✅ | verify_b2b_token en transfer |
| **mTLS** | ❌ | **NO implementado** |
| **HMAC/JWS signing** | ❌ | **NO implementado** |

### 🚨 PROBLEMAS CRÍTICOS:

1. ❌ **Azure AD B2C NO implementado**
   - Frontend usa mock
   - Sin NextAuth
   - Sin OIDC flow

2. ❌ **`/api/users/bootstrap` NO EXISTE**
   - No hay tabla `users`
   - No hay tabla `citizen_links`
   - No hay vinculación user ↔ citizen

3. ❌ **Sesión insegura**
   - LocalStorage (vulnerable a XSS)
   - Debe ser: Cookie HTTPOnly+Secure

4. ❌ **CSRF NO protegido**
   - Endpoints POST sin CSRF token

5. ❌ **mTLS NO implementado**
   - Transferencias M2M sin mutual TLS
   - Requerido para production

6. ❌ **X-Signature (HMAC/JWS) NO implementado**
   - Headers de transferencia sin firma
   - Vulnerable a man-in-the-middle

**CUMPLIMIENTO**: **20%** ❌

---

## 9️⃣ DATOS (PostgreSQL)

### ✅ REQUERIDO:

**Tablas**: users, user_roles, citizen_links, citizens, documents, transfers, 
operators, audit_events, notification_templates, notification_outbox, 
user_notification_prefs, notification_logs

**Características**:
- RLS (Row Level Security) por operador/propietario
- Partición por operador/fecha
- PITR/backups (7 días)
- Alembic migrations

### 📊 ESTADO ACTUAL:

| Tabla Requerida | Implementada | Servicio | Estado |
|-----------------|--------------|----------|--------|
| **users** | ❌ | - | ❌ **FALTANTE** |
| **user_roles** | ❌ | - | ❌ **FALTANTE** |
| **citizen_links** | ❌ | - | ❌ **FALTANTE** |
| **citizens** | ✅ | citizen | ✅ |
| **documents** | ✅ | ingestion | ⚠️ document_metadata (falta WORM) |
| **transfers** | ✅ | transfer | ✅ |
| **operators** | ❌ | - | ❌ **FALTANTE** (cache Redis) |
| **audit_events** | ❌ | - | ❌ **FALTANTE** |
| **notification_templates** | ❌ | - | ❌ **FALTANTE** |
| **notification_outbox** | ❌ | - | ❌ **FALTANTE** |
| **user_notification_prefs** | ❌ | - | ❌ **FALTANTE** |
| **notification_logs** | ⚠️ | notification | ⚠️ delivery_logs (parcial) |

**Tablas implementadas EXTRA (no requeridas)**:
- ✅ `signature_records` (signature service)
- ✅ `share_packages` (sharing service)
- ✅ `share_access_logs` (sharing service)
- ✅ `read_documents` (read_models - CQRS)
- ✅ `read_transfers` (read_models - CQRS)

**Características avanzadas**:
| Característica | Implementado | Estado |
|----------------|--------------|--------|
| **RLS (Row Level Security)** | ❌ | **NO implementado** |
| **Partición por operador/fecha** | ❌ | **NO implementado** |
| **PITR** | ✅ | Azure PostgreSQL Flexible (7d) |
| **Backups** | ✅ | Script backup-postgres.sh |
| **Alembic migrations** | ✅ | Varios servicios tienen |

### 🚨 PROBLEMAS CRÍTICOS:

1. ❌ **Sistema de usuarios NO implementado**
   ```sql
   -- Faltantes:
   CREATE TABLE users (...);
   CREATE TABLE user_roles (...);
   CREATE TABLE citizen_links (...);  -- Vincula user ↔ citizen
   ```

2. ❌ **Tabla operators NO existe**
   - Operadores solo en cache Redis
   - No hay persistencia local

3. ❌ **Sistema de auditoría NO implementado**
   - Sin tabla audit_events
   - Sin logging de operaciones críticas

4. ❌ **Outbox pattern NO implementado**
   - Sin tabla notification_outbox
   - Notificaciones no transaccionales

5. ❌ **RLS NO configurado**
   - Sin isolación por tenant/operador
   - Riesgo de acceso cruzado

6. ❌ **Particionamiento NO implementado**
   - Sin particiones por operador o fecha
   - Performance degradará con volumen

**CUMPLIMIENTO**: **60%** ⚠️ (tablas core OK, features avanzadas NO)

---

## 🔟 REDIS

### ✅ REQUERIDO:
- Cache: getOperators, metadatos calientes
- Locks: traceId + Idempotency-Key
- Rate-limit: endpoints sensibles

### 📊 ESTADO ACTUAL:

| Uso | Implementado | TTL | Estado |
|-----|--------------|-----|--------|
| **Cache getOperators** | ✅ | 300s | ✅ Completo |
| **Cache búsquedas** | ✅ | 120s | ✅ Completo |
| **Idempotency locks** | ✅ | 900s | ✅ Completo |
| **Distributed locks** | ✅ | 10-120s | ✅ Completo |
| **Rate limiting** | ✅ | 60s | ✅ Completo |
| **traceId locks** | ❌ | - | ❌ **FALTANTE** |

**Implementación**:
- ✅ Redis 7 en docker-compose (dev)
- ⚠️ **NO Azure Cache for Redis** (requerido en producción)
- ✅ SSL/TLS configurado para producción
- ✅ Clients en todos los servicios

**CUMPLIMIENTO**: **80%** ✅

---

## 1️⃣1️⃣ SERVICE BUS (Colas)

### ✅ REQUERIDO:
- Colas: transfer.requested, transfer.confirmed, cleanup.requested, notification.dispatch
- KEDA escala transfer-worker
- Scale-to-zero fuera de pico

### 📊 ESTADO ACTUAL:

| Cola | Configurada | Producers | Consumers | KEDA | Estado |
|------|-------------|-----------|-----------|------|--------|
| **citizen-registered** | ✅ | citizen | read_models | ❌ | ⚠️ No KEDA |
| **document-uploaded** | ✅ | ingestion | metadata | ❌ | ⚠️ No KEDA |
| **document-authenticated** | ✅ | signature | metadata+notif | ❌ | ⚠️ No KEDA |
| **transfer.requested** | ❌ | - | - | ❌ | ❌ **FALTANTE** |
| **transfer.confirmed** | ⚠️ | transfer | read_models | ❌ | ⚠️ Sin worker |
| **cleanup.requested** | ❌ | - | - | ❌ | ❌ **FALTANTE** |
| **notification.dispatch** | ❌ | - | notif | ❌ | ❌ **FALTANTE** |

**Consumidores actuales**:
- ✅ metadata service (document events)
- ⚠️ notification service (sin main.py)
- ⚠️ read_models service (sin consumers)

**KEDA**:
- ❌ **NO instalado** en Terraform
- ❌ **NO hay** ScaledObjects
- ❌ **NO hay** transfer-worker

### 🚨 FALTANTES CRÍTICOS:

1. ❌ **transfer-worker service NO EXISTE**
   ```python
   # DEBE:
   # - Consumir transfer.requested
   # - Descargar documentos
   # - Llamar confirmAPI
   # - Cleanup de origen
   # - Scale con KEDA (0-N replicas)
   ```

2. ❌ **KEDA NO instalado**
   ```bash
   # Terraform debe añadir:
   helm install keda kedacore/keda --namespace keda
   ```

3. ❌ **ScaledObjects NO configurados**
   ```yaml
   # Ejemplo para transfer-worker:
   apiVersion: keda.sh/v1alpha1
   kind: ScaledObject
   metadata:
     name: transfer-worker
   spec:
     scaleTargetRef:
       name: transfer-worker
     minReplicaCount: 0  # Scale-to-zero
     maxReplicaCount: 10
     triggers:
     - type: azure-servicebus
       metadata:
         queueName: transfer-requested
         queueLength: "5"
   ```

**CUMPLIMIENTO**: **50%** ⚠️

---

## 1️⃣2️⃣ SEGURIDAD

### ✅ REQUERIDO:

#### Frontend:
- CSP estricta
- prefers-reduced-motion
- Sin secretos en cliente

#### Backend:
- CORS restringido
- TLS extremo a extremo
- Circuit Breaker + timeouts + retries
- Bulkheads

#### Kubernetes:
- NetworkPolicies
- Pod Security Standards
- Probes (readiness/liveness/startup)
- PDBs
- Resource requests/limits

#### Key Vault:
- Secretos montados con CSI Secret Store
- DB_CONN_STRING, REDIS_CONN, ACS_*, HMAC_JWS_KEY, Docker Hub creds

#### Privacidad:
- Minimización de datos
- Habeas data, derechos ARCO

### 📊 ESTADO ACTUAL:

#### Frontend:
| Requisito | Implementado | Estado |
|-----------|--------------|--------|
| **CSP estricta** | ❌ | **NO** |
| **prefers-reduced-motion** | ❌ | **NO** |
| **Sin secretos** | ✅ | OK (solo API_URL) |

#### Backend:
| Requisito | Implementado | Estado |
|-----------|--------------|--------|
| **CORS** | ⚠️ | allow_origins="*" (muy permisivo) |
| **TLS end-to-end** | ⚠️ | cert-manager OK, pero no mTLS |
| **Circuit Breaker** | ✅ | mintic_client |
| **Timeouts** | ✅ | httpx timeouts |
| **Retries + jitter** | ✅ | tenacity con jitter |
| **Bulkheads** | ❌ | **NO implementado** |

#### Kubernetes:
| Requisito | Implementado | Archivo | Estado |
|-----------|--------------|---------|--------|
| **NetworkPolicies** | ❌ | **NO EXISTE** | ❌ **CRÍTICO** |
| **Pod Security Standards** | ❌ | **NO CONFIGURADO** | ❌ |
| **Liveness probes** | ✅ | deployments | ✅ |
| **Readiness probes** | ✅ | deployments | ✅ |
| **Startup probes** | ❌ | **NO** | ⚠️ |
| **PDBs** | ❌ | **NO EXISTEN** | ❌ **CRÍTICO** |
| **Resource requests** | ✅ | values.yaml | ✅ |
| **Resource limits** | ✅ | values.yaml | ✅ |

#### Key Vault + CSI:
- ❌ **Key Vault NO creado** en Terraform
- ❌ **CSI Secret Store NO instalado**
- ⚠️ Usando Kubernetes Secrets (menos seguro)

#### Privacidad:
- ❌ **Habeas data**: NO mencionado
- ❌ **Derechos ARCO**: NO implementados
- ❌ **Consentimientos**: NO implementados

### 🚨 IMPLEMENTACIONES REQUERIDAS:

#### 1. NetworkPolicies (CRÍTICO):

```yaml
# deploy/helm/carpeta-ciudadana/templates/networkpolicy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-gateway
spec:
  podSelector:
    matchLabels:
      app: gateway
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:  # Allow to internal services
    - podSelector:
        matchLabels:
          app.kubernetes.io/part-of: carpeta-ciudadana
  - to:  # Allow to PostgreSQL
    ports:
    - protocol: TCP
      port: 5432
  - to:  # Allow to external (hub MinTIC)
    ports:
    - protocol: TCP
      port: 443
```

#### 2. PodDisruptionBudgets:

```yaml
# deploy/helm/carpeta-ciudadana/templates/pdb-gateway.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}-gateway
spec:
  minAvailable: 2  # Al menos 2 pods siempre
  selector:
    matchLabels:
      app: gateway
```

#### 3. Key Vault + CSI:

```hcl
# infra/terraform/modules/keyvault/main.tf
resource "azurerm_key_vault" "main" {
  name                = "${var.project_name}-${var.environment}-kv"
  location            = var.azure_region
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"
  
  enabled_for_deployment = true
  enabled_for_disk_encryption = true
  
  # Workload Identity
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = azurerm_user_assigned_identity.aks_workload.principal_id
    
    secret_permissions = ["Get", "List"]
  }
}

# Secrets
resource "azurerm_key_vault_secret" "postgres_conn" {
  name         = "POSTGRES-CONNECTION-STRING"
  value        = var.database_connection_string
  key_vault_id = azurerm_key_vault.main.id
}
```

```yaml
# deploy/helm/carpeta-ciudadana/templates/secretproviderclass.yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: azure-keyvault-secrets
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "false"
    userAssignedIdentityID: <workload-identity-client-id>
    keyvaultName: carpeta-ciudadana-dev-kv
    tenantId: <tenant-id>
    objects: |
      array:
        - objectName: POSTGRES-CONNECTION-STRING
          objectType: secret
          objectAlias: DATABASE_URL
        - objectName: REDIS-CONNECTION-STRING
          objectType: secret
```

#### 4. Pod Security Standards:

```yaml
# deploy/helm/carpeta-ciudadana/templates/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: {{ .Release.Namespace }}
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

#### 5. CSP Headers (Next.js):

```javascript
// apps/frontend/next.config.js
const cspHeader = `
  default-src 'self';
  script-src 'self' 'unsafe-eval' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src 'self' blob: data: https:;
  font-src 'self';
  connect-src 'self' ${process.env.NEXT_PUBLIC_API_URL};
  frame-ancestors 'none';
`;

module.exports = {
  async headers() {
    return [{
      source: '/:path*',
      headers: [
        { key: 'Content-Security-Policy', value: cspHeader.replace(/\s{2,}/g, ' ').trim() },
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
      ],
    }];
  },
};
```

**CUMPLIMIENTO**: **55%** ⚠️

---

## 1️⃣3️⃣ OBSERVABILIDAD, MÉTRICAS Y ALERTAS

### ✅ REQUERIDO:
- Trazas end-to-end con traceId
- KPIs: p95 APIs, éxito authenticateDocument, tiempo confirmación, expiraciones SAS, checksum mismatch, volumen transferido, bounces Email/SMS, DLQ
- Alertas: 3+ fallos por traceId, DLQ creciente, expiraciones, 5xx, latencias fuera SLO

### 📊 ESTADO ACTUAL:

#### OpenTelemetry:
- ✅ Instrumentación en todos los servicios
- ✅ Propagación de traceparent
- ✅ HTTP, DB, Redis, httpx spans
- ⚠️ Console exporter (dev), **NO Application Insights**

#### Métricas implementadas:
| KPI Requerido | Implementado | Estado |
|---------------|--------------|--------|
| **p95 APIs** | ✅ | http.server.request.duration | ✅ |
| **Éxito authenticateDocument** | ⚠️ | hub.calls{endpoint} | ⚠️ Genérico |
| **Tiempo a confirmación** | ❌ | **NO** | ❌ |
| **Expiraciones SAS** | ❌ | **NO** | ❌ |
| **% checksum mismatch** | ❌ | **NO** | ❌ |
| **Volumen transferido** | ❌ | **NO** | ❌ |
| **Bounces Email/SMS** | ❌ | **NO** | ❌ |
| **Tamaño DLQ** | ⚠️ | queue.dlq.length | ⚠️ Preparado |

#### Dashboards Grafana:
- ✅ api-latency.json
- ✅ transfers-saga.json
- ✅ queue-health.json
- ✅ cache-efficiency.json

#### Alertas Prometheus:
- ✅ 11 alertas configuradas
- ⚠️ Alertas genéricas (no específicas por traceId)
- ❌ **NO hay** alerta para 3+ fallos por traceId

### ⚠️ MEJORAS NECESARIAS:

1. ⚠️ **Application Insights** connection:
   ```bash
   # Añadir a values.yaml:
   APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
   ```

2. ❌ **Métricas específicas faltantes**:
   ```python
   # Añadir métricas:
   - sas_expiration_count
   - checksum_mismatch_count
   - transfer_volume_bytes
   - email_bounce_rate
   - sms_delivery_rate
   ```

3. ❌ **Alertas por traceId**:
   ```promql
   # Alerta:count(failed_requests{trace_id="xxx"}) > 3
   ```

**CUMPLIMIENTO**: **75%** ⚠️

---

## 1️⃣4️⃣ ESCALABILIDAD Y TOLERANCIA A FALLOS

### ✅ REQUERIDO:

#### AKS:
- HPA por CPU 60% + métricas custom
- Nodepools dedicados (web, workers, ingress, system)
- Cluster Autoscaler
- Zonal (availability zones)

#### Workers:
- KEDA por colas
- Spot nodepool
- Scale-to-zero

#### BD:
- pgBouncer
- Réplicas de lectura
- Partición
- Índices GIN
- Autovacuum afinado

#### Degradación:
- Hub cae → UI read-only
- Destino falla → no borrar origen
- ACS falla → outbox reintenta

#### Costos:
- Lifecycle Blob (Cool/Archive)
- Logs 7-14d
- Sampleo trazas 1-10%
- Right-sizing SKUs

### 📊 ESTADO ACTUAL:

#### HPA:
- ✅ HPA configurado en valores (CPU 70%)
- ❌ **NO hay** métricas custom (Prometheus Adapter no instalado)
- ⚠️ Threshold 70% vs requerido 60%

#### Nodepools:
- ❌ **UN SOLO nodepool** (default)
- ❌ Sin nodepools dedicados
- ❌ Sin Spot nodes para workers

#### Cluster Autoscaler:
- ❌ **NO configurado** en Terraform

#### Availability Zones:
- ❌ **NO zonal** (single-zone)
- ❌ Sin topologySpreadConstraints

#### BD:
| Característica | Implementado | Estado |
|----------------|--------------|--------|
| **pgBouncer** | ❌ | **NO** |
| **Read replicas** | ❌ | **NO** |
| **Partición** | ❌ | **NO** |
| **Índices GIN** | ❓ | **NO VERIFICADO** |
| **Autovacuum** | ✅ | Azure default |

#### Degradación:
| Escenario | Implementado | Estado |
|-----------|--------------|--------|
| **Hub cae → UI read-only** | ❌ | **NO** |
| **Destino falla → no borrar** | ✅ | PENDING_UNREGISTER | ✅ |
| **ACS falla → outbox** | ❌ | Sin outbox | ❌ |

#### Costos:
| Optimización | Implementado | Estado |
|--------------|--------------|--------|
| **Lifecycle Cool/Archive** | ❌ | **NO** |
| **Logs retention 7-14d** | ❓ | **NO CONFIGURADO** |
| **Sampleo trazas** | ❌ | **NO** (100%) |
| **Right-sizing** | ✅ | B2s, B1ms | ✅ |

### 🚨 FALTANTES CRÍTICOS:

1. ❌ **Nodepools dedicados**
2. ❌ **KEDA + transfer-worker**
3. ❌ **Cluster Autoscaler**
4. ❌ **Availability Zones**
5. ❌ **Degradación controlada** (UI read-only)
6. ❌ **pgBouncer** (connection pooling)

**CUMPLIMIENTO**: **60%** ⚠️

---

## 1️⃣5️⃣ INGRESS/DNS/TLS

### ✅ REQUERIDO:
- `app.tu-dominio` → Next.js
- `api.tu-dominio` → FastAPI
- NGINX Ingress + cert-manager + ExternalDNS
- HTTPS forzado
- Límites de body
- Headers de seguridad

### 📊 ESTADO ACTUAL:

| Componente | Implementado | Estado |
|------------|--------------|--------|
| **NGINX Ingress** | ✅ | CI/CD platform-install | ✅ |
| **cert-manager** | ✅ | CI/CD platform-install | ✅ |
| **ClusterIssuers** | ✅ | letsencrypt-staging/prod | ✅ |
| **ExternalDNS** | ❌ | **NO IMPLEMENTADO** | ❌ |
| **Ingress resource** | ✅ | templates/ingress.yaml | ✅ |
| **TLS auto** | ✅ | cert-manager | ✅ |
| **HTTPS redirect** | ❓ | **NO VERIFICADO** | ❓ |
| **Body limits** | ❓ | **NO CONFIGURADO** | ❓ |
| **Security headers** | ❌ | **NO** | ❌ |

### ⚠️ MEJORAS NECESARIAS:

```yaml
# deploy/helm/carpeta-ciudadana/templates/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "carpeta-ciudadana.fullname" . }}
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"  # ← AÑADIR
    nginx.ingress.kubernetes.io/configuration-snippet: |  # ← AÑADIR
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-XSS-Protection: 1; mode=block";
      more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - app.carpeta-ciudadana.example.com
    - api.carpeta-ciudadana.example.com
    secretName: carpeta-ciudadana-tls
  rules:
  - host: app.carpeta-ciudadana.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {{ include "carpeta-ciudadana.fullname" . }}-frontend
            port:
              number: 80
  - host: api.carpeta-ciudadana.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {{ include "carpeta-ciudadana.fullname" . }}-gateway
            port:
              number: 8000
```

**CUMPLIMIENTO**: **70%** ⚠️

---

## 1️⃣6️⃣ CI/CD (GitHub Actions)

### ✅ REQUERIDO:
- Terraform plan/apply
- Docker buildx, SBOM, escaneo
- Push a Docker Hub
- Helm upgrade --install
- Alembic migrations
- Smoke tests
- Helm rollback
- OIDC federado
- Workload Identity

### 📊 ESTADO ACTUAL:

| Requisito | Implementado | Job | Estado |
|-----------|--------------|-----|--------|
| **Terraform plan/apply** | ✅ | infra-apply | ✅ |
| **Docker buildx** | ✅ | build-and-push | ✅ |
| **SBOM** | ❌ | - | ❌ |
| **Trivy scan** | ✅ | security-scan | ✅ |
| **Push Docker Hub** | ✅ | build-and-push | ✅ |
| **Helm install** | ✅ | deploy | ✅ |
| **Alembic migrations** | ✅ | run-migrations | ✅ |
| **Smoke tests** | ⚠️ | Health checks | ⚠️ Básico |
| **Helm rollback** | ❌ | **NO automático** | ❌ |
| **OIDC federado** | ✅ | azure/login@v1 | ✅ |
| **Workload Identity** | ⚠️ | Pods | ⚠️ Sin Key Vault |

### ⚠️ MEJORAS:

1. ❌ **SBOM generation**:
   ```yaml
   - name: Generate SBOM
     uses: anchore/sbom-action@v0
     with:
       image: ${{ secrets.DOCKERHUB_USERNAME }}/carpeta-${{ matrix.service }}:${{ github.sha }}
   ```

2. ❌ **Helm rollback automático** en fallo:
   ```yaml
   - name: Deploy with Helm
     run: helm upgrade --install ...
   
   - name: Verify deployment
     id: verify
     run: |
       # Health checks
       if [ $? -ne 0 ]; then
         helm rollback carpeta-ciudadana --namespace $NAMESPACE
         exit 1
       fi
   ```

3. ⚠️ **Smoke tests mejorados**:
   - Actualmente: Solo curl /health
   - Requerido: Flujo completo (register→upload→search)

**CUMPLIMIENTO**: **70%** ⚠️

---

## 1️⃣7️⃣ PRUEBAS

### ✅ REQUERIDO:
- Unitarias + Integración + Contratos (OpenAPI) + E2E completo
- Accesibilidad: axe en CI, teclado-solo, NVDA/VoiceOver, contraste
- Resiliencia: caos (matar pods, hub fail, SAS expiry, Service Bus cut)
- Rendimiento: LCP < 2.5s, p95 APIs < 300ms, transfer p95 < 10min
- Backups/DR: PITR, RA-GZRS, Geo-DR, runbooks

### 📊 ESTADO ACTUAL:

#### Tests Unitarios:
| Servicio | Tests | Coverage | Estado |
|----------|-------|----------|--------|
| gateway | ✅ | ❓ | ⚠️ Un test |
| mintic_client | ✅ | >90% | ✅ |
| transfer | ✅ | >85% | ✅ |
| citizen | ❌ | - | ❌ |
| ingestion | ❌ | - | ❌ |
| metadata | ❌ | - | ❌ |
| signature | ❌ | - | ❌ |

#### Tests E2E:
- ✅ Playwright configurado
- ❌ **NO hay** tests implementados (solo config)

#### Tests de Contratos:
- ❌ **NO implementados**
- ❌ Sin validación OpenAPI

#### Accesibilidad:
- ❌ **axe en CI**: NO
- ❌ **Tests teclado**: NO
- ❌ **Screen readers**: NO testado
- ❌ **Contraste**: NO validado

#### Resiliencia:
- ❌ **Chaos testing**: NO
- ❌ **Failure injection**: NO

#### Rendimiento:
- ❌ **LCP < 2.5s**: NO medido
- ❌ **p95 < 300ms**: NO validado
- ✅ **Load tests**: k6 + Locust configurados

#### Backups/DR:
- ✅ PITR: Azure PostgreSQL (7d)
- ❌ **RA-GZRS**: NO (usando LRS)
- ❌ **Geo-DR Service Bus**: NO
- ⚠️ **Runbooks**: Scripts backupexisten

**CUMPLIMIENTO**: **40%** ❌

---

## 1️⃣8️⃣ SLOs (Objetivos Operativos)

### ✅ REQUERIDO:
- Disponibilidad ≥ 99.9%
- p95 APIs < 300ms
- Éxito authenticateDocument > 99%
- Expiraciones SAS < 1%
- DLQ < 0.1%/día

### 📊 ESTADO ACTUAL:

| SLO | Target | Monitoreado | Alertas | Estado |
|-----|--------|-------------|---------|--------|
| **Disponibilidad** | ≥ 99.9% | ❌ | ❌ | ❌ |
| **p95 APIs** | < 300ms | ✅ | ⚠️ 2s threshold | ⚠️ Threshold muy alto |
| **authenticateDocument** | > 99% | ⚠️ | ❌ | ⚠️ Genérico |
| **Expiraciones SAS** | < 1% | ❌ | ❌ | ❌ |
| **DLQ** | < 0.1%/día | ⚠️ | ✅ | ⚠️ |

**Problemas**:
1. Threshold de latencia es 2s (requerido: 300ms) - **7x más lento**
2. Sin métricas de SLA/SLO dashboard
3. Sin error budget tracking

**CUMPLIMIENTO**: **40%** ❌

---

## 📊 MATRIZ DE CUMPLIMIENTO COMPLETA

| # | Requerimiento | Cumpl. | Criticidad | Acción |
|---|---------------|--------|------------|--------|
| **1** | Hub MinTIC integration | 90% | 🔴 Alta | Añadir idemp ops startup |
| **2** | Arquitectura AKS+Azure | 70% | 🔴 Alta | Key Vault, KEDA, zones |
| **3** | Microservicios | 65% | 🔴 Alta | transfer-worker, completar |
| **4** | Frontend UX/Accesibilidad | 40% | 🟡 Media | B2C, vistas, WCAG |
| **5** | APIs internas | 75% | 🔴 Alta | WORM, headers M2M |
| **6** | Transferencias P2P | 80% | 🟠 Alta | Orden, worker, DLQ |
| **7** | Docs WORM/Retención | 30% | 🔴 Alta | **CRÍTICO** |
| **8** | Identidad (B2C) | 20% | 🔴 Alta | **CRÍTICO** |
| **9** | Base de Datos | 60% | 🟡 Media | Tablas users, RLS |
| **10** | Redis | 80% | 🟢 Baja | Azure Cache |
| **11** | Service Bus + KEDA | 50% | 🔴 Alta | Worker, KEDA |
| **12** | Seguridad | 55% | 🔴 Alta | NetPol, PDB, KV |
| **13** | Observabilidad | 75% | 🟡 Media | App Insights, métricas |
| **14** | Escalabilidad | 60% | 🟡 Media | Nodepools, zones |
| **15** | Ingress/DNS/TLS | 70% | 🟢 Baja | ExternalDNS |
| **16** | CI/CD | 70% | 🟢 Baja | SBOM, rollback |
| **17** | Testing | 40% | 🟡 Media | E2E, chaos, axe |
| **18** | SLOs | 40% | 🟡 Media | Thresholds correctos |

**CUMPLIMIENTO GLOBAL**: **~60%** ⚠️

---

## 🎯 PLAN DE ACCIÓN PRIORIZADO

Ver siguiente sección...


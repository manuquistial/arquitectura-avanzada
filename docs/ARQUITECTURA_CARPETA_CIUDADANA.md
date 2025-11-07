# Arquitectura de Carpeta Ciudadana

## 1. Contexto y Objetivos

El ecosistema **Carpeta Ciudadana** permite a los ciudadanos colombianos administrar documentos personales digitales y acceder a servicios estatales a través de operadores certificados. La solución está compuesta por microservicios desplegados en Azure Kubernetes Service (AKS) y sigue patrones event-driven con alta seguridad y cumplimiento.

**Objetivos clave**
- Centralizar la gestión de identidad y documentos ciudadanos.
- Garantizar autenticación robusta, trazabilidad y auditoría end-to-end.
- Permitir interoperabilidad con el Hub MinTIC y sistemas externos.
- Escalar horizontalmente en la nube manteniendo costos controlados.

**Actores**
- `Ciudadano`: usuario final que gestiona su carpeta.
- `Operador`: entidad autorizada que ofrece la Carpeta Ciudadana.
- `Administración MinTIC`: gobierno que valida identidad y documentos.
- `Sistemas Externos`: integraciones (notificaciones, analítica, etc.).

## 2. Casos de Uso Clave

### 2.1 Diagrama de Casos de Uso

```mermaid
%%{init: {'theme': 'neutral'}}%%
usecaseDiagram
title Casos de uso Carpeta Ciudadana
actor Ciudadano
actor Operador
actor Hub as "Hub MinTIC"
actor Ext as "Servicios Externos"

Ciudadano --> (CU1 Registrar ciudadano)
Operador --> (CU1 Registrar ciudadano)

Ciudadano --> (CU2 Autenticarse en operador)
Operador --> (CU2 Autenticarse en operador)

Ciudadano --> (CU3 Cargar documentos)
Operador --> (CU3 Cargar documentos)

Ciudadano --> (CU4 Autenticar documento vía Gov)
Operador --> (CU4 Autenticar documento vía Gov)
Hub --> (CU4 Autenticar documento vía Gov)

Ext --> (CU5 Recibir notificaciones de eventos)
Operador --> (CU5 Recibir notificaciones de eventos)
```

### 2.2 Especificaciones de Casos de Uso

**CU1 Registrar ciudadano**
- **Actor primario:** Operador (con asistencia del ciudadano).
- **Stakeholders:** Ciudadano, Administrador MinTIC, Auditoría.
- **Precondiciones:** Operador autenticado; ciudadano no registrado previamente.
- **Postcondiciones:** Ciudadano creado en `citizen` (PostgreSQL), sincronizado con Hub MinTIC, evento `citizen.registered` publicado.
- **Flujo principal:**
  1. Operador captura datos del ciudadano desde el portal.
  2. Frontend invoca `gateway` → `citizen` (`POST /api/citizens/register`).
  3. `citizen` valida datos y consulta duplicados.
  4. `citizen` registra ciudadano localmente y llama a `mintic_client`.
  5. `mintic_client` registra ciudadano en Hub MinTIC.
  6. `citizen` confirma registro, publica evento en Service Bus y retorna éxito.
- **Flujos alternos:**
  - A1: Hub MinTIC rechaza registro → rollback local, mensaje de error según código.
  - A2: Ciudadano ya existe → responde `409 Conflict`.
- **Reglas de negocio:** ID único de 10 dígitos; correo verificado; sincronización con Hub obligatoria.

**CU2 Autenticarse en el operador**
- **Actor primario:** Ciudadano.
- **Precondiciones:** Cuenta creada en Azure AD B2C; operador activo.
- **Postcondiciones:** Sesión válida en Frontend; token JWT emitido por `auth`; sesión registrada en Redis.
- **Flujo principal:**
  1. Ciudadano navega al portal e inicia login (OIDC).
  2. Frontend delega a Azure AD B2C para credenciales.
  3. AD B2C redirige con token; frontend canjea token vía `auth`.
  4. `auth` valida credenciales, genera tokens firmados RS256.
  5. Frontend almacena sesión (NextAuth) y habilita menú del ciudadano.
- **Flujos alternos:** Credenciales inválidas → `auth` retorna `401`; usuario bloqueado → flujo de recaptcha/reset.
- **Reglas:** MFA opcional; sesiones expiran a las 12h; revocación inmediata en logout.

**CU3 Cargar documentos**
- **Actor primario:** Ciudadano.
- **Precondiciones:** Ciudadano autenticado; cuota de almacenamiento disponible.
- **Postcondiciones:** Documento almacenado en Azure Blob Storage, metadatos registrados en `ingestion` y `metadata`, evento `document.uploaded` publicado.
- **Flujo principal:**
  1. Ciudadano solicita carga; frontend llama a `ingestion` para SAS de upload.
  2. `ingestion` valida permisos, genera SAS URL PUT (HTTPS).
  3. Ciudadano sube archivo directamente al Blob Storage.
  4. Frontend confirma upload (`POST /api/documents/confirm-upload`).
  5. `ingestion` valida blob, calcula hash, guarda metadatos y emite evento.
- **Flujos alternos:** Archivo no permitido → `413/415`; error al subir → reintento con nueva SAS.
- **Reglas:** Tamaño máx 50 MB; tipos MIME permitidos; WORM activado al firmar.

**CU4 Autenticar documentos via Gov**
- **Actor primario:** Ciudadano.
- **Stakeholders:** Hub MinTIC, Auditoría.
- **Precondiciones:** Documento existente y sin autenticación previa; ciudadano autenticado.
- **Postcondiciones:** Registro `SignatureRecord` creado, documento marcado WORM y autenticado en Hub MinTIC, evento `document.hubAuthenticated`.
- **Flujo principal:**
  1. Ciudadano solicita autenticación; frontend llama `signature`.
  2. `signature` obtiene documento (SAS GET), calcula hash y firma (RSA-SHA256).
  3. Genera SAS temporal y envía `PUT` al Hub MinTIC vía `mintic_client`.
  4. Hub confirma autenticación; `signature` persiste resultado y bloquea documento (WORM).
  5. Respuesta con certificado y URL firmada al frontend.
- **Flujos alternos:** Hub indisponible → reintento exponencial, estado `PENDING_HUB`; validación fallida → documento marcado como `FAILED_AUTH`.
- **Reglas:** Retención mínima 5 años; registros inmutables.

### 2.3 Historias de Usuario + Scenario (Gherkin-like)

**HU1 - Registro de ciudadano**
- **Como** operador certificado  
- **Quiero** registrar un ciudadano en la Carpeta  
- **Para** habilitarle todos los servicios digitales

_Scenario: Registro exitoso_
1. Ana inicia sesión en el portal operador.
2. Desde `Ciudadanos` selecciona `Registrar`.
3. Ingresa cédula, correo y datos básicos.
4. El portal invoca el servicio `citizen`.
5. El sistema verifica que la cédula no existe.
6. Se crea el registro local y se sincroniza con Hub MinTIC.
7. El sistema devuelve confirmación y notificación.
8. Ana recibe mensaje “Registro exitoso”.

**HU2 - Autenticación de ciudadano**
- **Como** ciudadano registrado  
- **Quiero** autenticarme en el operador  
- **Para** gestionar mis documentos

_Scenario: Autenticación con MFA habilitado_
1. Luis ingresa a `carpeta-ciudadana.gov.co`.
2. Presiona `Iniciar sesión`.
3. Azure AD B2C solicita usuario y contraseña.
4. Luis ingresa código MFA SMS.
5. AD B2C devuelve token OIDC al frontend.
6. Frontend intercambia token con `auth` para recibir JWT.
7. Luis accede al dashboard personal.

**HU3 - Carga de documentos**
- **Como** ciudadano autenticado  
- **Quiero** subir documentos personales  
- **Para** mantener mi carpeta actualizada

_Scenario: Upload con validación de tipo_
1. Marta selecciona `Agregar documento`.
2. El sistema pide tipo de documento y archivo.
3. Marta selecciona `PDF`.
4. Frontend solicita SAS de upload a `ingestion`.
5. `ingestion` devuelve URL prefirmada.
6. Marta sube el archivo directo al blob.
7. Frontend confirma carga.
8. `ingestion` valida hash y responde `processed`.

**HU4 - Autenticación gubernamental de documentos**
- **Como** ciudadano  
- **Quiero** autenticar un documento ante MinTIC  
- **Para** garantizar su validez legal

_Scenario: Autenticación exitosa_
1. Carlos abre su documento firmado pendiente.
2. Clic en `Autenticar en Gov`.
3. Frontend envía petición a `signature`.
4. `signature` firma digitalmente y genera SAS para Hub.
5. `mintic_client` invoca `PUT /authenticateDocument`.
6. Hub retorna `200 OK` con referencia.
7. `signature` marca documento como `SIGNED` y WORM.
8. Carlos descarga el certificado oficial.

## 3. Arquitectura de Componentes

### 3.1 Componentes Lógicos (dominio)

```mermaid
%%{init: {'theme': 'neutral', 'flowchart': {'useMaxWidth': false}}}%%
flowchart LR
  subgraph ExperienciaUsuario
    UI[Portal Ciudadano\n(Next.js)]
    Gateway[API Gateway\nLímites, CORS, AuthZ]
  end
  subgraph GestionIdentidad
    Auth[Auth Service\nOIDC, JWT]
    Citizen[Citizen Service\nGestión de perfiles]
  end
  subgraph GestionDocumental
    Ingestion[Document Ingestion\nSAS, Metadatos]
    Metadata[Metadata Service\nCatálogo documentos]
    Signature[Signature Service\nFirma & WORM]
  end
  subgraph Integraciones
    Mintic[MinTIC Client\nProxy oficial]
    Notification[Notification Service\nEmail/Webhook]
    Transfer[Transfer Saga\nIntercambio docs]
  end
  UI --> Gateway
  Gateway --> Auth
  Gateway --> Citizen
  Gateway --> Ingestion
  Gateway --> Signature
  Ingestion --> Metadata
  Signature --> Metadata
  Signature --> Mintic
  Gateway --> Notification
  Signature --> Notification
  Citizen --> Mintic
```

### 3.2 Componentes Técnicos (microservicios y data stores)

```mermaid
%%{init: {'theme': 'neutral'}}%%
graph TD
  subgraph AKS["Azure Kubernetes Service"]
    Frontend["frontend (Next.js)"]
    GatewayMS["gateway (FastAPI + Redis)"]
    CitizenMS["citizen (FastAPI + PostgreSQL)"]
    AuthMS["auth (FastAPI + Redis)"]
    IngestionMS["ingestion (FastAPI + Blob SDK)"]
    MetadataMS["metadata (FastAPI + PostgreSQL)"]
    SignatureMS["signature (FastAPI + Crypto)"]
    MinticMS["mintic_client (FastAPI + CircuitBreaker)"]
    NotificationMS["notification (FastAPI + SendGrid/Webhooks)"]
    TransferMS["transfer (FastAPI + Saga)"]
    TransferWorker["transfer_worker (Async worker via KEDA)"]
    CommonLib[":common library (Pydantic utils)"]
  end

  PostgreSQL[(Azure PostgreSQL Flexible Server)]
  Redis[(Azure Cache for Redis)]
  Blob[(Azure Blob Storage)]
  ServiceBus[(Azure Service Bus)]
  KeyVault[(Azure Key Vault)]
  AppInsights[(Azure Application Insights)]
  ADB2C[(Azure AD B2C)]
  MinTIC[(Hub MinTIC API)]

  Frontend --> GatewayMS
  GatewayMS --> AuthMS
  GatewayMS --> CitizenMS
  GatewayMS --> IngestionMS
  GatewayMS --> SignatureMS
  CitizenMS --> PostgreSQL
  MetadataMS --> PostgreSQL
  SignatureMS --> PostgreSQL
  IngestionMS --> Blob
  IngestionMS --> PostgreSQL
  SignatureMS --> Blob
  AuthMS --> Redis
  GatewayMS --> Redis
  TransferMS --> ServiceBus
  SignatureMS --> ServiceBus
  NotificationMS --> ServiceBus
  GatewayMS --> KeyVault
  AuthMS --> ADB2C
  SignatureMS --> MinTIC
  AllMS["Microservicios"] --> AppInsights
```

## 4. Diagramas de Secuencia de Operaciones

### 4.1 Registro de ciudadano (CU1)

```mermaid
%%{init: {'theme': 'neutral'}}%%
sequenceDiagram
    participant UI as Portal Ciudadano
    participant GW as Gateway API
    participant CT as Citizen Service
    participant MC as MinTIC Client
    participant HUB as Hub MinTIC
    participant DB as PostgreSQL
    participant SB as Azure Service Bus

    UI->>GW: POST /citizens/register
    GW->>CT: POST /api/citizens/register
    CT->>DB: INSERT ciudadano
    alt Ciudad ya existe
        DB-->>CT: Constraint error
        CT-->>GW: 409 Conflict
        GW-->>UI: Error duplicado
    else Registro válido
        CT->>MC: POST /mintic/register
        MC->>HUB: POST /citizen
        HUB-->>MC: 200 OK
        MC-->>CT: Confirmación
        CT->>SB: Publicar citizen.registered
        CT-->>GW: 201 Created
        GW-->>UI: Éxito
    end
```

### 4.2 Autenticación (CU2)

```mermaid
%%{init: {'theme': 'neutral'}}%%
sequenceDiagram
    participant User as Ciudadano
    participant B2C as Azure AD B2C
    participant FE as Frontend
    participant AUTH as Auth Service
    participant Redis as Cache Redis

    User->>FE: Accede /login
    FE->>B2C: Redirect OAuth2 authorize
    B2C-->>User: Pantalla credenciales
    User->>B2C: Envia usuario/MFA
    B2C-->>FE: Authorization Code
    FE->>AUTH: POST /callback (code)
    AUTH->>B2C: Token exchange
    B2C-->>AUTH: id_token + access_token
    AUTH->>Redis: Store session + nonce
    AUTH-->>FE: JWT + refresh token
    FE-->>User: Dashboard autenticado
```

### 4.3 Carga de documentos (CU3)

```mermaid
%%{init: {'theme': 'neutral'}}%%
sequenceDiagram
    participant UI as Frontend
    participant GW as Gateway API
    participant ING as Ingestion Service
    participant BLOB as Azure Blob Storage
    participant DB as PostgreSQL
    participant SB as Service Bus

    UI->>GW: Solicita upload URL
    GW->>ING: POST /documents/upload-url
    ING->>BLOB: Genera SAS PUT
    ING-->>GW: SAS + document_id
    GW-->>UI: SAS + instructions
    UI->>BLOB: PUT archivo (SAS HTTPS)
    UI->>GW: POST confirm-upload
    GW->>ING: confirm-upload
    ING->>BLOB: Verifica existencia
    ING->>DB: Guarda metadatos + hash
    ING->>SB: Publicar document.uploaded
    ING-->>GW: 200 processed
    GW-->>UI: Documento disponible
```

### 4.4 Autenticación Gov (CU4)

```mermaid
%%{init: {'theme': 'neutral'}}%%
sequenceDiagram
    participant UI as Frontend
    participant GW as Gateway
    participant SIG as Signature Service
    participant BLOB as Azure Blob
    participant CRY as Crypto Service
    participant MINTIC as Mintic Client
    participant HUB as Hub MinTIC
    participant DB as PostgreSQL
    participant SB as Service Bus

    UI->>GW: POST /signature/sign
    GW->>SIG: Solicitud autenticar
    SIG->>BLOB: GET documento (SAS)
    SIG->>CRY: Calcular SHA256 y firma RSA
    SIG->>BLOB: Generar SAS GET 15min
    SIG->>MINTIC: PUT /authenticateDocument
    MINTIC->>HUB: Relay solicitud
    HUB-->>MINTIC: Resultado
    MINTIC-->>SIG: Respuesta autenticación
    SIG->>DB: Guarda SignatureRecord + WORM
    SIG->>SB: Publicar document.authenticated
    SIG-->>GW: Firma + certificado
    GW-->>UI: Documento autenticado
```

## 5. Diagrama de Despliegue

```mermaid
%%{init: {'theme': 'neutral', 'flowchart': {'useMaxWidth': false}}}%%
graph LR
  subgraph Usuario["Internet / Ciudadanos"]
    Browser["Navegador / App Móvil"]
  end

  Browser -- HTTPS (TLS 1.3, JSON) --> FrontDoor

  subgraph AzureEdge["Azure Front Door + WAF"]
    FrontDoor["Front Door\nCDN, WAF, DDoS"]
  end

  FrontDoor -- HTTPS (TLS 1.3) --> AGW

  subgraph AKSCluster["Azure Kubernetes Service (AKS)"]
    AGW["Nginx Ingress Controller"]
    subgraph NodePools["Node Pools"]
      NPSystem["System Pool\n3 nodes"]
      NPUser["User Pool\n3-10 nodes"]
      NPSpot["Spot Pool\n0-30 nodes"]
    end
    FrontendPod["frontend Deployment\nNode.js 20\nHTTP/2"]
    GatewayPod["gateway Deployment\nFastAPI + Redis client"]
    CitizenPod["citizen Service\nFastAPI"]
    AuthPod["auth Service\nFastAPI"]
    IngestionPod["ingestion Service\nFastAPI"]
    MetadataPod["metadata Service\nFastAPI"]
    SignaturePod["signature Service\nFastAPI"]
    MinticPod["mintic_client\nFastAPI\nCircuit Breaker"]
    NotificationPod["notification Service\nFastAPI"]
    TransferPod["transfer & worker\nFastAPI + Celery"]
  end

  AGW --> FrontendPod
  AGW --> GatewayPod
  GatewayPod --> CitizenPod
  GatewayPod --> AuthPod
  GatewayPod --> IngestionPod
  GatewayPod --> SignaturePod
  GatewayPod --> NotificationPod

  subgraph ManagedServices["Servicios Gestionados Azure"]
    Postgres["Azure PostgreSQL\nTLS, JSON/SQL"]
    Redis["Azure Cache for Redis\nTLS"]
    Blob["Azure Blob Storage\nHTTPS, Binary"]
    ServiceBus["Azure Service Bus\nAMQP 1.0 / JSON"]
    KeyVault["Azure Key Vault\nREST, TLS"]
    Monitor["Azure Monitor + Application Insights"]
  end

  CitizenPod --> Postgres
  MetadataPod --> Postgres
  SignaturePod --> Postgres
  AuthPod --> Redis
  GatewayPod --> Redis
  IngestionPod --> Blob
  SignaturePod --> Blob
  AllPods["Pods"] --> KeyVault
  AllPods --> ServiceBus
  AllPods --> Monitor

  MinticPod -- REST/JSON + MTLS --> HubAPI["VPN/Private Endpoint -> Hub MinTIC"]
  NotificationPod -- HTTPS/SMTP --> ExternalServices["SendGrid / Notificaciones"]
```

**Protocolos y formatos**
- Frontera externa: `HTTPS (TLS 1.3)` + `JSON`.
- Mensajería interna: `AMQP 1.0` (Service Bus), `JSON` eventos.
- Persistencia: `PostgreSQL` (SQL, JSONB), `Redis` (Key/Value), `Blob` (binario + metadata).
- Secrets: `CSI driver` monta desde `Key Vault`.

## 6. Decisiones de Arquitectura

| ID | Decisión | Alternativas | Racional | Implicaciones |
|----|----------|--------------|----------|---------------|
| AD-01 | **Despliegue primario en Azure AKS** | On-prem Kubernetes, VM scale sets | Necesidad de elasticidad (KEDA/HPA), integración nativa con servicios Azure (Blob, Service Bus) y menores costos operativos | Requiere gestión de cluster AKS; dependencia cloud provider |
| AD-02 | **Eventos con Azure Service Bus** | Kafka, RabbitMQ | Garantiza orden FIFO por sesión, soporte nativo en Azure, integración con KEDA para autoescalado | Contrato AMQP; costos por mensaje |
| AD-03 | **Storage documental en Azure Blob + WORM** | Filesystem on-prem, S3 | SAS URLs y políticas WORM, integración compliance gubernamental | Necesario gestionar expiración SAS y redundancia Geo-RA |
| AD-04 | **Autenticación OIDC con Azure AD B2C** | Keycloak, Auth0 | Requisito gobierno colombiano, integra MFA, soporte identidad ciudadana | Debe configurarse tenant y sincronizar usuarios |
| AD-05 | **Base de datos transaccional PostgreSQL** | MySQL, Cosmos DB | Soporta JSONB, replicación, ACID; madurez en Python (SQLAlchemy) | Administrar backups y high availability (zona múltiple) |
| AD-06 | **Microservicios en Python FastAPI** | .NET, Spring Boot | Cohesión equipo, velocidad de desarrollo, interoperabilidad con libs existentes | Controlar performance (uvicorn/gunicorn) |
| AD-07 | **Frontend Next.js SSR** | Angular, React SPA | SSR + SEO + compatibilidad con NextAuth; rehidratación rápida y control de rutas | Necesita Node.js 20 en build pipeline |
| AD-08 | **Criterios nube vs on-prem** | Mixed | Componentes con requisitos de elasticidad, seguridad y compliance se alojan en Azure; solo servicios de firma privada podrían evaluarse on-prem con HSM dedicado. Se mantiene posibilidad híbrida usando VPN/ExpressRoute para integraciones legadas. | Latencia dependiente de red; contratos de servicio; CAPEX reducido |

## 7. Microservicios y Responsabilidades

| Servicio | Responsabilidades principales | Dependencias |
|----------|------------------------------|--------------|
| `gateway` | Enrutamiento, rate limiting, validación de tokens, CORS, versionamiento API | `auth`, `redis`, `citizen`, `ingestion`, `signature` |
| `frontend` | UI portal ciudadanos/operadores, NextAuth, flujos SSR | `gateway`, Azure AD B2C |
| `auth` | Proveedor OIDC, emisión JWT, gestión sesiones, MFA | Azure AD B2C, `redis`, `postgres` (usuarios del sistema) |
| `citizen` | CRUD ciudadanos, sincronización Hub MinTIC, eventos `citizen.*` | `postgres`, `mintic_client`, Service Bus |
| `ingestion` | SAS URLs, validación uploads, metadatos, antivirus/OCR | Azure Blob, `metadata`, `postgres`, Service Bus |
| `metadata` | Catálogo de documentos, índices de búsqueda, retención | `postgres`, `ingestion`, `signature` |
| `signature` | Firma digital, autenticación Hub, WORM, auditoría | Azure Blob, `postgres`, `mintic_client`, Service Bus |
| `mintic_client` | Gateway seguro hacia Hub MinTIC, circuit breaker, logging legal | VPN/ExpressRoute, Hub API |
| `notification` | Emails, webhooks, colas push, plantillas regulatorias | Service Bus, SendGrid/Azure Communication Services |
| `transfer` + `transfer_worker` | Orquestación de intercambios P2P, sagas, compensaciones | Service Bus, `citizen`, `metadata`, `notification` |
| `common` | Librería compartida: validaciones, modelos Pydantic, utilidades | Consumido por todos los servicios Python |

## 8. Implementación de Flujos Solicitados

### 8.1 Registro de ciudadano
- **Endpoint:** `POST /api/citizens/register` (orquestado por `gateway`).
- **Validaciones:** longitud cédula, email RFC 5322, idempotencia.
- **Persistencia:** tabla `citizens` en PostgreSQL.
- **Eventos:** `citizen.registered` (Service Bus) para notificar a `notification` y `transfer`.
- **Observabilidad:** Métrica `citizen_registrations_total`, trazas en App Insights.

### 8.2 Autenticación (login)
- **Flujo:** Azure AD B2C ↔ `auth` ↔ `frontend`.
- **Tokens:** ID token (B2C) → JWT RS256 firmado localmente, refresh token en Redis.
- **Seguridad:** rotación cada 24 h, introspección de scopes para ABAC.

### 8.3 Carga de documentos
- **Servicios:** `ingestion`, `metadata`, `notification`.
- **Almacenamiento:** Azure Blob Storage (hot tier) con redundancia GRS.
- **Validaciones:** `MAX_FILE_SIZE_MB`, `ALLOWED_CONTENT_TYPES`, escaneo antivirus.
- **Auditoría:** Registro en tabla `document_audit` + evento `document.uploaded`.

### 8.4 Autenticación Gov (firma)
- **Servicios:** `signature`, `mintic_client`, `metadata`.
- **Criptografía:** Hash `SHA-256`, firma `RSA` con claves en Key Vault (HSM opcional).
- **Retención:** `retention_until = now + 5 años`, bandera WORM.
- **Integración:** `PUT /apis/authenticateDocument` del Hub con SAS URL `https`.

## 9. Consideraciones de Seguridad y Cumplimiento

- **Cifrado en tránsito:** TLS 1.3 extremo a extremo; MTLS opcional entre microservicios sensibles.
- **Cifrado en reposo:** Blob Storage y PostgreSQL cifrados por defecto, claves en Key Vault.
- **Políticas de acceso:** ABAC para ciudadanos vs operadores; RBAC para administración.
- **Auditoría:** Logs estructurados (`service`, `action`, `correlation_id`) sincronizados con Azure Monitor.
- **Continuidad:** Backups automáticos, runbooks de recuperación, pruebas de caos trimestrales.

## 10. Roadmap y Riesgos

- **Riesgos:** Dependencia de disponibilidad del Hub MinTIC; manejo de picos de carga (campañas masivas); cumplimiento WORM multi-región.
- **Mitigaciones:** Circuit breakers (`mintic_client`), colas de reintentos, KEDA para escalar workers, replicación GRS y retención legal.
- **Roadmap corto plazo:** Integrar motor de búsqueda (Azure Cognitive Search), habilitar app móvil, automatizar clasificación de documentos con IA.

---

**Última actualización:** 2025-11-07  
**Preparado por:** GPT-5 Codex (Cursor Assistant)



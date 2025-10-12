# Lista completa de requerimientos — Operador GovCarpeta (AKS + Azure)

> **Estado del hub**: **GovCarpeta YA IMPLEMENTADO**. Se **consume su API pública** (sin token/cert) **exclusivamente desde backend**.

---

## 1) Hub MinTIC **GovCarpeta** (YA IMPLEMENTADO; **sólo consumir**; **público**, sin token/cert)
**Base URL**: `https://govcarpeta-apis-4905ff3c005b.herokuapp.com`

**Endpoints y payloads** *(los consume solo el backend)*:

- **POST `/apis/registerCitizen`** → body
  ```json
  { "id": 1234567890, "name": "Carlos Andres Caro", "address": "Cra 54 # 45 -67", "email": "caro@mymail.com", "operatorId": "65ca0a00d833e984e2608756", "operatorName": "Operador Ciudadano" }
  ```
  **Lo llama**: `citizen-svc`

- **DELETE `/apis/unregisterCitizen`** → body
  ```json
  { "id": 1234567890, "operatorId": "65ca0a00d833e984e2608756", "operatorName": "Operador Ciudadano" }
  ```
  **Lo llama**: `transfer-orchestrator-api` (paso 1 transferencia)

- **PUT `/apis/authenticateDocument`** → body
  ```json
  { "idCitizen": 1234567890, "UrlDocument": "https://<presigned>", "documentTitle": "Diploma Grado" }
  ```
  **Lo llama**: `signature-proxy`

- **GET `/apis/validateCitizen/{id}`**
  **Lo llama**: `citizen-svc`

- **POST `/apis/registerOperator`** → body
  ```json
  { "name": "Operador 123", "address": "Cra 34 # 35 -67", "contactMail": "info@operador123.com", "participants": ["Nombre 1","Nombre 2","Nombre 3"] }
  ```
  **Lo llama**: `operator-registry-client`

- **PUT `/apis/registerTransferEndPoint`** → body
  ```json
  { "idOperator": "65ca0a00d833e984e2608756", "endPoint": "https://mioperador.com/api/transferCitizen", "endPointConfirm": "https://mioperador.com/api/transferCitizenConfirm" }
  ```
  **Lo llama**: `operator-registry-client`

- **GET `/apis/getOperators`**
  **Lo llama**: `operator-registry-client` (cache corto en Redis)

> Al ser pública, **siempre** se invoca desde backend con **validación de esquema**, **timeouts**, **reintentos con backoff**, **circuit breaker** y **rate-limit de salida**.

---

## 2) Arquitectura (Azure + Kubernetes)
- **Orquestación**: **AKS** (Azure Kubernetes Service), red **zonal** con `topologySpreadConstraints`.
- **Despliegue**: **Helm** (charts por servicio + umbrella).
- **Infra como código**: **Terraform** (RG, VNet/Subnets, AKS, PostgreSQL Flexible Server, Azure Cache for Redis, Blob Storage, Service Bus, Key Vault, DNS, cert-manager CRDs, KEDA, NGINX Ingress, ExternalDNS).
- **Registro de imágenes**: **Docker Hub** (tags inmutables `:sha`, `imagePullSecrets` en AKS).
- **CDN/estáticos**: caching para assets Next.js (via NGINX/Front Door si aplica).
- **Observabilidad**: **OpenTelemetry** → **Application Insights** + Azure Monitor for Containers.

---

## 3) Componentes y microservicios
- **Frontend**: Next.js (App Router) dockerizado.
- **Backends (FastAPI)**:
  - `citizen-svc` (registro/validación/desvinculación con el hub).
  - `document-svc` (presign SAS, metadatos, acceso).
  - `signature-proxy` (proxy a `PUT /apis/authenticateDocument`).
  - `operator-registry-client` (alta/actualiza endpoints en hub y catálogo).
  - `transfer-orchestrator-api` (APIs M2M entre operadores; SAGA).
  - `transfer-worker` (KEDA; colas Service Bus; descarga/confirm/cleanup).
  - `notifications-svc` (outbox → Azure Communication Services Email/SMS).
- **Datos**: **PostgreSQL** (Flexible Server).
- **Caché/locks**: **Redis** (Azure Cache).
- **Mensajería**: **Azure Service Bus** (+ KEDA).
- **Documentos**: **Azure Blob Storage** (SAS, lifecycle Hot/Cool/Archive).
- **Identidad/secretos**: **Azure AD B2C** (OIDC), **Key Vault** + Workload Identity + CSI Secret Store.

---

## 4) Frontend (UX/UI/Accesibilidad/Responsivo)
- **Autenticación**: **Azure AD B2C (OIDC)** con NextAuth; sesión cookie **HTTPOnly+Secure**; middleware de rutas protegidas.
- **UX**: lenguaje claro; botones “verbo + objeto”; feedback de estado (toasts `aria-live`).
- **Accesibilidad**: **WCAG 2.2 AA**; navegación solo teclado; roles/labels ARIA correctos; `skip to content`; **focus ring** visible; `prefers-reduced-motion`.
- **Tipografía/targets**: base 16px, contenido 18–20px; objetivos ≥ 44×44px; contraste ≥ 4.5:1.
- **Responsivo (mobile-first)**: breakpoints xs/sm/md/lg/xl; tablas → **cards** en móvil; drawer accesible; botones primarios sticky en móvil.
- **Vistas**:
  - **Dashboard**: estado en hub, operador actual, timeline.
  - **Documentos**: subir (presign+SAS write), listar/filtrar, detalle (titulo/mime/tamaño/hash/estado), visor PDF/imagen, descarga (SAS read).
  - **Firma**: botón “Autenticar en GovCarpeta” → estado en vivo y resultado.
  - **Transferencia**: asistente (selección desde `/apis/getOperators`, revisión manifiesto, confirmación) + tracking `PENDING/RECEIVED/CONFIRMED/COMPLETED/FAILED`.
  - **Notificaciones**: centro y **preferencias** (Email/SMS).
  - **Retención**: TTL **UNSIGNED 30d** y **SIGNED 5y (WORM)** visibles.
- **Seguridad UI**: **CSP** estricta; no exponer secretos; manejo robusto de errores/red; modo lectura si el hub cae.

---

## 5) APIs internas del operador (FastAPI)
**Ciudadanos (`citizen-svc`)**
- `POST /api/citizens/register` → **POST hub `/apis/registerCitizen`**.
- `GET /api/citizens/{id}` → BD + **GET hub `/apis/validateCitizen/{id}`**.
- `DELETE /api/citizens/{id}` → **DELETE hub `/apis/unregisterCitizen`**.

**Documentos (`document-svc`)**
- `POST /api/documents/presign` → SAS (`r|w`, TTL 5–15 min).
- `GET /api/documents/{docId}` → metadatos (`state`, `hash`, `retention_until`).
- `POST /api/documents/{docId}/download` → SAS lectura.

**Firma (`signature-proxy`)**
- `POST /api/documents/{docId}/authenticate` → **PUT hub `/apis/authenticateDocument`**; actualiza `worm_locked=true`, `state=SIGNED`, `signed_at`, `hub_signature_ref`.

**Operadores (`operator-registry-client`)**
- `GET /api/operators` (catálogo cacheado de **`GET /apis/getOperators`**).
- Tareas: **POST `/apis/registerOperator`**, **PUT `/apis/registerTransferEndPoint`**.

**Transferencias (`transfer-orchestrator-api`)**
- **Paso 1 obligatorio**: **DELETE hub `/apis/unregisterCitizen`**.
- `POST /api/transferCitizen` *(origen→destino; M2M)* — **headers**: `Authorization: Bearer <JWT M2M>`, `Idempotency-Key`, `X-Trace-Id`, `X-Nonce`, `X-Timestamp`, `X-Signature(HMAC/JWS)`; **body**:
  ```json
  {
    "id": 1032236578,
    "citizenName": "Carlos Castro",
    "citizenEmail": "myemail@example.com",
    "urlDocuments": {
      "URL1": ["https://.../document1?sig=..."],
      "URL2": ["https://.../document2?sig=..."]
    },
    "confirmAPI": "https://dest-operator.com/api/transferCitizenConfirm"
  }
  ```
- `POST /api/transferCitizenConfirm` *(destino→origen)* — body `{ "id": 1032236578, "req_status": 1 }`.
- **SAGA**: `PENDING → RECEIVED → CONFIRMED → COMPLETED|FAILED`; reintentos; **DLQ**; idempotencia con **locks Redis**.

**Notificaciones (`notifications-svc`)**
- `GET/POST /api/notifications/preferences` (preferencias por usuario).
- Outbox → **ACS Email/SMS** (entregas con reintentos y logging).

---

## 6) Transferencia de ciudadanos (interoperable y agnóstica de storage)
- **Secuencia**: (1) **unregister en hub** → (2) `POST /api/transferCitizen` (con **URLs presignadas** HTTPS, TTL 5–15 min + `confirmAPI`) → (3) esperar `POST /api/transferCitizenConfirm` (`req_status`) → (4) **cleanup** (BD+Blob) **sólo** si `req_status=1`.
- **Integridad**: destino recalcula **SHA-256** por archivo antes de confirmar.
- **Reintentos**: reemisión de presigns al expirar; idempotencia por `Idempotency-Key`/`traceId`; **DLQ** y reconciliación.
- **No borrar** en origen hasta confirmación; **auditoría** completa con `traceId`.

---

## 7) Documentos (almacenamiento y retención)
- **UNSIGNED (staging)**: TTL **30 días**, editable; auto-purga si no progresa.
- **SIGNED (post-hub)**: **WORM/inmutable**, retención **5 años**, legal hold; lifecycle **Cool/Archive**.
- **Azure Blob Storage**: contenedores por operador/tenant; etiquetas (`state`, `tenant`, `docId`); acceso **sólo** por **SAS** mínimo (`r|w`, TTL 5–15 min); cifrado en reposo; antivirus (hook); nombres opacos `storage_path`.
- **Metadatos (BD)**: `hash(SHA-256)`, `storage_path`, `state`, `signed_at`, `retention_until`, `hub_signature_ref`.

---

## 8) Identidad, registro y autorización
- **Usuarios**: **Azure AD B2C (OIDC)**; `POST /api/users/bootstrap` vincula `citizenId` validando/registrando en hub.
- **Sesión**: cookie HTTPOnly; revocación en logout; CSRF en POST.
- **RBAC/ABAC**: roles (`citizen`, `operator_admin`, `admin`) y propietario del recurso en BD.
- **Operador↔Operador (M2M)**: **JWT client-credentials + mTLS + HMAC/JWS** en `/api/transferCitizen*`.
- **GovCarpeta**: público; consumo sólo desde backend.

---

## 9) Datos (PostgreSQL)
- Tablas: `users`, `user_roles`, `citizen_links`, `citizens`, `documents`, `transfers`, `operators`, `audit_events`, `notification_templates`, `notification_outbox`, `user_notification_prefs`, `notification_logs`.
- **RLS** por operador/propietario; partición por operador/fecha (tablas grandes); **PITR/backups**; migraciones **Alembic**.

---

## 10) Redis
- **Cache**: `/apis/getOperators`, metadatos calientes.
- **Locks**: `traceId` + `Idempotency-Key` (idempotencia).
- **Rate-limit**: endpoints sensibles; contadores/pub-sub.

---

## 11) Service Bus (colas)
- `transfer.requested`, `transfer.confirmed`, `cleanup.requested`, `notification.dispatch`.
- **KEDA** escala `transfer-worker` por longitud de cola; **scale-to-zero** fuera de pico.

---

## 12) Seguridad
- **Frontend**: CSP estricta; `prefers-reduced-motion`; no secretos en cliente.
- **Back**: CORS restringido; **TLS** extremo a extremo; **Circuit Breaker** + timeouts + retries con jitter; **bulkheads**.
- **K8s**: **NetworkPolicies**, **Pod Security Standards**, `readiness/liveness/startup` probes, **PDBs**, **resource requests/limits**.
- **Key Vault**: `DB_CONN_STRING`, `REDIS_CONN`, `ACS_*`, `HMAC_JWS_KEY`, credencial Docker Hub (via `imagePullSecrets`) — montados con **CSI Secret Store**.
- **Privacidad**: minimización de datos en payloads/URLs/SMS; cumplimiento de **habeas data** (consentimientos, derechos ARCO).

---

## 13) Observabilidad, métricas y alertas
- **Trazas** end-to-end (front→back→hub/operadores) con `traceId`.
- **KPIs**: p95 APIs, éxito/fallo `authenticateDocument`, tiempo a confirmación, expiraciones SAS, % checksum mismatch, volumen transferido, bounces Email/SMS, tamaño DLQ.
- **Alertas**: 3+ fallos por `traceId`, DLQ creciente, expiraciones repetidas, 5xx anómalos, latencias fuera de SLO.

---

## 14) Escalabilidad, tolerancia a fallos y costo-efectividad
- **AKS**: HPA en APIs (CPU 60% + métricas), nodepools dedicados (`web`, `workers`, `ingress`, `system`), **Cluster Autoscaler**; **zonal**.
- **Workers**: KEDA por colas; **spot nodepool** para `workers`; **scale-to-zero** fuera de pico.
- **BD**: pgBouncer, réplicas de lectura (cuando se requiera), partición; índices GIN; autovacuum afinado.
- **Degradación controlada**: si el **hub** cae → UI **read-only**; si **destino** falla → no borrar origen; si **ACS** falla → outbox reintenta.
- **Costos**: lifecycle Blob (Cool/Archive), retención de logs 7–14d, sampleo de trazas (1–10%), right-sizing de SKUs.

---

## 15) Ingress/DNS/TLS
- **`app.tu-dominio`** → Next.js; **`api.tu-dominio`** → FastAPI (rutas `/citizens`, `/documents`, `/transfer`, `/notifications`).
- **NGINX Ingress** + **cert-manager** (Let’s Encrypt) + **ExternalDNS**; HTTPS forzado; límites de body; headers de seguridad.

---

## 16) CI/CD (GitHub Actions OIDC + Helm + Terraform)
- **Terraform**: `plan/apply` (AKS, Postgres, Redis, Blob, Service Bus, Key Vault, DNS, CRDs).
- **Build**: Docker buildx; SBOM y escaneo; **push a Docker Hub**.
- **Deploy**: `helm upgrade --install` (umbrella + charts); migraciones **Alembic**; smoke tests; **helm rollback**.
- **Credenciales**: OIDC federado (sin secretos largos); Workload Identity en pods.

---

## 17) Pruebas (calidad, accesibilidad, resiliencia, rendimiento)
- **Unitarias** + **Integración** + **Contratos (OpenAPI)** + **E2E** (registro, subida, firma, transferencia completa unregister→transfer→confirm→cleanup).
- **Accesibilidad**: `axe` en CI; teclado-solo; NVDA/VoiceOver; contraste; reflow 200%.
- **Resiliencia**: caos (matar pods; fallos de hub; expiración masiva de SAS; cortes ACS/Service Bus).
- **Rendimiento**: LCP < 2.5s; p95 APIs < 300ms (sin I/O pesado); confirmación transferencia p95 < 10min.
- **Backups/DR**: PITR Postgres; RA-GZRS Blob; Service Bus Geo-DR alias; runbooks y pruebas de restore.

---

## 18) SLOs (objetivos operativos)
- Disponibilidad web/APIs **≥ 99.9%**.
- p95 latencia APIs **< 300 ms** (operaciones sin transferencia/firma).
- Éxito `authenticateDocument` **> 99%** (hub sano).
- Expiraciones SAS en transfer **< 1%**; DLQ **< 0.1%**/día.

---

**Fin del documento.**

# Diagramas de Secuencia - Carpeta Ciudadana

> Este documento organiza los diagramas de secuencia del sistema.

---

## Registro de ciudadano
<img width="6260" height="4572" alt="Registro de Ciudadano" src="https://github.com/user-attachments/assets/7f7d137b-2a57-4b9f-a88f-173c0b0b7434" />


**Participantes**  
Operador (Admin), Portal Web (UI), Ingress NGINX, Citizen Service, MinTIC Client Service, MinTIC Hub API (GovCarpeta), Citizen DB (PostgreSQL), Auth Service, Event Bus (Service Bus, cola `citizen-events`)

**Flujo principal**
- Portal → Ingress → Citizen Service: `POST /api/citizens/register` (Bearer).
- Opcional: Citizen → MinTIC Client: `GET /api/mintic/system-config/operator` para completar `operator_id/name`.
- Citizen → DB: `SELECT` por cédula/email (duplicados).
- Si no hay duplicado: `INSERT` con `status=PENDING_SYNC` (**flush sin commit**).
- Citizen → MinTIC Client → Hub: `POST /registerCitizen`.
- Si Hub responde **200 OK**: **COMMIT + REFRESH** (`status=ACTIVE`, `ref=ext_id`).
- Best-effort: Citizen → Auth: `POST /api/auth/register` (si falla, solo warning).
- Citizen → Bus: publica **`citizen.registered`** (cola `citizen-events`).
- Respuesta: **201 Created** al Portal.

**Alternativas**
- Duplicado: **409 Conflict**; no se llama al Hub ni se publica evento.
- Error/timeout Hub: **ROLLBACK** completo; **400/409/502/503** según causa; no hay evento.

---

## Autenticación de ciudadano (login)
<img width="3874" height="3592" alt="Autenticación de Ciudadano" src="https://github.com/user-attachments/assets/6dfccc57-cf83-4e17-88d1-5e66c8d97cea" />


**Participantes**  
Ciudadano, Portal Web (UI), Ingress NGINX, Auth Service (FastAPI), User DB (PostgreSQL), Redis (session cache)

**Flujo principal**
- Formulario local → `POST /api/auth/login` vía Ingress.
- Auth → DB: `SELECT` por email/username, obtiene `hash_bcrypt`, `is_active`, `roles`.
- Verifica contraseña con **bcrypt**.
- Si OK y `is_active=true`:
  - Genera **JWT HS256** (secreto de configuración).
  - Guarda sesión en **Redis** (jti/exp).
  - Responde **200 OK** + JWT.

**Alternativas**
- Usuario inexistente/clave inválida: **401 Unauthorized**.
- Cuenta bloqueada (`is_active=false`): **423 Locked**.

---

## Carga de documento
<img width="5994" height="4454" alt="Carga de Documento" src="https://github.com/user-attachments/assets/09673c56-f6f9-491a-8a2d-f0e722c3321e" />


**Participantes**  
Ciudadano, Portal Web (UI), Ingress NGINX, Ingestion Service, Metadata Service, Azure Blob Storage, PostgreSQL, Service Bus, Notification Service, Transfer Service

**Flujo principal**
- Validación cliente (tipo/tamaño).
- Portal → Ingress → Ingestion: `POST /api/documents/upload-url`.
- Ingestion: crea **PendingDocument** (`PENDING_UPLOAD`) y retorna `document_id` + **SAS URL**.
- Cliente sube con **PUT** al Blob usando SAS.
- Portal → Ingress → Ingestion: `POST /api/documents/confirm-upload` con `document_id`.
- Ingestion verifica blob (**HEAD/properties**) y ejecuta **AV scan**.
- Si OK: `status=UPLOADED`, `uploaded_at`, publica **`document.uploaded`**.
- **Metadata** consume `document.uploaded` y persiste metadatos finales.
- **Notification** y **Transfer** también consumen el evento.

**Alternativas**
- Archivo inválido (cliente): error inmediato.
- Blob no encontrado / AV falla: **412** o **422**; `status=REJECTED`.

---

## Autenticación de documento
<img width="9501" height="5750" alt="Firma de Documento" src="https://github.com/user-attachments/assets/b8c4c4cb-6c0c-4c99-9453-90305f636a61" />


**Participantes**  
Ciudadano, Portal Web (UI), Ingress NGINX, Signature Service, Ingestion Service, Metadata Service, MinTIC Client Service, MinTIC Hub API, Azure Blob Storage, PostgreSQL, Service Bus, Notification Service, Transfer Service, Key Vault

**Flujo principal**
- Portal solicita autenticación y confirma.
- Portal → Ingress → Signature: `POST /api/signature/sign` (`document_id`, `type=GOVERNMENT_AUTH`).
- Signature → Metadata: obtiene estado y hash almacenado.
- Si no está firmado: Signature → Ingestion: solicita **SAS de lectura** y props; descarga blob y calcula **SHA-256**; compara con Metadata.
- Si integridad OK: carga clave/cert (desde configuración/KV) y genera **firma RSA-SHA256**.
- Signature → MinTIC Client → Hub: `PUT /authenticateDocument` (hash+firma+URL).
- Si Hub **200 OK**: **Metadata** registra `SignatureRecord`, actualiza a `SIGNED` y aplica **WORM/legal hold**.
- Signature publica **`document.authenticated`**; **Notification** y **Transfer** consumen.

**Alternativas**
- Ya firmado: **400 Bad Request**.
- Hash distinto: **400 Bad Request** (modificado tras carga).
- Falla Hub: **502 Bad Gateway**.

---

## Publicación y manejo de eventos
<img width="4362" height="2722" alt="Manejo de Eventos" src="https://github.com/user-attachments/assets/9eebbb47-b854-4136-bc3d-2a0131a3aa10" />


**Participantes**  
Citizen Service (publisher), Service Bus (topic/subscriptions), Notification Service (subscriber), Transfer Service (subscriber), Email/SMS Provider, Dead-letter queue (DLQ)

**Flujo principal**
- Publicación: **`citizen.registered`**, **`document.uploaded`**, **`document.authenticated`** hacia **Azure Service Bus**.
- Fan-out: entrega a suscripciones (p. ej., `citizen-registered`).
- Notification procesa y envía email; si OK, hace **`complete_message()`**.

**Reintentos y DLQ**
- Fallos transitorios: **`abandon_message()`** para reentrega hasta `max_delivery_count=10`.
- Agotado el conteo: **`dead_letter_message()`** a la **DLQ**.
- Observabilidad: logs a stdout; alertas vía Azure Monitor.


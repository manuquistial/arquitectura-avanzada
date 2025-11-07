# Análisis del Rol "admin" del Operador Carpeta Ciudadana

## 📋 Resumen Ejecutivo

El rol **"admin"** está diseñado para administrar el **Operador Carpeta Ciudadana** internamente. Este rol permite gestionar usuarios, documentos, transferencias y configuración del operador Carpeta Ciudadana, pero **NO tiene relación con la administración de otros operadores MinTIC**.

**⚠️ IMPORTANTE - Privacidad de Documentos**:
El admin **NO puede acceder al contenido de documentos privados** sin una solicitud explícita y aprobada por el usuario. Esto garantiza la privacidad de los usuarios y sigue el mismo principio que las solicitudes entre usuarios normales.

---

## 1. Contexto: Sistema de Solicitudes de Documentos

### 1.1 Solicitudes entre Usuarios

**Según la documentación y el código**:
- Los usuarios pueden **solicitar documentos a otros usuarios**
- Esto funciona **incluso si los usuarios están en diferentes operadores**
- El flujo es: Usuario A solicita → Usuario B aprueba/rechaza → Usuario A accede

**Mecanismo**:
- Usuario A crea una solicitud de transferencia/compartir documento
- Usuario B recibe una notificación
- Usuario B puede aceptar o rechazar
- Si acepta, Usuario A puede acceder al documento

**Funcionalidad existente**:
- Transferencias P2P entre operadores (CU5)
- Usuarios pueden compartir documentos entre ellos
- Sistema de aprobación/rechazo de transferencias

### 1.2 Admin y Solicitudes de Documentos

**El admin sigue el mismo principio que los usuarios**:
- El admin puede **solicitar documentos a usuarios** (igual que cualquier usuario)
- El usuario debe **aprobar la solicitud** para que el admin acceda
- El admin **NO tiene acceso automático** sin aprobación del usuario
- El admin puede gestionar metadatos sin aprobación (ver nombre, tipo, tamaño, fecha)

---

## 2. Funcionalidades Heredadas de Usuario Normal (Citizen)

Un admin puede realizar todas las acciones de un usuario normal:

- ✅ Ver y gestionar sus propios documentos
- ✅ Subir documentos a su carpeta personal
- ✅ Descargar documentos propios
- ✅ Ver transferencias recibidas y enviadas (propias)
- ✅ **Solicitar documentos a otros usuarios** (igual que cualquier usuario)
- ✅ Gestionar su perfil personal
- ✅ Autenticar/firmar sus propios documentos

---

## 3. Funcionalidades de Administración del Operador Carpeta Ciudadana

### 3.1 Gestión de Usuarios del Operador

**Propósito**: Administrar todos los usuarios registrados en Carpeta Ciudadana.

**Permisos requeridos**:
- `users:read:all` - Ver todos los usuarios del operador
- `users:create` - Crear nuevos usuarios
- `users:update` - Editar información de usuarios
- `users:delete` - Eliminar/desactivar usuarios
- `users:manage:roles` - Asignar/revocar roles a usuarios
- `users:manage:permissions` - Gestionar permisos de usuarios

**Funcionalidades**:
- Ver lista completa de usuarios de Carpeta Ciudadana
- Buscar/filtrar usuarios por email, nombre, rol, estado
- Crear usuarios manualmente (sin registro público)
- Editar información de usuarios (email, nombre, datos de contacto)
- Activar/desactivar cuentas de usuarios
- Asignar roles a usuarios (citizen, admin, etc.)
- Gestionar permisos específicos de usuarios
- Ver historial de actividad por usuario
- Ver último acceso y estadísticas de uso

---

### 3.2 Gestión de Documentos del Operador

**Propósito**: Administrar todos los documentos almacenados en Carpeta Ciudadana.

**⚠️ PRIVACIDAD DE DOCUMENTOS - Regla Fundamental**:
El admin **NO puede acceder al contenido de documentos privados** sin una solicitud explícita y aprobada por el usuario. Esto es **igual al mecanismo que usan los usuarios normales** para solicitar documentos entre ellos.

**Lo que el admin PUEDE hacer sin solicitud**:
- ✅ Ver metadatos de documentos (nombre, tipo, tamaño, fecha, usuario dueño)
- ✅ Ver estadísticas de almacenamiento
- ✅ Ver solicitudes de documentos pendientes entre usuarios
- ✅ Eliminar documentos que violen políticas claramente (con notificación al usuario)
- ✅ Ver logs de auditoría (sin contenido)

**Lo que el admin NO PUEDE hacer sin solicitud**:
- ❌ Acceder al contenido de documentos privados
- ❌ Descargar documentos de usuarios
- ❌ Leer el contenido de documentos
- ❌ Ver el contenido de documentos

**Lo que el admin PUEDE hacer CON solicitud aprobada**:
- ✅ **Solicitar documentos a usuarios** (igual que cualquier usuario)
- ✅ El usuario debe aprobar la solicitud
- ✅ Una vez aprobada, el admin puede acceder al contenido
- ✅ El acceso queda registrado en auditoría

**Permisos requeridos**:
- `documents:read:metadata` - Ver metadatos de todos los documentos (sin acceso al contenido)
- `documents:read:content:on-request` - Acceder al contenido solo cuando el usuario lo solicite y apruebe
- `documents:request:access` - Solicitar acceso a documentos (igual que usuarios normales)
- `documents:moderate` - Moderar contenido de documentos (con solicitud/reporte del usuario)
- `documents:delete:all` - Eliminar documentos que violen políticas
- `documents:audit` - Ver auditoría completa de documentos

**Funcionalidades**:
- Ver metadatos de todos los documentos almacenados:
  - Nombre del documento
  - Tipo de documento (PDF, imagen, etc.)
  - Tamaño en bytes
  - Fecha de creación/actualización
  - Ciudadano dueño (email, nombre)
  - Estado (activo, eliminado, firmado)
  - **NO incluye acceso al contenido sin solicitud**
- Filtrar documentos por:
  - Ciudadano dueño
  - Tipo de documento
  - Estado (activo, eliminado, firmado)
  - Fecha de creación/actualización
  - Tamaño
- **Solicitar acceso a documentos específicos** (igual que usuarios normales):
  - El admin puede crear una solicitud de acceso a un documento
  - La solicitud debe incluir:
    - Motivo de la solicitud (requerido)
    - Descripción de por qué necesita acceder (requerida)
    - Fecha límite de acceso (opcional)
    - Tipo de acceso (visualización, descarga, ambos)
  - El usuario dueño recibe una notificación
  - El usuario puede:
    - Aprobar la solicitud
    - Rechazar la solicitud
    - Solicitar más información
  - Una vez aprobada, el admin puede:
    - Descargar el documento
    - Ver el contenido
    - El acceso queda registrado en auditoría
  - **El admin no tiene privilegios especiales en este proceso**
- Ver solicitudes de documentos entre usuarios:
  - Ver todas las solicitudes de documentos en el operador
  - Filtrar por estado (pendiente, aprobada, rechazada)
  - Ver historial de solicitudes
  - Moderar solicitudes si hay reportes de abuso
- Moderar contenido cuando hay solicitud/reporte:
  - El usuario puede reportar un documento por contenido inapropiado
  - El admin puede moderar el documento reportado
  - Marcar como seguro/inseguro
  - Tomar acciones (eliminar, ocultar)
- Eliminar documentos que violen políticas:
  - Eliminar documentos inapropiados
  - Eliminar documentos que violen términos de servicio
  - Notificar al usuario de la eliminación
- Ver logs de auditoría completos:
  - Ver quién accedió a qué documento y cuándo
  - Ver historial de solicitudes de acceso (entre usuarios y admin)
  - Ver historial de moderaciones
  - **Los logs NO incluyen el contenido de documentos**
- Exportar reportes de documentos:
  - Reportes de metadatos (sin contenido)
  - Estadísticas de almacenamiento
  - Reportes de solicitudes de acceso

---

### 3.3 Gestión de Transferencias del Operador

**Propósito**: Administrar todas las transferencias realizadas desde/hacia Carpeta Ciudadana.

**Permisos requeridos**:
- `transfers:read:all` - Ver todas las transferencias del operador
- `transfers:moderate` - Moderar transferencias
- `transfers:cancel` - Cancelar transferencias pendientes
- `transfers:retry` - Reintentar transferencias fallidas

**Funcionalidades**:
- Ver todas las transferencias (enviadas/recibidas) de Carpeta Ciudadana
- Filtrar transferencias por:
  - Estado (pendiente, completada, fallida, cancelada)
  - Ciudadano origen/destino
  - Operador destino (si es transferencia entre operadores)
  - Fecha de creación
- Ver transferencias entre usuarios:
  - Transferencias P2P dentro del operador
  - Transferencias entre operadores
  - Transferencias pendientes, aceptadas, rechazadas
- Moderar transferencias:
  - Cancelar transferencias sospechosas
  - Revisar transferencias reportadas
- Cancelar transferencias pendientes (solo por razones de seguridad)
- Reintentar transferencias fallidas
- Ver historial completo de transferencias
- Exportar reportes de transferencias
- Ver estadísticas de transferencias (volumen, tasa de éxito)

---

### 3.4 Configuración del Operador Carpeta Ciudadana

**Propósito**: Configurar y gestionar la información y parámetros del operador Carpeta Ciudadana.

**Permisos requeridos**:
- `operator:config:read` - Ver configuración del operador
- `operator:config:update` - Actualizar configuración del operador

**Funcionalidades**:
- Ver información del operador Carpeta Ciudadana:
  - Nombre oficial
  - Dirección
  - Contacto (email, teléfono)
  - Identificador en MinTIC Hub
- Editar información del operador
- Configurar límites y cuotas:
  - Límite de almacenamiento por usuario
  - Límite de documentos por usuario
  - Límite de transferencias por día
- Configurar notificaciones:
  - Notificaciones de registro de usuarios
  - Notificaciones de transferencias
  - Notificaciones de documentos
  - Notificaciones de solicitudes de acceso
- Gestionar integraciones:
  - Configuración de servicios externos
  - APIs y webhooks
- Configurar políticas de retención de documentos
- Gestionar certificados y credenciales del operador

---

### 3.5 Estadísticas y Reportes del Operador

**Propósito**: Visualizar métricas y generar reportes del operador Carpeta Ciudadana.

**Permisos requeridos**:
- `reports:read` - Ver reportes y estadísticas
- `reports:export` - Exportar reportes

**Funcionalidades**:
- Dashboard con métricas clave:
  - **Usuarios**: Total activos/inactivos, nuevos registros (día/semana/mes)
  - **Documentos**: Total, por tipo, por ciudadano, crecimiento (solo metadatos)
  - **Transferencias**: Enviadas/recibidas, pendientes/completadas, tasa de éxito
  - **Solicitudes de Acceso**: Pendientes, aprobadas, rechazadas (entre usuarios y admin)
  - **Almacenamiento**: Uso total, por usuario, tendencias
  - **Actividad**: Eventos diarios/semanales/mensuales
- Gráficos y visualizaciones:
  - Gráficos de líneas (tendencias temporales)
  - Gráficos de barras (comparativas)
  - Gráficos de pastel (distribuciones)
- Reportes exportables:
  - Reportes de usuarios (PDF, Excel, CSV)
  - Reportes de documentos (PDF, Excel, CSV) - solo metadatos
  - Reportes de transferencias (PDF, Excel, CSV)
  - Reportes de solicitudes de acceso (PDF, Excel, CSV)
  - Reportes de actividad (PDF, Excel, CSV)
- Alertas y notificaciones automáticas:
  - Alertas de almacenamiento
  - Alertas de transferencias fallidas
  - Alertas de actividad inusual
  - Alertas de solicitudes de acceso pendientes

---

### 3.6 Logs y Auditoría del Operador

**Propósito**: Monitorear y auditar todas las actividades del operador Carpeta Ciudadana.

**Permisos requeridos**:
- `audit:read` - Ver logs y auditoría
- `audit:export` - Exportar logs

**Funcionalidades**:
- Ver logs del sistema:
  - Logs de autenticación (login, logout, intentos fallidos)
  - Logs de operaciones de documentos (crear, leer, actualizar, eliminar)
  - Logs de transferencias (inicio, confirmación, cancelación)
  - Logs de solicitudes de acceso (creación, aprobación, rechazo)
  - Logs de administración (cambios de configuración, gestión de usuarios)
  - **Logs NO incluyen contenido de documentos**
- Filtrar logs por:
  - Usuario
  - Tipo de acción
  - Fecha/hora
  - Estado (éxito/fallo)
- Buscar en logs:
  - Búsqueda por texto
  - Búsqueda avanzada con múltiples criterios
- Exportar logs:
  - Exportar logs completos (formato JSON, CSV)
  - Exportar logs filtrados
  - Programar exportaciones periódicas
- Visualización de auditoría:
  - Timeline de eventos
  - Trazabilidad de acciones
  - Análisis de patrones
  - Trazabilidad de solicitudes de acceso

---

### 3.7 Gestión de Roles y Permisos del Operador

**Propósito**: Gestionar roles y permisos dentro del operador Carpeta Ciudadana.

**Permisos requeridos**:
- `roles:read` - Ver roles del operador
- `roles:create` - Crear roles personalizados
- `roles:update` - Actualizar roles existentes
- `roles:delete` - Eliminar roles
- `permissions:manage` - Gestionar permisos

**Funcionalidades**:
- Ver lista de roles del operador:
  - Roles predefinidos (citizen, admin)
  - Roles personalizados (si existen)
- Crear roles personalizados:
  - Definir nombre y descripción
  - Asignar permisos específicos
  - Configurar restricciones
- Editar roles existentes:
  - Agregar/remover permisos
  - Modificar descripción
- Eliminar roles (con validaciones):
  - Verificar que no haya usuarios asignados
  - Confirmar eliminación
- Gestionar permisos:
  - Ver lista de permisos disponibles
  - Crear permisos personalizados
  - Documentar permisos

---

## 4. Estructura de Permisos del Rol "admin"

```json
{
  "role": "admin",
  "description": "Administrador del Operador Carpeta Ciudadana",
  "operator_id": "carpeta-ciudadana",
  "permissions": [
    // ============================================
    // Permisos heredados de citizen (usuario normal)
    // ============================================
    "documents:read:own",
    "documents:upload",
    "documents:download:own",
    "documents:delete:own",
    "documents:request:access",  // Solicitar documentos a otros usuarios
    "transfers:read:own",
    "transfers:create",
    "profile:read",
    "profile:update",
    
    // ============================================
    // Permisos de administración del operador
    // ============================================
    
    // Gestión de Usuarios
    "users:read:all",
    "users:create",
    "users:update",
    "users:delete",
    "users:manage:roles",
    "users:manage:permissions",
    
    // Gestión de Documentos
    "documents:read:metadata",  // Ver metadatos sin acceso al contenido
    "documents:read:content:on-request",  // Acceder solo con solicitud aprobada
    "documents:request:access",  // Solicitar acceso (igual que usuarios normales)
    "documents:moderate",  // Moderar documentos (con solicitud/reporte)
    "documents:delete:all",  // Eliminar documentos que violen políticas
    "documents:audit",  // Ver auditoría completa
    
    // Gestión de Transferencias
    "transfers:read:all",
    "transfers:moderate",
    "transfers:cancel",
    "transfers:retry",
    
    // Gestión de Solicitudes de Acceso
    "requests:read:all",  // Ver todas las solicitudes de acceso
    "requests:moderate",  // Moderar solicitudes sospechosas
    
    // Configuración del Operador
    "operator:config:read",
    "operator:config:update",
    
    // Estadísticas y Reportes
    "reports:read",
    "reports:export",
    
    // Logs y Auditoría
    "audit:read",
    "audit:export",
    
    // Gestión de Roles y Permisos
    "roles:read",
    "roles:create",
    "roles:update",
    "roles:delete",
    "permissions:manage"
  ]
}
```

---

## 5. Diferencias con Otros Roles

| Rol | Funcionalidad | Alcance |
|-----|---------------|---------|
| **citizen** | Usuario normal | Solo sus propios recursos<br/>Puede solicitar documentos a otros usuarios<br/>Puede recibir solicitudes y aprobar/rechazar |
| **admin** | Administrador del operador Carpeta Ciudadana | **Todos los recursos del operador Carpeta Ciudadana** + funcionalidades de citizen<br/>**⚠️ NO puede acceder a contenido de documentos sin solicitud aprobada**<br/>**Puede solicitar documentos igual que cualquier usuario** |
| **mintic** | Administrador MinTIC (gestión de operadores en el Hub) | Gestión de operadores en el Hub MinTIC (NO relacionado con admin) |

**Nota importante**: El rol `admin` NO tiene acceso a:
- ❌ Gestión de otros operadores MinTIC (eso es rol `mintic`)
- ❌ Registro de nuevos operadores en MinTIC Hub (eso es rol `mintic`)
- ❌ Configuración del sistema MinTIC (eso es rol `mintic`)
- ❌ **Contenido de documentos privados sin solicitud aprobada**
- ❌ **Acceso automático a documentos de usuarios** (debe solicitar igual que cualquier usuario)

El rol `admin` SOLO administra:
- ✅ Usuarios de Carpeta Ciudadana
- ✅ **Metadatos de documentos de Carpeta Ciudadana** (sin contenido sin solicitud)
- ✅ Transferencias de Carpeta Ciudadana
- ✅ **Solicitudes de acceso entre usuarios** (puede moderar)
- ✅ Configuración de Carpeta Ciudadana
- ✅ Estadísticas y reportes de Carpeta Ciudadana

---

## 6. Sistema de Solicitudes de Acceso a Documentos

### 6.1 Flujo de Solicitud de Acceso (Igual para Admin y Usuarios)

**El admin sigue el mismo flujo que los usuarios normales**:

1. **Admin o Usuario solicita acceso**:
   - Selecciona un documento específico
   - Completa un formulario con:
     - Motivo de la solicitud (requerido)
     - Descripción detallada (requerida)
     - Fecha límite de acceso (opcional)
     - Tipo de acceso (visualización, descarga, ambos)
   - Envía la solicitud

2. **Usuario dueño recibe notificación**:
   - El usuario dueño recibe una notificación
   - Puede ver los detalles de la solicitud
   - Puede ver el motivo y la descripción
   - **No sabe si es admin o usuario normal** (opcional: mostrar rol si es admin)

3. **Usuario decide**:
   - **Aprobar**: El admin/usuario obtiene acceso temporal al documento
   - **Rechazar**: La solicitud se cierra y no se puede acceder
   - **Solicitar más información**: El solicitante puede proporcionar más detalles

4. **Acceso otorgado** (si fue aprobado):
   - El admin/usuario puede acceder al contenido del documento
   - El acceso se registra en auditoría
   - El acceso puede tener fecha de expiración
   - El usuario puede revocar el acceso en cualquier momento

### 6.2 Diferencias entre Admin y Usuario Normal en Solicitudes

| Aspecto | Usuario Normal | Admin |
|---------|---------------|-------|
| **Puede solicitar** | ✅ Sí, a otros usuarios | ✅ Sí, igual que usuarios normales |
| **Proceso de aprobación** | Usuario dueño aprueba/rechaza | Usuario dueño aprueba/rechaza |
| **Privilegios especiales** | ❌ No | ❌ **NO hay privilegios especiales** |
| **Puede ver todas las solicitudes** | ❌ Solo las propias | ✅ Sí, puede ver todas las solicitudes del operador |
| **Puede moderar solicitudes** | ❌ No | ✅ Sí, puede moderar solicitudes sospechosas |
| **Puede cancelar solicitudes** | ✅ Solo las propias | ✅ Puede cancelar cualquier solicitud (solo por seguridad) |

### 6.3 Modelo de Datos de Solicitud

```json
{
  "id": "request-123",
  "document_id": "doc-456",
  "document_owner_id": "user-789",
  "requester_id": "admin-001",  // Puede ser admin o usuario normal
  "requester_type": "admin",  // "admin" o "user"
  "status": "pending",  // pending, approved, rejected, expired, revoked
  "reason": "Investigación de posible violación de políticas",
  "description": "Necesito revisar el contenido para verificar si viola nuestros términos de servicio",
  "requested_at": "2025-01-15T10:00:00Z",
  "expires_at": "2025-01-20T10:00:00Z",  // Opcional
  "access_type": "download",  // view, download, both
  "approved_at": null,
  "approved_by": null,
  "rejected_at": null,
  "rejected_by": null,
  "revoked_at": null,
  "revoked_by": null,
  "access_granted_at": null,
  "access_expires_at": null
}
```

---

## 7. Prioridades de Implementación

### 🔴 Alta Prioridad
1. **Sistema de Solicitudes de Acceso a Documentos**
   - Crear solicitud (admin igual que usuario)
   - Notificar al usuario
   - Aprobar/rechazar solicitud
   - Acceder al contenido solo con aprobación
   - **El admin NO tiene privilegios especiales en este proceso**
   
2. **Gestión de Usuarios del Operador**
   - Listar usuarios
   - Crear/editar/eliminar usuarios
   - Asignar roles
   
3. **Gestión de Documentos del Operador** (solo metadatos)
   - Ver metadatos de todos los documentos
   - Filtrar documentos
   - Eliminar documentos que violen políticas
   
4. **Estadísticas Básicas del Operador**
   - Dashboard con métricas clave
   - Gráficos básicos

### 🟡 Media Prioridad
5. **Gestión de Transferencias del Operador**
   - Ver todas las transferencias
   - Moderar transferencias sospechosas
   - Cancelar transferencias pendientes
   
6. **Configuración del Operador**
   - Editar información del operador
   - Configurar límites y cuotas
   
7. **Logs y Auditoría Básica**
   - Ver logs del sistema
   - Filtrar por usuario/acción/fecha
   - Ver historial de solicitudes de acceso

### 🟢 Baja Prioridad
8. **Reportes Exportables**
   - Exportar reportes en PDF/Excel/CSV
   
9. **Dashboard Avanzado**
   - Gráficos avanzados
   - Visualizaciones interactivas
   
10. **Gestión de Roles Personalizados**
    - Crear roles personalizados
    - Gestionar permisos avanzados

---

## 8. Endpoints Propuestos

### Gestión de Usuarios
- `GET /api/admin/users` - Listar todos los usuarios
- `GET /api/admin/users/{user_id}` - Ver detalle de usuario
- `POST /api/admin/users` - Crear usuario
- `PATCH /api/admin/users/{user_id}` - Actualizar usuario
- `DELETE /api/admin/users/{user_id}` - Eliminar/desactivar usuario
- `POST /api/admin/users/{user_id}/roles` - Asignar roles
- `DELETE /api/admin/users/{user_id}/roles` - Revocar roles

### Gestión de Documentos
- `GET /api/admin/documents` - Listar todos los documentos (solo metadatos)
- `GET /api/admin/documents/{document_id}` - Ver metadatos de documento (sin contenido)
- `POST /api/admin/documents/{document_id}/request-access` - **Solicitar acceso** (igual que usuarios normales)
- `GET /api/admin/documents/{document_id}/content` - Obtener contenido (solo si hay solicitud aprobada)
- `DELETE /api/admin/documents/{document_id}` - Eliminar documento que viola políticas
- `POST /api/admin/documents/{document_id}/moderate` - Moderar documento (con solicitud/reporte)

### Gestión de Solicitudes de Acceso
- `GET /api/admin/document-requests` - Ver todas las solicitudes de acceso del operador
- `GET /api/admin/document-requests/{request_id}` - Ver detalle de solicitud
- `POST /api/admin/document-requests/{request_id}/moderate` - Moderar solicitud sospechosa
- `DELETE /api/admin/document-requests/{request_id}` - Cancelar solicitud (solo por seguridad)

### Gestión de Transferencias
- `GET /api/admin/transfers` - Listar todas las transferencias
- `GET /api/admin/transfers/{transfer_id}` - Ver detalle de transferencia
- `POST /api/admin/transfers/{transfer_id}/cancel` - Cancelar transferencia
- `POST /api/admin/transfers/{transfer_id}/retry` - Reintentar transferencia

### Configuración del Operador
- `GET /api/admin/operator/config` - Ver configuración
- `PATCH /api/admin/operator/config` - Actualizar configuración

### Estadísticas y Reportes
- `GET /api/admin/stats` - Obtener estadísticas
- `GET /api/admin/reports` - Generar reportes
- `POST /api/admin/reports/export` - Exportar reportes

### Logs y Auditoría
- `GET /api/admin/audit/logs` - Ver logs
- `GET /api/admin/audit/logs/export` - Exportar logs

---

## 9. Recomendaciones Técnicas

1. **Privacidad y Seguridad**:
   - Implementar sistema de solicitudes de acceso robusto
   - El admin usa el mismo mecanismo que los usuarios normales
   - Validar que el admin solo puede acceder con solicitud aprobada
   - Registrar todos los accesos en auditoría
   - Permitir revocación de acceso por el usuario

2. **Separación de Responsabilidades**:
   - El rol `admin` gestiona SOLO el operador Carpeta Ciudadana
   - El rol `mintic` gestiona operadores en el Hub MinTIC
   - No mezclar funcionalidades

3. **Implementación de ABAC**:
   - Validar permisos en cada endpoint usando middleware
   - Implementar `require_permission()` decorators
   - Validar que el admin solo pueda administrar su propio operador
   - Validar que las solicitudes de acceso sigan el mismo flujo para admin y usuarios

4. **Auditoría Completa**:
   - Registrar todas las acciones del admin
   - Incluir en logs: usuario, acción, recurso, timestamp
   - Registrar especialmente las solicitudes de acceso
   - Exportable para compliance

5. **UI Administrativa**:
   - Crear secciones dedicadas en `/admin`:
     - `/admin/users` - Gestión de usuarios
     - `/admin/documents` - Gestión de documentos (metadatos)
     - `/admin/document-requests` - Solicitudes de acceso (propias y del operador)
     - `/admin/transfers` - Gestión de transferencias
     - `/admin/config` - Configuración del operador
     - `/admin/reports` - Estadísticas y reportes
     - `/admin/audit` - Logs y auditoría
     - `/admin/roles` - Gestión de roles

6. **Validaciones de Seguridad**:
   - Un admin no puede eliminarse a sí mismo
   - Un admin no puede desactivar su propia cuenta
   - Requerir confirmación para acciones destructivas
   - Limitar permisos por alcance (solo Carpeta Ciudadana)
   - Validar solicitudes de acceso antes de aprobarlas
   - **El admin NO puede auto-aprobar sus propias solicitudes**

---

## 10. Resumen

El rol **"admin"** permite:
- ✅ Administrar el operador **Carpeta Ciudadana** completamente
- ✅ Gestionar usuarios, documentos (metadatos), transferencias del operador
- ✅ Configurar el operador Carpeta Ciudadana
- ✅ Ver estadísticas y generar reportes
- ✅ Monitorear y auditar actividades
- ✅ **Solicitar acceso a documentos igual que cualquier usuario**
- ✅ Ver y moderar solicitudes de acceso entre usuarios

El rol **"admin"** NO permite:
- ❌ Administrar otros operadores MinTIC
- ❌ Gestionar el Hub MinTIC
- ❌ Registrar nuevos operadores en MinTIC
- ❌ **Acceder al contenido de documentos privados sin solicitud aprobada**
- ❌ **Auto-aprobar sus propias solicitudes de acceso**
- ❌ **Tener privilegios especiales en el proceso de solicitud de documentos**

**Principio fundamental**: El admin sigue el mismo mecanismo que los usuarios normales para solicitar documentos. No hay privilegios especiales que permitan acceso automático sin aprobación del usuario dueño.

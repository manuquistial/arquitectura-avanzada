# Plan de Corrección del Frontend - Carpeta Ciudadana

## 📋 Resumen Ejecutivo

Este documento detalla el plan de acción para corregir todos los problemas identificados en el frontend, priorizados por criticidad e impacto.

---

## 🎯 Objetivos

1. **Corregir endpoints mal configurados** (CRÍTICO)
2. **Corregir tipos de datos incorrectos** (CRÍTICO)
3. **Integrar servicios faltantes** (ALTA)
4. **Implementar funcionalidades faltantes** (MEDIA)
5. **Mejorar UX y completitud** (BAJA)

---

## 📊 Fases del Plan

### **FASE 1: Correcciones Críticas** 🔴
**Prioridad:** CRÍTICA - Bloquea funcionalidad  
**Tiempo estimado:** 30-45 minutos

#### 1.1 Corregir Endpoints de Signature Service
- **Archivo:** `apps/frontend/src/lib/api.ts`
- **Líneas:** 275-308
- **Cambios:**
  - Corregir `signDocument()`: Agregar prefijo `/api/signature`
  - Corregir `getSignatureStatus()`: Eliminar o usar `verifySignature`
  - Corregir `verifySignature()`: Agregar prefijo `/api/signature` y cambiar parámetro

#### 1.2 Corregir Tipos de Datos
- **Archivo:** `apps/frontend/src/types/api.ts`
- **Líneas:** 41-47, 134-138
- **Cambios:**
  - `UploadURLRequest.citizen_id`: `number` → `string`
  - `SignDocumentRequest`: Agregar campos requeridos

#### 1.3 Verificar y Corregir Uso de Tipos
- **Archivo:** `apps/frontend/src/lib/api.ts`
- **Verificar:** Uso correcto de tipos corregidos
- **Cambios:** Ajustar llamadas a funciones si es necesario

---

### **FASE 2: Integración de Servicios** 🟡
**Prioridad:** ALTA - Funcionalidad importante  
**Tiempo estimado:** 45-60 minutos

#### 2.1 Integrar Metadata Service
- **Archivo:** `apps/frontend/src/lib/api.ts`
- **Agregar después de línea 204:**
  - `getDocumentMetadata(citizenId: string)`
  - `searchDocuments(query: string, citizenId?: string)`
- **Variables de entorno:**
  - Agregar `NEXT_PUBLIC_METADATA_SERVICE_URL` en `next.config.js`
  - Agregar en Helm chart `deployment-frontend.yaml`

#### 2.2 Integrar Notification Service
- **Archivo:** `apps/frontend/src/lib/api.ts`
- **Agregar después de línea 272:**
  - `getNotificationStats()`
  - `getUserNotifications(citizenId: string)`
- **Variables de entorno:**
  - Agregar `NEXT_PUBLIC_NOTIFICATION_SERVICE_URL` en `next.config.js`
  - Agregar en Helm chart `deployment-frontend.yaml`

#### 2.3 Actualizar Dashboard con Datos Reales
- **Archivo:** `apps/frontend/src/lib/api.ts`
- **Líneas:** 534-557
- **Cambios:**
  - Reemplazar `getDashboardStats()` con implementación real
  - Reemplazar `getRecentActivities()` con implementación real
- **Archivo:** `apps/frontend/src/app/dashboard/page.tsx`
- **Verificar:** Uso correcto de datos reales

---

### **FASE 3: Funcionalidades Faltantes** 🟢
**Prioridad:** MEDIA - Mejora UX  
**Tiempo estimado:** 60-90 minutos

#### 3.1 Crear Página de Firma de Documentos
- **Archivo nuevo:** `apps/frontend/src/app/documents/sign/page.tsx`
- **Funcionalidad:**
  - Listar documentos disponibles para firmar
  - Formulario para seleccionar tipo de firma
  - Integración con Signature Service
  - Visualización de estado de firma

#### 3.2 Crear Página de Búsqueda
- **Archivo nuevo:** `apps/frontend/src/app/documents/search/page.tsx`
- **Funcionalidad:**
  - Barra de búsqueda
  - Integración con Metadata Service
  - Filtros avanzados
  - Resultados paginados

#### 3.3 Agregar Funcionalidad de Firma en Listado de Documentos
- **Archivo:** `apps/frontend/src/app/documents/page.tsx`
- **Cambios:**
  - Agregar botón "Firmar" en cada documento
  - Integrar con Signature Service
  - Mostrar estado de firma

---

### **FASE 4: Mejoras y Optimizaciones** 🔵
**Prioridad:** BAJA - Mejoras futuras  
**Tiempo estimado:** 30-45 minutos

#### 4.1 Agregar Notificaciones en UI
- **Componente nuevo:** `apps/frontend/src/components/NotificationBell.tsx`
- **Integración:** Notification Service
- **UI:** Badge con contador, dropdown con notificaciones

#### 4.2 Mejorar Manejo de Errores
- **Archivo:** `apps/frontend/src/lib/api.ts`
- **Mejoras:**
  - Mensajes de error más descriptivos
  - Manejo de errores específicos por servicio
  - Retry logic para requests fallidos

#### 4.3 Agregar Loading States
- **Componentes:** Mejorar estados de carga en todas las páginas
- **UX:** Skeleton loaders, spinners mejorados

---

## 📝 Detalle de Tareas por Fase

### **FASE 1: Correcciones Críticas**

#### Tarea 1.1: Corregir `signDocument()`
```typescript
// Archivo: apps/frontend/src/lib/api.ts
// Línea: 275-286

// ANTES:
async signDocument(documentId: string, signatureData: any) {
  const response = await api.post(`${SIGNATURE_SERVICE_URL}/sign`, {
    document_id: documentId,
    ...signatureData,
  });
}

// DESPUÉS:
async signDocument(documentId: string, signatureData: SignDocumentRequest) {
  const response = await api.post(`${SIGNATURE_SERVICE_URL}/api/signature/sign`, {
    document_id: documentId,
    citizen_id: signatureData.citizen_id,
    signature_type: signatureData.signature_type || "PAdES",
    document_title: signatureData.document_title || "",
  });
}
```

#### Tarea 1.2: Corregir `getSignatureStatus()`
```typescript
// Archivo: apps/frontend/src/lib/api.ts
// Línea: 288-296

// OPCIÓN 1: Eliminar función (recomendado)
// OPCIÓN 2: Usar verifySignature en su lugar
async getSignatureStatus(documentId: string) {
  return await this.verifySignature(documentId);
}
```

#### Tarea 1.3: Corregir `verifySignature()`
```typescript
// Archivo: apps/frontend/src/lib/api.ts
// Línea: 298-308

// ANTES:
async verifySignature(documentId: string) {
  const response = await api.post(`${SIGNATURE_SERVICE_URL}/verify`, {
    document_id: documentId
  });
}

// DESPUÉS:
async verifySignature(documentId: string) {
  const response = await api.post(`${SIGNATURE_SERVICE_URL}/api/signature/verify`, {
    signed_document_id: documentId  // Nota: backend espera signed_document_id
  });
}
```

#### Tarea 1.4: Corregir `UploadURLRequest`
```typescript
// Archivo: apps/frontend/src/types/api.ts
// Línea: 41-47

// ANTES:
export interface UploadURLRequest {
  citizen_id: number;
  ...
}

// DESPUÉS:
export interface UploadURLRequest {
  citizen_id: string;  // Cambiar a string
  ...
}
```

#### Tarea 1.5: Corregir `SignDocumentRequest`
```typescript
// Archivo: apps/frontend/src/types/api.ts
// Línea: 134-138

// ANTES:
export interface SignDocumentRequest {
  document_id: string;
  citizen_id: string;
  signature_data?: any;
}

// DESPUÉS:
export interface SignDocumentRequest {
  document_id: string;
  citizen_id: string;
  signature_type: "PAdES" | "XAdES" | "CAdES";
  document_title: string;
}
```

---

### **FASE 2: Integración de Servicios**

#### Tarea 2.1: Agregar Metadata Service API
```typescript
// Archivo: apps/frontend/src/lib/api.ts
// Agregar después de línea 204

// Metadata Service API calls
async getDocumentMetadata(citizenId: string) {
  try {
    const METADATA_SERVICE_URL = process.env.NEXT_PUBLIC_METADATA_SERVICE_URL;
    if (!METADATA_SERVICE_URL) {
      console.warn('NEXT_PUBLIC_METADATA_SERVICE_URL not configured');
      return [];
    }
    const response = await api.get(`${METADATA_SERVICE_URL}/api/metadata/documents/citizen/${citizenId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching document metadata:', error);
    return [];
  }
},

async searchDocuments(query: string, citizenId?: string) {
  try {
    const METADATA_SERVICE_URL = process.env.NEXT_PUBLIC_METADATA_SERVICE_URL;
    if (!METADATA_SERVICE_URL) {
      console.warn('NEXT_PUBLIC_METADATA_SERVICE_URL not configured');
      return { documents: [], total: 0 };
    }
    const response = await api.post(`${METADATA_SERVICE_URL}/api/metadata/search`, {
      query,
      citizen_id: citizenId,
    });
    return response.data;
  } catch (error) {
    console.error('Error searching documents:', error);
    return { documents: [], total: 0 };
  }
},
```

#### Tarea 2.2: Agregar Notification Service API
```typescript
// Archivo: apps/frontend/src/lib/api.ts
// Agregar después de línea 272

// Notification Service API calls
async getNotificationStats() {
  try {
    const NOTIFICATION_SERVICE_URL = process.env.NEXT_PUBLIC_NOTIFICATION_SERVICE_URL;
    if (!NOTIFICATION_SERVICE_URL) {
      console.warn('NEXT_PUBLIC_NOTIFICATION_SERVICE_URL not configured');
      return { total_notifications: 0 };
    }
    const response = await api.get(`${NOTIFICATION_SERVICE_URL}/api/notifications/stats`);
    return response.data;
  } catch (error) {
    console.error('Error fetching notification stats:', error);
    return { total_notifications: 0 };
  }
},

async getUserNotifications(citizenId: string) {
  try {
    const NOTIFICATION_SERVICE_URL = process.env.NEXT_PUBLIC_NOTIFICATION_SERVICE_URL;
    if (!NOTIFICATION_SERVICE_URL) {
      console.warn('NEXT_PUBLIC_NOTIFICATION_SERVICE_URL not configured');
      return [];
    }
    const response = await api.get(`${NOTIFICATION_SERVICE_URL}/api/notifications/user/${citizenId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching user notifications:', error);
    return [];
  }
},
```

#### Tarea 2.3: Actualizar Variables de Entorno
```javascript
// Archivo: apps/frontend/next.config.js
// Agregar en env:

env: {
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8011',
  NEXT_PUBLIC_ENVIRONMENT: process.env.NODE_ENV || 'development',
  NEXT_PUBLIC_METADATA_SERVICE_URL: process.env.NEXT_PUBLIC_METADATA_SERVICE_URL || 'http://localhost:8007',
  NEXT_PUBLIC_NOTIFICATION_SERVICE_URL: process.env.NEXT_PUBLIC_NOTIFICATION_SERVICE_URL || 'http://localhost:8008',
},
```

#### Tarea 2.4: Actualizar Helm Chart
```yaml
# Archivo: deploy/helm/carpeta-ciudadana/templates/deployment-frontend.yaml
# Agregar después de línea 68:

- name: NEXT_PUBLIC_METADATA_SERVICE_URL
  valueFrom:
    secretKeyRef:
      name: frontend-config
      key: NEXT_PUBLIC_METADATA_SERVICE_URL
      optional: true
- name: NEXT_PUBLIC_NOTIFICATION_SERVICE_URL
  valueFrom:
    secretKeyRef:
      name: frontend-config
      key: NEXT_PUBLIC_NOTIFICATION_SERVICE_URL
      optional: true
```

#### Tarea 2.5: Actualizar `getDashboardStats()`
```typescript
// Archivo: apps/frontend/src/lib/api.ts
// Línea: 534-547

// ANTES:
async getDashboardStats() {
  return {
    totalDocuments: 0,
    signedDocuments: 0,
    pendingTransfers: 0,
    sharedDocuments: 0
  };
}

// DESPUÉS:
async getDashboardStats() {
  try {
    // Obtener citizenId de la sesión (necesita acceso a session)
    // Por ahora usar un ID por defecto o pasar como parámetro
    const citizenId = '1234567890'; // TODO: Obtener de sesión
    
    // Obtener documentos
    const documents = await this.getDocuments(citizenId);
    const totalDocuments = documents.length;
    
    // Contar documentos firmados
    const signedDocuments = documents.filter((doc: any) => 
      doc.status === 'signed' || doc.state === 'SIGNED'
    ).length;
    
    // Obtener transferencias
    const transfers = await this.getTransfers(citizenId);
    const pendingTransfers = transfers.filter((t: any) => 
      t.status === 'pending'
    ).length;
    
    // Obtener estadísticas de notificaciones
    const notifStats = await this.getNotificationStats();
    
    return {
      totalDocuments,
      signedDocuments,
      pendingTransfers,
      sharedDocuments: notifStats.total_notifications || 0,
    };
  } catch (error) {
    console.error('Error fetching dashboard stats:', error);
    return {
      totalDocuments: 0,
      signedDocuments: 0,
      pendingTransfers: 0,
      sharedDocuments: 0,
    };
  }
},
```

---

### **FASE 3: Funcionalidades Faltantes**

#### Tarea 3.1: Crear Página de Firma de Documentos
- **Archivo nuevo:** `apps/frontend/src/app/documents/sign/page.tsx`
- **Funcionalidad completa:** Ver template en sección de templates

#### Tarea 3.2: Crear Página de Búsqueda
- **Archivo nuevo:** `apps/frontend/src/app/documents/search/page.tsx`
- **Funcionalidad completa:** Ver template en sección de templates

#### Tarea 3.3: Agregar Botón de Firma en Listado
- **Archivo:** `apps/frontend/src/app/documents/page.tsx`
- **Cambios:** Agregar botón "Firmar" y lógica de firma

---

## 🔄 Orden de Ejecución

1. **FASE 1** (Crítico) → Ejecutar primero
2. **FASE 2** (Alta) → Ejecutar después de FASE 1
3. **FASE 3** (Media) → Ejecutar después de FASE 2
4. **FASE 4** (Baja) → Ejecutar al final

---

## ✅ Checklist de Verificación

### FASE 1: Correcciones Críticas
- [ ] Endpoints de Signature Service corregidos
- [ ] Tipos de datos corregidos
- [ ] Verificación de uso de tipos
- [ ] Pruebas de endpoints corregidos

### FASE 2: Integración de Servicios
- [ ] Metadata Service integrado
- [ ] Notification Service integrado
- [ ] Variables de entorno configuradas
- [ ] Helm chart actualizado
- [ ] Dashboard con datos reales

### FASE 3: Funcionalidades Faltantes
- [ ] Página de firma creada
- [ ] Página de búsqueda creada
- [ ] Botón de firma en listado

### FASE 4: Mejoras
- [ ] Notificaciones en UI
- [ ] Manejo de errores mejorado
- [ ] Loading states mejorados

---

## 🧪 Pruebas a Realizar

### Después de FASE 1:
- [ ] Probar firma de documentos
- [ ] Probar verificación de firmas
- [ ] Verificar tipos de datos

### Después de FASE 2:
- [ ] Probar obtención de metadata
- [ ] Probar búsqueda de documentos
- [ ] Probar estadísticas de notificaciones
- [ ] Verificar dashboard con datos reales

### Después de FASE 3:
- [ ] Probar página de firma
- [ ] Probar página de búsqueda
- [ ] Probar flujo completo de firma

---

## 📚 Referencias

- [Análisis del Frontend](./ANALISIS_FRONTEND.md)
- [Verificación Funcional](./VERIFICACION_FUNCIONAL.md)
- [Análisis de Arquitectura](./ANALISIS_ARQUITECTURA.md)

---

**Última actualización:** 2025-11-06  
**Estado:** Plan creado, listo para ejecución


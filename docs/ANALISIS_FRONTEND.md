# Análisis del Frontend - Carpeta Ciudadana

## 📋 Resumen Ejecutivo

Este documento analiza el estado actual del frontend, identifica problemas en los llamados a los endpoints, y documenta funcionalidades faltantes.

---

## 🔍 Análisis de Endpoints

### ✅ Endpoints Correctamente Configurados

#### 1. **Citizen Service**
- ✅ `POST /api/citizens/register` - Correcto
- ✅ `GET /api/citizens/{citizenId}` - Correcto
- ✅ `DELETE /api/citizens/unregister` - Correcto

#### 2. **Ingestion Service**
- ✅ `GET /api/documents/?citizen_id=XXX` - Correcto
- ✅ `POST /api/documents/upload-url` - Correcto
- ✅ `POST /api/documents/confirm-upload` - Correcto
- ✅ `POST /api/documents/download-url` - Correcto
- ✅ `GET /api/documents/download/{documentId}` - Correcto
- ✅ `DELETE /api/documents/{documentId}` - Correcto
- ✅ `POST /api/documents/upload-direct` - Correcto

#### 3. **Transfer Service**
- ✅ `GET /api?citizen_id=XXX` - Correcto
- ✅ `POST /api/initiate` - Correcto
- ✅ `GET /api/status/{transferId}` - Correcto
- ✅ `POST /api/{transferId}/accept` - Correcto
- ✅ `POST /api/{transferId}/reject` - Correcto

#### 4. **Auth Service**
- ✅ `POST /register` - Correcto (usado en NextAuth)
- ✅ `POST /login` - Correcto (usado en NextAuth)
- ✅ `GET /.well-known/openid-configuration` - Correcto

---

### ❌ Endpoints Incorrectamente Configurados

#### 1. **Signature Service** - **CRÍTICO**

**Problema 1: Falta prefijo `/api`**
```typescript
// ❌ INCORRECTO (línea 277 en api.ts)
const response = await api.post(`${SIGNATURE_SERVICE_URL}/sign`, {
  document_id: documentId,
  ...signatureData,
});

// ✅ CORRECTO
const response = await api.post(`${SIGNATURE_SERVICE_URL}/api/signature/sign`, {
  document_id: documentId,
  citizen_id: citizenId,
  signature_type: signatureData.signature_type || "PAdES",
  document_title: signatureData.document_title || "",
});
```

**Problema 2: Endpoint inexistente**
```typescript
// ❌ INCORRECTO (línea 290 en api.ts)
// Este endpoint NO existe en el backend
const response = await api.get(`${SIGNATURE_SERVICE_URL}/status/${documentId}`);
```

**Solución:** El endpoint de estado no existe. Se debe usar el endpoint de verificación o eliminar esta función.

**Problema 3: Falta prefijo `/api`**
```typescript
// ❌ INCORRECTO (línea 300 en api.ts)
const response = await api.post(`${SIGNATURE_SERVICE_URL}/verify`, {
  document_id: documentId
});

// ✅ CORRECTO
const response = await api.post(`${SIGNATURE_SERVICE_URL}/api/signature/verify`, {
  signed_document_id: documentId  // Nota: el backend espera signed_document_id
});
```

---

### ⚠️ Problemas de Tipos de Datos

#### 1. **UploadURLRequest - citizen_id**
```typescript
// ❌ INCORRECTO (types/api.ts línea 42)
export interface UploadURLRequest {
  citizen_id: number;  // El backend espera string
  filename: string;
  content_type: string;
  title: string;
  description?: string;
}

// ✅ CORRECTO
export interface UploadURLRequest {
  citizen_id: string;  // El backend espera string
  filename: string;
  content_type: string;
  title: string;
  description?: string;
}
```

#### 2. **SignDocumentRequest - Faltan campos requeridos**
```typescript
// ❌ INCORRECTO (types/api.ts línea 134)
export interface SignDocumentRequest {
  document_id: string;
  citizen_id: string;
  signature_data?: any;  // Campo opcional pero el backend requiere signature_type y document_title
}

// ✅ CORRECTO
export interface SignDocumentRequest {
  document_id: string;
  citizen_id: string;
  signature_type: "PAdES" | "XAdES" | "CAdES";  // Requerido
  document_title: string;  // Requerido
}
```

---

## 🚫 Funcionalidades Faltantes

### 1. **Integración con Metadata Service**
- ❌ No hay llamadas al Metadata Service
- ❌ No hay búsqueda de documentos
- ❌ No hay endpoint `/api/metadata/documents/citizen/{citizen_id}`
- ❌ No hay endpoint `/api/metadata/search`

**Endpoints disponibles en el backend:**
- `GET /api/metadata/documents/citizen/{citizen_id}`
- `POST /api/metadata/search`

### 2. **Integración con Notification Service**
- ❌ No hay llamadas al Notification Service
- ❌ No hay visualización de notificaciones
- ❌ No hay endpoint `/api/notifications/stats`
- ❌ No hay endpoint para obtener notificaciones del usuario

**Endpoints disponibles en el backend:**
- `GET /api/notifications/stats`
- `GET /api/notifications/user/{citizen_id}` (probablemente)

### 3. **Funcionalidad de Firma de Documentos**
- ❌ No hay página para firmar documentos
- ❌ No hay integración con el Signature Service (endpoints mal configurados)
- ❌ No hay visualización del estado de firma
- ❌ No hay verificación de firmas

### 4. **Dashboard con Datos Reales**
- ❌ `getDashboardStats()` retorna datos mock (línea 534-547 en api.ts)
- ❌ `getRecentActivities()` retorna array vacío (línea 549-557 en api.ts)
- ❌ No hay integración con servicios reales para obtener estadísticas

**Solución:** Integrar con:
- Ingestion Service para contar documentos
- Signature Service para contar documentos firmados
- Transfer Service para contar transferencias pendientes
- Metadata Service para obtener actividades recientes

### 5. **Página de Firma de Documentos**
- ❌ No existe página `/sign` o `/documents/sign`
- ❌ No hay UI para seleccionar documentos a firmar
- ❌ No hay UI para verificar firmas

### 6. **Búsqueda de Documentos**
- ❌ No hay página de búsqueda
- ❌ No hay integración con Metadata Service para búsqueda
- ❌ No hay filtros avanzados

### 7. **Notificaciones en Tiempo Real**
- ❌ No hay sistema de notificaciones
- ❌ No hay integración con Notification Service
- ❌ No hay UI para mostrar notificaciones

---

## 🔧 Correcciones Necesarias

### 1. **Corregir Endpoints de Signature Service**

**Archivo:** `apps/frontend/src/lib/api.ts`

```typescript
// Línea 275-286: Corregir signDocument
async signDocument(documentId: string, signatureData: any) {
  try {
    const response = await api.post(`${SIGNATURE_SERVICE_URL}/api/signature/sign`, {
      document_id: documentId,
      citizen_id: signatureData.citizen_id,
      signature_type: signatureData.signature_type || "PAdES",
      document_title: signatureData.document_title || "",
    });
    return response.data;
  } catch (error) {
    console.error('Error signing document:', error);
    throw error;
  }
},

// Línea 288-296: Eliminar o corregir getSignatureStatus
// Este endpoint no existe en el backend
async getSignatureStatus(documentId: string) {
  // Opción 1: Eliminar esta función
  // Opción 2: Usar verifySignature en su lugar
  try {
    const response = await api.post(`${SIGNATURE_SERVICE_URL}/api/signature/verify`, {
      signed_document_id: documentId
    });
    return response.data;
  } catch (error) {
    console.error('Error getting signature status:', error);
    throw error;
  }
},

// Línea 298-308: Corregir verifySignature
async verifySignature(documentId: string) {
  try {
    const response = await api.post(`${SIGNATURE_SERVICE_URL}/api/signature/verify`, {
      signed_document_id: documentId  // Nota: el backend espera signed_document_id
    });
    return response.data;
  } catch (error) {
    console.error('Error verifying signature:', error);
    throw error;
  }
},
```

### 2. **Corregir Tipos de Datos**

**Archivo:** `apps/frontend/src/types/api.ts`

```typescript
// Línea 41-47: Corregir UploadURLRequest
export interface UploadURLRequest {
  citizen_id: string;  // Cambiar de number a string
  filename: string;
  content_type: string;
  title: string;
  description?: string;
}

// Línea 134-138: Corregir SignDocumentRequest
export interface SignDocumentRequest {
  document_id: string;
  citizen_id: string;
  signature_type: "PAdES" | "XAdES" | "CAdES";  // Requerido
  document_title: string;  // Requerido
}
```

### 3. **Agregar Integración con Metadata Service**

**Archivo:** `apps/frontend/src/lib/api.ts`

```typescript
// Agregar después de la línea 204
// Metadata Service API calls
async getDocumentMetadata(citizenId: string) {
  try {
    const METADATA_SERVICE_URL = process.env.NEXT_PUBLIC_METADATA_SERVICE_URL;
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

### 4. **Agregar Integración con Notification Service**

**Archivo:** `apps/frontend/src/lib/api.ts`

```typescript
// Agregar después de la línea 272
// Notification Service API calls
async getNotificationStats() {
  try {
    const NOTIFICATION_SERVICE_URL = process.env.NEXT_PUBLIC_NOTIFICATION_SERVICE_URL;
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
    const response = await api.get(`${NOTIFICATION_SERVICE_URL}/api/notifications/user/${citizenId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching user notifications:', error);
    return [];
  }
},
```

### 5. **Corregir Dashboard con Datos Reales**

**Archivo:** `apps/frontend/src/lib/api.ts`

```typescript
// Línea 534-547: Reemplazar getDashboardStats con implementación real
async getDashboardStats() {
  try {
    const citizenId = session?.user?.id || '1234567890';
    
    // Obtener documentos del Ingestion Service
    const documents = await this.getDocuments(citizenId);
    const totalDocuments = documents.length;
    
    // Contar documentos firmados (filtrar por status === 'signed')
    const signedDocuments = documents.filter((doc: any) => doc.status === 'signed').length;
    
    // Obtener transferencias del Transfer Service
    const transfers = await this.getTransfers(citizenId);
    const pendingTransfers = transfers.filter((t: any) => t.status === 'pending').length;
    
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

## 📝 Variables de Entorno Faltantes

### Variables Necesarias en el Frontend

```bash
# Metadata Service
NEXT_PUBLIC_METADATA_SERVICE_URL=http://localhost:8007

# Notification Service
NEXT_PUBLIC_NOTIFICATION_SERVICE_URL=http://localhost:8008
```

### Configuración en Helm

**Archivo:** `deploy/helm/carpeta-ciudadana/templates/deployment-frontend.yaml`

Agregar después de la línea 68:

```yaml
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

---

## 🎯 Prioridades de Implementación

### 🔴 **CRÍTICO - Corregir Inmediatamente**
1. ✅ Corregir endpoints de Signature Service (falta `/api`)
2. ✅ Corregir tipos de datos (citizen_id como string)
3. ✅ Agregar campos requeridos en SignDocumentRequest

### 🟡 **ALTA - Implementar Pronto**
4. ✅ Agregar integración con Metadata Service
5. ✅ Agregar integración con Notification Service
6. ✅ Corregir Dashboard con datos reales
7. ✅ Crear página de firma de documentos

### 🟢 **MEDIA - Mejoras Futuras**
8. ⚠️ Crear página de búsqueda de documentos
9. ⚠️ Implementar notificaciones en tiempo real
10. ⚠️ Agregar filtros avanzados en listado de documentos

---

## 📊 Resumen de Estado

| Componente | Estado | Problemas | Acción Requerida |
|------------|--------|-----------|-----------------|
| Citizen Service | ✅ OK | Ninguno | - |
| Ingestion Service | ✅ OK | Ninguno | - |
| Transfer Service | ✅ OK | Ninguno | - |
| Auth Service | ✅ OK | Ninguno | - |
| Signature Service | ❌ ERROR | Endpoints mal configurados | Corregir URLs |
| Metadata Service | ❌ FALTA | No integrado | Agregar integración |
| Notification Service | ❌ FALTA | No integrado | Agregar integración |
| Dashboard | ⚠️ MOCK | Datos mock | Implementar datos reales |
| Firma Documentos | ❌ FALTA | No existe página | Crear página |

---

## 🔗 Referencias

- [Backend Endpoints Verification](./VERIFICACION_FUNCIONAL.md)
- [Architecture Analysis](./ANALISIS_ARQUITECTURA.md)
- [Signature Service README](../../services/signature/README.md)
- [Metadata Service README](../../services/metadata/README.md)
- [Notification Service README](../../services/notification/README.md)

---

**Última actualización:** 2025-11-06
**Autor:** Análisis Automático del Frontend


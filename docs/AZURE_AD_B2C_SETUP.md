# 🔐 Azure AD B2C Setup Guide

**Fecha**: 2025-10-12  
**Versión**: 1.0  
**Autor**: Manuel Jurado

Este documento detalla la configuración completa de Azure AD B2C para Carpeta Ciudadana.

---

## 📋 Índice

1. [Requisitos Previos](#requisitos-previos)
2. [Crear Tenant Azure AD B2C](#crear-tenant-azure-ad-b2c)
3. [Configurar User Flow](#configurar-user-flow)
4. [Registrar Aplicación](#registrar-aplicación)
5. [Configurar Custom Claims](#configurar-custom-claims)
6. [Configurar Frontend](#configurar-frontend)
7. [Configurar Backend](#configurar-backend)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

---

## 🔧 Requisitos Previos

- Suscripción activa de Azure
- Permisos de Administrador Global o similar
- Azure CLI instalado (opcional)
- Node.js 22+ instalado
- PostgreSQL configurado

---

## 1️⃣ Crear Tenant Azure AD B2C

### Paso 1.1: Crear Tenant en Azure Portal

1. Ir a [Azure Portal](https://portal.azure.com)
2. Buscar "Azure AD B2C"
3. Click en "Create a B2C tenant"
4. Seleccionar "Create a new Azure AD B2C Tenant"
5. Completar formulario:
   - **Organization name**: `Carpeta Ciudadana`
   - **Initial domain name**: `carpetaciudadana` (será `carpetaciudadana.onmicrosoft.com`)
   - **Country/Region**: `Colombia`
   - **Subscription**: Seleccionar tu suscripción
   - **Resource group**: Crear nuevo o usar existente
6. Click "Review + create"
7. Esperar creación (2-3 minutos)

### Paso 1.2: Cambiar a Tenant B2C

1. En Azure Portal, click en tu perfil (esquina superior derecha)
2. Click "Switch directory"
3. Seleccionar el tenant B2C recién creado

---

## 2️⃣ Configurar User Flow

### Paso 2.1: Crear Sign Up and Sign In Flow

1. En Azure AD B2C, ir a "User flows"
2. Click "+ New user flow"
3. Seleccionar "Sign up and sign in"
4. Seleccionar "Recommended" version
5. Configurar:
   - **Name**: `signupsignin1` (será `B2C_1_signupsignin1`)
   - **Identity providers**:
     - ✅ Email signup
     - ✅ Local account (opcional)
   - **Multifactor authentication**: Opcional (recomendado para producción)
   - **Conditional access**: Disabled (por ahora)
6. Click "Create"

### Paso 2.2: Configurar User Attributes

1. Ir a "User attributes and token claims"
2. **Collect attributes** (información pedida al registrarse):
   - ✅ Display Name
   - ✅ Given Name
   - ✅ Surname
   - ✅ Email Address
3. **Return claims** (incluir en JWT):
   - ✅ Display Name
   - ✅ Email Addresses
   - ✅ Given Name
   - ✅ Surname
   - ✅ User's Object ID
   - ✅ Identity Provider
4. Click "Save"

---

## 3️⃣ Registrar Aplicación

### Paso 3.1: Crear App Registration

1. En Azure AD B2C, ir a "App registrations"
2. Click "+ New registration"
3. Configurar:
   - **Name**: `Carpeta Ciudadana Frontend`
   - **Supported account types**: `Accounts in any identity provider or organizational directory (for authenticating users with user flows)`
   - **Redirect URI**:
     - Platform: `Web`
     - URI: `http://localhost:3000/api/auth/callback/azure-ad-b2c` (dev)
     - URI: `https://your-domain.com/api/auth/callback/azure-ad-b2c` (prod)
4. Click "Register"

### Paso 3.2: Generar Client Secret

1. En la aplicación registrada, ir a "Certificates & secrets"
2. Click "+ New client secret"
3. Configurar:
   - **Description**: `Frontend NextAuth`
   - **Expires**: `24 months` (recomendado)
4. Click "Add"
5. **⚠️ IMPORTANTE**: Copiar el `Value` (solo se muestra una vez)

### Paso 3.3: Configurar API Permissions

1. Ir a "API permissions"
2. Click "+ Add a permission"
3. Seleccionar "Microsoft Graph"
4. Seleccionar "Delegated permissions"
5. Agregar:
   - ✅ `openid`
   - ✅ `profile`
   - ✅ `email`
   - ✅ `offline_access`
6. Click "Add permissions"
7. Click "Grant admin consent" (requiere permisos de admin)

---

## 4️⃣ Configurar Custom Claims (Roles y Permissions)

### Paso 4.1: Crear Custom Attributes

1. En Azure AD B2C, ir a "User attributes"
2. Click "+ Add"
3. Crear atributo `Role`:
   - **Name**: `Role`
   - **Data type**: `String`
4. Crear atributo `Permissions`:
   - **Name**: `Permissions`
   - **Data type**: `StringCollection`
5. Click "Create"

### Paso 4.2: Incluir en User Flow

1. Ir a "User flows"
2. Seleccionar `B2C_1_signupsignin1`
3. Ir a "Application claims"
4. Marcar:
   - ✅ `extension_Role`
   - ✅ `extension_Permissions`
5. Click "Save"

**Nota**: Los custom attributes se retornan como `extension_Role` y `extension_Permissions` en el JWT.

---

## 5️⃣ Configurar Frontend

### Paso 5.1: Instalar Dependencias

```bash
cd apps/frontend
npm install next-auth jose
```

### Paso 5.2: Configurar Variables de Entorno

Crear archivo `.env.local`:

```env
# Azure AD B2C Configuration
AZURE_AD_B2C_TENANT_NAME=carpetaciudadana
AZURE_AD_B2C_TENANT_ID=your-tenant-id-here
AZURE_AD_B2C_CLIENT_ID=your-client-id-here
AZURE_AD_B2C_CLIENT_SECRET=your-client-secret-here
AZURE_AD_B2C_PRIMARY_USER_FLOW=B2C_1_signupsignin1

# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=$(openssl rand -base64 32)

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Cómo obtener los valores**:
- `TENANT_NAME`: Del paso 1.1 (ej: `carpetaciudadana`)
- `TENANT_ID`: Azure Portal → Azure AD B2C → Overview → Directory ID
- `CLIENT_ID`: Del paso 3.1 (Application (client) ID)
- `CLIENT_SECRET`: Del paso 3.2 (copiado del Value)
- `NEXTAUTH_SECRET`: Generar con `openssl rand -base64 32`

### Paso 5.3: Verificar Archivos Creados

Asegurarse de que existan:
- ✅ `src/app/api/auth/[...nextauth]/route.ts`
- ✅ `src/middleware.ts`
- ✅ `src/app/providers.tsx`
- ✅ `src/app/login/page.tsx`
- ✅ `src/types/next-auth.d.ts`

---

## 6️⃣ Configurar Backend

### Paso 6.1: Agregar Variables de Entorno

Agregar a los servicios backend (vía Kubernetes secrets):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: azure-b2c
  namespace: carpeta-ciudadana-dev
type: Opaque
stringData:
  AZURE_AD_B2C_TENANT_NAME: carpetaciudadana
  AZURE_AD_B2C_TENANT_ID: your-tenant-id
  AZURE_AD_B2C_CLIENT_ID: your-client-id
  AZURE_AD_B2C_PRIMARY_USER_FLOW: B2C_1_signupsignin1
```

### Paso 6.2: Instalar Dependencias Common

```bash
cd services/common
poetry add PyJWT[crypto] cryptography
```

### Paso 6.3: Usar JWT Validator

Ejemplo en un servicio:

```python
from fastapi import Depends
from carpeta_common.jwt_auth import get_current_user

@router.get("/protected")
async def protected_route(user: dict = Depends(get_current_user)):
    return {
        "user_id": user["sub"],
        "email": user["email"],
        "roles": user.get("extension_Role", [])
    }
```

---

## 7️⃣ Testing

### Paso 7.1: Testing Local

1. Iniciar frontend:
```bash
cd apps/frontend
npm run dev
```

2. Iniciar backend citizen service:
```bash
cd services/citizen
poetry run uvicorn app.main:app --reload --port 8001
```

3. Abrir navegador: `http://localhost:3000/login`
4. Click "Iniciar Sesión con Azure AD"
5. Registrarse o iniciar sesión
6. Verificar redirección a `/dashboard`
7. Verificar sesión en DevTools:
```javascript
// En consola del navegador
import { getSession } from "next-auth/react"
const session = await getSession()
console.log(session)
```

### Paso 7.2: Testing de API con JWT

```bash
# 1. Obtener token (desde frontend)
TOKEN="eyJhbGc..."  # Copiar de session.accessToken

# 2. Llamar API protegida
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8001/api/users/me

# Respuesta esperada:
# {
#   "id": "sub-claim-value",
#   "email": "user@example.com",
#   "roles": ["user"],
#   ...
# }
```

### Paso 7.3: Testing de Roles

1. Ir a Azure Portal → Azure AD B2C → Users
2. Seleccionar un usuario
3. Ir a "Extension attributes"
4. Agregar `extension_xxxxx_Role` = `["admin"]`
5. Logout y login nuevamente en frontend
6. Verificar acceso a `/admin` (debe permitir)

---

## 8️⃣ Production Deployment

### Paso 8.1: Agregar Redirect URIs de Producción

1. Azure Portal → App registrations → Tu app
2. Ir a "Authentication"
3. Click "+ Add a platform" → Web
4. Agregar:
   - `https://your-domain.com/api/auth/callback/azure-ad-b2c`
5. Click "Configure"

### Paso 8.2: Configurar CORS

Azure AD B2C permite cualquier origen por defecto. No requiere configuración adicional.

### Paso 8.3: Secrets en Kubernetes

```bash
# Crear secret en producción
kubectl create secret generic azure-b2c \
  --from-literal=AZURE_AD_B2C_TENANT_NAME=carpetaciudadana \
  --from-literal=AZURE_AD_B2C_TENANT_ID=$TENANT_ID \
  --from-literal=AZURE_AD_B2C_CLIENT_ID=$CLIENT_ID \
  --from-literal=AZURE_AD_B2C_CLIENT_SECRET=$CLIENT_SECRET \
  --namespace carpeta-ciudadana-prod
```

---

## 9️⃣ Troubleshooting

### Error: "AADB2C90118: The user has forgotten their password"

**Causa**: Usuario click en "Forgot password?" durante sign in.

**Solución**: Configurar "Password reset" user flow:
1. Azure AD B2C → User flows → + New user flow
2. Seleccionar "Password reset"
3. Name: `passwordreset1`
4. Configurar igual que sign up flow

### Error: "Invalid redirect URI"

**Causa**: Redirect URI no coincide con lo configurado en App Registration.

**Solución**:
1. Verificar NEXTAUTH_URL en `.env.local`
2. Verificar Redirect URIs en Azure Portal
3. Asegurarse de que coincidan exactamente

### Error: "Token validation failed"

**Causa**: Token expirado o inválido.

**Solución**:
1. Verificar que `AZURE_AD_B2C_CLIENT_ID` coincida entre frontend y backend
2. Verificar que JWKS endpoint sea accesible
3. Verificar logs del servicio para más detalles

### Error: "Cannot read custom claims"

**Causa**: Custom attributes no configurados en User Flow.

**Solución**:
1. Verificar que `extension_Role` y `extension_Permissions` estén marcados en "Application claims"
2. Re-login del usuario después de configurar

---

## 📚 Referencias

- [Azure AD B2C Documentation](https://learn.microsoft.com/en-us/azure/active-directory-b2c/)
- [NextAuth.js Azure AD B2C Provider](https://next-auth.js.org/providers/azure-ad-b2c)
- [JWT.io Debugger](https://jwt.io/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)

---

## ✅ Checklist de Implementación

- [ ] Tenant Azure AD B2C creado
- [ ] User flow `B2C_1_signupsignin1` configurado
- [ ] App registration creada
- [ ] Client secret generado y guardado
- [ ] Custom attributes creados (Role, Permissions)
- [ ] Frontend configurado (.env.local)
- [ ] Backend configurado (JWT validator)
- [ ] Tabla `users` creada en PostgreSQL
- [ ] Endpoint `/api/users/bootstrap` implementado
- [ ] Middleware de protección configurado
- [ ] Testing local exitoso
- [ ] Redirect URIs de producción agregados
- [ ] Secrets de Kubernetes creados

---

**Generado**: 2025-10-12 23:45  
**Autor**: Manuel Jurado  
**Versión**: 1.0


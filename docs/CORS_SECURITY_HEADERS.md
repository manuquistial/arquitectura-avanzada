# 🔒 CORS & Security Headers

**Configuración de Seguridad HTTP**

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Introducción](#introducción)
2. [CORS Restrictivo](#cors-restrictivo)
3. [Security Headers](#security-headers)
4. [Content Security Policy](#content-security-policy)
5. [Configuración](#configuración)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## 🎯 Introducción

La seguridad HTTP se implementa mediante:

1. **CORS (Cross-Origin Resource Sharing)**: Controla qué orígenes pueden acceder a la API
2. **Security Headers**: Headers HTTP que protegen contra ataques comunes
3. **CSP (Content Security Policy)**: Previene XSS y otros ataques de inyección

---

## 🌐 CORS Restrictivo

### ¿Qué es CORS?

**CORS** permite que recursos de un origen (dominio) sean solicitados desde otro origen.

**Sin CORS**:
```
Frontend (https://app.example.com)
    ↓
API (https://api.example.com)
    ↓
🚫 BLOCKED (different origin)
```

**Con CORS**:
```
Frontend (https://app.example.com)
    ↓
API (https://api.example.com)
    ↓
✅ ALLOWED (CORS configured)
```

### Configuración Restrictiva

#### Gateway (Python/FastAPI)

```python
from fastapi.middleware.cors import CORSMiddleware

# ❌ BAD: Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # INSECURE!
    allow_credentials=True
)

# ✅ GOOD: Restrictive origins
allowed_origins = [
    "https://carpeta.example.com",
    "https://app.carpeta.example.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Request-ID"
    ],
    expose_headers=["X-Request-ID"],
    max_age=3600  # Cache preflight for 1 hour
)
```

#### Frontend (Next.js)

Next.js no necesita CORS middleware (renderiza HTML), pero debe enviar requests a API con CORS headers correctos.

### CORS Preflight

**OPTIONS request** (preflight):
```http
OPTIONS /api/documents HTTP/1.1
Origin: https://app.example.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Authorization
```

**Response**:
```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Authorization
Access-Control-Max-Age: 3600
```

### Wildcard Subdomain

```python
# Allow all subdomains of example.com
allowed_origins = ["*.example.com"]

def validate_origin(origin: str) -> bool:
    if origin.endswith(".example.com"):
        return True
    return False
```

---

## 🛡️ Security Headers

### 1. X-Content-Type-Options

**Purpose**: Prevenir MIME sniffing

```http
X-Content-Type-Options: nosniff
```

**Protege contra**: Browser interpretando respuesta como tipo diferente (e.g., HTML como JS)

---

### 2. X-Frame-Options

**Purpose**: Prevenir clickjacking

```http
X-Frame-Options: DENY
```

**Options**:
- `DENY`: No permite iframes
- `SAMEORIGIN`: Permite iframes del mismo origen
- `ALLOW-FROM uri`: Permite URI específico (deprecated)

**Use Case**: Carpeta Ciudadana usa `DENY` (no necesita iframes)

---

### 3. X-XSS-Protection

**Purpose**: Enable browser XSS filter

```http
X-XSS-Protection: 1; mode=block
```

**Note**: Deprecated en favor de CSP, pero agregado para browsers antiguos

---

### 4. Strict-Transport-Security (HSTS)

**Purpose**: Forzar HTTPS

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Parámetros**:
- `max-age=31536000`: 1 año en segundos
- `includeSubDomains`: Aplicar a todos los subdominios
- `preload`: Incluir en HSTS preload list

**⚠️ Warning**: Solo usar en HTTPS. No usar en desarrollo HTTP.

---

### 5. Referrer-Policy

**Purpose**: Controlar información de referrer

```http
Referrer-Policy: strict-origin-when-cross-origin
```

**Options**:
- `no-referrer`: No enviar referrer
- `same-origin`: Solo para mismo origen
- `strict-origin-when-cross-origin`: URL completa para mismo origen, solo origen para cross-origin

---

### 6. Permissions-Policy

**Purpose**: Controlar browser features

```http
Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()
```

**Deshabilita**:
- Cámara
- Micrófono
- Geolocalización
- FLoC (Google privacy concern)

---

## 🔐 Content Security Policy

### ¿Qué es CSP?

**CSP** define qué recursos puede cargar la página, previniendo XSS attacks.

### Directivas Principales

#### default-src

```
default-src 'self'
```

Fuente predeterminada para todos los recursos.

#### script-src

```
script-src 'self' 'unsafe-inline' 'unsafe-eval'
```

**Options**:
- `'self'`: Solo scripts del mismo origen
- `'unsafe-inline'`: Permite `<script>` inline (⚠️ inseguro)
- `'unsafe-eval'`: Permite `eval()` (⚠️ inseguro)
- `'nonce-ABC123'`: Solo scripts con nonce específico
- `https://cdn.example.com`: CDN específico

**Frontend (Next.js)** requiere `unsafe-eval` para HMR y `unsafe-inline` para Tailwind.

#### style-src

```
style-src 'self' 'unsafe-inline'
```

**Tailwind CSS** requiere `unsafe-inline` para estilos generados.

#### connect-src

```
connect-src 'self' https://api.example.com https://*.b2clogin.com
```

Controla orígenes para fetch/XHR/WebSocket.

#### frame-src

```
frame-src 'self' https://*.b2clogin.com
```

Controla qué puede ser embebido en `<iframe>`.

**Azure B2C** requiere iframe para authentication flow.

#### frame-ancestors

```
frame-ancestors 'none'
```

Controla qué orígenes pueden embedar esta página.

**Carpeta Ciudadana**: `'none'` (no permite ser embebido)

#### object-src

```
object-src 'none'
```

Deshabilita `<object>`, `<embed>`, `<applet>` (legacy plugins).

### CSP Completo (Frontend)

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'unsafe-eval' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: blob: https:;
  font-src 'self' data:;
  connect-src 'self' https://*.b2clogin.com https://*.mintic.gov.co;
  frame-src 'self' https://*.b2clogin.com;
  frame-ancestors 'none';
  form-action 'self';
  base-uri 'self';
  object-src 'none';
  upgrade-insecure-requests
```

### CSP Completo (Backend API)

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self' data:;
  connect-src 'self';
  frame-ancestors 'none';
  form-action 'self';
  base-uri 'self';
  object-src 'none'
```

### CSP Report-Only Mode

Para testing sin bloquear:

```http
Content-Security-Policy-Report-Only: <policy>
```

Envía violations a report URI sin bloquear.

---

## ⚙️ Configuración

### Helm Values

```yaml
global:
  # CORS Configuration
  corsOrigins: "https://carpeta.example.com,https://app.carpeta.example.com"
  
  # Security Headers
  security:
    hstsEnabled: true          # HSTS (production only)
    cspEnabled: true           # Content Security Policy
    cspReportUri: ""           # CSP violation reporting (optional)
```

### Environment Variables (Gateway)

```bash
# CORS
CORS_ORIGINS="https://carpeta.example.com,https://app.carpeta.example.com"
CORS_ALLOW_CREDENTIALS="true"
CORS_ALLOW_METHODS="GET,POST,PUT,DELETE,PATCH,OPTIONS"
CORS_ALLOW_HEADERS="Content-Type,Authorization,X-Request-ID"
CORS_EXPOSE_HEADERS="X-Request-ID,X-RateLimit-Limit,X-RateLimit-Remaining"
CORS_MAX_AGE="3600"

# Security Headers
SECURITY_HEADERS_ENABLED="true"
HSTS_ENABLED="true"  # false in development
CSP_ENABLED="true"
CSP_REPORT_URI=""
```

### Next.js Configuration

```javascript
// next.config.js
const nextConfig = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload'
          },
          // ... other headers
        ]
      }
    ]
  }
}
```

---

## 🧪 Testing

### Test CORS

```bash
# Test preflight
curl -X OPTIONS http://localhost:8000/api/documents \
  -H "Origin: https://app.example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Authorization" \
  -v

# Check response headers:
# Access-Control-Allow-Origin: https://app.example.com
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE
```

### Test Security Headers

```bash
# Test security headers
curl -I http://localhost:8000/health

# Should include:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Content-Security-Policy: ...
```

### Test CSP

```bash
# Check CSP header
curl -I https://app.example.com | grep Content-Security-Policy
```

### Browser Testing

**Chrome DevTools**:
1. Open DevTools (F12)
2. Network tab
3. Make request
4. Check response headers
5. Security tab → View CSP violations

**CSP Validator**:
- https://csp-evaluator.withgoogle.com/

---

## 🔍 Troubleshooting

### CORS Blocked

**Symptom**: `Access-Control-Allow-Origin` error in browser

**Causes**:
1. Origin not in allowed list
2. Credentials=true but origin=*
3. Missing preflight headers

**Solutions**:
```bash
# Check allowed origins
echo $CORS_ORIGINS

# Add origin to allowed list
CORS_ORIGINS="https://app.example.com,https://new-app.example.com"

# Check browser origin
console.log(window.location.origin)
```

### CSP Violations

**Symptom**: Resources blocked, CSP errors in console

**Common violations**:
1. Inline scripts: `script-src 'unsafe-inline'` needed
2. eval(): `script-src 'unsafe-eval'` needed
3. External resources: Add domain to directive

**Solutions**:
```javascript
// Use nonce instead of unsafe-inline
<script nonce="ABC123">...</script>

// CSP with nonce
script-src 'self' 'nonce-ABC123'

// Or add specific domain
script-src 'self' https://cdn.example.com
```

### HSTS Too Strict

**Symptom**: Can't access site via HTTP even after removing HSTS

**Cause**: Browser cached HSTS policy

**Solutions**:
```
Chrome: chrome://net-internals/#hsts
- Query domain
- Delete domain security policies

Firefox: Clear browsing data → Active Logins
```

---

## ✅ Best Practices

### CORS

✅ **DO**:
- Whitelist specific origins
- Use credentials=true carefully
- Set max_age for preflight cache
- Log CORS rejections

❌ **DON'T**:
- Allow all origins (*)
- Allow credentials with *
- Allow all headers
- Ignore CORS in production

### CSP

✅ **DO**:
- Start with report-only mode
- Use nonces for inline scripts
- Whitelist specific CDNs
- Monitor violations

❌ **DON'T**:
- Use unsafe-inline/unsafe-eval unless necessary
- Allow all sources (*)
- Skip CSP in production
- Ignore violation reports

### HSTS

✅ **DO**:
- Use in production with HTTPS
- Set long max-age (1 year)
- Include preload
- Test before preload submission

❌ **DON'T**:
- Use in development (HTTP)
- Set short max-age (<6 months)
- Forget includeSubDomains
- Skip testing

---

## 📊 Security Headers Checklist

**Essential** (must have):
- [x] X-Content-Type-Options: nosniff
- [x] X-Frame-Options: DENY/SAMEORIGIN
- [x] X-XSS-Protection: 1; mode=block
- [x] Content-Security-Policy
- [x] Referrer-Policy

**Production** (HTTPS only):
- [x] Strict-Transport-Security (HSTS)

**Advanced**:
- [x] Permissions-Policy
- [x] X-Permitted-Cross-Domain-Policies

**Optional**:
- [ ] Public-Key-Pins (HPKP) - deprecated
- [ ] Expect-CT - deprecated

---

## 🔗 Tools

**Testing**:
- [SecurityHeaders.com](https://securityheaders.com/)
- [Mozilla Observatory](https://observatory.mozilla.org/)
- [CSP Evaluator](https://csp-evaluator.withgoogle.com/)

**Generators**:
- [CSP Builder](https://report-uri.com/home/generate)
- [HSTS Preload](https://hstspreload.org/)

---

## 📚 Referencias

- [MDN - CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [MDN - CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [OWASP - Security Headers](https://owasp.org/www-project-secure-headers/)
- [Scott Helme - Security Headers](https://scotthelme.co.uk/hardening-your-http-response-headers/)

---

## ✅ Resumen

**CORS Restrictivo**:
- ✅ Whitelist de orígenes específicos
- ✅ Credentials solo con orígenes explícitos
- ✅ Headers restrictivos
- ✅ Preflight caching

**Security Headers** (8):
1. ✅ X-Content-Type-Options: nosniff
2. ✅ X-Frame-Options: DENY
3. ✅ X-XSS-Protection: 1; mode=block
4. ✅ Strict-Transport-Security (HTTPS)
5. ✅ Content-Security-Policy
6. ✅ Referrer-Policy
7. ✅ Permissions-Policy
8. ✅ X-Permitted-Cross-Domain-Policies

**CSP**:
- ✅ Restrictive policy
- ✅ No unsafe-inline (when possible)
- ✅ Whitelist specific domains
- ✅ frame-ancestors 'none'
- ✅ object-src 'none'

**Estado**: 🟢 Production-ready

---

**Generado**: 2025-10-13 06:45  
**Autor**: Manuel Jurado  
**Versión**: 1.0

